import os
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.config import get_config
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

from memory_short import fetch_last_messages, insert_message

dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Checkpointer Postgres (psycopg3) — mesmo stack que database/docker-compose.yaml
_default_pg_uri = (
    "postgresql://app_user:app_password@127.0.0.1:5432/app_db"
)

_checkpoint_pool: ConnectionPool | None = None
_checkpointer: PostgresSaver | MemorySaver | None = None


def _use_memory_checkpointer() -> bool:
    return os.getenv("USE_MEMORY_CHECKPOINTER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def get_checkpointer() -> PostgresSaver | MemorySaver:
    """PostgresSaver por defeito (Docker Postgres); MemorySaver se USE_MEMORY_CHECKPOINTER=1."""
    global _checkpoint_pool, _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    if _use_memory_checkpointer():
        _checkpointer = MemorySaver()
        return _checkpointer
    uri = (
        os.getenv("CHECKPOINT_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or _default_pg_uri
    )
    _checkpoint_pool = ConnectionPool(
        conninfo=uri,
        max_size=10,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )
    saver = PostgresSaver(_checkpoint_pool)
    saver.setup()
    _checkpointer = saver
    return _checkpointer


def close_checkpoint_pool() -> None:
    global _checkpoint_pool, _checkpointer
    if _checkpoint_pool is not None:
        _checkpoint_pool.close()
        _checkpoint_pool = None
    _checkpointer = None


groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY nao encontrado em backend/.env")

MODEL_NAME = "openai/gpt-oss-120b"
TEMPERATURE = 0.2

# LLM sem streaming para passos internos (menos ruido no stream_mode messages).
llm_internal = ChatGroq(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=groq_api_key,
    streaming=False,
)

# Mesmo modelo, com streaming para a resposta final exposta no /chat.
llm = ChatGroq(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    api_key=groq_api_key,
    streaming=True,
)

MAIN_LLM_NODE = "main_llm"

BLOCKED_USER_MESSAGE = (
    "Nao posso processar esta mensagem por motivos de seguranca. "
    "Reformule de forma adequada."
)


class State(TypedDict):
    input: str
    security: NotRequired[bool]
    improved_question: NotRequired[str]


class SecurityCheck(BaseModel):
    safe: bool = Field(description="Se o input e seguro (true) ou nao (false)")


def check_security(state: State) -> Command[Literal["improve_question", END]]:
    user_input = state["input"]
    structured_llm = llm_internal.with_structured_output(SecurityCheck)
    result = structured_llm.invoke(
        f"Analise se o seguinte input e seguro:\n{user_input}"
    )
    if not result.safe:
        return Command(update={"security": False}, goto=END)
    return Command(update={"security": True}, goto="improve_question")


def improve_question(state: State) -> Command[Literal[MAIN_LLM_NODE]]:
    user_input = state["input"]
    prompt = (
        "Melhore a clareza da pergunta ou mensagem do usuario.\n"
        "Responda APENAS com o texto reescrito, em uma unica linha ou paragrafo curto. "
        "Sem listas, sem numeracao, sem explicacoes.\n"
        f"Texto original:\n{user_input}"
    )
    result = llm_internal.invoke(prompt)
    text = result.content if isinstance(result.content, str) else str(result.content)
    improved = (text or "").strip() or user_input.strip()
    return Command(update={"improved_question": improved}, goto=MAIN_LLM_NODE)


def _build_main_prompt(
    history: list[tuple[str, str]], improved_question: str
) -> str:
    parts: list[str] = []
    if history:
        lines = [f"({role}): {text}" for role, text in history]
        parts.append("## Historico recente (mesma conversa)\n" + "\n".join(lines))
    parts.append("## Pergunta atual\n" + (improved_question or "").strip())
    return "\n\n".join(parts)


def main_llm(state: State) -> Command[Literal[END]]:
    cfg = get_config() or {}
    configurable = cfg.get("configurable") or {}
    thread_id = str(configurable.get("thread_id") or "default")

    user_question = (state.get("input") or "").strip()
    improved = (state.get("improved_question") or "").strip()

    history = fetch_last_messages(thread_id, limit=10)
    prompt = _build_main_prompt(history, improved)
    response = llm.invoke(prompt)

    answer = ""
    if isinstance(response.content, str):
        answer = response.content.strip()
    elif response.content is not None:
        answer = str(response.content).strip()

    if user_question:
        insert_message(thread_id, "user", user_question)
    if answer:
        insert_message(thread_id, "assistant", answer)

    return Command(update={}, goto=END)


def build_graph():
    graph = StateGraph(State)
    graph.add_node("check_security", check_security)
    graph.add_node("improve_question", improve_question)
    graph.add_node(MAIN_LLM_NODE, main_llm)
    graph.set_entry_point("check_security")
    return graph.compile(checkpointer=get_checkpointer())


def _message_content_piece(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def extract_stream_text_chunk(message: BaseMessage) -> str:
    """Somente texto visivel (AIMessage / AIMessageChunk), ignorando tool_calls."""
    if getattr(message, "tool_calls", None):
        return ""
    return _message_content_piece(getattr(message, "content", ""))


def _unpack_messages_stream_event(event: Any) -> tuple[BaseMessage, dict[str, Any]] | None:
    """Aceita evento v2 (dict) ou v1 (tupla) do stream_mode=[\"messages\"]."""
    if isinstance(event, dict) and event.get("type") == "messages":
        data = event.get("data")
        if isinstance(data, tuple) and len(data) >= 2 and isinstance(data[1], dict):
            msg, meta = data[0], data[1]
            if isinstance(msg, BaseMessage):
                return msg, meta
        return None
    if isinstance(event, tuple) and len(event) == 2:
        mode, data = event
        if mode == "messages" and isinstance(data, tuple) and len(data) >= 2:
            msg, meta = data[0], data[1]
            if isinstance(msg, BaseMessage) and isinstance(meta, dict):
                return msg, meta
    return None


def iter_public_chat_tokens(
    graph: Any,
    user_input: str,
    *,
    thread_id: str,
):
    """Yield apenas trechos nao vazios do campo content (AIMessageChunk) no no main_llm."""
    config = {"configurable": {"thread_id": thread_id}}
    text_in = (user_input or "").strip()
    if not text_in:
        return

    yielded = False
    for event in graph.stream(
        {"input": text_in},
        config=config,
        stream_mode=["messages"],
        version="v2",
    ):
        unpacked = _unpack_messages_stream_event(event)
        if unpacked is None:
            continue
        msg, meta = unpacked
        if meta.get("langgraph_node") != MAIN_LLM_NODE:
            continue
        # AIMessageChunk.type e a string "AIMessageChunk", nao "ai" — nao usar msg.type == "ai".
        if not isinstance(msg, AIMessageChunk):
            continue
        piece = extract_stream_text_chunk(msg)
        if piece:
            yielded = True
            yield piece

    if not yielded:
        snap = graph.get_state(config)
        values = getattr(snap, "values", None) or {}
        if values.get("security") is False:
            yield BLOCKED_USER_MESSAGE
