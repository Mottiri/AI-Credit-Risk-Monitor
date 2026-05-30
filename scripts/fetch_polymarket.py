#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "polymarket.json"
EVENT_URL = "https://gamma-api.polymarket.com/events/slug/ai-bubble-burst-by"
MARKET_URL = "https://polymarket.com/event/ai-bubble-burst-by?outcomeIndex=0"


def fetch_event():
    request = Request(
        EVENT_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Credit-Risk-Monitor/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def as_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_outcome_price(market, outcome="Yes"):
    outcomes = json.loads(market.get("outcomes", "[]"))
    prices = json.loads(market.get("outcomePrices", "[]"))
    if outcome not in outcomes:
        raise RuntimeError(f"{outcome} outcome not found")
    return as_float(prices[outcomes.index(outcome)], 0)


def risk_for_probability(probability, one_day_change, one_week_change):
    if probability >= 50:
        emoji, risk_class, score = "🔴", "risk-danger", 90
    elif probability >= 35:
        emoji, risk_class, score = "🟠", "risk-high", 70
    elif probability >= 20:
        emoji, risk_class, score = "🟡", "risk-watch", 45
    else:
        emoji, risk_class, score = "🟢", "risk-low", 20

    # Prediction markets are noisy, so the level is only part of the signal.
    # A fast repricing is important even if the absolute probability is modest.
    if one_day_change >= 5 or one_week_change >= 10:
        return "🟠", "risk-high", max(score, 70)
    if one_day_change >= 3 or one_week_change >= 6:
        return "🟡", "risk-watch", max(score, 45)
    return emoji, risk_class, score


def format_pct(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def format_probability(value):
    return f"{value:.1f}%"


def format_point(value, suffix="pt"):
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}{suffix}"


def format_usd(value):
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


def load_existing_history():
    if not OUT_PATH.exists():
        return []
    try:
        return json.loads(OUT_PATH.read_text(encoding="utf-8")).get("history", [])
    except json.JSONDecodeError:
        return []


def update_history(history, point):
    history = [item for item in history if item.get("date") != point["date"]]
    history.append(point)
    return history[-90:]


def main():
    event = fetch_event()
    markets = event.get("markets", [])
    active_market = next(
        (
            market
            for market in markets
            if not market.get("closed")
            and "2026" in str(market.get("question", "") + market.get("groupItemTitle", ""))
        ),
        None,
    )
    if not active_market:
        raise RuntimeError("Active 2026 AI bubble market not found")

    probability = parse_outcome_price(active_market) * 100
    one_day_change = as_float(active_market.get("oneDayPriceChange"), 0) * 100
    one_week_change = as_float(active_market.get("oneWeekPriceChange"), 0) * 100
    one_month_change = as_float(active_market.get("oneMonthPriceChange"), 0) * 100
    volume_24h = as_float(active_market.get("volume24hr"), 0)
    volume_1wk = as_float(active_market.get("volume1wk"), 0)
    total_volume = as_float(active_market.get("volume"), 0)
    liquidity = as_float(active_market.get("liquidity") or active_market.get("liquidityClob"), 0)
    best_bid = as_float(active_market.get("bestBid"))
    best_ask = as_float(active_market.get("bestAsk"))
    spread = as_float(active_market.get("spread"))

    risk, risk_class, risk_score = risk_for_probability(probability, one_day_change, one_week_change)
    now = datetime.now(timezone.utc).astimezone()
    history = update_history(
        load_existing_history(),
        {
            "date": now.date().isoformat(),
            "probability": round(probability, 2),
            "volume24h": round(volume_24h, 2),
        },
    )

    output = {
        "updatedAt": now.isoformat(timespec="minutes"),
        "source": "Polymarket Gamma API",
        "sourceUrl": MARKET_URL,
        "signal": {
            "key": "prediction",
            "label": "Prediction Market",
            "emoji": risk,
            "value": f"AIバブル崩壊予測 {probability:.1f}%",
            "help": "Polymarket参加者がAIバブル崩壊リスクをどう価格付けしているかを見る市場心理指標です。実体データではないため、総合スコアへの影響は軽めにします。水準よりも24時間・7日での急変を重視します。",
        },
        "indicators": [
            {
                "id": "POLYMARKET-AI-BUBBLE",
                "name": "AI bubble burst by Dec 31, 2026",
                "help": "Polymarket上のAIバブル崩壊予測です。Yes確率が上がるほど、市場参加者がAI関連の急な調整を意識していることを示します。20%超で注意、35%超で高めの警戒、50%超で予測市場も本格警戒と見ます。24hで+5pt、7日で+10ptのような急上昇は特に重要です。",
                "latest": format_probability(probability),
                "latestRaw": probability,
                "date": active_market.get("updatedAt") or event.get("updatedAt"),
                "previousChange": f"{format_point(one_day_change)} / 24h",
                "previousChangeRaw": one_day_change,
                "yoy": f"{format_point(one_week_change)} / 7d",
                "yoyRaw": one_week_change,
                "risk": risk,
                "riskClass": risk_class,
                "riskScore": risk_score,
                "nextRelease": "Scheduled",
                "block": "prediction",
                "volume24h": format_usd(volume_24h),
                "volume1wk": format_usd(volume_1wk),
                "totalVolume": format_usd(total_volume),
                "liquidity": format_usd(liquidity),
                "bestBid": best_bid,
                "bestAsk": best_ask,
                "spread": spread,
                "oneMonthChange": one_month_change,
            }
        ],
        "history": history,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
