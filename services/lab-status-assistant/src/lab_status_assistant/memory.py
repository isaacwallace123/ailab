from __future__ import annotations

import uuid
from datetime import UTC, datetime

import psycopg

from .models import MemoryCreate, MemoryEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assistant_memories (
    memory_id text PRIMARY KEY,
    user_id text,
    kind text NOT NULL CHECK (kind IN ('preference', 'project', 'decision', 'task', 'fact')),
    content text NOT NULL,
    source text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
ALTER TABLE assistant_memories ADD COLUMN IF NOT EXISTS user_id text;
UPDATE assistant_memories SET user_id = 'legacy-unscoped' WHERE user_id IS NULL;
ALTER TABLE assistant_memories ALTER COLUMN user_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS assistant_memories_user_updated_idx
    ON assistant_memories (user_id, updated_at DESC);
"""


class PersonalMemoryStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, connect_timeout=5)

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(_SCHEMA)

    def add(self, user_id: str, request: MemoryCreate) -> MemoryEntry:
        now = datetime.now(UTC)
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            kind=request.kind,
            content=request.content.strip(),
            source=request.source,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assistant_memories "
                "(memory_id, user_id, kind, content, source, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    entry.id,
                    user_id,
                    entry.kind,
                    entry.content,
                    entry.source,
                    entry.created_at,
                    entry.updated_at,
                ),
            )
        return entry

    def list(self, user_id: str, limit: int = 20) -> list[MemoryEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT memory_id, kind, content, source, created_at, updated_at "
                "FROM assistant_memories WHERE user_id = %s "
                "ORDER BY updated_at DESC LIMIT %s",
                (user_id, limit),
            ).fetchall()
        return [
            MemoryEntry(
                id=row[0],
                kind=row[1],
                content=row[2],
                source=row[3],
                created_at=row[4],
                updated_at=row[5],
            )
            for row in rows
        ]

    def delete(self, user_id: str, memory_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM assistant_memories WHERE user_id = %s AND memory_id = %s",
                (user_id, memory_id),
            )
        return result.rowcount == 1
