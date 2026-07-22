# ruff: noqa: E501
"""
title: Finance Visualizer
author: AI Lab
version: 1.0.0
description: Safe in-chat bar, line, pie, and candlestick charts for reviewed finance data.
"""

import html
import math

from fastapi.responses import HTMLResponse


class Tools:
    _COLORS = ("#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#22d3ee")

    @staticmethod
    def _text(value: str, name: str, maximum: int = 100) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > maximum:
            raise ValueError(f"{name} must contain 1 to {maximum} characters")
        return html.escape(cleaned)

    @staticmethod
    def _numbers(values: list[float], expected: int | None = None) -> list[float]:
        if expected is not None and len(values) != expected:
            raise ValueError("Every chart series must have the same number of entries")
        if not 2 <= len(values) <= 30:
            raise ValueError("Charts require 2 to 30 data points")
        normalized = [float(value) for value in values]
        if any(not math.isfinite(value) or abs(value) > 1_000_000_000_000 for value in normalized):
            raise ValueError("Chart values must be finite and no larger than 1 trillion")
        return normalized

    @classmethod
    def _labels(cls, labels: list[str]) -> list[str]:
        if not 2 <= len(labels) <= 30:
            raise ValueError("Charts require 2 to 30 labels")
        return [cls._text(label, "label", 40) for label in labels]

    @staticmethod
    def _format(value: float, symbol: str) -> str:
        sign = "-" if value < 0 else ""
        return f"{sign}{symbol}{abs(value):,.2f}"

    @classmethod
    def _document(
        cls,
        title: str,
        subtitle: str,
        svg: str,
        labels: list[str],
        series: list[tuple[str, list[float]]],
        currency_symbol: str,
    ) -> HTMLResponse:
        rows = []
        headings = "".join(f"<th>{html.escape(name)}</th>" for name, _ in series)
        for index, label in enumerate(labels):
            cells = "".join(
                f"<td>{cls._format(values[index], currency_symbol)}</td>" for _, values in series
            )
            rows.append(f"<tr><th>{label}</th>{cells}</tr>")
        content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#0f172a; --panel:#111827; --text:#e5e7eb;
    --muted:#94a3b8; --line:#334155; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:16px; background:var(--bg); color:var(--text);
    font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }}
  .card {{ max-width:900px; margin:auto; padding:18px; border:1px solid var(--line);
    border-radius:16px; background:var(--panel); box-shadow:0 10px 30px #0004; }}
  h2 {{ margin:0 0 3px; font-size:20px; }}
  .subtitle,.note {{ color:var(--muted); }}
  .chart {{ width:100%; overflow-x:auto; margin:12px 0; }}
  svg {{ width:100%; min-width:620px; height:auto; display:block; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; font-variant-numeric:tabular-nums; }}
  th,td {{ padding:7px 9px; border-bottom:1px solid var(--line); text-align:right; }}
  th:first-child {{ text-align:left; }}
  thead th {{ color:var(--muted); font-size:12px; }}
  .note {{ margin:12px 0 0; font-size:12px; }}
  @media (prefers-color-scheme:light) {{ :root {{ --bg:#f8fafc; --panel:#fff; --text:#0f172a;
    --muted:#64748b; --line:#e2e8f0; }} .card {{ box-shadow:0 10px 30px #0f172a12; }} }}
</style>
</head>
<body>
<main class="card">
  <h2>{title}</h2>
  <div class="subtitle">{subtitle}</div>
  <div class="chart">{svg}</div>
  <table aria-label="Chart data"><thead><tr><th>Period / category</th>{headings}</tr></thead>
    <tbody>{"".join(rows)}</tbody></table>
  <p class="note">Educational visualization only. Values reflect the supplied assumptions or data;
  they are not predictions, guarantees, or personalized financial advice.</p>
</main>
<script>
  function reportHeight() {{ parent.postMessage({{type:'iframe:height',height:document.documentElement.scrollHeight}},'*'); }}
  addEventListener('load',reportHeight); new ResizeObserver(reportHeight).observe(document.body);
</script>
</body>
</html>"""
        return HTMLResponse(content=content, headers={"Content-Disposition": "inline"})

    @classmethod
    def _cartesian_svg(
        cls, labels: list[str], values: list[float], chart_type: str, symbol: str
    ) -> str:
        width, height = 760, 390
        left, right, top, bottom = 78, 24, 35, 86
        plot_width, plot_height = width - left - right, height - top - bottom
        minimum = min(0.0, min(values))
        maximum = max(0.0, max(values))
        if maximum == minimum:
            maximum = minimum + 1
        margin = (maximum - minimum) * 0.08
        minimum -= margin
        maximum += margin

        def y(value: float) -> float:
            return top + (maximum - value) / (maximum - minimum) * plot_height

        elements = [
            f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{chart_type} chart">',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#64748b"/>',
            f'<line x1="{left}" y1="{y(0):.2f}" x2="{left + plot_width}" y2="{y(0):.2f}" stroke="#64748b"/>',
        ]
        for tick in range(5):
            value = minimum + (maximum - minimum) * tick / 4
            tick_y = y(value)
            elements.append(
                f'<line x1="{left}" y1="{tick_y:.2f}" x2="{left + plot_width}" y2="{tick_y:.2f}" stroke="#334155" stroke-dasharray="3 5" opacity=".55"/>'
            )
            elements.append(
                f'<text x="{left - 8}" y="{tick_y + 4:.2f}" text-anchor="end" fill="#94a3b8" font-size="11">{html.escape(cls._format(value, symbol))}</text>'
            )
        step = plot_width / len(values)
        if chart_type == "bar":
            bar_width = max(8, step * 0.62)
            for index, value in enumerate(values):
                x = left + step * index + (step - bar_width) / 2
                value_y, zero_y = y(value), y(0)
                bar_y, bar_height = min(value_y, zero_y), max(2, abs(zero_y - value_y))
                elements.append(
                    f'<rect x="{x:.2f}" y="{bar_y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="5" fill="{cls._COLORS[index % len(cls._COLORS)]}"/>'
                )
        else:
            points = [
                (left + step * index + step / 2, y(value)) for index, value in enumerate(values)
            ]
            point_text = " ".join(f"{x:.2f},{point_y:.2f}" for x, point_y in points)
            elements.append(
                f'<polyline points="{point_text}" fill="none" stroke="#60a5fa" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
            )
            elements.extend(
                f'<circle cx="{x:.2f}" cy="{point_y:.2f}" r="5" fill="#0f172a" stroke="#60a5fa" stroke-width="3"/>'
                for x, point_y in points
            )
        for index, label in enumerate(labels):
            x = left + step * index + step / 2
            short_label = label if len(label) <= 12 else f"{label[:11]}…"
            elements.append(
                f'<text x="{x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" fill="#94a3b8" font-size="11">{short_label}</text>'
            )
        elements.append("</svg>")
        return "".join(elements)

    @classmethod
    def _pie_svg(cls, labels: list[str], values: list[float], symbol: str) -> str:
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("Pie charts require non-negative values with a positive total")
        total = sum(values)
        cx, cy, radius = 205, 195, 135
        angle = -math.pi / 2
        elements = ['<svg viewBox="0 0 760 410" role="img" aria-label="pie chart">']
        for index, value in enumerate(values):
            portion = value / total
            next_angle = angle + portion * math.tau
            if portion >= 0.999999:
                elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{cls._COLORS[index % len(cls._COLORS)]}"/>'
                )
            elif portion > 0:
                x1, y1 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
                x2, y2 = cx + radius * math.cos(next_angle), cy + radius * math.sin(next_angle)
                large = 1 if portion > 0.5 else 0
                elements.append(
                    f'<path d="M {cx} {cy} L {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large} 1 {x2:.2f} {y2:.2f} Z" fill="{cls._COLORS[index % len(cls._COLORS)]}" stroke="#111827" stroke-width="2"/>'
                )
            angle = next_angle
            legend_y = 70 + index * 30
            percentage = value / total * 100
            elements.append(
                f'<rect x="410" y="{legend_y - 13}" width="16" height="16" rx="4" fill="{cls._COLORS[index % len(cls._COLORS)]}"/>'
            )
            elements.append(
                f'<text x="438" y="{legend_y}" fill="#e5e7eb" font-size="13">{labels[index]} — {html.escape(cls._format(value, symbol))} ({percentage:.1f}%)</text>'
            )
        elements.append("</svg>")
        return "".join(elements)

    def render_finance_chart(
        self,
        title: str,
        chart_type: str,
        labels: list[str],
        values: list[float],
        series_name: str = "Value",
        currency_symbol: str = "$",
    ) -> tuple[HTMLResponse, dict]:
        """Render a persistent bar, line, or pie chart from supplied finance data.

        Use only after calculations are complete or the source data is verified.

        :param title: Short chart title.
        :param chart_type: One of bar, line, or pie.
        :param labels: Ordered period or category labels, from 2 to 30 entries.
        :param values: Numeric values corresponding exactly to labels.
        :param series_name: Name shown above the values in the accessible table.
        :param currency_symbol: Currency prefix such as $, C$, €, or £.
        """
        safe_title = self._text(title, "title", 100)
        safe_type = chart_type.strip().lower()
        if safe_type not in {"bar", "line", "pie"}:
            raise ValueError("chart_type must be bar, line, or pie")
        safe_labels = self._labels(labels)
        safe_values = self._numbers(values, len(safe_labels))
        safe_series = self._text(series_name, "series_name", 50)
        safe_symbol = self._text(currency_symbol, "currency_symbol", 5)
        svg = (
            self._pie_svg(safe_labels, safe_values, safe_symbol)
            if safe_type == "pie"
            else self._cartesian_svg(safe_labels, safe_values, safe_type, safe_symbol)
        )
        response = self._document(
            safe_title,
            f"{safe_type.title()} chart · {safe_series}",
            svg,
            safe_labels,
            [(safe_series, safe_values)],
            safe_symbol,
        )
        return response, {
            "status": "rendered",
            "chart_type": safe_type,
            "title": html.unescape(safe_title),
            "series": html.unescape(safe_series),
            "data": dict(zip(map(html.unescape, safe_labels), safe_values, strict=True)),
            "warning": "Educational visualization only; not a prediction or recommendation.",
        }

    def render_candlestick_chart(
        self,
        title: str,
        labels: list[str],
        open_prices: list[float],
        high_prices: list[float],
        low_prices: list[float],
        close_prices: list[float],
        currency_symbol: str = "$",
    ) -> tuple[HTMLResponse, dict]:
        """Render supplied, verified OHLC values as a persistent candlestick chart.

        This renderer does not retrieve market data. Do not invent missing prices.

        :param title: Short chart title including the asset and period when known.
        :param labels: Ordered period labels, from 2 to 30 entries.
        :param open_prices: Opening prices corresponding to labels.
        :param high_prices: High prices corresponding to labels.
        :param low_prices: Low prices corresponding to labels.
        :param close_prices: Closing prices corresponding to labels.
        :param currency_symbol: Currency prefix such as $, C$, €, or £.
        """
        safe_title = self._text(title, "title", 100)
        safe_labels = self._labels(labels)
        count = len(safe_labels)
        opens = self._numbers(open_prices, count)
        highs = self._numbers(high_prices, count)
        lows = self._numbers(low_prices, count)
        closes = self._numbers(close_prices, count)
        safe_symbol = self._text(currency_symbol, "currency_symbol", 5)
        for index, (opened, high, low, closed) in enumerate(
            zip(opens, highs, lows, closes, strict=True)
        ):
            if low > min(opened, closed) or high < max(opened, closed) or low > high:
                raise ValueError(f"Invalid OHLC relationship at entry {index + 1}")

        width, height = 760, 400
        left, top, plot_width, plot_height = 78, 35, 658, 275
        minimum, maximum = min(lows), max(highs)
        if maximum == minimum:
            maximum = minimum + 1
        margin = (maximum - minimum) * 0.08
        minimum -= margin
        maximum += margin

        def y(value: float) -> float:
            return top + (maximum - value) / (maximum - minimum) * plot_height

        step = plot_width / count
        body_width = max(6, step * 0.48)
        elements = [
            f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="candlestick chart">'
        ]
        for tick in range(5):
            value = minimum + (maximum - minimum) * tick / 4
            tick_y = y(value)
            elements.append(
                f'<line x1="{left}" y1="{tick_y:.2f}" x2="{left + plot_width}" y2="{tick_y:.2f}" stroke="#334155" stroke-dasharray="3 5" opacity=".6"/>'
            )
            elements.append(
                f'<text x="{left - 8}" y="{tick_y + 4:.2f}" text-anchor="end" fill="#94a3b8" font-size="11">{html.escape(self._format(value, safe_symbol))}</text>'
            )
        for index, (label, opened, high, low, closed) in enumerate(
            zip(safe_labels, opens, highs, lows, closes, strict=True)
        ):
            x = left + step * index + step / 2
            color = "#34d399" if closed >= opened else "#f87171"
            body_top = min(y(opened), y(closed))
            body_height = max(2, abs(y(opened) - y(closed)))
            elements.append(
                f'<line x1="{x:.2f}" y1="{y(high):.2f}" x2="{x:.2f}" y2="{y(low):.2f}" stroke="{color}" stroke-width="2"/>'
            )
            elements.append(
                f'<rect x="{x - body_width / 2:.2f}" y="{body_top:.2f}" width="{body_width:.2f}" height="{body_height:.2f}" fill="{color}" rx="2"/>'
            )
            short_label = label if len(label) <= 12 else f"{label[:11]}…"
            elements.append(
                f'<text x="{x:.2f}" y="{top + plot_height + 25}" text-anchor="middle" fill="#94a3b8" font-size="11">{short_label}</text>'
            )
        elements.append("</svg>")
        response = self._document(
            safe_title,
            "Candlestick chart · supplied OHLC data",
            "".join(elements),
            safe_labels,
            [("Open", opens), ("High", highs), ("Low", lows), ("Close", closes)],
            safe_symbol,
        )
        return response, {
            "status": "rendered",
            "chart_type": "candlestick",
            "title": html.unescape(safe_title),
            "points": count,
            "warning": "Chart uses supplied data only; verify source and timestamp before relying on it.",
        }
