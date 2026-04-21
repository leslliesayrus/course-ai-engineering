import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import DEFAULT_SYSTEM_PROMPT
from tools import get_video_transcript, search_video_summaries, search_video_titles
#from langchain_ollama import ChatOllama
# Igual ao 01: prioriza backend/.env (copie as chaves do data-engineering se precisar).
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

_google_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
if not _google_key:
    raise ValueError("GOOGLE_API_KEY (ou GEMINI_API_KEY) nao encontrado em backend/.env")

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GOOGLE_GENAI_MODEL", "gemini-2.5-flash"),
    temperature=float(os.getenv("GOOGLE_GENAI_TEMPERATURE", "0.2")),
    google_api_key=_google_key,
)

# llm = ChatOllama(
#     model="qwen3.5:0.8b",
#     temperature=0,
#     base_url="http://localhost:11434"
# )

agent = create_agent(
    llm,
    tools=[search_video_summaries, search_video_titles, get_video_transcript],
)


def _text_from_ai_message(msg: AIMessage) -> str:
    """Gemini 2.x: string; Gemini 3+: lista de blocos com type/text."""
    content = msg.content
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        joined = "".join(parts).strip()
        if joined:
            return joined
    return ""


def ask_agent(user_message: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    result = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        }
    )

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _text_from_ai_message(msg)
            if text:
                return text

    return ""
