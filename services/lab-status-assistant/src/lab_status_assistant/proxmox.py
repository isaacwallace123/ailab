from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .models import (
    ProxmoxGuestStatus,
    ProxmoxRuntimeStatus,
    ProxmoxStorageStatus,
    RuntimeSignal,
)


class ProxmoxError(RuntimeError):
    pass


class ProxmoxClient:
    def __init__(
        self,
        endpoint: str,
        api_token: str,
        *,
        timeout_seconds: float = 10.0,
        verify_tls: bool = True,
        fetcher: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        normalized = endpoint.rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("Proxmox endpoint must use https")
        if "!" not in api_token or "=" not in api_token:
            raise ValueError("Proxmox API token has an invalid format")
        self.endpoint = normalized
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls
        self.fetcher = fetcher or self._fetch

    def _fetch(self, url: str) -> dict[str, Any]:
        context = ssl.create_default_context()
        if not self.verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        request = Request(
            url,
            headers={
                "Authorization": f"PVEAPIToken={self.api_token}",
                "User-Agent": "ailab-proxmox-collector/0.1",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds, context=context) as response:
            return json.load(response)

    def get(self, path: str, parameters: dict[str, str] | None = None) -> Any:
        query = f"?{urlencode(parameters)}" if parameters else ""
        payload = self.fetcher(f"{self.endpoint}/api2/json{path}{query}")
        if "data" not in payload:
            raise ProxmoxError("Proxmox returned an invalid API response")
        return payload["data"]


def _percent(used: int | float, total: int | float) -> float | None:
    return (float(used) / float(total) * 100) if total else None


def _pressure_signal(
    name: str,
    value: float | None,
    *,
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
    return RuntimeSignal(
        name=name,
        state=state,
        value=value,
        unit="percent",
        detail=detail,
    )


class ProxmoxNodeConnector:
    def __init__(self, client: ProxmoxClient, *, node: str) -> None:
        self.client = client
        self.node = node

    def status(self) -> ProxmoxRuntimeStatus:
        observed_at = datetime.now(UTC)
        limitations = [
            "The PVEAuditor collector is read-only and cannot create or modify guests.",
            (
                "Guest names and capacity are private operational data; raw snapshots are "
                "ignored by Git."
            ),
            (
                "PCI/IOMMU discovery remains a separate root-reviewed collection because the "
                "API denied it."
            ),
        ]
        encoded_node = quote(self.node, safe="")
        try:
            node_status = self.client.get(f"/nodes/{encoded_node}/status")
            storage_payload = self.client.get(f"/nodes/{encoded_node}/storage")
            resource_payload = self.client.get("/cluster/resources", {"type": "vm"})
            if not isinstance(node_status, dict):
                raise ProxmoxError("Proxmox returned invalid node status")
            if not isinstance(storage_payload, list) or not isinstance(resource_payload, list):
                raise ProxmoxError("Proxmox returned invalid inventory data")
        except (OSError, TimeoutError, ValueError, ProxmoxError):
            return ProxmoxRuntimeStatus(
                state="unavailable",
                source="proxmox-api",
                observed_at=observed_at,
                node=self.node,
                version=None,
                kernel=None,
                signals=[],
                storages=[],
                guests=[],
                limitations=limitations,
                error="The Proxmox runtime source is unavailable or returned invalid data.",
            )

        memory = node_status.get("memory", {})
        rootfs = node_status.get("rootfs", {})
        cpu_percent = float(node_status.get("cpu", 0)) * 100
        memory_percent = _percent(memory.get("used", 0), memory.get("total", 0))
        root_percent = _percent(rootfs.get("used", 0), rootfs.get("total", 0))

        storages = [
            ProxmoxStorageStatus(
                name=str(item.get("storage", "unknown")),
                storage_type=str(item.get("type", "unknown")),
                active=bool(item.get("active", 0)),
                enabled=bool(item.get("enabled", 1)),
                total_bytes=int(item.get("total", 0) or 0),
                used_bytes=int(item.get("used", 0) or 0),
                available_bytes=int(item.get("avail", 0) or 0),
                used_percent=_percent(item.get("used", 0), item.get("total", 0)),
            )
            for item in storage_payload
        ]
        active_storage_percentages = [
            storage.used_percent
            for storage in storages
            if storage.active and storage.enabled and storage.used_percent is not None
        ]
        max_storage_percent = max(active_storage_percentages, default=None)

        guests = [
            ProxmoxGuestStatus(
                vmid=int(item["vmid"]),
                name=str(item.get("name") or f"guest-{item['vmid']}"),
                guest_type=str(item.get("type", "unknown")),
                status=str(item.get("status", "unknown")),
                pool=item.get("pool") or None,
                template=bool(item.get("template", 0)),
                cpu_count=int(item.get("maxcpu", 0) or 0),
                memory_bytes=int(item.get("maxmem", 0) or 0),
            )
            for item in resource_payload
            if item.get("node") == self.node and item.get("type") in {"qemu", "lxc"}
        ]
        running_guests = sum(guest.status == "running" for guest in guests)
        ai_node = next((guest for guest in guests if guest.name == "ai-node-01"), None)

        signals = [
            _pressure_signal(
                "cpu_percent",
                cpu_percent,
                warning_at=85,
                critical_at=95,
                detail="Current Proxmox node CPU utilization.",
            ),
            _pressure_signal(
                "memory_percent",
                memory_percent,
                warning_at=80,
                critical_at=95,
                detail="Current Proxmox node memory utilization.",
            ),
            _pressure_signal(
                "root_disk_percent",
                root_percent,
                warning_at=80,
                critical_at=95,
                detail="Current Proxmox root filesystem utilization.",
            ),
            _pressure_signal(
                "max_active_storage_percent",
                max_storage_percent,
                warning_at=80,
                critical_at=95,
                detail="Highest utilization among active, enabled Proxmox storage targets.",
            ),
            RuntimeSignal(
                name="running_guests",
                state="healthy",
                value=float(running_guests),
                unit="guests",
                detail=f"{running_guests} of {len(guests)} guests on this node are running.",
            ),
            RuntimeSignal(
                name="ai_node_present",
                state=(
                    "healthy"
                    if ai_node and ai_node.status == "running"
                    else "warning"
                    if ai_node
                    else "unknown"
                ),
                value=1.0 if ai_node else 0.0,
                unit="guest",
                detail=(
                    f"ai-node-01 exists and is {ai_node.status}."
                    if ai_node
                    else "ai-node-01 has not been provisioned yet."
                ),
            ),
        ]

        if any(signal.state == "critical" for signal in signals):
            overall_state = "critical"
        elif any(signal.state == "warning" for signal in signals):
            overall_state = "warning"
        else:
            overall_state = "healthy"

        return ProxmoxRuntimeStatus(
            state=overall_state,
            source="proxmox-api",
            observed_at=observed_at,
            node=self.node,
            version=node_status.get("pveversion") or None,
            kernel=node_status.get("kversion") or None,
            signals=signals,
            storages=sorted(storages, key=lambda storage: storage.name),
            guests=sorted(guests, key=lambda guest: guest.vmid),
            limitations=limitations,
        )


class ProxmoxSnapshotConnector:
    def __init__(self, snapshot_path: Path, *, max_age_seconds: float = 300.0) -> None:
        self.snapshot_path = snapshot_path
        self.max_age_seconds = max_age_seconds

    def status(self) -> ProxmoxRuntimeStatus:
        now = datetime.now(UTC)
        try:
            snapshot = ProxmoxRuntimeStatus.model_validate_json(
                self.snapshot_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return ProxmoxRuntimeStatus(
                state="unavailable",
                source="proxmox-snapshot",
                observed_at=now,
                node="unknown",
                version=None,
                kernel=None,
                signals=[],
                storages=[],
                guests=[],
                limitations=["The Proxmox snapshot is missing or invalid."],
                error="No valid Proxmox runtime snapshot is available.",
            )

        age_seconds = (now - snapshot.observed_at).total_seconds()
        limitations = [
            *snapshot.limitations,
            "The API consumes a host-collected snapshot and never receives the Proxmox token.",
        ]
        if age_seconds > self.max_age_seconds:
            return snapshot.model_copy(
                update={
                    "state": "unavailable",
                    "source": "proxmox-snapshot",
                    "limitations": [
                        *limitations,
                        f"The snapshot is stale by policy ({age_seconds:.0f} seconds old).",
                    ],
                    "error": "The Proxmox runtime snapshot is stale.",
                }
            )
        return snapshot.model_copy(
            update={"source": "proxmox-snapshot", "limitations": limitations}
        )
