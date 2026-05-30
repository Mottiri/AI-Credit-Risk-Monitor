#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "latest.json"

AI_SERIES = [
    {
        "id": "LNFACBM027SBOG",
        "name": "Loans to Nondepository Financial Institutions",
        "help": "銀行からノンバンク金融機関への貸出残高です。AI/private creditへお金が流れているかを見るproxyです。前年比+20%超は、経済成長よりかなり速く信用が膨らんでいる目安。高止まりは過熱、急減速や残高減少は信用収縮に注意です。",
        "unit": "B",
        "frequency": "Monthly",
        "block": "credit",
        "higher_is_risk": True,
        "change_unit": "%",
        "risk_thresholds": {"watch": 8, "high": 15, "danger": 22},
    },
    {
        "id": "BAMLH0A0HYM2",
        "name": "ICE BofA High Yield OAS",
        "help": "信用力が低めの企業が借りる時の追加金利です。4%超で投資家がリスクを意識、5.5%超で信用不安がはっきり、7%超でデフォルトや景気悪化を強く織り込む水準です。",
        "unit": "%",
        "frequency": "Daily",
        "block": "stress",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.0, "high": 5.5, "danger": 7.0},
    },
    {
        "id": "STLFSI4",
        "name": "St. Louis Fed Financial Stress Index",
        "help": "金融市場全体の体温計のような指数です。マイナスなら平常、0超で平均よりストレス高め、0.8超で複数市場に不安、1.6超でかなり強いストレスと見ます。",
        "unit": "",
        "frequency": "Weekly",
        "block": "stress",
        "higher_is_risk": True,
        "change_unit": "",
        "risk_thresholds": {"watch": 0.0, "high": 0.8, "danger": 1.6},
    },
    {
        "id": "VIXCLS",
        "name": "CBOE Volatility Index",
        "help": "株式市場の不安度を見る指数です。20超で不安定、30超で投資家がかなり警戒、40超で急落・危機局面に近い水準です。HYスプレッドや金融ストレスと同時に上がると重要です。",
        "unit": "",
        "frequency": "Daily",
        "block": "stress",
        "higher_is_risk": True,
        "change_unit": "",
        "risk_thresholds": {"watch": 20, "high": 30, "danger": 40},
    },
    {
        "id": "DGS10",
        "name": "10-Year Treasury Yield",
        "help": "米10年国債利回りです。長期の借入コストの目安です。4.5%超で資金調達が重くなり始め、5%超でデータセンター投資の採算に圧力、5.5%超で借金依存の成長にかなり厳しい水準です。",
        "unit": "%",
        "frequency": "Daily",
        "block": "rates",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 5.5},
    },
    {
        "id": "DGS2",
        "name": "2-Year Treasury Yield",
        "help": "米2年国債利回りです。今後数年の高金利見通しに敏感です。高止まりすると短期借入や借り換えコストが重くなり、AIインフラやprivate creditの負担になります。",
        "unit": "%",
        "frequency": "Daily",
        "block": "rates",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 5.5},
    },
    {
        "id": "WTREGEN",
        "name": "Treasury General Account at the Fed",
        "help": "米財務省のFRB口座残高です。TGAが増えると、市場から資金を吸い上げやすくなります。800B超で注意、1T超で高リスク、1.2T超で流動性の重さを強く警戒します。",
        "unit": "M",
        "frequency": "Weekly",
        "block": "liquidity",
        "higher_is_risk": True,
        "change_unit": "B",
        "risk_thresholds": {"watch": 800000, "high": 1000000, "danger": 1200000},
    },
    {
        "id": "RRPONTSYD",
        "name": "Overnight Reverse Repurchase Agreements",
        "help": "マネーマーケット資金がFRBに退避している残高です。多い時は余剰流動性のクッションになります。250B割れで注意、100B割れで高リスク、25B割れでクッション枯渇を警戒します。",
        "unit": "B",
        "frequency": "Daily",
        "block": "liquidity",
        "higher_is_risk": False,
        "change_unit": "B",
        "risk_thresholds": {"watch": 250, "high": 100, "danger": 25},
    },
    {
        "id": "WRESBAL",
        "name": "Reserve Balances with Federal Reserve Banks",
        "help": "銀行がFRBに置いている準備預金です。金融システムの余裕を示します。3.2T割れで注意、3.0T割れで高リスク、2.8T割れで流動性の薄さを強く警戒します。",
        "unit": "M",
        "frequency": "Weekly",
        "block": "liquidity",
        "higher_is_risk": False,
        "change_unit": "B",
        "risk_thresholds": {"watch": 3200000, "high": 3000000, "danger": 2800000},
    },
]

