-- Historico curto por thread (ultimas mensagens gravadas pelo backend LangGraph).
-- Nome com hifen: usar sempre aspas duplas em SQL: "memory-short"

CREATE TABLE IF NOT EXISTS "memory-short" (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_short_thread_created
    ON "memory-short" (thread_id, created_at DESC);
