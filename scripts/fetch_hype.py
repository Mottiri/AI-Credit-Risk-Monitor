#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "hype.json"
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
LLAMA_FEES_URL = "https://api.llama.fi/summary/fees/hyperliquid"
LLAMA_DEX_URL = "https://api.llama.fi/summary/dexs/hyperliquid"


def post_hyperliquid(body):
    request = Request(
        HL_INFO_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url):
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def format_usd(value):
    if value is None:
        return "n/a"
    value = float(value)
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


def format_price(value):
    return f"${float(value):,.2f}"


def format_pct(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_funding(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.4f}%"


def format_number(value):
    value = float(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def risk_item(emoji, class_name, score):
    return {"risk": emoji, "riskClass": class_name, "riskScore": score}


def market_risk(price_change, funding, oi_usd, day_volume):
    oi_to_volume = oi_usd / day_volume if day_volume else 0
    if funding > 0.00008 and price_change > 8 and oi_to_volume > 2:
        return risk_item("🟠", "risk-high", 68)
    if funding > 0.00004 and price_change > 4:
        return risk_item("🟡", "risk-watch", 48)
    return risk_item("🟢", "risk-low", 22)


def revenue_risk(change_7d, change_30d):
    if change_7d is not None and change_7d < -25:
        return risk_item("🟠", "risk-high", 68)
    if change_30d is not None and change_30d < -20:
        return risk_item("🟡", "risk-watch", 45)
    return risk_item("🟢", "risk-low", 20)


def strength_score(hype_ctx, revenue_summary, holders_summary, hip3):
    mark = float(hype_ctx["markPx"])
    prev = float(hype_ctx["prevDayPx"])
    price_change = (mark / prev - 1) * 100 if prev else 0
    funding = float(hype_ctx["funding"])
    revenue_30d = float(revenue_summary.get("total30d") or 0)
    holders_30d = float(holders_summary.get("total30d") or 0)
    hip3_volume = float(hip3.get("dayNtlVlm") or 0)

    score = 50
    if revenue_30d >= 50_000_000:
        score += 12
    if holders_30d >= 50_000_000:
        score += 10
    if hip3_volume >= 500_000_000:
        score += 8
    if price_change > 0:
        score += 5
    if funding > 0.00008 and price_change > 8:
        score -= 12
    if funding < -0.00008 and price_change < -8:
        score -= 10
    return max(0, min(100, round(score)))


def chart_from_llama(summary, days=30):
    chart = summary.get("totalDataChart", [])[-days:]
    return [
        {
            "date": datetime.fromtimestamp(point[0], timezone.utc).strftime("%Y-%m-%d"),
            "value": float(point[1] or 0),
        }
        for point in chart
    ]


def sum_hip3_contexts():
    dexs = [item for item in post_hyperliquid({"type": "perpDexs"}) if item]
    totals = {"dayNtlVlm": 0.0, "openInterestUsd": 0.0, "marketCount": 0, "activeMarketCount": 0}
    top_markets = []

    for dex in dexs:
        name = dex.get("name")
        if not name:
            continue
        try:
            meta, ctxs = post_hyperliquid({"type": "metaAndAssetCtxs", "dex": name})
        except Exception:
            continue
        for asset, ctx in zip(meta.get("universe", []), ctxs):
            volume = float(ctx.get("dayNtlVlm") or 0)
            oi_base = float(ctx.get("openInterest") or 0)
            mark = float(ctx.get("markPx") or ctx.get("oraclePx") or 0)
            oi_usd = oi_base * mark
            totals["dayNtlVlm"] += volume
            totals["openInterestUsd"] += oi_usd
            totals["marketCount"] += 1
            if volume > 0:
                totals["activeMarketCount"] += 1
            top_markets.append(
                {
                    "name": asset.get("name", ""),
                    "volume": volume,
                    "openInterestUsd": oi_usd,
                    "markPx": mark,
                }
            )

    top_markets.sort(key=lambda item: item["volume"], reverse=True)
    totals["topMarkets"] = top_markets[:8]
    return totals


def get_hype_context():
    meta, ctxs = post_hyperliquid({"type": "metaAndAssetCtxs"})
    for asset, ctx in zip(meta.get("universe", []), ctxs):
        if asset.get("name") == "HYPE":
            return asset, ctx
    raise RuntimeError("HYPE perp context not found")


def build():
    _, hype_ctx = get_hype_context()
    fees = get_json(LLAMA_FEES_URL)
    revenue = get_json(f"{LLAMA_FEES_URL}?dataType=dailyRevenue")
    holders = get_json(f"{LLAMA_FEES_URL}?dataType=dailyHoldersRevenue")
    dex_volume = get_json(LLAMA_DEX_URL)
    hip3 = sum_hip3_contexts()

    mark = float(hype_ctx["markPx"])
    prev = float(hype_ctx["prevDayPx"])
    funding = float(hype_ctx["funding"])
    day_volume = float(hype_ctx["dayNtlVlm"])
    oi_base = float(hype_ctx["openInterest"])
    oi_usd = oi_base * mark
    price_change = (mark / prev - 1) * 100 if prev else None
    market = market_risk(price_change or 0, funding, oi_usd, day_volume)
    revenue_meta = revenue_risk(revenue.get("chainBreakdown", {}).get("Hyperliquid L1", {}).get("change_7d"), revenue.get("chainBreakdown", {}).get("Hyperliquid L1", {}).get("change_1m"))
    score = strength_score(hype_ctx, revenue, holders, hip3)

    score_history = [
        {"date": item["date"], "score": score}
        for item in chart_from_llama(revenue, 30)
    ]

    indicators = [
        {
            "id": "HYPE-PRICE",
            "name": "HYPE Perp Mark Price",
            "help": "Hyperliquid公式APIのHYPE perp mark priceです。短期の市場評価として見ます。",
            "latest": format_price(mark),
            "latestRaw": mark,
            "previousChange": format_pct(price_change),
            "previousChangeRaw": price_change,
            "yoy": "n/a",
            "risk": market["risk"],
            "riskClass": market["riskClass"],
            "riskScore": market["riskScore"],
            "nextRelease": "Live",
            "block": "market",
        },
        {
            "id": "HYPE-PERP-OI",
            "name": "HYPE Perp Open Interest",
            "help": "HYPE perpの建玉です。価格上昇とOI急増、Funding上昇が重なると短期過熱に注意します。",
            "latest": format_usd(oi_usd),
            "latestRaw": oi_usd,
            "previousChange": f"{format_number(oi_base)} HYPE",
            "previousChangeRaw": oi_base,
            "yoy": "n/a",
            "risk": market["risk"],
            "riskClass": market["riskClass"],
            "riskScore": market["riskScore"],
            "nextRelease": "Live",
            "block": "market",
        },
        {
            "id": "HYPE-FUNDING",
            "name": "HYPE Perp Funding",
            "help": "HYPE perpのFundingです。プラスが大きいほどロング過熱、マイナスが大きいほどショート過熱を示しやすいです。",
            "latest": format_funding(funding),
            "latestRaw": funding,
            "previousChange": "Live",
            "previousChangeRaw": None,
            "yoy": "n/a",
            "risk": market["risk"],
            "riskClass": market["riskClass"],
            "riskScore": market["riskScore"],
            "nextRelease": "Live",
            "block": "market",
        },
        {
            "id": "HYPE-PERP-VOLUME",
            "name": "HYPE Perp 24h Volume",
            "help": "HYPE perp単体の24時間名目出来高です。流動性と投機需要の強さを見ます。",
            "latest": format_usd(day_volume),
            "latestRaw": day_volume,
            "previousChange": "24h",
            "previousChangeRaw": None,
            "yoy": "n/a",
            "risk": "🟢",
            "riskClass": "risk-low",
            "riskScore": 20,
            "nextRelease": "Live",
            "block": "market",
        },
        {
            "id": "HL-REVENUE-24H",
            "name": "Hyperliquid Revenue 24h",
            "help": "DeFiLlamaのHyperliquid revenueです。取引所ビジネスとしての収益力を見ます。",
            "latest": format_usd(revenue.get("total24h")),
            "latestRaw": revenue.get("total24h"),
            "previousChange": format_pct(revenue.get("change_1d")),
            "previousChangeRaw": revenue.get("change_1d"),
            "yoy": format_usd(revenue.get("total30d")),
            "risk": revenue_meta["risk"],
            "riskClass": revenue_meta["riskClass"],
            "riskScore": revenue_meta["riskScore"],
            "nextRelease": "Daily",
            "block": "revenue",
        },
        {
            "id": "HL-HOLDERS-REVENUE-30D",
            "name": "Holders Revenue / Buyback Pressure 30d",
            "help": "HYPE保有者への価値還元に近いRevenueです。MVPではbuyback pressureのproxyとして使います。",
            "latest": format_usd(holders.get("total30d")),
            "latestRaw": holders.get("total30d"),
            "previousChange": format_pct(holders.get("chainBreakdown", {}).get("Hyperliquid L1", {}).get("change_1m")),
            "previousChangeRaw": holders.get("chainBreakdown", {}).get("Hyperliquid L1", {}).get("change_1m"),
            "yoy": format_usd(holders.get("totalAllTime")),
            "risk": revenue_meta["risk"],
            "riskClass": revenue_meta["riskClass"],
            "riskScore": revenue_meta["riskScore"],
            "nextRelease": "Daily",
            "block": "revenue",
        },
        {
            "id": "HL-DEX-VOLUME-24H",
            "name": "Hyperliquid Spot DEX Volume 24h",
            "help": "DeFiLlamaのHyperliquid spot DEX volumeです。perp以外の取引活動を見る補助指標です。",
            "latest": format_usd(dex_volume.get("total24h")),
            "latestRaw": dex_volume.get("total24h"),
            "previousChange": format_pct(dex_volume.get("change_1d")),
            "previousChangeRaw": dex_volume.get("change_1d"),
            "yoy": format_usd(dex_volume.get("total30d")),
            "risk": "🟢" if (dex_volume.get("total30d") or 0) > 1_000_000_000 else "🟡",
            "riskClass": "risk-low" if (dex_volume.get("total30d") or 0) > 1_000_000_000 else "risk-watch",
            "riskScore": 25 if (dex_volume.get("total30d") or 0) > 1_000_000_000 else 45,
            "nextRelease": "Daily",
            "block": "volume",
        },
        {
            "id": "HIP3-VOLUME-24H",
            "name": "HIP-3 24h Volume",
            "help": "Hyperliquid公式APIで取得したHIP-3 builder-deployed perpsの24時間出来高合計です。Hyperliquidの非クリプト/拡張市場の成長を見る指標です。",
            "latest": format_usd(hip3["dayNtlVlm"]),
            "latestRaw": hip3["dayNtlVlm"],
            "previousChange": f"{hip3['activeMarketCount']} active markets",
            "previousChangeRaw": hip3["activeMarketCount"],
            "yoy": format_usd(hip3["openInterestUsd"]),
            "risk": "🟢" if hip3["dayNtlVlm"] >= 500_000_000 else "🟡",
            "riskClass": "risk-low" if hip3["dayNtlVlm"] >= 500_000_000 else "risk-watch",
            "riskScore": 25 if hip3["dayNtlVlm"] >= 500_000_000 else 45,
            "nextRelease": "Live",
            "block": "hip3",
        },
    ]

    signals = [
        {
            "key": "revenue",
            "label": "Revenue",
            "emoji": revenue_meta["risk"],
            "value": f"24h {format_usd(revenue.get('total24h'))}",
            "help": "HyperliquidのRevenue推移を見ます。30日Revenueが伸びているほどHYPEのファンダは強くなります。",
        },
        {
            "key": "buyback",
            "label": "Buyback Pressure",
            "emoji": revenue_meta["risk"],
            "value": f"30d {format_usd(holders.get('total30d'))}",
            "help": "Holders RevenueをHYPE買い戻し圧力のproxyとして見ます。",
        },
        {
            "key": "market",
            "label": "Perp Market",
            "emoji": market["risk"],
            "value": f"OI {format_usd(oi_usd)} / Funding {format_funding(funding)}",
            "help": "HYPE perpのOI、Funding、価格変化を見ます。ロング過熱やショート過熱の確認材料です。",
        },
        {
            "key": "hip3",
            "label": "HIP-3",
            "emoji": "🟢" if hip3["dayNtlVlm"] >= 500_000_000 else "🟡",
            "value": f"{format_usd(hip3['dayNtlVlm'])} / 24h",
            "help": "HIP-3市場の出来高とOIを見ます。Hyperliquidがクリプト外の取引需要を取り込めているかを確認します。",
        },
    ]

    return {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "scoreHistory": score_history,
        "signals": signals,
        "indicators": indicators,
        "charts": {
            "revenue": chart_from_llama(revenue, 30),
            "holdersRevenue": chart_from_llama(holders, 30),
            "dexVolume": chart_from_llama(dex_volume, 30),
            "fees": chart_from_llama(fees, 30),
        },
        "hip3": hip3,
        "sources": [
            "https://api.hyperliquid.xyz/info",
            "https://api.llama.fi/summary/fees/hyperliquid",
            "https://api.llama.fi/summary/dexs/hyperliquid",
        ],
    }


def main():
    output = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
