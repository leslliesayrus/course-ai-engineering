"""Persistencia de historico curto por thread_id na tabela \"memory-short\" (Postgres)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PgConnection

load_dotenv(Path(__file__).resolve().parent / ".env")

TABLE = '"memory-short"'
Role = Literal["user", "assistant"]


def _db_connect_kwargs() -> dict:
    """Mesmo padrao do docker-compose (postgres): DATABASE_URL ou POSTGRES_*."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "app_db"),
        "user": os.getenv("POSTGRES_USER", "app_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "app_password"),
    }


def _connect() -> PgConnection:
    kwargs = _db_connect_kwargs()
    if "dsn" in kwargs:
        return psycopg2.connect(kwargs["dsn"])
    return psycopg2.connect(**kwargs)


def fetch_last_messages(thread_id: str, limit: int = 10) -> list[tuple[Role, str]]:
    """Ultimas `limit` mensagens do thread, da mais antiga para a mais recente."""
    sql = (
        f"SELECT role, content FROM {TABLE} "
        "WHERE thread_id = %s ORDER BY created_at DESC LIMIT %s"
    )
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (thread_id, limit))
            rows = cur.fetchall()
    out: list[tuple[Role, str]] = []
    for role, content in reversed(rows):
        r = str(role).lower()
        if r == "user" or r == "assistant":
            out.append((r, content))
    return out


def insert_message(thread_id: str, role: Role, content: str) -> None:
    text = (content or "").strip()
    if not text:
        return
    sql = (
        f"INSERT INTO {TABLE} (thread_id, role, content) VALUES (%s, %s, %s)"
    )
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (thread_id, role, text))
        conn.commit()
