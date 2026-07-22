from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime

from lab_status_assistant.memory import _SCHEMA, PersonalMemoryStore
from lab_status_assistant.models import MemoryCreate


class _FakeConnection:
    def __init__(self) -> None:
        self.calls = []
        self.rows = []
        self.rowcount = 1

    def execute(self, query, parameters=None):
        self.calls.append((query, parameters))
        return self

    def fetchall(self):
        return self.rows


def _store(connection: _FakeConnection) -> PersonalMemoryStore:
    store = PersonalMemoryStore("postgresql://unused")
    store._connect = lambda: nullcontext(connection)
    return store


def test_memory_schema_archives_legacy_unscoped_rows() -> None:
    assert "user_id text" in _SCHEMA
    assert "legacy-unscoped" in _SCHEMA
    assert "assistant_memories_user_updated_idx" in _SCHEMA


def test_memory_writes_and_reads_are_user_scoped() -> None:
    connection = _FakeConnection()
    store = _store(connection)
    store.add("user-a", MemoryCreate(content="Prefers concise answers"))

    insert_parameters = connection.calls[-1][1]
    assert insert_parameters[1] == "user-a"

    now = datetime.now(UTC)
    connection.rows = [("memory-1", "fact", "Private A", "explicit-user-request", now, now)]
    memories = store.list("user-b", limit=5)

    assert connection.calls[-1][1] == ("user-b", 5)
    assert memories[0].content == "Private A"


def test_memory_delete_cannot_cross_user_boundary() -> None:
    connection = _FakeConnection()
    store = _store(connection)

    assert store.delete("user-a", "memory-owned-by-b") is True
    assert connection.calls[-1][1] == ("user-a", "memory-owned-by-b")
