import json
import os

import chainlit as cl
import httpx

# URL completa do POST /message do backend FastAPI (SSE).
BACKEND_MESSAGE_URL = os.environ.get(
    "BACKEND_MESSAGE_URL",
    "http://127.0.0.1:8000/message",
)


async def _apply_sse_event_lines(event_lines: list[str], assistant_msg: cl.Message) -> None:
    for raw in event_lines:
        line = raw.strip("\r")
        if line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].lstrip()
        if not payload or payload.strip() == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if obj.get("type") == "message":
            chunk = obj.get("content")
            if isinstance(chunk, str) and chunk != "":
                await assistant_msg.stream_token(chunk)


@cl.on_chat_start
async def on_chat_start() -> None:
    await cl.Message(
        content=(
            "Enviei sua mensagem para o backend configurado em **BACKEND_MESSAGE_URL** "
            f"(`{BACKEND_MESSAGE_URL}`). A resposta aparece em streaming."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    assistant_msg = cl.Message(content="")

    timeout = httpx.Timeout(120.0, connect=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                BACKEND_MESSAGE_URL,
                json={"message": message.content},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    snippet = body.decode(errors="replace")[:2000]
                    await cl.Message(
                        content=f"Erro HTTP {resp.status_code} do backend: {snippet}"
                    ).send()
                    return

                event_lines: list[str] = []
                async for line in resp.aiter_lines():
                    if line == "":
                        await _apply_sse_event_lines(event_lines, assistant_msg)
                        event_lines.clear()
                    else:
                        event_lines.append(line)

                if event_lines:
                    await _apply_sse_event_lines(event_lines, assistant_msg)

    except httpx.RequestError as e:
        await cl.Message(
            content=f"Não foi possível conectar ao backend em `{BACKEND_MESSAGE_URL}`: {e}"
        ).send()
        return

    await assistant_msg.update()
