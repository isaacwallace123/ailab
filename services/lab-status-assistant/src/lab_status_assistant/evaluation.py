from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .index import IndexedChunk, KnowledgeIndex
from .models import SearchResult
from .postgres import PostgresKnowledgeStore
from .settings import Settings


class ExpectedCitation(BaseModel):
    collection: str = Field(min_length=2)
    path: str = Field(min_length=1)
    max_rank: int = Field(default=5, ge=1, le=25)


class RetrievalCase(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    query: str = Field(min_length=2, max_length=500)
    collections: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)
    expected_citations: list[ExpectedCitation] = Field(min_length=1)


class EvaluationThresholds(BaseModel):
    hit_rate_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    citation_validity: float = Field(ge=0, le=1)


class RetrievalSuite(BaseModel):
    version: Literal[1]
    name: str = Field(min_length=1)
    description: str = ""
    thresholds: EvaluationThresholds
    cases: list[RetrievalCase] = Field(min_length=1)


class CaseEvaluation(BaseModel):
    id: str
    passed: bool
    first_relevant_rank: int | None
    missing_expectations: list[str]
    invalid_citations: int
    returned_citations: list[str]


class EvaluationMetrics(BaseModel):
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    citation_validity: float


class RetrievalReport(BaseModel):
    suite: str
    backend: str
    generated_at: datetime
    passed: bool
    passed_cases: int
    total_cases: int
    metrics: EvaluationMetrics
    thresholds: EvaluationThresholds
    cases: list[CaseEvaluation]


SearchFunction = Callable[[str, list[str] | None, int], list[SearchResult]]


def load_suite(path: Path) -> RetrievalSuite:
    with path.open(encoding="utf-8") as handle:
        return RetrievalSuite.model_validate(yaml.safe_load(handle))


def evaluate_suite(
    suite: RetrievalSuite,
    *,
    search: SearchFunction,
    indexed_chunks: list[IndexedChunk],
    backend: str,
) -> RetrievalReport:
    valid_citations = {
        (
            chunk.collection,
            chunk.relative_path,
            chunk.line_start,
            chunk.line_end,
            chunk.sha256,
        )
        for chunk in indexed_chunks
    }
    case_reports: list[CaseEvaluation] = []
    relevant_ranks: list[int | None] = []
    returned_count = 0
    invalid_count = 0

    for case in suite.cases:
        results = search(case.query, case.collections, case.top_k)
        returned_count += len(results)
        case_invalid = sum(
            (
                result.citation.collection,
                result.citation.path,
                result.citation.line_start,
                result.citation.line_end,
                result.citation.sha256,
            )
            not in valid_citations
            for result in results
        )
        invalid_count += case_invalid

        missing: list[str] = []
        matched_ranks: list[int] = []
        for expected in case.expected_citations:
            rank = next(
                (
                    rank
                    for rank, result in enumerate(results, start=1)
                    if result.citation.collection == expected.collection
                    and result.citation.path == expected.path
                ),
                None,
            )
            if rank is None or rank > expected.max_rank:
                missing.append(
                    f"{expected.collection}:{expected.path} within rank {expected.max_rank}"
                )
            else:
                matched_ranks.append(rank)

        first_relevant_rank = min(matched_ranks, default=None)
        relevant_ranks.append(first_relevant_rank)
        case_reports.append(
            CaseEvaluation(
                id=case.id,
                passed=not missing and case_invalid == 0,
                first_relevant_rank=first_relevant_rank,
                missing_expectations=missing,
                invalid_citations=case_invalid,
                returned_citations=[
                    f"{result.citation.collection}:{result.citation.path}" for result in results
                ],
            )
        )

    total_cases = len(case_reports)
    hit_rate = sum(rank is not None for rank in relevant_ranks) / total_cases
    mrr = sum(1 / rank if rank else 0 for rank in relevant_ranks) / total_cases
    citation_validity = 1.0 if returned_count == 0 else 1 - (invalid_count / returned_count)
    metrics = EvaluationMetrics(
        hit_rate_at_k=hit_rate,
        mean_reciprocal_rank=mrr,
        citation_validity=citation_validity,
    )
    passed = (
        all(case.passed for case in case_reports)
        and metrics.hit_rate_at_k >= suite.thresholds.hit_rate_at_k
        and metrics.mean_reciprocal_rank >= suite.thresholds.mean_reciprocal_rank
        and metrics.citation_validity >= suite.thresholds.citation_validity
    )
    return RetrievalReport(
        suite=suite.name,
        backend=backend,
        generated_at=datetime.now(UTC),
        passed=passed,
        passed_cases=sum(case.passed for case in case_reports),
        total_cases=total_cases,
        metrics=metrics,
        thresholds=suite.thresholds,
        cases=case_reports,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and citation quality.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--backend", choices=("memory", "postgres"), default="memory")
    args = parser.parse_args()

    settings = Settings.from_env()
    index = KnowledgeIndex(
        config_path=settings.source_config,
        max_file_bytes=settings.max_file_bytes,
        chunk_lines=settings.chunk_lines,
    )
    index.refresh()

    if args.backend == "postgres":
        if not settings.database_url:
            parser.error("AILAB_DATABASE_URL is required for the postgres backend")
        store = PostgresKnowledgeStore(settings.database_url)
        store.ensure_schema()
        store.sync(index.chunks, index.indexed_at)
        search = store.search
    else:
        search = index.search

    report = evaluate_suite(
        load_suite(args.dataset),
        search=search,
        indexed_chunks=index.chunks,
        backend=args.backend,
    )
    print(report.model_dump_json(indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
