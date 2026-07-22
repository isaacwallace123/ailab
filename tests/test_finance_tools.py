from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name: str):
    path = ROOT / "cookbook" / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cookbook_tool_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_market_data_denies_unconfigured_access() -> None:
    tool = load_tool("market_data").Tools()
    with pytest.raises(ValueError, match="not configured"):
        tool.latest_stock_quote("AAPL")


def test_market_data_preserves_feed_and_timestamp_provenance(monkeypatch) -> None:
    tool = load_tool("market_data").Tools()
    tool.valves.alpaca_api_key_id = "test-key-id"
    tool.valves.alpaca_api_secret_key = "test-secret"
    monkeypatch.setattr(
        tool,
        "_get",
        lambda path, parameters: (
            {"quote": {"ap": 202.5, "bp": 202.4, "t": "2026-07-17T19:59:59Z"}},
            "request-123",
        ),
    )

    result = json.loads(tool.latest_stock_quote("aapl", "iex"))

    assert result["symbol"] == "AAPL"
    assert result["feed"] == "iex"
    assert "IEX exchange only" in result["coverage"]
    assert result["request_id"] == "request-123"
    assert result["data"]["ap"] == 202.5
    assert result["retrieved_at"].endswith("+00:00")


def test_market_data_rejects_invalid_symbols() -> None:
    tool = load_tool("market_data").Tools()
    with pytest.raises(ValueError, match="valid"):
        tool.latest_stock_quote("AAPL;DROP")


def test_finance_search_builds_bounded_searxng_request(monkeypatch) -> None:
    tool = load_tool("finance_search").Tools()
    tool.valves.api_key = "test-key"
    captured = {}

    def fake_post(path, payload):
        captured.update({"path": path, "payload": payload})
        return {"query": payload["query"], "retrieved_at": "2026-07-19T00:00:00Z", "results": []}

    monkeypatch.setattr(tool, "_post", fake_post)
    result = json.loads(
        tool.search_stock_sources("td.to", "Toronto-Dominion Bank", "TSX", "quote", "day", 6)
    )

    assert captured["path"] == "/v1/search"
    assert '"TD.TO"' in captured["payload"]["query"]
    assert captured["payload"]["count"] == 6
    assert result["data_kind"] == "search_discovery"
    assert "not a licensed or consolidated real-time quote feed" in result["freshness_warning"]


def test_finance_search_rejects_invalid_inputs() -> None:
    tool = load_tool("finance_search").Tools()
    with pytest.raises(ValueError, match="valid ticker"):
        tool.search_stock_sources("AAPL;DROP")
    with pytest.raises(ValueError, match="topic must be"):
        tool.search_stock_sources("AAPL", topic="rumours")


def test_bank_of_canada_result_is_source_labeled(monkeypatch) -> None:
    tool = load_tool("official_finance_data").Tools()
    monkeypatch.setattr(
        tool,
        "_get",
        lambda url, user_agent: {
            "seriesDetail": {"FXUSDCAD": {"label": "USD/CAD"}},
            "observations": [{"d": "2026-07-17", "FXUSDCAD": {"v": "1.3600"}}],
        },
    )

    result = json.loads(tool.bank_of_canada_observations("FXUSDCAD", recent=1))

    assert result["provider"] == "Bank of Canada Valet API"
    assert result["series"] == "FXUSDCAD"
    assert result["observations"][0]["FXUSDCAD"]["v"] == "1.3600"


def test_sec_access_requires_real_contact_email() -> None:
    tool = load_tool("official_finance_data").Tools()
    with pytest.raises(ValueError, match="real contact email"):
        tool.sec_recent_filings("320193")
    tool.valves.sec_contact_email = "isaac@ailab.local"
    with pytest.raises(ValueError, match="real contact email"):
        tool.sec_recent_filings("320193")


def test_retirement_scenarios_are_ordered_and_inflation_adjusted() -> None:
    tool = load_tool("finance_planner").Tools()
    result = json.loads(
        tool.retirement_scenarios(
            current_savings=100_000,
            monthly_contribution=1_000,
            years=20,
            annual_return_percents=[3, 5, 7],
            annual_fee_percent=0.25,
            annual_inflation_percent=2,
        )
    )

    balances = [item["ending_balance_nominal"] for item in result["scenarios"]]
    assert balances == sorted(balances)
    assert all(
        item["ending_balance_in_today_dollars"] < item["ending_balance_nominal"]
        for item in result["scenarios"]
    )


def test_extra_debt_payment_saves_time_and_interest() -> None:
    tool = load_tool("finance_planner").Tools()
    result = json.loads(
        tool.compare_debt_payoff(
            principal=25_000,
            annual_interest_percent=8,
            regular_monthly_payment=600,
            extra_monthly_payment=200,
        )
    )

    assert result["months_saved"] > 0
    assert result["interest_saved"] > 0
    assert result["accelerated"]["months"] < result["baseline"]["months"]


def test_debt_payment_must_cover_interest() -> None:
    tool = load_tool("finance_planner").Tools()
    with pytest.raises(ValueError, match="does not cover"):
        tool.compare_debt_payoff(100_000, 20, 100, 0)