MACRO_SERIES = [
    {
        "id": "CPIAUCSL",
        "name": "Consumer Price Index",
        "help": "米国の消費者物価指数です。前年比が3%を超えるとインフレ再燃を意識しやすく、4%超で株式市場には金利高止まりリスク、5%超でかなり強い逆風と見ます。",
        "unit": "",
        "frequency": "Monthly",
        "block": "inflation",
        "higher_is_risk": True,
        "change_unit": "%",
        "risk_basis": "yoy",
        "risk_thresholds": {"watch": 3.0, "high": 4.0, "danger": 5.0},
    },
    {
        "id": "CPILFESL",
        "name": "Core CPI",
        "help": "食品とエネルギーを除いた物価指数です。粘着的なインフレを見るため重要です。前年比3%超で注意、4%超で金融引き締め長期化、5%超で株式市場には強い逆風と見ます。",
        "unit": "",
        "frequency": "Monthly",
        "block": "inflation",
        "higher_is_risk": True,
        "change_unit": "%",
        "risk_basis": "yoy",
        "risk_thresholds": {"watch": 3.0, "high": 4.0, "danger": 5.0},
    },
    {
        "id": "PPIACO",
        "name": "Producer Price Index",
        "help": "企業側の仕入れ・生産コストを見る物価指数です。CPIに先行してインフレ圧力を示すことがあります。前年比3%超で注意、5%超で高リスク、8%超で強いインフレ圧力と見ます。",
        "unit": "",
        "frequency": "Monthly",
        "block": "inflation",
        "higher_is_risk": True,
        "change_unit": "%",
        "risk_basis": "yoy",
        "risk_thresholds": {"watch": 3.0, "high": 5.0, "danger": 8.0},
    },
    {
        "id": "DGS10",
        "name": "10-Year Treasury Yield",
        "help": "株式の割引率に効く長期金利です。4.5%超でバリュエーションの重荷、5%超で成長株に強い圧力、5.5%超でかなり厳しい金利環境と見ます。",
        "unit": "%",
        "frequency": "Daily",
        "block": "rates",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 5.5},
    },
    {
        "id": "DGS2",
        "name": "2-Year Treasury Yield",
        "help": "政策金利見通しに敏感な短期金利です。高止まりすると利下げ期待が後退し、株式市場には逆風です。4.5%超で注意、5%超で高リスク、5.5%超で危険水準と見ます。",
        "unit": "%",
        "frequency": "Daily",
        "block": "rates",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 5.5},
    },
    {
        "id": "FEDFUNDS",
        "name": "Effective Federal Funds Rate",
        "help": "米国の実効政策金利です。高いほど株式市場にとっては資金調達・割引率の重荷です。4.5%超で注意、5%超で高リスク、5.5%超でかなり強い逆風と見ます。",
        "unit": "%",
        "frequency": "Monthly",
        "block": "rates",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 5.5},
    },
    {
        "id": "UNRATE",
        "name": "Unemployment Rate",
        "help": "米国の失業率です。低すぎる時は利下げしにくく、高すぎる時は景気悪化懸念になります。ここでは景気悪化リスクとして4.5%超で注意、5%超で高リスク、6%超で危険水準と見ます。",
        "unit": "%",
        "frequency": "Monthly",
        "block": "growth",
        "higher_is_risk": True,
        "change_unit": "pt",
        "risk_thresholds": {"watch": 4.5, "high": 5.0, "danger": 6.0},
    },
    {
        "id": "VIXCLS",
        "name": "CBOE Volatility Index",
        "help": "株式市場の不安度を見る指数です。20超で不安定、30超で投資家がかなり警戒、40超で急落・危機局面に近い水準です。",
        "unit": "",
        "frequency": "Daily",
        "block": "volatility",
        "higher_is_risk": True,
        "change_unit": "",
        "risk_thresholds": {"watch": 20, "high": 30, "danger": 40},
    },
]


