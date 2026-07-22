from datetime import UTC, datetime

from lab_status_assistant.evaluation import (
    EvaluationThresholds,
    ExpectedCitation,
    RetrievalCase,
    RetrievalSuite,
    evaluate_suite,
)
from lab_status_assistant.index import IndexedChunk
from lab_status_assistant.models import Citation, SearchResult


def _chunk(path: str = "docs/architecture.md") -> IndexedChunk:
    return IndexedChunk(
        collection="ailab",
        relative_path=path,
        heading="Architecture",
        line_start=1,
        line_end=10,
        content="The AI lab uses read-only integrations.",
        sha256="a" * 64,
        modified_at=datetime.now(UTC),
    )


def _suite() -> RetrievalSuite:
    return RetrievalSuite(
        version=1,
        name="test-suite",
        thresholds=EvaluationThresholds(
            hit_rate_at_k=1.0,
            mean_reciprocal_rank=1.0,
            citation_validity=1.0,
        ),
        cases=[
            RetrievalCase(
                id="architecture",
                query="read-only integrations",
                expected_citations=[
                    ExpectedCitation(collection="ailab", path="docs/architecture.md", max_rank=1)
                ],
            )
        ],
    )


def test_evaluation_passes_relevant_valid_citation() -> None:
    chunk = _chunk()
    result = SearchResult(
        score=1,
        snippet=chunk.content,
        citation=Citation(
            collection=chunk.collection,
            path=chunk.relative_path,
            heading=chunk.heading,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            sha256=chunk.sha256,
        ),
    )

    report = evaluate_suite(
        _suite(),
        search=lambda _query, _collections, _limit: [result],
        indexed_chunks=[chunk],
        backend="test",
    )

    assert report.passed is True
    assert report.metrics.hit_rate_at_k == 1
    assert report.metrics.mean_reciprocal_rank == 1
    assert report.metrics.citation_validity == 1


def test_evaluation_rejects_tampered_citation() -> None:
    chunk = _chunk()
    result = SearchResult(
        score=1,
        snippet=chunk.content,
        citation=Citation(
            collection=chunk.collection,
            path=chunk.relative_path,
            heading=chunk.heading,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            sha256="b" * 64,
        ),
    )

    report = evaluate_suite(
        _suite(),
        search=lambda _query, _collections, _limit: [result],
        indexed_chunks=[chunk],
        backend="test",
    )

    assert report.passed is False
    assert report.metrics.citation_validity == 0
    assert report.cases[0].invalid_citations == 1
