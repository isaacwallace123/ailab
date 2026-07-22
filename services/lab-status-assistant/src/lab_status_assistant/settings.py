from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    api_token: str | None
    source_config: Path
    database_url: str | None = None
    prometheus_url: str | None = None
    prometheus_snapshot_path: Path | None = None
    prometheus_verify_tls: bool = True
    prometheus_timeout_seconds: float = 5.0
    prometheus_snapshot_max_age_seconds: float = 120.0
    kubernetes_snapshot_path: Path | None = None
    kubernetes_snapshot_max_age_seconds: float = 120.0
    proxmox_snapshot_path: Path | None = None
    proxmox_snapshot_max_age_seconds: float = 300.0
    max_file_bytes: int = 1_000_000
    chunk_lines: int = 120
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None
    assistant_model: str = "local-auto"
    assistant_timeout_seconds: float = 210.0
    assistant_knowledge_limit: int = 8
    embedding_model: str | None = None
    embedding_dimensions: int = 384
    embedding_cache_dir: Path = Path("models/cache/embeddings")
    embedding_threads: int | None = None
    assistant_profile_path: Path | None = None

    @classmethod
    def from_env(cls) -> Settings:
        environment = os.getenv("AILAB_ENVIRONMENT", "development").strip().lower()
        api_token = os.getenv("AILAB_API_TOKEN") or None
        source_config = Path(
            os.getenv("AILAB_SOURCE_CONFIG", "config/sources.local.yaml")
        ).expanduser()
        database_url = os.getenv("AILAB_DATABASE_URL") or None
        prometheus_url = os.getenv("AILAB_PROMETHEUS_URL") or None
        snapshot_value = os.getenv("AILAB_PROMETHEUS_SNAPSHOT_PATH") or None
        prometheus_snapshot_path = Path(snapshot_value) if snapshot_value else None
        prometheus_verify_tls = os.getenv("AILAB_PROMETHEUS_VERIFY_TLS", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        prometheus_timeout_seconds = float(os.getenv("AILAB_PROMETHEUS_TIMEOUT_SECONDS", "5"))
        prometheus_snapshot_max_age_seconds = float(
            os.getenv("AILAB_PROMETHEUS_SNAPSHOT_MAX_AGE_SECONDS", "120")
        )
        kubernetes_snapshot_value = os.getenv("AILAB_KUBERNETES_SNAPSHOT_PATH") or None
        kubernetes_snapshot_path = (
            Path(kubernetes_snapshot_value) if kubernetes_snapshot_value else None
        )
        kubernetes_snapshot_max_age_seconds = float(
            os.getenv("AILAB_KUBERNETES_SNAPSHOT_MAX_AGE_SECONDS", "120")
        )
        proxmox_snapshot_value = os.getenv("AILAB_PROXMOX_SNAPSHOT_PATH") or None
        proxmox_snapshot_path = Path(proxmox_snapshot_value) if proxmox_snapshot_value else None
        proxmox_snapshot_max_age_seconds = float(
            os.getenv("AILAB_PROXMOX_SNAPSHOT_MAX_AGE_SECONDS", "300")
        )
        max_file_bytes = int(os.getenv("AILAB_MAX_FILE_BYTES", "1000000"))
        chunk_lines = int(os.getenv("AILAB_CHUNK_LINES", "120"))
        litellm_api_base = os.getenv("AILAB_LITELLM_API_BASE") or None
        litellm_api_key = os.getenv("AILAB_LITELLM_API_KEY") or None
        assistant_model = os.getenv("AILAB_ASSISTANT_MODEL", "local-auto").strip()
        assistant_timeout_seconds = float(os.getenv("AILAB_ASSISTANT_TIMEOUT_SECONDS", "210"))
        assistant_knowledge_limit = int(os.getenv("AILAB_ASSISTANT_KNOWLEDGE_LIMIT", "8"))
        embedding_model = os.getenv("AILAB_EMBEDDING_MODEL") or None
        embedding_dimensions = int(os.getenv("AILAB_EMBEDDING_DIMENSIONS", "384"))
        embedding_cache_dir = Path(
            os.getenv("AILAB_EMBEDDING_CACHE_DIR", "models/cache/embeddings")
        ).expanduser()
        embedding_threads_value = os.getenv("AILAB_EMBEDDING_THREADS")
        embedding_threads = int(embedding_threads_value) if embedding_threads_value else None
        assistant_profile_value = os.getenv("AILAB_ASSISTANT_PROFILE_PATH") or None
        assistant_profile_path = Path(assistant_profile_value) if assistant_profile_value else None

        if environment not in {"development", "test", "production"}:
            raise ValueError("AILAB_ENVIRONMENT must be development, test, or production")
        if environment == "production" and not api_token:
            raise ValueError("AILAB_API_TOKEN is required in production")
        if max_file_bytes < 1:
            raise ValueError("AILAB_MAX_FILE_BYTES must be positive")
        if chunk_lines < 10:
            raise ValueError("AILAB_CHUNK_LINES must be at least 10")
        if prometheus_timeout_seconds <= 0:
            raise ValueError("AILAB_PROMETHEUS_TIMEOUT_SECONDS must be positive")
        if prometheus_snapshot_max_age_seconds <= 0:
            raise ValueError("AILAB_PROMETHEUS_SNAPSHOT_MAX_AGE_SECONDS must be positive")
        if kubernetes_snapshot_max_age_seconds <= 0:
            raise ValueError("AILAB_KUBERNETES_SNAPSHOT_MAX_AGE_SECONDS must be positive")
        if proxmox_snapshot_max_age_seconds <= 0:
            raise ValueError("AILAB_PROXMOX_SNAPSHOT_MAX_AGE_SECONDS must be positive")
        if bool(litellm_api_base) != bool(litellm_api_key):
            raise ValueError(
                "AILAB_LITELLM_API_BASE and AILAB_LITELLM_API_KEY must be configured together"
            )
        if assistant_model not in {"local-auto", "local-primary", "local-fast"}:
            raise ValueError("AILAB_ASSISTANT_MODEL must be a reviewed local model alias")
        if assistant_timeout_seconds <= 0:
            raise ValueError("AILAB_ASSISTANT_TIMEOUT_SECONDS must be positive")
        if not 1 <= assistant_knowledge_limit <= 12:
            raise ValueError("AILAB_ASSISTANT_KNOWLEDGE_LIMIT must be between 1 and 12")
        if embedding_dimensions < 1:
            raise ValueError("AILAB_EMBEDDING_DIMENSIONS must be positive")
        if embedding_threads is not None and embedding_threads < 1:
            raise ValueError("AILAB_EMBEDDING_THREADS must be positive when configured")

        return cls(
            environment=environment,
            api_token=api_token,
            source_config=source_config,
            database_url=database_url,
            prometheus_url=prometheus_url,
            prometheus_snapshot_path=prometheus_snapshot_path,
            prometheus_verify_tls=prometheus_verify_tls,
            prometheus_timeout_seconds=prometheus_timeout_seconds,
            prometheus_snapshot_max_age_seconds=prometheus_snapshot_max_age_seconds,
            kubernetes_snapshot_path=kubernetes_snapshot_path,
            kubernetes_snapshot_max_age_seconds=kubernetes_snapshot_max_age_seconds,
            proxmox_snapshot_path=proxmox_snapshot_path,
            proxmox_snapshot_max_age_seconds=proxmox_snapshot_max_age_seconds,
            max_file_bytes=max_file_bytes,
            chunk_lines=chunk_lines,
            litellm_api_base=litellm_api_base,
            litellm_api_key=litellm_api_key,
            assistant_model=assistant_model,
            assistant_timeout_seconds=assistant_timeout_seconds,
            assistant_knowledge_limit=assistant_knowledge_limit,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            embedding_cache_dir=embedding_cache_dir,
            embedding_threads=embedding_threads,
            assistant_profile_path=assistant_profile_path,
        )
