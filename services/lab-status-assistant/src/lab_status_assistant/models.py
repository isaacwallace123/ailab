from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    collection: str
    path: str
    heading: str | None
    line_start: int
    line_end: int
    sha256: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    collections: list[str] | None = None
    limit: int = Field(default=8, ge=1, le=25)


class SearchResult(BaseModel):
    score: float
    snippet: str
    citation: Citation


class SearchResponse(BaseModel):
    query: str
    generated_at: datetime
    results: list[SearchResult]


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    collections: list[str] | None = None
    include_runtime: bool | None = None


class OpenAIChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class OpenAIChatRequest(BaseModel):
    model: str
    messages: list[OpenAIChatMessage] = Field(min_length=1, max_length=50)
    stream: bool = False


MemoryKind = Literal["preference", "project", "decision", "task", "fact"]


class MemoryCreate(BaseModel):
    kind: MemoryKind = "fact"
    content: str = Field(min_length=2, max_length=2000)
    source: str = Field(default="explicit-user-request", min_length=2, max_length=200)


class MemoryEntry(BaseModel):
    id: str
    kind: MemoryKind
    content: str
    source: str
    created_at: datetime
    updated_at: datetime


class AssistantEvidence(BaseModel):
    id: str
    source_type: Literal["knowledge", "runtime"]
    source: str
    observed_at: datetime
    excerpt: str
    citation: Citation | None = None


class AssistantResponse(BaseModel):
    question: str
    answer: str
    generated_at: datetime
    model: str
    citations: list[AssistantEvidence]


class CollectionStatus(BaseModel):
    id: str
    label: str
    available: bool
    document_count: int
    chunk_count: int
    latest_source_modified_at: datetime | None
    errors: list[str]


class DocumentationStatus(BaseModel):
    kind: str = "repository-documentation"
    live_infrastructure_status: bool = False
    warning: str = "This snapshot describes indexed repository content, not current runtime health."
    indexed_at: datetime
    collections: list[CollectionStatus]


class RuntimeSignal(BaseModel):
    name: str
    state: Literal["healthy", "warning", "critical", "unknown"]
    value: float | None
    unit: str | None = None
    detail: str


class RuntimeAlert(BaseModel):
    name: str
    severity: str
    state: str
    active_at: datetime | None
    summary: str


class LabRuntimeStatus(BaseModel):
    lab: str
    state: Literal["healthy", "warning", "critical", "unavailable", "unconfigured"]
    source_type: Literal["runtime"] = "runtime"
    source: str
    observed_at: datetime
    signals: list[RuntimeSignal]
    alerts: list[RuntimeAlert]
    limitations: list[str]
    error: str | None = None


class RuntimeIssue(BaseModel):
    kind: str
    severity: Literal["warning", "critical"]
    namespace: str | None = None
    name: str | None = None
    count: int = Field(default=1, ge=1)
    summary: str


class ArgoApplicationStatus(BaseModel):
    name: str
    project: str
    destination_namespace: str | None
    health: str
    sync: str
    reconciled_at: datetime | None


class KubernetesRuntimeStatus(BaseModel):
    lab: str = "homelab"
    state: Literal["healthy", "warning", "critical", "unavailable", "unconfigured"]
    source_type: Literal["runtime"] = "runtime"
    source: str
    observed_at: datetime
    signals: list[RuntimeSignal]
    applications: list[ArgoApplicationStatus]
    issues: list[RuntimeIssue]
    limitations: list[str]
    error: str | None = None


class ProxmoxStorageStatus(BaseModel):
    name: str
    storage_type: str
    active: bool
    enabled: bool
    total_bytes: int
    used_bytes: int
    available_bytes: int
    used_percent: float | None


class ProxmoxGuestStatus(BaseModel):
    vmid: int
    name: str
    guest_type: str
    status: str
    pool: str | None
    template: bool
    cpu_count: int
    memory_bytes: int


class ProxmoxRuntimeStatus(BaseModel):
    lab: str = "ailab"
    state: Literal["healthy", "warning", "critical", "unavailable", "unconfigured"]
    source_type: Literal["runtime"] = "runtime"
    source: str
    observed_at: datetime
    node: str
    version: str | None
    kernel: str | None
    signals: list[RuntimeSignal]
    storages: list[ProxmoxStorageStatus]
    guests: list[ProxmoxGuestStatus]
    limitations: list[str]
    error: str | None = None
