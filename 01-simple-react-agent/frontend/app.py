"""
Chainlit UI que encaminha mensagens para o FastAPI em backend/main.py (POST /chat).

Rodar o backend antes:
  cd backend && uvicorn main:app --reload

Rodar o frontend:
  cd frontend && chainlit run app.py -w

Opcional: definir CHAT_API_BASE_URL no .env (mesma pasta do app) ou no ambiente.
Ex.: CHAT_API_BASE_URL=http://127.0.0.1:8000
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
CHAT_TIMEOUT = 120.0


def _api_base() -> str:
    return os.getenv("CHAT_API_BASE_URL", DEFAULT_API_BASE).rstrip("/")


@cl.on_chat_start
async def on_chat_start() -> None:
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

    reply = data.get("reply", "")
    if reply == "":
        await cl.Message(content="_(resposta vazia do backend)_").send()
    else:
        await cl.Message(content=reply).send()
