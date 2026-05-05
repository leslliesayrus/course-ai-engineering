from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import build_graph, close_checkpoint_pool, iter_public_chat_tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_checkpoint_pool()


app = FastAPI(title="Multiagent chat API", lifespan=lifespan)

_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": app.title,
        "health": "/health",
        "docs": "/docs",
        "chat": 'POST /chat  body: {"input": "...", "thread_id": "opcional"} — streaming text/plain',
        "checkpoint": "LangGraph em Postgres (env CHECKPOINT_DATABASE_URL ou DATABASE_URL; "
        "default alinhado ao docker-compose). USE_MEMORY_CHECKPOINTER=1 forca MemorySaver.",
    }


class ChatRequest(BaseModel):
    input: str = Field(description="Texto enviado ao fluxo (State.input)")
    thread_id: str = Field(default="default", description="ID do thread LangGraph (checkpoint)")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(payload: ChatRequest) -> StreamingResponse:
    graph = get_graph()

    def body():
        for token in iter_public_chat_tokens(
            graph,
            payload.input,
            thread_id=payload.thread_id.strip() or "default",
        ):
            yield token

    return StreamingResponse(body(), media_type="text/plain; charset=utf-8")
