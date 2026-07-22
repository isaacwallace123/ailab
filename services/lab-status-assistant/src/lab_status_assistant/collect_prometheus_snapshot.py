from __future__ import annotations

import argparse
from pathlib import Path

from .prometheus import PrometheusClient, PrometheusHomelabConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a fixed-query homelab status snapshot.")
    parser.add_argument("--url", required=True, help="Prometheus base URL")
    parser.add_argument("--output", required=True, type=Path, help="Snapshot output path")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--no-verify-tls", action="store_true")
    arguments = parser.parse_args()

    connector = PrometheusHomelabConnector(
        PrometheusClient(
            arguments.url,
            timeout_seconds=arguments.timeout,
            verify_tls=not arguments.no_verify_tls,
        )
    )
    status = connector.status()
    if status.state == "unavailable":
        raise SystemExit("Prometheus snapshot collection failed")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(f"{arguments.output.suffix}.tmp")
    temporary.write_text(status.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(arguments.output)


if __name__ == "__main__":
    main()
