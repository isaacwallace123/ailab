from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lab_status_assistant.proxmox import (
    ProxmoxClient,
    ProxmoxNodeConnector,
    ProxmoxSnapshotConnector,
)


def _fetcher(url: str):
    parsed = urlparse(url)
    if parsed.path.endswith("/nodes/cyberlab/status"):
        return {
            "data": {
                "cpu": 0.1,
                "memory": {"used": 20, "total": 100},
                "rootfs": {"used": 30, "total": 100},
                "pveversion": "pve-manager/9.2.4",
                "kversion": "Linux test",
            }
        }
    if parsed.path.endswith("/nodes/cyberlab/storage"):
        return {
            "data": [
                {
                    "storage": "local-lvm",
                    "type": "lvmthin",
                    "active": 1,
                    "enabled": 1,
                    "used": 20,
                    "total": 100,
                    "avail": 80,
                }
            ]
        }
    if parsed.path.endswith("/cluster/resources"):
        assert parse_qs(parsed.query) == {"type": ["vm"]}
        return {
            "data": [
                {
                    "node": "cyberlab",
                    "vmid": 9100,
                    "name": "cyb-gw-01",
                    "type": "qemu",
                    "status": "running",
                    "maxcpu": 2,
                    "maxmem": 4_000,
                },
                {
                    "node": "pve2",
                    "vmid": 100,
                    "name": "other-node",
                    "type": "qemu",
                    "status": "running",
                    "maxcpu": 2,
                    "maxmem": 4_000,
                },
            ]
        }
    raise AssertionError(f"Unexpected URL: {url}")


def _live_status():
    client = ProxmoxClient(
        "https://proxmox.test:8006",
        "status@pve!collector=secret",
        fetcher=_fetcher,
    )
    return ProxmoxNodeConnector(client, node="cyberlab").status()


def test_proxmox_connector_reports_capacity_and_filters_node() -> None:
    status = _live_status()

    assert status.state == "healthy"
    assert status.version == "pve-manager/9.2.4"
    assert len(status.storages) == 1
    assert [guest.name for guest in status.guests] == ["cyb-gw-01"]
    assert next(signal for signal in status.signals if signal.name == "memory_percent").value == 20
    assert next(signal for signal in status.signals if signal.name == "ai_node_present").state == (
        "unknown"
    )


def test_proxmox_connector_degrades_without_leaking_error() -> None:
    def failed_fetcher(_url: str):
        raise OSError("token=do-not-leak")

    client = ProxmoxClient(
        "https://proxmox.test:8006",
        "status@pve!collector=secret",
        fetcher=failed_fetcher,
    )
    status = ProxmoxNodeConnector(client, node="cyberlab").status()

    assert status.state == "unavailable"
    assert "do-not-leak" not in status.error


def test_stale_proxmox_snapshot_is_unavailable(tmp_path: Path) -> None:
    stale = _live_status().model_copy(
        update={"observed_at": datetime.now(UTC) - timedelta(minutes=10)}
    )
    snapshot_path = tmp_path / "proxmox.json"
    snapshot_path.write_text(stale.model_dump_json(), encoding="utf-8")

    status = ProxmoxSnapshotConnector(snapshot_path, max_age_seconds=300).status()

    assert status.state == "unavailable"
    assert status.error == "The Proxmox runtime snapshot is stale."
