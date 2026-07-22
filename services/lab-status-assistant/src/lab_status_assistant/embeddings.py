from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_documents(self, documents: Iterable[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class FastEmbedProvider:
    """Small CPU embedding runtime backed by ONNX rather than a second GPU service."""

    def __init__(
        self,
        *,
        model: str,
        dimensions: int,
        cache_dir: Path,
        threads: int | None = None,
    ) -> None:
        from fastembed import TextEmbedding

        self.model = model
        self.dimensions = dimensions
        self._runtime = TextEmbedding(
            model_name=model,
            cache_dir=str(cache_dir),
            threads=threads,
            providers=["CPUExecutionProvider"],
        )

    def embed_documents(self, documents: Iterable[str]) -> list[list[float]]:
        vectors = [vector.tolist() for vector in self._runtime.passage_embed(documents)]
        self._validate(vectors)
        return vectors

    def embed_query(self, query: str) -> list[float]:
        vectors = [vector.tolist() for vector in self._runtime.query_embed(query)]
        self._validate(vectors)
        if len(vectors) != 1:
            raise ValueError("The embedding runtime did not return exactly one query vector")
        return vectors[0]

    def _validate(self, vectors: list[list[float]]) -> None:
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError(
                f"Embedding dimension mismatch for {self.model}; expected {self.dimensions}"
            )
