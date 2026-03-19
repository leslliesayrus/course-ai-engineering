from fastapi import FastAPI
from pydantic import BaseModel

from agent import ask_agent


app = FastAPI(title="Agent SQL API")


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
