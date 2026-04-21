"""
Chainlit -> FastAPI backend (POST /chat).

Importante: uvicorn e Chainlit nao podem usar a mesma porta.
  - API: http://127.0.0.1:8000
  - Chat (Chainlit): http://127.0.0.1:8001

1) Backend:
   cd backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000

2) Frontend (defina CHAINLIT_PORT=8001 no frontend/.env OU use --port):
   cd frontend && chainlit run app.py -w --port 8001

Abra o chat em http://localhost:8001 — nao use :8000 (ali e so a API JSON).
"""

from __future__ import annotations

import os
from pathlib import Path

import chainlit as cl
import httpx
from dotenv import load_dotenv

# Carrega frontend/.env se existir
load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_API_BASE = "http://127.0.0.1:8000"
# Agente com varias tools (Pinecone + SQLite) pode demorar mais que o Market Agent.
CHAT_TIMEOUT = 180.0


def _api_base() -> str:
    return os.getenv("CHAT_API_BASE_URL", DEFAULT_API_BASE).rstrip("/")


@cl.on_chat_start
async def on_chat_start() -> None:
    await cl.Message(
        content=(
            "Ola! Sou o **PoD Academy Agent** — busco em resumos e titulos (Pinecone) e "
            "posso trazer a transcricao pelo video_id (SQLite). Como posso ajudar?"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = (message.content or "").strip()
    if not text:
        await cl.Message(content="Envie uma mensagem não vazia.").send()
        return

    url = f"{_api_base()}/chat"
    try:
        async with httpx.AsyncClient(timeout=CHAT_TIMEOUT) as client:
            response = await client.post(url, json={"message": text})
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        await cl.Message(
            content=(
                f"**Não foi possível conectar** em `{url}`.\n\n"
                "Confirme que o backend está rodando, por exemplo:\n"
                "`cd backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000`"
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

    reply = data.get("reply", "")
    if reply == "":
        await cl.Message(content="_(resposta vazia do backend)_").send()
    else:
        await cl.Message(content=reply).send()
