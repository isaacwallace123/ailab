"""
title: Market Data
author: AI Lab
version: 1.0.0
description: Read-only US equity quotes, trades, snapshots, and bars with explicit feed provenance.
"""

import json
import re
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        alpaca_api_key_id: str = Field(
            default="", description="Alpaca Market Data API key ID (read-only use)."
        )
        alpaca_api_secret_key: str = Field(
            default="", description="Alpaca Market Data API secret key."
        )
        default_feed: str = Field(
            default="iex",
            description="Default stock feed: iex, sip, or delayed_sip. SIP requires entitlement.",
        )
        timeout_seconds: int = Field(default=20, ge=2, le=120)

    _SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
    _FEEDS = {"iex", "sip", "delayed_sip"}
    _TIMEFRAMES = {
        "1Min",
        "5Min",
        "15Min",
        "30Min",
        "1Hour",
        "1Day",
        "1Week",
        "1Month",
    }

    def __init__(self):
        self.valves = self.Valves()

    @classmethod
    def _symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not cls._SYMBOL.fullmatch(symbol):
            raise ValueError("symbol must be a valid 1-to-15-character US equity symbol")
        return symbol

    def _feed(self, value: str) -> str:
        feed = (value or self.valves.default_feed).strip().lower()
        if feed not in self._FEEDS:
            raise ValueError("feed must be iex, sip, or delayed_sip")
        return feed

    @staticmethod
    def _retrieved_at() -> str:
        return datetime.now(UTC).isoformat()

    def _get(self, path: str, parameters: dict) -> tuple[dict, str]:
        if not self.valves.alpaca_api_key_id or not self.valves.alpaca_api_secret_key:
            raise ValueError(
                "Market Data is not configured. Add an Alpaca key ID and secret in the tool valves."
            )
        url = f"https://data.alpaca.markets{path}?{urlencode(parameters)}"
        request = Request(
            url,
            headers={
                "APCA-API-KEY-ID": self.valves.alpaca_api_key_id,
                "APCA-API-SECRET-KEY": self.valves.alpaca_api_secret_key,
                "Accept": "application/json",
                "User-Agent": "openwebui-ailab-market-data/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:  # noqa: S310
                return json.load(response), response.headers.get("X-Request-ID", "")
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            if error.code == 403:
                detail = (
                    f"{detail} Check the API credentials and whether the requested feed is "
                    "included in the Alpaca market-data subscription."
                )
            raise RuntimeError(f"Alpaca returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The Alpaca market-data service is unavailable.") from error

    @staticmethod
    def _envelope(*, symbol: str, feed: str, endpoint: str, request_id: str, data: dict) -> str:
        return json.dumps(
            {
                "provider": "Alpaca Market Data API",
                "feed": feed,
                "coverage": {
                    "iex": "Real-time trades and quotes from the IEX exchange only.",
                    "sip": "Consolidated US exchange feed; recent data requires SIP entitlement.",
                    "delayed_sip": "Consolidated US exchange feed delayed by 15 minutes.",
                }[feed],
                "symbol": symbol,
                "retrieved_at": Tools._retrieved_at(),
                "source_url": f"https://data.alpaca.markets{endpoint}",
                "request_id": request_id or None,
                "data": data,
                "warning": (
                    "Read-only market data. Verify feed, timestamps, currency, session, and "
                    "entitlement before relying on a value; this is not a trade instruction."
                ),
            },
            indent=2,
        )

    def latest_stock_quote(self, symbol: str, feed: str = "") -> str:
        """Get the latest bid and ask for one US equity with feed and timestamp provenance.

        :param symbol: US stock or ETF symbol, such as AAPL.
        :param feed: Optional iex, sip, or delayed_sip override.
        """
        normalized = self._symbol(symbol)
        selected_feed = self._feed(feed)
        endpoint = f"/v2/stocks/{normalized}/quotes/latest"
        payload, request_id = self._get(endpoint, {"feed": selected_feed})
        return self._envelope(
            symbol=normalized,
            feed=selected_feed,
            endpoint=endpoint,
            request_id=request_id,
            data=payload.get("quote") or payload,
        )

    def latest_stock_trade(self, symbol: str, feed: str = "") -> str:
        """Get the latest reported trade for one US equity with exact event time.

        :param symbol: US stock or ETF symbol, such as AAPL.
        :param feed: Optional iex, sip, or delayed_sip override.
        """
        normalized = self._symbol(symbol)
        selected_feed = self._feed(feed)
        endpoint = f"/v2/stocks/{normalized}/trades/latest"
        payload, request_id = self._get(endpoint, {"feed": selected_feed})
        return self._envelope(
            symbol=normalized,
            feed=selected_feed,
            endpoint=endpoint,
            request_id=request_id,
            data=payload.get("trade") or payload,
        )

    def stock_snapshot(self, symbol: str, feed: str = "") -> str:
        """Get a US equity snapshot containing latest trade/quote and recent bars.

        :param symbol: US stock or ETF symbol, such as AAPL.
        :param feed: Optional iex, sip, or delayed_sip override.
        """
        normalized = self._symbol(symbol)
        selected_feed = self._feed(feed)
        endpoint = f"/v2/stocks/{normalized}/snapshot"
        payload, request_id = self._get(endpoint, {"feed": selected_feed})
        return self._envelope(
            symbol=normalized,
            feed=selected_feed,
            endpoint=endpoint,
            request_id=request_id,
            data=payload,
        )

    def stock_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        timeframe: str = "1Day",
        feed: str = "",
        limit: int = 30,
    ) -> str:
        """Get timestamped OHLCV bars for one US equity.

        :param symbol: US stock or ETF symbol, such as AAPL.
        :param start: Inclusive RFC-3339 timestamp or YYYY-MM-DD date.
        :param end: Exclusive RFC-3339 timestamp or YYYY-MM-DD date.
        :param timeframe: 1Min, 5Min, 15Min, 30Min, 1Hour, 1Day, 1Week, or 1Month.
        :param feed: Optional iex, sip, or delayed_sip override.
        :param limit: Maximum bars from 1 to 1000.
        """
        normalized = self._symbol(symbol)
        selected_feed = self._feed(feed)
        if timeframe not in self._TIMEFRAMES:
            raise ValueError(f"timeframe must be one of: {', '.join(sorted(self._TIMEFRAMES))}")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not start.strip() or not end.strip() or len(start) > 40 or len(end) > 40:
            raise ValueError("start and end must be short ISO-8601 dates or timestamps")
        endpoint = f"/v2/stocks/{normalized}/bars"
        payload, request_id = self._get(
            endpoint,
            {
                "feed": selected_feed,
                "timeframe": timeframe,
                "start": start.strip(),
                "end": end.strip(),
                "limit": limit,
                "adjustment": "all",
                "sort": "asc",
            },
        )
        return self._envelope(
            symbol=normalized,
            feed=selected_feed,
            endpoint=endpoint,
            request_id=request_id,
            data={
                "bars": payload.get("bars", []),
                "next_page_token": payload.get("next_page_token"),
            },
        )