def load_env_file():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def fred_observations(series_id, api_key):
    params = urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 420,
        }
    )
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(f"{FRED_BASE_URL}?{params}", timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            retryable_http = isinstance(exc, HTTPError) and exc.code in {429, 500, 502, 503, 504}
            retryable_url = isinstance(exc, (URLError, TimeoutError))
            if attempt == 3 or not (retryable_http or retryable_url):
                raise
            time.sleep(2 * (attempt + 1))
    else:
        raise last_error

    observations = []
    for obs in reversed(payload.get("observations", [])):
        value = obs.get("value")
        if value in (None, "."):
            continue
        try:
            observations.append({"date": obs["date"], "value": float(value)})
        except ValueError:
            continue
    if len(observations) < 2:
        raise RuntimeError(f"Not enough observations for {series_id}")
    return observations


def pct_change(current, previous):
    if previous == 0:
        return None
    return (current / previous - 1) * 100


def find_year_ago(observations):
    latest = observations[-1]
    latest_year = int(latest["date"][:4])
    target_prefix = f"{latest_year - 1}{latest['date'][4:7]}"
    candidates = [obs for obs in observations if obs["date"].startswith(target_prefix)]
    if candidates:
        return candidates[-1]
    if len(observations) > 252:
        return observations[-253]
    if len(observations) > 12:
        return observations[-13]
    return None


def risk_for_value(value, thresholds):
    if value >= thresholds["danger"]:
        return ("🔴", "risk-danger", 90)
    if value >= thresholds["high"]:
        return ("🟠", "risk-high", 70)
    if value >= thresholds["watch"]:
        return ("🟡", "risk-watch", 45)
    return ("🟢", "risk-low", 20)


def risk_for_low_value(value, thresholds):
    if value <= thresholds["danger"]:
        return ("🔴", "risk-danger", 90)
    if value <= thresholds["high"]:
        return ("🟠", "risk-high", 70)
    if value <= thresholds["watch"]:
        return ("🟡", "risk-watch", 45)
    return ("🟢", "risk-low", 20)


def format_value(value, unit):
    if unit == "M":
        billions = value / 1000
        if abs(billions) >= 1000:
            return f"{billions / 1000:.2f}T"
        return f"{billions:.0f}B"
    if unit == "B":
        if abs(value) >= 1000:
            return f"{value / 1000:.2f}T"
        return f"{value:.0f}B"
    if unit == "%":
        return f"{value:.2f}%"
    if abs(value) >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}"


def format_change(value, unit, source_unit=None):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    if unit == "%":
        return f"{sign}{value:.1f}%"
    if unit == "pt":
        return f"{sign}{value:.2f}pt"
    if unit == "B":
        display_value = value / 1000 if source_unit == "M" else value
        if abs(display_value) >= 10:
            return f"{sign}{display_value:.0f}B"
        return f"{sign}{display_value:.1f}B"
    return f"{sign}{value:.2f}"


def build_indicator(config, observations):
    latest = observations[-1]
    previous = observations[-2]
    year_ago = find_year_ago(observations)

    latest_value = latest["value"]
    previous_change = latest_value - previous["value"]
    yoy = pct_change(latest_value, year_ago["value"]) if year_ago else None
    risk_basis_type = config.get("risk_basis", "latest")
    if risk_basis_type == "yoy" and yoy is not None:
        risk_basis = yoy
    elif risk_basis_type == "previous_change":
        risk_basis = previous_change
    elif config["id"] == "LNFACBM027SBOG" and yoy is not None:
        risk_basis = yoy
    else:
        risk_basis = latest_value
    if config.get("higher_is_risk", True):
        risk, risk_class, score = risk_for_value(risk_basis, config["risk_thresholds"])
    else:
        risk, risk_class, score = risk_for_low_value(risk_basis, config["risk_thresholds"])

    return {
        "id": config["id"],
        "name": config["name"],
        "help": config.get("help", ""),
        "latest": format_value(latest_value, config["unit"]),
        "latestRaw": latest_value,
        "date": latest["date"],
        "previousChange": format_change(
            pct_change(latest_value, previous["value"]) if config["change_unit"] == "%" else previous_change,
            config["change_unit"],
            config["unit"],
        ),
        "previousChangeRaw": previous_change,
        "yoy": format_change(yoy, "%") if yoy is not None else "n/a",
        "yoyRaw": yoy,
        "risk": risk,
        "riskClass": risk_class,
        "riskScore": score,
        "nextRelease": config["frequency"],
        "block": config["block"],
    }


