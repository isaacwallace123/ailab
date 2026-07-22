"""
title: Official Finance Data
author: AI Lab
version: 1.0.0
description: Read-only Bank of Canada series and SEC filing facts with source provenance.
"""

import json
import re
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        sec_contact_email: str = Field(
            default="",
            description="Real contact email included in the SEC-compliant User-Agent.",
        )
        timeout_seconds: int = Field(default=25, ge=2, le=120)

    _SERIES = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
    _CONCEPT = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,119}$")
    _TAXONOMY = {"us-gaap", "ifrs-full", "dei", "srt"}

    def __init__(self):
        self.valves = self.Valves()

    @staticmethod
    def _retrieved_at() -> str:
        return datetime.now(UTC).isoformat()

    def _get(self, url: str, user_agent: str) -> dict:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:  # noqa: S310
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Official data source returned HTTP {error.code}: {detail}"
            ) from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The official finance-data source is unavailable.") from error

    @staticmethod
    def _cik(value: str) -> str:
        cleaned = value.strip().removeprefix("CIK")
        if not cleaned.isdigit() or not 1 <= len(cleaned) <= 10:
            raise ValueError("cik must contain 1 to 10 digits")
        return cleaned.zfill(10)

    def _sec_user_agent(self) -> str:
        email = self.valves.sec_contact_email.strip()
        if "@" not in email or email.endswith(".local") or len(email) > 200:
            raise ValueError(
                "SEC access requires a real contact email in the Official Finance Data valves."
            )
        return f"AI Lab finance research {email}"

    def bank_of_canada_observations(
        self, series_name: str, start_date: str = "", end_date: str = "", recent: int = 30
    ) -> str:
        """Retrieve an official Bank of Canada economic or exchange-rate series.

        :param series_name: Valet series identifier, such as FXUSDCAD or V39079.
        :param start_date: Optional inclusive date in YYYY-MM-DD format.
        :param end_date: Optional inclusive date in YYYY-MM-DD format.
        :param recent: Maximum recent observations from 1 to 1000 when dates are omitted.
        """
        series = series_name.strip()
        if not self._SERIES.fullmatch(series):
            raise ValueError("series_name contains unsupported characters")
        if not 1 <= recent <= 1000:
            raise ValueError("recent must be between 1 and 1000")
        parameters: dict[str, str | int] = {}
        if start_date:
            parameters["start_date"] = start_date.strip()
        if end_date:
            parameters["end_date"] = end_date.strip()
        if not start_date and not end_date:
            parameters["recent"] = recent
        url = (
            f"https://www.bankofcanada.ca/valet/observations/{quote(series, safe='')}/json"
            f"?{urlencode(parameters)}"
        )
        payload = self._get(url, "openwebui-ailab-finance/1.0")
        return json.dumps(
            {
                "provider": "Bank of Canada Valet API",
                "series": series,
                "retrieved_at": self._retrieved_at(),
                "source_url": url,
                "series_detail": payload.get("seriesDetail", {}).get(series),
                "observations": payload.get("observations", []),
                "warning": (
                    "Check the series methodology, units, frequency, and publication schedule."
                ),
            },
            indent=2,
        )

    def sec_recent_filings(self, cik: str, forms: str = "10-K,10-Q,8-K", limit: int = 20) -> str:
        """List recent SEC filings for a verified company CIK.

        :param cik: SEC Central Index Key, with or without leading zeroes.
        :param forms: Comma-separated exact form types, or empty for all forms.
        :param limit: Maximum filings from 1 to 100.
        """
        normalized = self._cik(cik)
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        requested_forms = {item.strip().upper() for item in forms.split(",") if item.strip()}
        url = f"https://data.sec.gov/submissions/CIK{normalized}.json"
        payload = self._get(url, self._sec_user_agent())
        recent = (payload.get("filings") or {}).get("recent") or {}
        keys = (
            "accessionNumber",
            "filingDate",
            "reportDate",
            "acceptanceDateTime",
            "act",
            "form",
            "fileNumber",
            "primaryDocument",
            "primaryDocDescription",
        )
        rows = []
        for values in zip(*(recent.get(key, []) for key in keys), strict=False):
            row = dict(zip(keys, values, strict=True))
            if requested_forms and str(row.get("form", "")).upper() not in requested_forms:
                continue
            accession = str(row.get("accessionNumber", "")).replace("-", "")
            document = quote(str(row.get("primaryDocument", "")), safe="._-")
            row["filing_url"] = (
                f"https://www.sec.gov/Archives/edgar/data/{int(normalized)}/{accession}/{document}"
            )
            rows.append(row)
            if len(rows) >= limit:
                break
        return json.dumps(
            {
                "provider": "U.S. SEC EDGAR submissions API",
                "cik": normalized,
                "company": payload.get("name"),
                "tickers": payload.get("tickers", []),
                "retrieved_at": self._retrieved_at(),
                "source_url": url,
                "filings": rows,
            },
            indent=2,
        )

    def sec_company_concept(
        self,
        cik: str,
        concept: str,
        taxonomy: str = "us-gaap",
        unit: str = "USD",
        limit: int = 40,
    ) -> str:
        """Retrieve recent structured SEC XBRL facts for one company and concept.

        :param cik: SEC Central Index Key, with or without leading zeroes.
        :param concept: Exact XBRL concept, such as Revenues or NetIncomeLoss.
        :param taxonomy: us-gaap, ifrs-full, dei, or srt.
        :param unit: Exact unit key returned by SEC, commonly USD, shares, or USD/shares.
        :param limit: Maximum facts from 1 to 200.
        """
        normalized = self._cik(cik)
        selected_taxonomy = taxonomy.strip().lower()
        if selected_taxonomy not in self._TAXONOMY:
            raise ValueError("taxonomy must be us-gaap, ifrs-full, dei, or srt")
        selected_concept = concept.strip()
        if not self._CONCEPT.fullmatch(selected_concept):
            raise ValueError("concept contains unsupported characters")
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        url = (
            "https://data.sec.gov/api/xbrl/companyconcept/"
            f"CIK{normalized}/{selected_taxonomy}/{quote(selected_concept, safe='')}.json"
        )
        payload = self._get(url, self._sec_user_agent())
        units = (payload.get("units") or {}).get(unit)
        if units is None:
            available = sorted((payload.get("units") or {}).keys())
            raise ValueError(f"unit {unit!r} is unavailable; choose one of {available}")
        facts = sorted(units, key=lambda item: item.get("filed", ""), reverse=True)[:limit]
        return json.dumps(
            {
                "provider": "U.S. SEC EDGAR XBRL API",
                "cik": normalized,
                "company": payload.get("entityName"),
                "taxonomy": payload.get("taxonomy"),
                "concept": payload.get("tag"),
                "label": payload.get("label"),
                "description": payload.get("description"),
                "unit": unit,
                "retrieved_at": self._retrieved_at(),
                "source_url": url,
                "facts": facts,
                "warning": (
                    "Verify fiscal period, units, duration versus instant context, amendments, "
                    "and restatements before comparing facts."
                ),
            },
            indent=2,
        )
