"""
Chainlit -> FastAPI (POST /chat). Uvicorn e Chainlit nao podem dividir a mesma porta.

  API: http://127.0.0.1:8000
  Chat: http://127.0.0.1:8001  (ex.: chainlit run app.py -w --port 8001)

Backend:
  cd backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000

Frontend:
  cd frontend && chainlit run app.py -w --port 8001

CHAT_API_BASE_URL no .env aponta para a API (8000), nao para o Chainlit.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import chainlit as cl
import httpx
from dotenv import load_dotenv

# Carrega frontend/.env se existir
load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_API_BASE = "http://127.0.0.1:8000"
CHAT_TIMEOUT = 120.0


def _api_base() -> str:
    return os.getenv("CHAT_API_BASE_URL", DEFAULT_API_BASE).rstrip("/")


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    await cl.Message(
        content=(
            "Ola eu sou o **Market Agent AI**! Como eu posso te ajudar hoje?"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = (message.content or "").strip()
    if not text:
        await cl.Message(content="Envie uma mensagem não vazia.").send()
        return

    url = f"{_api_base()}/chat"
    thread_id = cl.user_session.get("thread_id") or str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    try:
        async with httpx.AsyncClient(timeout=CHAT_TIMEOUT) as client:
            async with client.stream(
                "POST",
                url,
                json={"input": text, "thread_id": thread_id},
            ) as response:
                response.raise_for_status()
                out = cl.Message(content="")
                await out.send()
                async for piece in response.aiter_text():
                    if piece:
                        await out.stream_token(piece)
                await out.update()
    except httpx.ConnectError:
        await cl.Message(
            content=(
                f"**Não foi possível conectar** em `{url}`.\n\n"
                "Confirme que o backend está rodando, por exemplo:\n"
                "`cd backend && uvicorn main:app --reload`"
            )
        ).send()
        return
    except httpx.HTTPStatusError as e:
        await cl.Message(
            content=(
                f"**Erro HTTP {e.response.status_code}** ao chamar o backend.\n\n"
                f"```\n{e.response.text[:2000]}\n```"
            )
        ).send()
        return
    except httpx.HTTPError as e:
        await cl.Message(content=f"**Erro na requisição:** {e!s}").send()
        return
