"""
title: Research Gateway
author: AI Lab
version: 1.0.0
description: Safely retrieve public pages or extract public documents with provenance.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        api_base: str = Field(
            default="http://127.0.0.1:18089",
            description="Loopback URL of the controlled AI Lab Research Gateway.",
        )
        api_key: str = Field(default="", description="Dedicated Research Gateway API key.")
        timeout_seconds: int = Field(default=180, ge=5, le=240)

    def __init__(self):
        self.valves = self.Valves()

    def _request(self, path: str, source_url: str) -> dict:
        base = urlsplit(self.valves.api_base.rstrip("/"))
        if base.scheme != "http" or base.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("Research Gateway api_base must remain on local HTTP loopback.")
        if not self.valves.api_key:
            raise ValueError("Research Gateway is not configured with its API key.")
        source = urlsplit(source_url.strip())
        if source.scheme.lower() not in {"http", "https"} or not source.hostname:
            raise ValueError("source_url must be an absolute HTTP or HTTPS URL.")
        if len(source_url) > 4096:
            raise ValueError("source_url is too long.")
        request = Request(
            f"{self.valves.api_base.rstrip('/')}{path}",
            data=json.dumps({"url": source_url.strip()}).encode("utf-8"),
            method="POST",
            headers={
                "X-Api-Key": self.valves.api_key,
                "Content-Type": "application/json",
                "User-Agent": "openwebui-ailab-research/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:  # noqa: S310
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Research Gateway returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The controlled Research Gateway is unavailable.") from error

    def fetch_public_page(self, source_url: str) -> str:
        """Retrieve readable text from one public HTML or text URL with source provenance.

        Use after search to open a selected source. The gateway rejects LAN, loopback, metadata,
        credentials, unsafe ports, oversized responses, and unsafe redirects.

        :param source_url: Absolute public HTTP or HTTPS page URL returned by search.
        """
        return json.dumps(self._request("/v1/fetch", source_url), indent=2)

    def extract_public_document(self, source_url: str) -> str:
        """Retrieve a public document safely and extract it through private Docling OCR.

        Use for PDFs, Office documents, images, tables, HTML, CSV, XML, or XBRL. The result includes
        final URL, retrieval time, content type, byte count, SHA-256 digest, and extracted Markdown.

        :param source_url: Absolute public HTTP or HTTPS document URL returned by search.
        """
        return json.dumps(self._request("/v1/extract", source_url), indent=2)
