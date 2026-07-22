from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import LabRuntimeStatus, RuntimeAlert, RuntimeSignal

_QUERIES = {
    "observed_nodes": "count(count by (instance) (node_uname_info))",
    "max_cpu_percent": (
        'max(100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))'
    ),
    "max_memory_percent": (
        "max((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100)"
    ),
    "max_root_disk_percent": (
        'max((1 - (node_filesystem_avail_bytes{mountpoint="/",'
        'fstype!~"tmpfs|overlay|squashfs"} / '
        'node_filesystem_size_bytes{mountpoint="/",'
        'fstype!~"tmpfs|overlay|squashfs"})) * 100)'
    ),
    "down_targets": "count(up == 0)",
}


class PrometheusError(RuntimeError):
    pass


class PrometheusClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        verify_tls: bool = True,
        fetcher: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        normalized = base_url.rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("Prometheus URL must use http or https")
        self.base_url = normalized
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls
        self.fetcher = fetcher or self._fetch

    def _fetch(self, url: str) -> dict[str, Any]:
        context = None
        if url.startswith("https://"):
            context = ssl.create_default_context()
            if not self.verify_tls:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
        request = Request(url, headers={"User-Agent": "ailab-runtime-connector/0.1"})
        with urlopen(request, timeout=self.timeout_seconds, context=context) as response:
            return json.load(response)

    def _request(self, path: str, parameters: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(parameters)}" if parameters else ""
        payload = self.fetcher(f"{self.base_url}{path}{query}")
        if payload.get("status") != "success":
            raise PrometheusError("Prometheus returned a non-success response")
        return payload

    def scalar(self, expression: str) -> float | None:
        payload = self._request("/api/v1/query", {"query": expression})
        results = payload.get("data", {}).get("result", [])
        if not results:
            return None
        try:
            return float(results[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise PrometheusError("Prometheus returned an invalid query result") from error

    def active_alerts(self) -> list[RuntimeAlert]:
        payload = self._request("/api/v1/alerts")
        alerts: list[RuntimeAlert] = []
        for item in payload.get("data", {}).get("alerts", []):
            labels = item.get("labels", {})
            annotations = item.get("annotations", {})
            active_at = item.get("activeAt")
            alerts.append(
                RuntimeAlert(
                    name=str(labels.get("alertname", "UnnamedAlert")),
                    severity=str(labels.get("severity", "unknown")),
                    state=str(item.get("state", "unknown")),
                    active_at=active_at or None,
                    summary=str(annotations.get("summary", "No summary supplied")),
                )
            )
        return alerts


def _threshold_signal(
    name: str,
    value: float | None,
    *,
    unit: str | None,
    warning_at: float,
    critical_at: float,
    detail: str,
) -> RuntimeSignal:
    if value is None:
        state = "unknown"
    elif value >= critical_at:
        state = "critical"
    elif value >= warning_at:
        state = "warning"
    else:
        state = "healthy"
    return RuntimeSignal(name=name, state=state, value=value, unit=unit, detail=detail)


class PrometheusHomelabConnector:
    def __init__(self, client: PrometheusClient) -> None:
        self.client = client

    def status(self) -> LabRuntimeStatus:
        observed_at = datetime.now(UTC)
        limitations = [
            "Prometheus currently proves node-exporter, scrape-target, and alert state only.",
            (
                "Kubernetes and ArgoCD object health are provided by the separate read-only "
                "snapshot connector; this Prometheus source does not infer those states."
            ),
        ]
        try:
            values = {name: self.client.scalar(query) for name, query in _QUERIES.items()}
            alerts = self.client.active_alerts()
        except (OSError, TimeoutError, ValueError, PrometheusError):
            return LabRuntimeStatus(
                lab="homelab",
                state="unavailable",
                source="prometheus",
                observed_at=observed_at,
                signals=[],
                alerts=[],
                limitations=limitations,
                error="The Prometheus runtime source is unavailable or returned invalid data.",
            )

        observed_nodes = values["observed_nodes"]
        signals = [
            RuntimeSignal(
                name="observed_nodes",
                state=("healthy" if observed_nodes and observed_nodes > 0 else "warning"),
                value=observed_nodes,
                unit="nodes",
                detail="Nodes currently represented by node_uname_info.",
            ),
            _threshold_signal(
                "max_cpu_percent",
                values["max_cpu_percent"],
                unit="percent",
                warning_at=85,
                critical_at=95,
                detail="Highest five-minute CPU usage observed across nodes.",
            ),
            _threshold_signal(
                "max_memory_percent",
                values["max_memory_percent"],
                unit="percent",
                warning_at=85,
                critical_at=95,
                detail="Highest memory usage observed across nodes.",
            ),
            _threshold_signal(
                "max_root_disk_percent",
                values["max_root_disk_percent"],
                unit="percent",
                warning_at=80,
                critical_at=95,
                detail="Highest root filesystem usage observed across nodes.",
            ),
            _threshold_signal(
                "down_targets",
                values["down_targets"],
                unit="targets",
                warning_at=1,
                critical_at=10,
                detail="Prometheus scrape targets currently reporting down.",
            ),
        ]

        firing_alerts = [alert for alert in alerts if alert.state == "firing"]
        critical_alerts = [alert for alert in firing_alerts if alert.severity == "critical"]
        if critical_alerts or any(signal.state == "critical" for signal in signals):
            state = "critical"
        elif firing_alerts or any(signal.state == "warning" for signal in signals):
            state = "warning"
        else:
            state = "healthy"

        return LabRuntimeStatus(
            lab="homelab",
            state=state,
            source="prometheus",
            observed_at=observed_at,
            signals=signals,
            alerts=alerts,
            limitations=limitations,
        )


class PrometheusSnapshotConnector:
    def __init__(self, snapshot_path: Path, *, max_age_seconds: float = 120.0) -> None:
        self.snapshot_path = snapshot_path
        self.max_age_seconds = max_age_seconds

    def status(self) -> LabRuntimeStatus:
        now = datetime.now(UTC)
        try:
            snapshot = LabRuntimeStatus.model_validate_json(
                self.snapshot_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return LabRuntimeStatus(
                lab="homelab",
                state="unavailable",
                source="prometheus-snapshot",
                observed_at=now,
                signals=[],
                alerts=[],
                limitations=["The local Prometheus snapshot is missing or invalid."],
                error="No valid Prometheus runtime snapshot is available.",
            )

        age_seconds = (now - snapshot.observed_at).total_seconds()
        limitations = [
            *snapshot.limitations,
            "Docker Desktop consumes a host-collected read-only Prometheus snapshot.",
        ]
        if age_seconds > self.max_age_seconds:
            return snapshot.model_copy(
                update={
                    "state": "unavailable",
                    "source": "prometheus-snapshot",
                    "limitations": [
                        *limitations,
                        f"The snapshot is stale by policy ({age_seconds:.0f} seconds old).",
                    ],
                    "error": "The Prometheus runtime snapshot is stale.",
                }
            )
        return snapshot.model_copy(
            update={"source": "prometheus-snapshot", "limitations": limitations}
        )