def build_credit_yoy(observations):
    points = []
    for index, obs in enumerate(observations):
        if index < 12:
            continue
        year_ago = observations[index - 12]
        yoy = pct_change(obs["value"], year_ago["value"])
        if yoy is None:
            continue
        points.append({"date": obs["date"][:7], "value": round(yoy, 2)})
    return points[-12:]


def build_yoy_series(observations):
    points = []
    for index, obs in enumerate(observations):
        if index < 12:
            continue
        year_ago = observations[index - 12]
        yoy = pct_change(obs["value"], year_ago["value"])
        if yoy is None:
            continue
        points.append({"date": obs["date"][:7], "value": round(yoy, 2)})
    return points[-12:]


def signal_for_block(label, key, indicators):
    help_by_key = {
        "credit": "銀行からノンバンク金融機関への貸出など、信用仲介の拡大を見ます。前年比が高止まりすると過熱、急減速や残高減少に転じると信用収縮リスクです。",
        "stress": "HYスプレッド、金融ストレス指数、VIXなどで市場が信用リスクを織り込み始めているかを見ます。同時に上昇すると危険度が上がります。",
        "rates": "長短金利や借入コストを見ます。高金利が続くほど、AIデータセンターやprivate creditの資金調達負担が増えます。",
        "liquidity": "TGA、RRP、準備預金などで市場流動性を見ます。TGA上昇、RRP低下、準備預金低下が重なると、信用市場が不安定になりやすいです。",
    }
    if not indicators:
        return {"key": key, "label": label, "emoji": "⚪", "value": "データなし", "help": help_by_key.get(key, "")}
    avg = sum(item["riskScore"] for item in indicators) / len(indicators)
    if avg >= 80:
        emoji, text = "🔴", "強い警戒シグナル"
    elif avg >= 60:
        emoji, text = "🟠", "高めの監視局面"
    elif avg >= 35:
        emoji, text = "🟡", "注意シグナル"
    else:
        emoji, text = "🟢", "落ち着いた状態"
    return {"key": key, "label": label, "emoji": emoji, "value": text, "help": help_by_key.get(key, "")}


def macro_signal_for_block(label, key, indicators):
    help_by_key = {
        "inflation": "CPI、Core CPI、PPIでインフレ圧力を見ます。物価が強いほど利下げ期待が後退し、株式市場には逆風になりやすいです。",
        "rates": "10年金利、2年金利、政策金利で割引率と資金調達コストを見ます。高止まりするほど株式のバリュエーションには重くなります。",
        "growth": "失業率などで景気悪化リスクを見ます。雇用が急に悪化すると企業業績への警戒が強まります。",
        "volatility": "VIXで株式市場の不安度を見ます。急上昇は市場がリスクを再評価しているサインです。",
    }
    if not indicators:
        return {"key": key, "label": label, "emoji": "⚪", "value": "データなし", "help": help_by_key.get(key, "")}
    avg = sum(item["riskScore"] for item in indicators) / len(indicators)
    if avg >= 80:
        emoji, text = "🔴", "株式に強い逆風"
    elif avg >= 60:
        emoji, text = "🟠", "高めの警戒"
    elif avg >= 35:
        emoji, text = "🟡", "注意シグナル"
    else:
        emoji, text = "🟢", "株式に比較的落ち着き"
    return {"key": key, "label": label, "emoji": emoji, "value": text, "help": help_by_key.get(key, "")}


def weighted_score(indicators):
    blocks = {
        "credit": [item for item in indicators if item["block"] == "credit"],
        "stress": [item for item in indicators if item["block"] == "stress"],
        "rates": [item for item in indicators if item["block"] == "rates"],
        "liquidity": [item for item in indicators if item["block"] == "liquidity"],
    }
    block_scores = {}
    for key, items in blocks.items():
        block_scores[key] = sum(item["riskScore"] for item in items) / len(items) if items else 30

    # AI bubble monitoring should overweight hidden credit growth, while still
    # requiring market stress/rates confirmation before calling it a crisis.
    score = (
        block_scores["credit"] * 0.45
        + block_scores["stress"] * 0.30
        + block_scores["rates"] * 0.15
        + block_scores["liquidity"] * 0.10
    )
    return round(score)


