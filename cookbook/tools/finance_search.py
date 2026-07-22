"""
title: Finance Web Research
author: AI Lab
version: 1.0.0
description: Search private SearXNG for finance sources, then safely fetch or extract them.
"""

import json
import re
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

    _symbol_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,14}$")
    _topics = {
        "quote": "stock quote market price exchange currency as of",
        "news": "stock company latest news material announcement",
        "filings": "investor relations regulatory filing annual quarterly report",
        "fundamentals": "revenue earnings cash flow balance sheet fundamentals",
        "dividends": "dividend history ex-dividend date payout investor relations",
        "analyst": "analyst estimate consensus target methodology",
    }

    def __init__(self):
        self.valves = self.Valves()

    def _post(self, path: str, payload: dict) -> dict:
        base = urlsplit(self.valves.api_base.rstrip("/"))
        if base.scheme != "http" or base.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("Finance Research api_base must remain on local HTTP loopback.")
        if not self.valves.api_key:
            raise ValueError("Finance Research is not configured with its API key.")
        request = Request(
            f"{self.valves.api_base.rstrip('/')}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "X-Api-Key": self.valves.api_key,
                "Content-Type": "application/json",
                "User-Agent": "openwebui-ailab-finance-research/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:  # noqa: S310
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Finance Research returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The controlled Finance Research service is unavailable.") from error

    @staticmethod
    def _source_url(source_url: str) -> str:
        source_url = source_url.strip()
        source = urlsplit(source_url)
        if source.scheme.lower() not in {"http", "https"} or not source.hostname:
            raise ValueError("source_url must be an absolute HTTP or HTTPS URL.")
        if len(source_url) > 4096:
            raise ValueError("source_url is too long.")
        return source_url

    @staticmethod
    def _search_envelope(result: dict) -> str:
        return json.dumps(
            {
                "data_kind": "search_discovery",
                "freshness_warning": (
                    "Search results and snippets are discovery evidence, not a licensed or "
                    "consolidated real-time quote feed. Open relevant sources, verify their own "
                    "as-of timestamps, currency, exchange, and delay, and cross-check "
                    "material data."
                ),
                **result,
            },
            indent=2,
        )

    def search_stock_sources(
        self,
        symbol: str,
        company_name: str = "",
        exchange: str = "",
        topic: str = "quote",
        time_range: str = "day",
        result_count: int = 8,
    ) -> str:
        """Search several web engines for current sources about one public security.

        This discovers quote pages, company news, filings, fundamentals, dividends, or analyst
        commentary. It does not turn search snippets into a real-time market-data feed.

        :param symbol: Ticker or exchange-qualified symbol, such as AAPL, TD.TO, or BRK-B.
        :param company_name: Optional company name used to reduce ticker ambiguity.
        :param exchange: Optional exchange name, such as NASDAQ, NYSE, or TSX.
        :param topic: One of quote, news, filings, fundamentals, dividends, or analyst.
        :param time_range: SearXNG recency filter: day, month, or year.
        :param result_count: Number of normalized results, from 1 through 10.
        """
        symbol = symbol.strip().upper()
        if not self._symbol_pattern.fullmatch(symbol):
            raise ValueError("symbol must be a valid ticker or exchange-qualified ticker.")
        topic = topic.strip().lower()
        if topic not in self._topics:
            raise ValueError(f"topic must be one of: {', '.join(sorted(self._topics))}.")
        if time_range not in {"day", "month", "year"}:
            raise ValueError("time_range must be day, month, or year.")
        if not 1 <= result_count <= 10:
            raise ValueError("result_count must be between 1 and 10.")
        identity = " ".join(
            part for part in (f'"{symbol}"', company_name.strip(), exchange.strip()) if part
        )
        result = self._post(
            "/v1/search",
            {
                "query": f"{identity} {self._topics[topic]}",
                "categories": "news" if topic == "news" else "general",
                "language": "en",
                "time_range": time_range,
                "count": result_count,
            },
        )
        return self._search_envelope(result)

    def search_finance_sources(
        self,
        question: str,
        time_range: str = "month",
        result_count: int = 8,
    ) -> str:
        """Search private SearXNG for current finance, tax, policy, or market sources.

        :param question: A precise finance research question with jurisdiction and instrument.
        :param time_range: SearXNG recency filter: day, month, or year.
        :param result_count: Number of normalized results, from 1 through 10.
        """
        question = question.strip()
        if len(question) < 4 or len(question) > 400:
            raise ValueError("question must contain between 4 and 400 characters.")
        if time_range not in {"day", "month", "year"}:
            raise ValueError("time_range must be day, month, or year.")
        if not 1 <= result_count <= 10:
            raise ValueError("result_count must be between 1 and 10.")
        result = self._post(
            "/v1/search",
            {
                "query": question,
                "categories": "general",
                "language": "en",
                "time_range": time_range,
                "count": result_count,
            },
        )
        return self._search_envelope(result)

    def fetch_finance_source(self, source_url: str) -> str:
        """Safely fetch readable text from a finance result selected after SearXNG search.

        :param source_url: Absolute public HTTP or HTTPS result URL.
        """
        return json.dumps(self._post("/v1/fetch", {"url": self._source_url(source_url)}), indent=2)

    def extract_finance_document(self, source_url: str) -> str:
        """Safely fetch and OCR/extract a public filing, report, table, image, or PDF.

        :param source_url: Absolute public HTTP or HTTPS document URL.
        """
        return json.dumps(
            self._post("/v1/extract", {"url": self._source_url(source_url)}), indent=2
        )
