#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST_PATH = ROOT / "data" / "latest.json"
AI_DEMAND_PATH = ROOT / "data" / "ai-demand.json"
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


def merge():
    latest = read_json(LATEST_PATH)
    if latest is None:
        raise RuntimeError("data/latest.json not found")

    ai_demand = read_json(AI_DEMAND_PATH)
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

    if ai_demand:
        ai_indicators = ai_demand.get("indicators", [])
        demand_score = average_score(ai_indicators)
        if score_history:
            score_history[-1]["score"] = round(score_history[-1]["score"] * 0.9 + demand_score * 0.1)
        indicators.extend(ai_indicators)
        if ai_demand.get("signal"):
            signals = replace_signal(signals, ai_demand["signal"])
        merged.append("ai-demand")

    if polymarket:
        prediction_indicators = polymarket.get("indicators", [])
        prediction_score = average_score(prediction_indicators)
        if score_history:
            score_history[-1]["score"] = round(score_history[-1]["score"] * 0.95 + prediction_score * 0.05)
        indicators.extend(prediction_indicators)
        if polymarket.get("signal"):
            signals = replace_signal(signals, polymarket["signal"])
        merged.append("polymarket")

    latest["baseScoreHistory"] = base_score_history
    latest["scoreHistory"] = score_history
    latest["signals"] = signals
    latest["indicators"] = indicators
    latest["externalDataMerged"] = merged

    LATEST_PATH.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Merged external data into {LATEST_PATH}")


if __name__ == "__main__":
    merge()
