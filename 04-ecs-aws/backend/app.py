import json
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_groq import ChatGroq
from pydantic import BaseModel

app = FastAPI()

GROQ_SECRET_ID = "groq-key"
GROQ_SECRET_JSON_KEY = "GROQ-API-KEY"
GROQ_MODEL = "llama-3.3-70b-versatile"

_llm: ChatGroq | None = None


class MessageRequest(BaseModel):
    message: str


def _secrets_manager_client():
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("secretsmanager", region_name=region)


def _load_groq_api_key() -> str:
    try:
        response = _secrets_manager_client().get_secret_value(SecretId=GROQ_SECRET_ID)
    except ClientError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read secret {GROQ_SECRET_ID} from Secrets Manager.",
        ) from e
    raw = response.get("SecretString")
    if not raw:
        raise HTTPException(status_code=503, detail=f"Secret {GROQ_SECRET_ID} has no SecretString.")

    payload = json.loads(raw)
    key = payload.get(GROQ_SECRET_JSON_KEY)
    if not key or not isinstance(key, str):
        raise HTTPException(
            status_code=503,
            detail=f"Secret {GROQ_SECRET_ID} missing string key {GROQ_SECRET_JSON_KEY}.",
        )
    return key


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is not None:
        return _llm
    api_key = _load_groq_api_key()
    _llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0.7,
        groq_api_key=api_key,
    )
    return _llm


def _sse_data_line(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def groq_message_stream_events(user_message: str):
    llm = _get_llm()
    for token in llm.stream(user_message):
        content = getattr(token, "content", None)
        if isinstance(content, str) and content != "":
            yield _sse_data_line({"type": "message", "content": content})

    yield _sse_data_line({"type": "done"})


@app.post("/message")
def message_endpoint(payload: MessageRequest) -> StreamingResponse:
    # Fail fast before streaming so the client gets a proper HTTP error.
    try:
        _get_llm()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Could not initialize Groq client.") from e

    return StreamingResponse(
        groq_message_stream_events(payload.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
