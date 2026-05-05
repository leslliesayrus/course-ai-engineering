from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class MessageRequest(BaseModel):
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/message")
def echo_message(payload: MessageRequest) -> dict[str, str]:
    return {"message": payload.message}
