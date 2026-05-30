#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST_PATH = ROOT / "data" / "latest.json"
AI_DEMAND_PATH = ROOT / "data" / "ai-demand.json"
NVIDIA_PATH = ROOT / "data" / "nvidia.json"
BIG_TECH_CAPEX_PATH = ROOT / "data" / "big-tech-capex.json"
POLYMARKET_PATH = ROOT / "data" / "polymarket.json"


def read_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def average_score(items, default=30):
    scores = [item.get("riskScore") for item in items if isinstance(item.get("riskScore"), (int, float))]
    if not scores:
        return default
    return sum(scores) / len(scores)


def replace_signal(signals, incoming):
    return [signal for signal in signals if signal.get("key") != incoming.get("key")] + [incoming]


def demand_signal(items):
    avg = average_score(items)
    if avg >= 70:
        emoji, value = "🔴", "AI需要リスク上昇"
    elif avg >= 40:
        emoji, value = "🟡", "AI投資の減速に注意"
    else:
        emoji, value = "🟢", "AI需要・投資は強い"
    return {
        "key": "demand",
        "label": "AI Demand",
        "emoji": emoji,
        "value": value,
        "help": "NVIDIAの需要指標とBig Techの設備投資を見ます。Big Tech CapexはAIデータセンター投資のproxyです。売上成長や設備投資が急減速すると、信用拡大を正当化しにくくなります。",
    }


def macro_earnings_signal(items):
    avg = average_score(items)
    if avg >= 70:
        emoji, value = "🔴", "企業業績に強い逆風"
    elif avg >= 40:
        emoji, value = "🟡", "企業業績の鈍化に注意"
    else:
        emoji, value = "🟢", "企業業績は底堅い"
    return {
        "key": "earnings",
        "label": "Corporate Earnings",
        "emoji": emoji,
        "value": value,
        "help": "SEC CompanyfactsからBig Techの売上成長率と営業利益率を見ます。マクロ環境が株式市場に効いているかを企業業績側から確認します。",
    }


def merge():
    latest = read_json(LATEST_PATH)
    if latest is None:
        raise RuntimeError("data/latest.json not found")

    ai_demand = read_json(AI_DEMAND_PATH)
    nvidia = read_json(NVIDIA_PATH)
    big_tech_capex = read_json(BIG_TECH_CAPEX_PATH)
    polymarket = read_json(POLYMARKET_PATH)
    merged = []

    base_score_history = latest.get("baseScoreHistory", latest.get("scoreHistory", []))
    score_history = [dict(item) for item in base_score_history]
    indicators = [
        item
        for item in latest.get("indicators", [])
        if item.get("block") not in ("demand", "prediction")
    ]
    signals = [
        signal
        for signal in latest.get("signals", [])
        if signal.get("key") not in ("demand", "prediction")
    ]

    demand_indicators = []
    if nvidia:
        demand_indicators.extend(nvidia.get("indicators", []))
        merged.append("nvidia")
    elif ai_demand:
        demand_indicators.extend(ai_demand.get("indicators", []))
        merged.append("ai-demand")
    if big_tech_capex:
        demand_indicators.extend(big_tech_capex.get("indicators", []))
        merged.append("big-tech-capex")

    if demand_indicators:
        demand_score = average_score(demand_indicators)
        if score_history:
            score_history[-1]["score"] = round(score_history[-1]["score"] * 0.9 + demand_score * 0.1)
        indicators.extend(demand_indicators)
        signals = replace_signal(signals, demand_signal(demand_indicators))

    if polymarket:
        prediction_indicators = polymarket.get("indicators", [])
        prediction_score = average_score(prediction_indicators)
        if score_history:
            score_history[-1]["score"] = round(score_history[-1]["score"] * 0.95 + prediction_score * 0.05)
        indicators.extend(prediction_indicators)
        if polymarket.get("signal"):
            signals = replace_signal(signals, polymarket["signal"])
        merged.append("polymarket")

    if big_tech_capex and latest.get("macro"):
        macro_indicators = big_tech_capex.get("macroIndicators", [])
        if macro_indicators:
            latest["macro"]["indicators"] = [
                item
                for item in latest["macro"].get("indicators", [])
                if item.get("block") != "earnings"
            ] + macro_indicators
            latest["macro"]["signals"] = replace_signal(
                latest["macro"].get("signals", []),
                macro_earnings_signal(macro_indicators),
            )
            if latest["macro"].get("scoreHistory"):
                earnings_score = average_score(macro_indicators)
                latest["macro"]["scoreHistory"][-1]["score"] = round(
                    latest["macro"]["scoreHistory"][-1]["score"] * 0.9 + earnings_score * 0.1
                )

    latest["baseScoreHistory"] = base_score_history
    latest["scoreHistory"] = score_history
    latest["signals"] = signals
    latest["indicators"] = indicators
    latest["externalDataMerged"] = merged

    LATEST_PATH.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Merged external data into {LATEST_PATH}")


if __name__ == "__main__":
    merge()
