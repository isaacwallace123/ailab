---
name: interpret-market-data
description: Interpret stock quotes, trades, OHLC bars, volume, spreads, feed coverage, and timestamps. Use for live or historical market-data questions, comparisons between providers, candlestick charts, and any claim about a current security price.
---

# Interpret Market Data

1. Identify the symbol, security, exchange, currency, session, timezone, and requested point in time. Confirm ambiguous tickers before retrieving data.
2. Use the market-data tool; never fabricate prices or fill missing OHLC periods. Preserve provider, feed, exchange, timestamp, retrieval time, and entitlement metadata.
3. Label feed coverage precisely. IEX is one US exchange; SIP is the consolidated US feed; delayed SIP is not real-time. For Canadian securities, do not claim consolidated real-time coverage without a licensed Canadian feed.
4. For a quote, show bid, ask, sizes, midpoint, spread, latest trade, and their separate timestamps when available. A last trade is not the same as an executable price.
5. For OHLC bars, confirm `low <= open/close <= high`, interval, corporate-action adjustment policy, session coverage, missing bars, and whether the final bar is incomplete.
6. Before comparing providers, normalize symbol, currency, session, feed, adjustment, and timestamp. Report the absolute and percentage difference; explain plausible causes instead of choosing a preferred number silently.
7. Use the Finance Visualizer only after verification. Include the symbol, interval, timezone, feed, and as-of time in or next to the chart.
8. Explain that market data can be stale, corrected, or subject to entitlements and is informational—not a trade instruction.

