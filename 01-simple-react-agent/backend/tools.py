import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from langchain.tools import tool

# Garante .env do backend mesmo se tools for importado antes do agent.py
load_dotenv(Path(__file__).resolve().parent / ".env")

_BACKEND_DIR = Path(__file__).resolve().parent
_METADATA_FILE = _BACKEND_DIR / "database_metadata.txt"
_MAX_RESULT_ROWS = 200


def _db_connect_kwargs() -> dict:
    """Parametros de conexao alinhados ao docker-compose (postgres) por padrao."""
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


@tool
def read_database_metadata() -> str:
    """Le o arquivo database_metadata.txt (esquema: tabelas, colunas, FKs) e retorna o texto completo.
    Use sempre antes de escrever SQL para garantir nomes corretos das tabelas e colunas."""
    try:
        if not _METADATA_FILE.is_file():
            return (
                f"ERRO: arquivo de metadata nao encontrado em {_METADATA_FILE}. "
                "Crie ou restaure database_metadata.txt no diretorio backend."
            )
        return _METADATA_FILE.read_text(encoding="utf-8")
    except OSError as e:
        return f"ERRO [leitura arquivo] [{type(e).__name__}]: {e}"


def _format_rows(colnames: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "(nenhuma linha retornada)"
    lines = []
    header = " | ".join(colnames)
    lines.append(header)
    lines.append("-" * min(len(header), 120))
    for row in rows:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
    return "\n".join(lines)


@tool
def execute_sql(sql: str) -> str:
    """Executa SQL no PostgreSQL. Retorna o resultado como string (linhas ou linhas afetadas).
    Se falhar (sintaxe, conexao, regra do banco), retorna somente a mensagem de erro para o modelo."""
    query = (sql or "").strip()
    if not query:
        return "SQL vazio."

    conn = None
    cur = None
    try:
        kwargs = _db_connect_kwargs()
        if "dsn" in kwargs:
            conn = psycopg2.connect(kwargs["dsn"])
        else:
            conn = psycopg2.connect(**kwargs)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query)

        if cur.description:
            colnames = [d[0] for d in cur.description]
            rows = cur.fetchmany(_MAX_RESULT_ROWS + 1)
            truncated = len(rows) > _MAX_RESULT_ROWS
            rows = rows[:_MAX_RESULT_ROWS]
            out = _format_rows(colnames, rows)
            if truncated:
                out += f"\n... (+ truncado; max {_MAX_RESULT_ROWS} linhas)"
            return out

        return str(cur.rowcount)

    except Exception as e:  # noqa: BLE001
        msg = str(e).strip() or repr(e)
        if getattr(e, "pgcode", None):
            msg = f"{msg} pgcode={e.pgcode}"
        return msg

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
