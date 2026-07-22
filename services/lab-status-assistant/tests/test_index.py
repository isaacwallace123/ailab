from datetime import UTC, datetime
from pathlib import Path

from lab_status_assistant.index import KnowledgeIndex, _chunk_lines, _query_tokens


def test_markdown_chunks_follow_heading_boundaries() -> None:
    chunks = _chunk_lines(
        collection="ailab",
        relative_path="docs/roadmap.md",
        content=(
            "# AI Lab Roadmap\n\nOverview.\n\n"
            "## Phase 1: Retrieval\n\nImprove ranking.\n\n"
            "## Phase 2: MCP\n\nPublish read-only tools.\n"
        ),
        sha256="a" * 64,
        modified_at=datetime.now(UTC),
        chunk_lines=120,
    )

    assert [chunk.heading for chunk in chunks] == [
        "AI Lab Roadmap",
        "Phase 1: Retrieval",
        "Phase 2: MCP",
    ]
    assert [(chunk.line_start, chunk.line_end) for chunk in chunks] == [
        (1, 4),
        (5, 8),
        (9, 11),
    ]


def test_markdown_skips_heading_only_chunks() -> None:
    chunks = _chunk_lines(
        collection="ailab",
        relative_path="docs/roadmap.md",
        content="# AI Lab Roadmap\n\n## Current Priority Queue\n\n1. Build the core VM.\n",
        sha256="a" * 64,
        modified_at=datetime.now(UTC),
        chunk_lines=120,
    )

    assert [chunk.heading for chunk in chunks] == ["Current Priority Queue"]


def test_query_tokens_expand_compound_terms() -> None:
    tokens = _query_tokens("highest-priority ai-core roadmap")

    assert {"highest-priority", "highest", "priority", "ai-core", "ai", "core"} <= set(tokens)


def test_roadmap_query_prefers_roadmap_over_broad_architecture_docs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    docs = source / "docs"
    docs.mkdir(parents=True)
    (docs / "hardware-and-placement.md").write_text(
        "# Hardware And Placement\n\nThe AI lab has several remaining hardware decisions.\n",
        encoding="utf-8",
    )
    (docs / "roadmap.md").write_text(
        "# AI Lab Roadmap\n\n"
        "## Current Priority Queue\n\n"
        "These are the highest-priority unfinished items, in order.\n\n"
        "1. Build MCP.\n2. Evaluate retrieval.\n3. Add backups.\n\n"
        "## Phase 4: Unified AI Station\n\nStatus: in progress.\n",
        encoding="utf-8",
    )
    config = tmp_path / "sources.yaml"
    config.write_text(
        "\n".join(
            [
                "version: 1",
                "collections:",
                "  - id: ailab",
                "    label: AI Lab",
                f"    root: {source.as_posix()}",
                "    includes:",
                "      - 'docs/**/*.md'",
            ]
        ),
        encoding="utf-8",
    )

    index = KnowledgeIndex(config_path=config, max_file_bytes=10_000, chunk_lines=120)
    index.refresh()
    results = index.search(
        "What are the three highest-priority unfinished items in the AI lab roadmap?",
        ["ailab"],
        6,
    )

    assert results[0].citation.path == "docs/roadmap.md"
    assert results[0].citation.heading == "Current Priority Queue"
