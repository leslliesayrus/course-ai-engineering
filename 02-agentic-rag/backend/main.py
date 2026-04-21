from fastapi import FastAPI
from pydantic import BaseModel

from agent import ask_agent

app = FastAPI(title="PoD Academy Agent API")


@app.get("/")
def root() -> dict[str, str]:
    """Evita 404 ao abrir http://127.0.0.1:8000 no navegador; o chat e via POST /chat."""
    return {
        "service": app.title,
        "health": "/health",
        "docs": "/docs",
        "chat": 'POST /chat  body: {"message": "sua pergunta"}',
    }


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    text = payload.message.strip()
    if not text:
        return ChatResponse(reply="")

    return ChatResponse(reply=ask_agent(text))
