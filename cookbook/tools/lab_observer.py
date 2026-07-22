"""
title: Lab Observer
author: AI Lab
version: 1.0.0
description: Read-only cited search and normalized status for the shared labs.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        api_base: str = Field(
            default="http://127.0.0.1:18088",
            description="Loopback or internal URL of the Lab Status Assistant, without /api/v1.",
        )
        api_token: str = Field(
            default="",
            description="Dedicated read-only Lab Status Assistant bearer token.",
        )
        timeout_seconds: int = Field(default=30, ge=2, le=240)

    def __init__(self):
        self.valves = self.Valves()

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        base = self.valves.api_base.rstrip("/")
        if not base.startswith(("http://", "https://")):
            raise ValueError("Lab Observer api_base must use http or https.")
        if not self.valves.api_token:
            raise ValueError("Lab Observer is not configured with its read-only API token.")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{base}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.valves.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "openwebui-lab-observer/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:  # noqa: S310
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Lab Observer API returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The read-only Lab Observer API is unavailable.") from error

    def list_collections(self) -> str:
        """List indexed repository collections and their freshness.

        Use this before searching when the relevant lab or project collection is unknown.
        """
        return json.dumps(self._request("GET", "/api/v1/collections"), indent=2)

    def search_knowledge(
        self, query: str, collections: list[str] | None = None, limit: int = 8
    ) -> str:
        """Search approved local repository knowledge with exact file and line citations.

        :param query: Concept, identifier, decision, project, runbook, or error to find.
        :param collections: Optional collection IDs such as ailab, homelab, or cyberlab.
        :param limit: Maximum results from 1 to 12.
        """
        if not 2 <= len(query.strip()) <= 500:
            raise ValueError("query must contain 2 to 500 characters")
        limit = max(1, min(limit, 12))
        payload = {"query": query.strip(), "collections": collections, "limit": limit}
        return json.dumps(self._request("POST", "/api/v1/knowledge/search", payload), indent=2)

    def get_lab_status(self, lab: str) -> str:
        """Get normalized timestamped read-only runtime status for one lab.

        :param lab: One of homelab, kubernetes, or ailab.
        """
        routes = {
            "homelab": "/api/v1/status/runtime/homelab",
            "kubernetes": "/api/v1/status/runtime/homelab/kubernetes",
            "ailab": "/api/v1/status/runtime/ailab/proxmox",
        }
        normalized = lab.strip().lower()
        if normalized not in routes:
            raise ValueError("lab must be one of: homelab, kubernetes, ailab")
        return json.dumps(self._request("GET", routes[normalized]), indent=2)

    def ask_grounded(
        self,
        question: str,
        collections: list[str] | None = None,
        include_runtime: bool | None = None,
    ) -> str:
        """Ask the citation-validating lab assistant to synthesize approved evidence.

        Use for cross-source questions after direct search/status calls are insufficient.
        This tool remains read-only and does not execute remediation.

        :param question: Lab, project, architecture, roadmap, or current-status question.
        :param collections: Optional collection IDs to constrain retrieval.
        :param include_runtime: Explicitly include or exclude current runtime evidence.
        """
        if not 3 <= len(question.strip()) <= 1000:
            raise ValueError("question must contain 3 to 1000 characters")
        payload = {
            "question": question.strip(),
            "collections": collections,
            "include_runtime": include_runtime,
        }
        return json.dumps(self._request("POST", "/api/v1/assistant/ask", payload), indent=2)
