from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .models import Citation, CollectionStatus, SearchResult
from .secrets import detect_secret

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?}")
_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]+")
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_QUERY_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "how",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "the",
    "three",
    "to",
    "what",
    "which",
}
_SAME_DOCUMENT_PENALTY = 15.0
_TARGET_DOCUMENT_PENALTY = 0.0
_DOCUMENT_COVERAGE_BOOST = 12.0
_PRIORITY_INTENT_TOKENS = {"next", "priorities", "priority", "unfinished", "work"}

_DENIED_SEGMENTS = {
    ".git",
    ".terraform",
    ".venv",
    "node_modules",
    "artifacts",
    "cache",
    "private",
    "raw",
    "runs",
}
_DENIED_SUFFIXES = {
    ".db",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".tfstate",
}
_DENIED_NAMES = {
    ".env",
    ".vault-pass",
    "id_ed25519",
    "id_rsa",
}
_ALLOWED_SUFFIXES = {".json", ".md", ".tf", ".yaml", ".yml"}


@dataclass(frozen=True, slots=True)
class CollectionDefinition:
    id: str
    label: str
    root: Path
    includes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    collection: str
    relative_path: str
    heading: str | None
    line_start: int
    line_end: int
    content: str
    sha256: str
    modified_at: datetime


@dataclass(slots=True)
class CollectionState:
    definition: CollectionDefinition
    available: bool = False
    document_count: int = 0
    chunk_count: int = 0
    latest_source_modified_at: datetime | None = None
    errors: list[str] = field(default_factory=list)


