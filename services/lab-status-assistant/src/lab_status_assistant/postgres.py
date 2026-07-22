from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import psycopg

from .embeddings import EmbeddingProvider
from .index import (
    _DOCUMENT_COVERAGE_BOOST,
    _SAME_DOCUMENT_PENALTY,
    _TARGET_DOCUMENT_PENALTY,
    IndexedChunk,
    _lexical_score,
    _matched_tokens,
    _query_tokens,
)
from .models import Citation, SearchResult

_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations (version) VALUES (1)
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id text PRIMARY KEY,
    collection text NOT NULL,
    relative_path text NOT NULL,
    heading text,
    line_start integer NOT NULL CHECK (line_start > 0),
    line_end integer NOT NULL CHECK (line_end >= line_start),
    content text NOT NULL,
    sha256 text NOT NULL,
    modified_at timestamptz NOT NULL,
    indexed_at timestamptz NOT NULL,
    embedding vector(384),
    embedding_model text,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(heading, '')), 'A') ||
        setweight(to_tsvector('simple', relative_path), 'B') ||
        setweight(to_tsvector('simple', content), 'C')
    ) STORED
);

ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_model text;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'knowledge_chunks'::regclass
          AND attname = 'embedding'
          AND format_type(atttypid, atttypmod) <> 'vector(384)'
    ) THEN
        ALTER TABLE knowledge_chunks
            ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS knowledge_chunks_collection_idx
    ON knowledge_chunks (collection);
CREATE INDEX IF NOT EXISTS knowledge_chunks_search_idx
    ON knowledge_chunks USING gin (search_vector);
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

