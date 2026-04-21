# PoD Academy Agent

Assistente sobre os videos da PoD Academy: busca em **resumos** e **titulos** (Pinecone) e pode carregar a **transcricao completa** pelo `video_id` (SQLite).

Escreva sua pergunta no chat — a mensagem vai para o backend FastAPI (`POST /chat`).

- **API FastAPI:** `http://127.0.0.1:8000` → JSON com rotas (não é o chat).
- **Chat Chainlit:** `http://127.0.0.1:8001` → use **outra porta** que não seja a do `uvicorn` (ex.: `CHAINLIT_PORT=8001` no `frontend/.env` ou `chainlit run app.py -w --port 8001`). Se as duas usarem 8000, o Windows retorna erro **10048**.
