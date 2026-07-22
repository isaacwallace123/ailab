from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lab_status_assistant.prometheus import (
    PrometheusClient,
    PrometheusHomelabConnector,
    PrometheusSnapshotConnector,
)


def _successful_fetcher(url: str):
    parsed = urlparse(url)
    if parsed.path.endswith("/alerts"):
        return {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {"alertname": "DiskPressure", "severity": "warning"},
                        "annotations": {"summary": "A node disk is nearly full"},
                        "state": "firing",
                        "activeAt": "2026-07-18T04:50:07Z",
                    }
                ]
            },
        }

    expression = parse_qs(parsed.query)["query"][0]
    if expression == "count(count by (instance) (node_uname_info))":
        value = 3
    elif "node_cpu_seconds_total" in expression:
        value = 12
    elif "node_memory_MemAvailable_bytes" in expression:
        value = 55
    elif "node_filesystem_avail_bytes" in expression:
        value = 88
    elif expression == "count(up == 0)":
        value = 2
    else:
        raise AssertionError(f"Unexpected Prometheus expression: {expression}")
    return {
        "status": "success",
        "data": {"result": [{"value": [1_700_000_000, str(value)]}]},
    }


def test_runtime_status_uses_fixed_signals_and_alerts() -> None:
    client = PrometheusClient("http://prometheus.test", fetcher=_successful_fetcher)
    status = PrometheusHomelabConnector(client).status()

    assert status.state == "warning"
    assert status.source_type == "runtime"
    assert {signal.name for signal in status.signals} == {
        "observed_nodes",
        "max_cpu_percent",
        "max_memory_percent",
        "max_root_disk_percent",
        "down_targets",
    }
    assert next(signal for signal in status.signals if signal.name == "down_targets").value == 2
    assert status.alerts[0].name == "DiskPressure"
    assert any("separate read-only" in item for item in status.limitations)
    assert all("planned" not in item for item in status.limitations)


def test_runtime_status_degrades_safely_when_prometheus_is_unavailable() -> None:
    def unavailable_fetcher(url: str):
        raise OSError("connection failed")

    client = PrometheusClient("http://prometheus.test", fetcher=unavailable_fetcher)
    status = PrometheusHomelabConnector(client).status()

    assert status.state == "unavailable"
    assert status.signals == []
    assert "connection failed" not in status.error


def test_fresh_snapshot_preserves_status_and_marks_snapshot_source(tmp_path: Path) -> None:
    live = PrometheusHomelabConnector(
        PrometheusClient("http://prometheus.test", fetcher=_successful_fetcher)
    ).status()
    snapshot_path = tmp_path / "homelab.json"
    snapshot_path.write_text(live.model_dump_json(), encoding="utf-8")

    snapshot = PrometheusSnapshotConnector(snapshot_path, max_age_seconds=120).status()

    assert snapshot.state == "warning"
    assert snapshot.source == "prometheus-snapshot"
    assert any("host-collected" in limitation for limitation in snapshot.limitations)


def test_stale_snapshot_is_unavailable(tmp_path: Path) -> None:
    live = PrometheusHomelabConnector(
        PrometheusClient("http://prometheus.test", fetcher=_successful_fetcher)
    ).status()
    stale = live.model_copy(update={"observed_at": datetime.now(UTC) - timedelta(minutes=5)})
    snapshot_path = tmp_path / "homelab.json"
    snapshot_path.write_text(stale.model_dump_json(), encoding="utf-8")

    snapshot = PrometheusSnapshotConnector(snapshot_path, max_age_seconds=120).status()

    assert snapshot.state == "unavailable"
    assert snapshot.error == "The Prometheus runtime snapshot is stale."