def weighted_macro_score(indicators):
    blocks = {
        "inflation": [item for item in indicators if item["block"] == "inflation"],
        "rates": [item for item in indicators if item["block"] == "rates"],
        "growth": [item for item in indicators if item["block"] == "growth"],
        "volatility": [item for item in indicators if item["block"] == "volatility"],
    }
    block_scores = {}
    for key, items in blocks.items():
        block_scores[key] = sum(item["riskScore"] for item in items) / len(items) if items else 30

    score = (
        block_scores["inflation"] * 0.35
        + block_scores["rates"] * 0.30
        + block_scores["growth"] * 0.20
        + block_scores["volatility"] * 0.15
    )
    return round(score)


def score_from_credit_yoy(yoy_value, non_credit_score):
    risk_score = risk_for_value(
        yoy_value,
        {"watch": 8, "high": 15, "danger": 22},
    )[2]
    return round(risk_score * 0.45 + non_credit_score * 0.55)


def main():
    load_env_file()
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY is not set. Add it to .env or export it in your shell.", file=sys.stderr)
        return 2

    fetched = {}
    indicators = []
    macro_indicators = []
    for config in AI_SERIES + MACRO_SERIES:
        if config["id"] not in fetched:
            fetched[config["id"]] = fred_observations(config["id"], api_key)
        indicator = build_indicator(config, fetched[config["id"]])
        if config in AI_SERIES:
            indicators.append(indicator)
        else:
            macro_indicators.append(indicator)

    credit_yoy = build_credit_yoy(fetched["LNFACBM027SBOG"])
    current_score = weighted_score(indicators)
    non_credit_score = round((current_score - indicators[0]["riskScore"] * 0.45) / 0.55)
    score_history = [
        {"date": point["date"], "score": score_from_credit_yoy(point["value"], non_credit_score)}
        for point in credit_yoy
    ]
    score_history[-1]["score"] = current_score

    stress_items = [item for item in indicators if item["block"] == "stress"]
    rate_items = [item for item in indicators if item["block"] == "rates"]
    credit_items = [item for item in indicators if item["block"] == "credit"]
    liquidity_items = [item for item in indicators if item["block"] == "liquidity"]
    signals = [
        signal_for_block("Credit Expansion", "credit", credit_items),
        signal_for_block("Market Stress", "stress", stress_items),
        {
            "key": "demand",
            "label": "AI Demand",
            "emoji": "⚪",
            "value": "決算データ接続待ち",
            "help": "NVIDIAやBig TechのAI関連売上・Capexを見ます。売上成長や設備投資計画が急減速すると、信用拡大を正当化しにくくなります。",
        },
        signal_for_block("Rates", "rates", rate_items),
        signal_for_block("Liquidity", "liquidity", liquidity_items),
    ]

    macro_score = weighted_macro_score(macro_indicators)
    macro_cpi_yoy = build_yoy_series(fetched["CPIAUCSL"])
    non_inflation_macro_score = round(
        (
            macro_score
            - (
                sum(item["riskScore"] for item in macro_indicators if item["block"] == "inflation")
                / len([item for item in macro_indicators if item["block"] == "inflation"])
            )
            * 0.35
        )
        / 0.65
    )
    macro_score_history = [
        {
            "date": point["date"],
            "score": round(risk_for_value(point["value"], {"watch": 3.0, "high": 4.0, "danger": 5.0})[2] * 0.35 + non_inflation_macro_score * 0.65),
        }
        for point in macro_cpi_yoy
    ]
    if macro_score_history:
        macro_score_history[-1]["score"] = macro_score

    macro_signals = [
        macro_signal_for_block("Inflation", "inflation", [item for item in macro_indicators if item["block"] == "inflation"]),
        macro_signal_for_block("Rates", "rates", [item for item in macro_indicators if item["block"] == "rates"]),
        macro_signal_for_block("Growth", "growth", [item for item in macro_indicators if item["block"] == "growth"]),
        macro_signal_for_block("Market Volatility", "volatility", [item for item in macro_indicators if item["block"] == "volatility"]),
    ]

    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "scoreHistory": score_history[-12:],
        "creditYoy": credit_yoy,
        "signals": signals,
        "indicators": indicators,
        "macro": {
            "scoreHistory": macro_score_history[-12:],
            "cpiYoy": macro_cpi_yoy,
            "signals": macro_signals,
            "indicators": macro_indicators,
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
