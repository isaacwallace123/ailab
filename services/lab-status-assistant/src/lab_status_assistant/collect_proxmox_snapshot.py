from __future__ import annotations

import argparse
import os
from pathlib import Path

from .proxmox import ProxmoxClient, ProxmoxNodeConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect read-only Proxmox node capacity status.")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--no-verify-tls", action="store_true")
    arguments = parser.parse_args()

    api_token = os.getenv("AILAB_PROXMOX_API_TOKEN")
    if not api_token:
        raise SystemExit("AILAB_PROXMOX_API_TOKEN is required")
    status = ProxmoxNodeConnector(
        ProxmoxClient(
            arguments.endpoint,
            api_token,
            timeout_seconds=arguments.timeout,
            verify_tls=not arguments.no_verify_tls,
        ),
        node=arguments.node,
    ).status()
    if status.state == "unavailable":
        raise SystemExit("Proxmox snapshot collection failed")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(f"{arguments.output.suffix}.tmp")
    temporary.write_text(status.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(arguments.output)


if __name__ == "__main__":
    main()