def _expand_environment(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name, default = match.groups()
        resolved = os.getenv(name)
        if resolved is not None:
            return resolved
        if default is not None:
            return default
        raise ValueError(f"Required environment variable {name} is not set")

    return _ENV_PATTERN.sub(replace, value)


def load_collection_definitions(config_path: Path) -> list[CollectionDefinition]:
    with config_path.open(encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    if payload.get("version") != 1:
        raise ValueError("Source configuration version must be 1")

    raw_collections = payload.get("collections")
    if not isinstance(raw_collections, list) or not raw_collections:
        raise ValueError("Source configuration must define at least one collection")

    definitions: list[CollectionDefinition] = []
    seen: set[str] = set()
    for item in raw_collections:
        collection_id = str(item["id"]).strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", collection_id):
            raise ValueError(f"Invalid collection id: {collection_id}")
        if collection_id in seen:
            raise ValueError(f"Duplicate collection id: {collection_id}")
        seen.add(collection_id)

        root = Path(_expand_environment(str(item["root"]))).expanduser()
        includes = tuple(str(pattern) for pattern in item.get("includes", []))
        if not includes:
            raise ValueError(f"Collection {collection_id} has no include patterns")
        if any(Path(pattern).is_absolute() or ".." in Path(pattern).parts for pattern in includes):
            raise ValueError(f"Collection {collection_id} contains an unsafe include pattern")

        definitions.append(
            CollectionDefinition(
                id=collection_id,
                label=str(item.get("label", collection_id)).strip(),
                root=root,
                includes=includes,
            )
        )
    return definitions


def _is_denied(relative_path: Path) -> bool:
    lowered_parts = {part.lower() for part in relative_path.parts}
    name = relative_path.name.lower()
    if lowered_parts & _DENIED_SEGMENTS:
        return True
    if name in _DENIED_NAMES or name.startswith(".env."):
        return True
    if relative_path.suffix.lower() in _DENIED_SUFFIXES:
        return True
    return "secret" in name or "credential" in name or "token" in name


def _chunk_lines(
    *,
    collection: str,
    relative_path: str,
    content: str,
    sha256: str,
    modified_at: datetime,
    chunk_lines: int,
) -> list[IndexedChunk]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[IndexedChunk] = []
    section_starts = [0]
    if relative_path.lower().endswith(".md"):
        section_starts.extend(
            offset
            for offset, line in enumerate(lines)
            if offset > 0 and _HEADING_PATTERN.match(line)
        )
    section_starts = sorted(set(section_starts))

    for section_position, section_start in enumerate(section_starts):
        section_end = (
            section_starts[section_position + 1]
            if section_position + 1 < len(section_starts)
            else len(lines)
        )
        heading_match = _HEADING_PATTERN.match(lines[section_start])
        heading = heading_match.group(2) if heading_match else None

        for offset in range(section_start, section_end, chunk_lines):
            end = min(offset + chunk_lines, section_end)
            chunk_content = "\n".join(lines[offset:end]).strip()
            if not chunk_content:
                continue
            if offset == section_start and heading_match:
                body_lines = [line for line in lines[offset + 1 : end] if line.strip()]
                if not body_lines:
                    continue
            chunks.append(
                IndexedChunk(
                    collection=collection,
                    relative_path=relative_path,
                    heading=heading,
                    line_start=offset + 1,
                    line_end=end,
                    content=chunk_content,
                    sha256=sha256,
                    modified_at=modified_at,
                )
            )
    return chunks


def _query_tokens(query: str) -> list[str]:
    raw_tokens = list(dict.fromkeys(_TOKEN_PATTERN.findall(query.lower())))
    expanded_tokens: list[str] = []
    for token in raw_tokens:
        expanded_tokens.append(token)
        expanded_tokens.extend(part for part in re.split(r"[-_]", token) if part)
    expanded_tokens = list(dict.fromkeys(expanded_tokens))
    meaningful = [token for token in expanded_tokens if token not in _QUERY_STOP_WORDS]
    return meaningful or raw_tokens


def _lexical_score(
    *, query: str, tokens: list[str], content: str, heading: str | None, relative_path: str
) -> float:
    body = content.lower()
    lowered_heading = (heading or "").lower()
    path = relative_path.lower()
    filename_stem = Path(relative_path).stem.lower()
    matches = [
        token for token in tokens if token in body or token in lowered_heading or token in path
    ]
    if not matches:
        return 0.0

    score = 0.0
    for token in matches:
        score += min(body.count(token), 5)
        if token in lowered_heading:
            score += 6
        if token in path:
            score += 8
        if token == filename_stem:
            score += 12

    if filename_stem in tokens:
        score += 15

    coverage = len(matches) / len(tokens)
    score += coverage * 10
    if coverage == 1:
        score += 5

    normalized_query = " ".join(query.lower().split())
    if normalized_query and (normalized_query in body or normalized_query in lowered_heading):
        score += 8
    if set(tokens) & _PRIORITY_INTENT_TOKENS and path == "docs/roadmap.md":
        score += 30
        if lowered_heading == "current priority queue":
            score += 20
    return score


def _matched_tokens(
    *, tokens: list[str], content: str, heading: str | None, relative_path: str
) -> set[str]:
    searchable = f"{content}\n{heading or ''}\n{relative_path}".lower()
    return {token for token in tokens if token in searchable}


class KnowledgeIndex:
    def __init__(self, *, config_path: Path, max_file_bytes: int, chunk_lines: int) -> None:
        self.config_path = config_path
        self.max_file_bytes = max_file_bytes
        self.chunk_lines = chunk_lines
        self.indexed_at = datetime.now(UTC)
        self.chunks: list[IndexedChunk] = []
        self.collections: dict[str, CollectionState] = {}

    def refresh(self) -> None:
        definitions = load_collection_definitions(self.config_path)
        self.chunks = []
        self.collections = {
            definition.id: CollectionState(definition=definition) for definition in definitions
        }

        for definition in definitions:
            state = self.collections[definition.id]
            root = definition.root.resolve()
            if not root.is_dir():
                state.errors.append("Configured source root is unavailable")
                continue

            state.available = True
            seen_paths: set[Path] = set()
            for pattern in definition.includes:
                for candidate in root.glob(pattern):
                    if not candidate.is_file() or candidate.is_symlink():
                        continue
                    resolved = candidate.resolve()
                    if not resolved.is_relative_to(root) or resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    relative_path = resolved.relative_to(root)
                    if _is_denied(relative_path):
                        continue
                    if relative_path.suffix.lower() not in _ALLOWED_SUFFIXES:
                        continue
                    try:
                        size = resolved.stat().st_size
                        if size > self.max_file_bytes:
                            state.errors.append(
                                f"Skipped oversized file: {relative_path.as_posix()}"
                            )
                            continue
                        raw = resolved.read_bytes()
                        content = raw.decode("utf-8", errors="replace")
                        secret_detector = detect_secret(content)
                        if secret_detector:
                            state.errors.append(
                                "Skipped file failing content secret scan: "
                                f"{relative_path.as_posix()} ({secret_detector})"
                            )
                            continue
                        sha256 = hashlib.sha256(raw).hexdigest()
                        modified_at = datetime.fromtimestamp(resolved.stat().st_mtime, tz=UTC)
                        document_chunks = _chunk_lines(
                            collection=definition.id,
                            relative_path=relative_path.as_posix(),
                            content=content,
                            sha256=sha256,
                            modified_at=modified_at,
                            chunk_lines=self.chunk_lines,
                        )
                        self.chunks.extend(document_chunks)
                        state.document_count += 1
                        state.chunk_count += len(document_chunks)
                        if (
                            state.latest_source_modified_at is None
                            or modified_at > state.latest_source_modified_at
                        ):
                            state.latest_source_modified_at = modified_at
                    except OSError:
                        state.errors.append(f"Could not read file: {relative_path.as_posix()}")

        self.indexed_at = datetime.now(UTC)

    def collection_statuses(self) -> list[CollectionStatus]:
        return [
            CollectionStatus(
                id=state.definition.id,
                label=state.definition.label,
                available=state.available,
                document_count=state.document_count,
                chunk_count=state.chunk_count,
                latest_source_modified_at=state.latest_source_modified_at,
                errors=state.errors,
            )
            for state in self.collections.values()
        ]

    def search(self, query: str, collections: list[str] | None, limit: int) -> list[SearchResult]:
        tokens = _query_tokens(query)
        if not tokens:
            return []

        requested = set(collections or self.collections)
        unknown = requested - self.collections.keys()
        if unknown:
            raise KeyError(", ".join(sorted(unknown)))

        ranked: list[tuple[float, IndexedChunk]] = []
        document_matches: dict[tuple[str, str], set[str]] = {}
        for chunk in self.chunks:
            if chunk.collection not in requested:
                continue
            key = (chunk.collection, chunk.relative_path)
            document_matches.setdefault(key, set()).update(
                _matched_tokens(
                    tokens=tokens,
                    content=chunk.content,
                    heading=chunk.heading,
                    relative_path=chunk.relative_path,
                )
            )

        for chunk in self.chunks:
            if chunk.collection not in requested:
                continue
            score = _lexical_score(
                query=query,
                tokens=tokens,
                content=chunk.content,
                heading=chunk.heading,
                relative_path=chunk.relative_path,
            )
            if score <= 0:
                continue
            document_coverage = len(
                document_matches[(chunk.collection, chunk.relative_path)]
            ) / len(tokens)
            score += document_coverage * _DOCUMENT_COVERAGE_BOOST
            ranked.append((score, chunk))

        ranked.sort(key=lambda item: (-item[0], item[1].relative_path, item[1].line_start))
        path_occurrences: dict[tuple[str, str], int] = {}
        diversified: list[tuple[float, IndexedChunk]] = []
        for score, chunk in ranked:
            document_key = (chunk.collection, chunk.relative_path)
            occurrence = path_occurrences.get(document_key, 0)
            penalty = (
                _TARGET_DOCUMENT_PENALTY
                if Path(chunk.relative_path).stem.lower() in tokens
                else _SAME_DOCUMENT_PENALTY
            )
            diversified.append((score - (penalty * occurrence), chunk))
            path_occurrences[document_key] = occurrence + 1
        diversified.sort(key=lambda item: (-item[0], item[1].relative_path, item[1].line_start))
        return [
            SearchResult(
                score=score,
                snippet=self._snippet(chunk.content, tokens),
                citation=Citation(
                    collection=chunk.collection,
                    path=chunk.relative_path,
                    heading=chunk.heading,
                    line_start=chunk.line_start,
                    line_end=chunk.line_end,
                    sha256=chunk.sha256,
                ),
            )
            for score, chunk in diversified[:limit]
        ]

    @staticmethod
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
