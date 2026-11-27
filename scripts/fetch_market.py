#!/usr/bin/env python3
"""Fetch daily market prices for major AI-related stocks and score drawdowns.

Prices are the fastest-moving public signal of how the market is repricing
AI-infrastructure risk. SEC/FRED fundamentals in the other fetchers are
quarterly or monthly and cannot react to a selloff for weeks, so this script
adds a daily "market" block:

- AI-BASKET-DRAWDOWN: equal-weight average drawdown from 52-week highs
  across the major AI names (NVDA, AVGO, MSFT, GOOGL, META, AMZN, ORCL,
  PLTR) and the semiconductor ETF SMH.
- NVDA-DRAWDOWN / SMH-DRAWDOWN / ORCL-DRAWDOWN: headline drawdowns.
  ORCL is watched separately because Oracle sits at the center of the
  Stargate financing chain.
- CRWV-DRAWDOWN: CoreWeave as a credit thermometer. Single-name CDS for
  neoclouds is not available from free sources, so the equity drawdown is
  used as a proxy for how the market prices neocloud credit risk.

Data source: Yahoo Finance chart API (no API key required). If every
ticker fails, the previous data/market.json is left untouched and the
script exits non-zero so the failure is visible in the workflow log.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "market.json"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
USER_AGENT = "Mozilla/5.0 (compatible; AI-Credit-Risk-Monitor/1.0)"

BASKET_TICKERS = ["NVDA", "AVGO", "MSFT", "GOOGL", "META", "AMZN", "ORCL", "PLTR", "SMH"]

# Drawdown thresholds are in percent below the 52-week high.
# (watch, high, danger)
BASKET_THRESHOLDS = (15, 25, 35)
NAME_THRESHOLDS = (15, 25, 35)
ORCL_THRESHOLDS = (20, 35, 50)
CRWV_THRESHOLDS = (40, 55, 70)


def risk_for_drawdown(drawdown_pct, thresholds):
    """drawdown_pct is negative (e.g. -32.5). Deeper drawdown = higher risk."""
    depth = abs(drawdown_pct)
    watch, high, danger = thresholds
    if depth >= danger:
        return ("🔴", "risk-danger", 90)
    if depth >= high:
        return ("🟠", "risk-high", 70)
    if depth >= watch:
        return ("🟡", "risk-watch", 45)
    return ("🟢", "risk-low", 20)


def fetch_chart(ticker):
    request = Request(CHART_URL.format(ticker=ticker), headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    else:
        raise last_error

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    closes = quote.get("close") or []
    highs = quote.get("high") or []

    points = [
        (ts, close)
        for ts, close in zip(timestamps, closes)
        if close is not None
    ]
    if len(points) < 70:
        raise RuntimeError(f"Not enough price points for {ticker}: {len(points)}")

    valid_highs = [h for h in highs if h is not None]
    latest_ts, latest_close = points[-1]
    high_52w = max(valid_highs) if valid_highs else max(close for _, close in points)
    drawdown = (latest_close / high_52w - 1) * 100 if high_52w else 0.0

    def change(days_back):
        if len(points) <= days_back:
            return None
        past_close = points[-1 - days_back][1]
        return (latest_close / past_close - 1) * 100 if past_close else None

    return {
        "ticker": ticker,
        "date": datetime.fromtimestamp(latest_ts, tz=timezone.utc).strftime("%Y-%m-%d"),
        "close": latest_close,
        "high52w": high_52w,
        "drawdown": drawdown,
        "change1m": change(21),
        "change3m": change(63),
    }


def fmt_pct(value, digits=1):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def drawdown_indicator(ind_id, name, help_text, drawdown, change1m, change3m, date, thresholds):
    risk, risk_class, score = risk_for_drawdown(drawdown, thresholds)
    return {
        "id": ind_id,
        "name": name,
        "help": help_text,
        "latest": fmt_pct(drawdown),
        "latestRaw": round(drawdown, 2),
        "date": date,
        "previousChange": fmt_pct(change1m),
        "previousChangeRaw": round(change1m, 2) if change1m is not None else None,
        "yoy": fmt_pct(change3m),
        "yoyRaw": round(change3m, 2) if change3m is not None else None,
        "risk": risk,
        "riskClass": risk_class,
        "riskScore": score,
        "nextRelease": "Daily",
        "block": "market",
    }


def market_signal(indicators):
    scores = [item["riskScore"] for item in indicators]
    avg = sum(scores) / len(scores) if scores else 30
    if avg >= 80:
        emoji, value = "🔴", "株価が信用リスクを強く織り込み中"
    elif avg >= 60:
        emoji, value = "🟠", "株価の下落が目立つ"
    elif avg >= 35:
        emoji, value = "🟡", "株価は調整局面"
    else:
        emoji, value = "🟢", "株価は堅調"
    return {
        "key": "market",
        "label": "Market Prices",
        "emoji": emoji,
        "value": value,
        "help": "AI主要銘柄とCoreWeave等の株価（52週高値からの下落率）を見ます。決算やFREDの月次データより速く動くため、信用リスクの再評価を先行して捉えるための指標です。",
    }


def main():
    stocks = {}
    failures = []
    for ticker in BASKET_TICKERS + ["CRWV"]:
        try:
            stocks[ticker] = fetch_chart(ticker)
        except Exception as exc:  # keep going; partial data is still useful
            failures.append(f"{ticker}: {exc}")
            print(f"Warning: failed to fetch {ticker}: {exc}", file=sys.stderr)

    basket = [stocks[ticker] for ticker in BASKET_TICKERS if ticker in stocks]
    if len(basket) < 5:
        print(f"Too few basket tickers fetched ({len(basket)}). Keeping previous market.json.", file=sys.stderr)
        return 1

    avg_drawdown = sum(item["drawdown"] for item in basket) / len(basket)
    avg_1m = sum(item["change1m"] for item in basket if item["change1m"] is not None) / len(basket)
    avg_3m = sum(item["change3m"] for item in basket if item["change3m"] is not None) / len(basket)
    latest_date = max(item["date"] for item in basket)

    indicators = [
        drawdown_indicator(
            "AI-BASKET-DRAWDOWN",
            "AI Stocks Avg Drawdown from 52w High",
            "AI主要銘柄（NVDA、AVGO、MSFT、GOOGL、META、AMZN、ORCL、PLTR、SMH）の52週高値からの下落率の平均です。前回比はバスケットの1か月騰落率、前年比欄は3か月騰落率を表示します。-25%超で本格的な調整、-35%超で信用市場への波及を警戒します。",
            avg_drawdown, avg_1m, avg_3m, latest_date, BASKET_THRESHOLDS,
        ),
        drawdown_indicator(
            "NVDA-DRAWDOWN",
            "NVIDIA Drawdown from 52w High",
            "NVIDIA株価の52週高値からの下落率です。AIインフラ需要の期待が剥落している度合いを価格側から見ます。",
            stocks["NVDA"]["drawdown"], stocks["NVDA"]["change1m"], stocks["NVDA"]["change3m"],
            stocks["NVDA"]["date"], NAME_THRESHOLDS,
        ),
        drawdown_indicator(
            "SMH-DRAWDOWN",
            "Semiconductor ETF (SMH) Drawdown",
            "半導体ETF（SMH）の52週高値からの下落率です。半導体サイクルの価格側の温度計として、SECベースのファンダメンタルズ指標の遅行を補います。",
            stocks["SMH"]["drawdown"], stocks["SMH"]["change1m"], stocks["SMH"]["change3m"],
            stocks["SMH"]["date"], NAME_THRESHOLDS,
        ),
        drawdown_indicator(
            "ORCL-DRAWDOWN",
            "Oracle Drawdown from 52w High",
            "Oracle株価の52週高値からの下落率です。OracleはStargateの資金調達チェーンの中心にいるため、AI債務への市場の見方を映しやすい銘柄です。",
            stocks["ORCL"]["drawdown"], stocks["ORCL"]["change1m"], stocks["ORCL"]["change3m"],
            stocks["ORCL"]["date"], ORCL_THRESHOLDS,
        ),
    ]

    if "CRWV" in stocks:
        crwv = stocks["CRWV"]
        indicators.append(
            drawdown_indicator(
                "CRWV-DRAWDOWN",
                "CoreWeave Drawdown (Credit Thermometer)",
                "CoreWeave株価の52週高値からの下落率です。ネオクラウドのCDSは無料データがないため、株価の下落率を信用リスクの体温計として使います。同社は変動金利の債務が大きく、下落率-55%超は市場が信用不安をかなり織り込んでいる目安です。",
                crwv["drawdown"], crwv["change1m"], crwv["change3m"], crwv["date"], CRWV_THRESHOLDS,
            )
        )
    else:
        print("Warning: CRWV unavailable; continuing without the credit thermometer.", file=sys.stderr)

    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "signal": market_signal(indicators),
        "indicators": indicators,
        "stocks": {
            ticker: {
                "date": item["date"],
                "close": round(item["close"], 2),
                "high52w": round(item["high52w"], 2),
                "drawdown": round(item["drawdown"], 2),
                "change1m": round(item["change1m"], 2) if item["change1m"] is not None else None,
                "change3m": round(item["change3m"], 2) if item["change3m"] is not None else None,
            }
            for ticker, item in stocks.items()
        },
    }
    if failures:
        output["fetchWarnings"] = failures

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