INSERT INTO schema_migrations (version) VALUES (2)
ON CONFLICT (version) DO NOTHING;
"""

_UPSERT = """
INSERT INTO knowledge_chunks (
    chunk_id, collection, relative_path, heading, line_start, line_end,
    content, sha256, modified_at, indexed_at, embedding, embedding_model
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
ON CONFLICT (chunk_id) DO UPDATE SET
    heading = EXCLUDED.heading,
    content = EXCLUDED.content,
    modified_at = EXCLUDED.modified_at,
    indexed_at = EXCLUDED.indexed_at,
    embedding = COALESCE(EXCLUDED.embedding, knowledge_chunks.embedding),
    embedding_model = COALESCE(EXCLUDED.embedding_model, knowledge_chunks.embedding_model)
"""


def _chunk_id(chunk: IndexedChunk) -> str:
    identity = (
        f"{chunk.collection}:{chunk.relative_path}:{chunk.line_start}:"
        f"{chunk.line_end}:{chunk.sha256}"
    )
    return hashlib.sha256(identity.encode()).hexdigest()


def _snippet(content: str, tokens: list[str], max_length: int = 1200) -> str:
    normalized = " ".join(content.split())
    lowered = normalized.lower()
    positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
    start = max(min(positions, default=0) - 100, 0)
    snippet = normalized[start : start + max_length]
    if start:
        snippet = f"…{snippet}"
    if start + max_length < len(normalized):
        snippet = f"{snippet}…"
    return snippet


class PostgresKnowledgeStore:
    def __init__(
        self, database_url: str, embedding_provider: EmbeddingProvider | None = None
    ) -> None:
        self.database_url = database_url
        self.embedding_provider = embedding_provider
        if embedding_provider and embedding_provider.dimensions != 384:
            raise ValueError("The reviewed PostgreSQL embedding schema requires 384 dimensions")

    def _connect(self):
        return psycopg.connect(self.database_url, connect_timeout=5)

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(_SCHEMA)

    def sync(self, chunks: list[IndexedChunk], indexed_at: datetime) -> None:
        if not chunks:
            raise ValueError("Refusing to synchronize an empty knowledge index")

        embeddings: dict[str, list[float]] = {}
        if self.embedding_provider:
            chunk_ids = [_chunk_id(chunk) for chunk in chunks]
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT chunk_id FROM knowledge_chunks "
                    "WHERE chunk_id = ANY(%s) AND embedding IS NOT NULL "
                    "AND embedding_model = %s",
                    (chunk_ids, self.embedding_provider.model),
                ).fetchall()
            existing = {row[0] for row in rows}
            pending = [chunk for chunk in chunks if _chunk_id(chunk) not in existing]
            if pending:
                texts = [
                    f"{chunk.heading or ''}\n{chunk.relative_path}\n{chunk.content}".strip()
                    for chunk in pending
                ]
                vectors = self.embedding_provider.embed_documents(texts)
                if len(vectors) != len(pending):
                    raise ValueError("The embedding runtime returned an incomplete document batch")
                embeddings = {
                    _chunk_id(chunk): vector for chunk, vector in zip(pending, vectors, strict=True)
                }

        records = [
            (
                _chunk_id(chunk),
                chunk.collection,
                chunk.relative_path,
                chunk.heading,
                chunk.line_start,
                chunk.line_end,
                chunk.content,
                chunk.sha256,
                chunk.modified_at,
                indexed_at,
                _vector_literal(embeddings[_chunk_id(chunk)])
                if _chunk_id(chunk) in embeddings
                else None,
                self.embedding_provider.model
                if self.embedding_provider and _chunk_id(chunk) in embeddings
                else None,
            )
            for chunk in chunks
        ]
        seen = [(record[0],) for record in records]

        with self._connect() as connection, connection.transaction():
            connection.execute(
                "CREATE TEMP TABLE current_chunk_ids (chunk_id text PRIMARY KEY) ON COMMIT DROP"
            )
            with connection.cursor() as cursor:
                cursor.executemany(_UPSERT, records)
                cursor.executemany("INSERT INTO current_chunk_ids (chunk_id) VALUES (%s)", seen)
            connection.execute(
                "DELETE FROM knowledge_chunks "
                "WHERE chunk_id NOT IN (SELECT chunk_id FROM current_chunk_ids)"
            )

    def healthy(self) -> bool:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = 2)"
                ).fetchone()
                return bool(row and row[0])
        except psycopg.Error:
            return False

    def chunk_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT count(*) FROM knowledge_chunks").fetchone()
            return int(row[0]) if row else 0

    def search(self, query: str, collections: list[str] | None, limit: int) -> list[SearchResult]:
        tokens = _query_tokens(query)
        if not tokens:
            return []

        web_query = " OR ".join(f'"{token}"' for token in tokens)
        params: list[object] = [web_query]
        collection_filter = ""
        if collections:
            collection_filter = "AND collection = ANY(%s)"
            params.append(collections)
        candidate_limit = min(max(limit * 20, 100), 200)
        params.append(candidate_limit)

        statement = f"""
        WITH query AS (
            SELECT websearch_to_tsquery('simple', %s) AS value
        )
        SELECT
            collection,
            relative_path,
            heading,
            line_start,
            line_end,
            content,
            sha256
        FROM knowledge_chunks, query
        WHERE search_vector @@ query.value
          {collection_filter}
        ORDER BY ts_rank_cd(search_vector, query.value) DESC, relative_path, line_start
        LIMIT %s
        """

        with self._connect() as connection:
            lexical_rows = connection.execute(statement, params).fetchall()
            vector_scores: dict[tuple[str, str, int], float] = {}
            vector_rows: list[tuple] = []
            if self.embedding_provider:
                query_vector = _vector_literal(self.embedding_provider.embed_query(query))
                vector_params: list[object] = [query_vector, self.embedding_provider.model]
                vector_filter = ""
                if collections:
                    vector_filter = "AND collection = ANY(%s)"
                    vector_params.append(collections)
                vector_params.append(candidate_limit)
                vector_statement = f"""
                SELECT
                    collection,
                    relative_path,
                    heading,
                    line_start,
                    line_end,
                    content,
                    sha256,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_chunks
                WHERE embedding IS NOT NULL
                  AND embedding_model = %s
                  {vector_filter}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """
                vector_query_params = [*vector_params[:-1], query_vector, vector_params[-1]]
                vector_rows_with_score = connection.execute(
                    vector_statement, vector_query_params
                ).fetchall()
                vector_rows = [row[:7] for row in vector_rows_with_score]
                vector_scores = {
                    (row[0], row[1], row[3]): float(row[7]) for row in vector_rows_with_score
                }

        rows_by_key = {(row[0], row[1], row[3]): row for row in [*lexical_rows, *vector_rows]}
        rows = list(rows_by_key.values())

        document_matches: dict[tuple[str, str], set[str]] = {}
        for row in rows:
            key = (row[0], row[1])
            document_matches.setdefault(key, set()).update(
                _matched_tokens(
                    tokens=tokens,
                    content=row[5],
                    heading=row[2],
                    relative_path=row[1],
                )
            )

        ranked = []
        for row in rows:
            score = _lexical_score(
                query=query,
                tokens=tokens,
                content=row[5],
                heading=row[2],
                relative_path=row[1],
            )
            similarity = vector_scores.get((row[0], row[1], row[3]), 0.0)
            score += max(similarity - 0.25, 0.0) * 0.35
            document_coverage = len(document_matches[(row[0], row[1])]) / len(tokens)
            ranked.append((score + (document_coverage * _DOCUMENT_COVERAGE_BOOST), row))
        ranked.sort(key=lambda item: (-item[0], item[1][1], item[1][3]))
        path_occurrences: dict[tuple[str, str], int] = {}
        diversified: list[tuple[float, tuple]] = []
        for score, row in ranked:
            document_key = (row[0], row[1])
            occurrence = path_occurrences.get(document_key, 0)
            penalty = (
                _TARGET_DOCUMENT_PENALTY
                if Path(row[1]).stem.lower() in tokens
                else _SAME_DOCUMENT_PENALTY
            )
            diversified.append((score - (penalty * occurrence), row))
            path_occurrences[document_key] = occurrence + 1
        diversified.sort(key=lambda item: (-item[0], item[1][1], item[1][3]))

        return [
            SearchResult(
                score=score,
                snippet=_snippet(row[5], tokens),
                citation=Citation(
                    collection=row[0],
                    path=row[1],
                    heading=row[2],
                    line_start=row[3],
                    line_end=row[4],
                    sha256=row[6],
                ),
            )
            for score, row in diversified[:limit]
            if score > 0
        ]

    def embedding_status(self) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count(*), count(embedding), max(embedding_model) FROM knowledge_chunks"
            ).fetchone()
        return {
            "configured": self.embedding_provider is not None,
            "model": self.embedding_provider.model if self.embedding_provider else None,
            "total_chunks": int(row[0]) if row else 0,
            "embedded_chunks": int(row[1]) if row else 0,
            "stored_model": row[2] if row else None,
        }


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in vector) + "]"
