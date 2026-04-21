"""Ferramentas do agente: Pinecone (resumos + titulos) e SQLite (transcricao por video_id)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent
# Caminho fixo do banco gerado pelo ingest (nao usa variavel de ambiente).
SQLITE_VIDEOS_DB = (_REPO_ROOT / "data-engineering" / "videos.db").resolve()

_INDEX_SUMMARIES = "pod-academy"
_INDEX_TITLES = "titles-videos"

_MAX_TRANSCRIPT_CHARS = 200_000

_embeddings = None
_vs_summaries = None
_vs_titles = None


def _load_env() -> None:
    load_dotenv(_BACKEND_DIR / ".env")
    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(_REPO_ROOT / "data-engineering" / ".env", override=True)


def _ensure_rag() -> None:
    global _embeddings, _vs_summaries, _vs_titles
    if _vs_summaries is not None and _vs_titles is not None:
        return

    _load_env()
    key_google = os.environ.get("GOOGLE_API_KEY", "").strip()
    key_pc = os.environ.get("PINECONE_API_KEY", "").strip()
    if not key_google:
        raise RuntimeError("GOOGLE_API_KEY ausente no .env (necessario para embeddings).")
    if not key_pc:
        raise RuntimeError("PINECONE_API_KEY ausente no .env.")

    model = os.environ.get("GOOGLE_EMBEDDING_MODEL", "models/text-embedding-004")
    _embeddings = GoogleGenerativeAIEmbeddings(
        model=model,
        google_api_key=key_google,
    )
    _vs_summaries = PineconeVectorStore.from_existing_index(
        index_name=_INDEX_SUMMARIES,
        embedding=_embeddings,
    )
    _vs_titles = PineconeVectorStore.from_existing_index(
        index_name=_INDEX_TITLES,
        embedding=_embeddings,
    )


def _format_summary_hits(docs: list) -> str:
    lines: list[str] = []
    for i, doc in enumerate(docs, start=1):
        lines.append(f"--- Resultado {i} ---")
        lines.append(f"video_id: {doc.metadata.get('video_id', '')}")
        lines.append(f"video_title: {doc.metadata.get('video_title', '')}")
        lines.append(f"channel: {doc.metadata.get('channel', '')}")
        lines.append(f"resumo (trecho): {doc.page_content[:6000]}")
    return "\n".join(lines) if lines else "(nenhum resultado)"


def _format_title_hits(docs: list) -> str:
    lines: list[str] = []
    for i, doc in enumerate(docs, start=1):
        lines.append(f"--- Resultado {i} ---")
        lines.append(f"video_id: {doc.metadata.get('video_id', '')}")
        lines.append(f"titulo: {doc.page_content[:500]}")
    return "\n".join(lines) if lines else "(nenhum resultado)"


@tool
def search_video_summaries(query: str, k: int = 5) -> str:
    """Busca por similaridade nos RESUMOS dos videos (indice Pinecone pod-academy).
    Use para encontrar videos por tema, assunto ou ideias mencionadas nos resumos das transcricoes."""
    try:
        _ensure_rag()
    except RuntimeError as e:
        return f"ERRO: {e}"
    q = (query or "").strip()
    if not q:
        return "Informe uma consulta de texto nao vazia."
    k = max(1, min(int(k), 20))
    assert _vs_summaries is not None
    docs = _vs_summaries.similarity_search(q, k=k)
    return _format_summary_hits(docs)


@tool
def search_video_titles(query: str, k: int = 5) -> str:
    """Busca por similaridade nos TITULOS dos videos (indice Pinecone titles-videos).
    Use quando o usuario lembrar parte do nome do video ou quiser listar titulos parecidos."""
    try:
        _ensure_rag()
    except RuntimeError as e:
        return f"ERRO: {e}"
    q = (query or "").strip()
    if not q:
        return "Informe uma consulta de texto nao vazia."
    k = max(1, min(int(k), 20))
    assert _vs_titles is not None
    docs = _vs_titles.similarity_search(q, k=k)
    return _format_title_hits(docs)


@tool
def get_video_transcript(video_id: str) -> str:
    """Retorna o texto completo da transcricao (conteudo) de um video pelo video_id do YouTube.
    Use depois de saber o video_id, para citar ou analisar o que foi dito na integra."""
    _load_env()
    vid = (video_id or "").strip()
    if not vid:
        return "video_id vazio."
    if not SQLITE_VIDEOS_DB.is_file():
        return (
            f"ERRO: banco SQLite nao encontrado em {SQLITE_VIDEOS_DB}. "
            "Rode o ingest_pipeline.py antes."
        )

    conn = sqlite3.connect(SQLITE_VIDEOS_DB)
    try:
        cur = conn.execute(
            "SELECT channel, video_title, video_id, content FROM videos WHERE video_id = ?",
            (vid,),
        )
        row = cur.fetchone()
        if not row:
            return f"Nenhum video com video_id={vid!r} no banco."
        channel, title, v_id, content = row
        content = content or ""
        truncated = ""
        if len(content) > _MAX_TRANSCRIPT_CHARS:
            truncated = f"\n\n[AVISO: transcricao truncada; total {len(content)} caracteres, mostrando {_MAX_TRANSCRIPT_CHARS}]"
            content = content[:_MAX_TRANSCRIPT_CHARS]
        return (
            f"channel: {channel}\n"
            f"video_title: {title}\n"
            f"video_id: {v_id}\n"
            f"--- transcricao ---\n{content}{truncated}"
        )
    except Exception as e:  # noqa: BLE001
        return f"ERRO SQLite: {e}"
    finally:
        conn.close()
