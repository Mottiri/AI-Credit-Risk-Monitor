#!/usr/bin/env python3
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "big-tech-capex.json"
SEC_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Credit-Risk-Monitor/1.0 contact@example.com",
)

COMPANIES = [
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "cik": "0000789019",
        "fiscal_start": "07-01",
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "operating_income_tags": ["OperatingIncomeLoss"],
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet",
        "cik": "0001652044",
        "fiscal_start": "01-01",
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "operating_income_tags": ["OperatingIncomeLoss"],
    },
    {
        "ticker": "META",
        "name": "Meta Platforms",
        "cik": "0001326801",
        "fiscal_start": "01-01",
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "operating_income_tags": ["OperatingIncomeLoss"],
    },
    {
        "ticker": "AMZN",
        "name": "Amazon",
        "cik": "0001018724",
        "fiscal_start": "01-01",
        "tags": [
            "PaymentsToAcquireProductiveAssets",
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ],
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "operating_income_tags": ["OperatingIncomeLoss"],
    },
]


def fetch_companyfacts(cik):
    url = f"{SEC_BASE_URL}/CIK{cik}.json"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": SEC_USER_AGENT,
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def quarter_label(end_date):
    quarter = (end_date.month - 1) // 3 + 1
    return f"{end_date.year}Q{quarter}"


def calendar_frame_to_label(frame):
    match = re.fullmatch(r"CY(\d{4})Q([1-4])", frame or "")
    if not match:
        return None
    return f"{match.group(1)}Q{match.group(2)}"


def quarter_sort_key(label):
    year, quarter = label.split("Q")
    return int(year) * 4 + int(quarter)


def preferred_units(facts, tags):
    for tag in tags:
        units = facts.get("us-gaap", {}).get(tag, {}).get("units", {})
        if "USD" in units:
            return tag, units["USD"]
    raise RuntimeError(f"No usable capex tag found from {tags}")


def latest_by_key(items, key_fn):
    latest = {}
    for item in items:
        key = key_fn(item)
        if key is None:
            continue
        old = latest.get(key)
        if old is None or (item.get("filed") or "") > (old.get("filed") or ""):
            latest[key] = item
    return latest


def extract_quarterly_capex(company, facts):
    tag, units = preferred_units(facts.get("facts", {}), company["tags"])
    return tag, extract_quarterly_usd(company, tag, units)


def extract_quarterly_usd_fact(company, facts, tags):
    tag, units = preferred_units(facts.get("facts", {}), tags)
    return tag, extract_quarterly_usd(company, tag, units)


def extract_quarterly_usd(company, tag, units):
    candidates = [
        item
        for item in units
        if item.get("form") in ("10-Q", "10-K")
        and item.get("val") is not None
        and item.get("start")
        and item.get("end")
    ]
    quarterly = {}

    # Direct 3-month facts are the cleanest source when companies provide them.
    direct = latest_by_key(candidates, lambda item: calendar_frame_to_label(item.get("frame")))
    for label, item in direct.items():
        start = parse_date(item["start"])
        end = parse_date(item["end"])
        if 60 <= (end - start).days + 1 <= 110:
            quarterly[label] = {
                "value": float(item["val"]),
                "start": item["start"],
                "end": item["end"],
                "filed": item["filed"],
                "tag": tag,
                "source": "direct",
            }

    # Some filers only publish YTD values for Q2/Q3. Derive the missing
    # quarters by subtracting the previous YTD value in the same fiscal year.
    ytd_candidates = latest_by_key(
        [
            item
            for item in candidates
            if item.get("fp") in ("Q1", "Q2", "Q3", "FY")
            and item["start"][5:] == company["fiscal_start"]
        ],
        lambda item: (item["start"], item["end"]),
    )
    by_start = {}
    for item in ytd_candidates.values():
        by_start.setdefault(item["start"], []).append(item)

    for items in by_start.values():
        items.sort(key=lambda item: item["end"])
        previous_value = 0
        previous_end = None
        for item in items:
            end = parse_date(item["end"])
            label = quarter_label(end)
            value = float(item["val"]) - previous_value
            period_start = item["start"] if previous_end is None else previous_end.isoformat()
            if value > 0 and label not in quarterly:
                quarterly[label] = {
                    "value": value,
                    "start": period_start,
                    "end": item["end"],
                    "filed": item["filed"],
                    "tag": tag,
                    "source": "derived-ytd",
                }
            previous_value = float(item["val"])
            previous_end = end

    return dict(sorted(quarterly.items(), key=lambda entry: quarter_sort_key(entry[0])))


def pct_change(current, previous):
    if previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def risk_for_capex_growth(yoy, qoq):
    # For the demand block, falling capex is riskier than high capex. High
    # growth suggests AI infrastructure investment is still being funded.
    if (yoy is not None and yoy < 0) or (qoq is not None and qoq < -15):
        return "🔴", "risk-danger", 80
    if (yoy is not None and yoy < 15) or (qoq is not None and qoq < -5):
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def format_usd(value):
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    return f"${value / 1_000_000_000:.1f}B"


def format_pct(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def company_indicator(company, latest_label, latest, previous, year_ago):
    qoq = pct_change(latest["value"], previous["value"] if previous else None)
    yoy = pct_change(latest["value"], year_ago["value"] if year_ago else None)
    risk, risk_class, risk_score = risk_for_capex_growth(yoy, qoq)
    return {
        "id": f"{company['ticker']}-CAPEX",
        "name": f"{company['name']} Capital Expenditures",
        "help": f"{company['name']}の設備投資です。AIデータセンター投資のproxyとして見ます。前年比が強い間はAI需要を支える材料ですが、前年比が0%割れ、または前四半期比で大きく落ちる場合はAI投資減速の警戒です。",
        "latest": format_usd(latest["value"]),
        "latestRaw": latest["value"],
        "date": latest_label,
        "previousChange": format_pct(qoq),
        "previousChangeRaw": qoq,
        "yoy": format_pct(yoy),
        "yoyRaw": yoy,
        "risk": risk,
        "riskClass": risk_class,
        "riskScore": risk_score,
        "nextRelease": "Quarterly",
        "block": "demand",
        "sourceTag": latest["tag"],
        "sourceType": latest["source"],
        "filed": latest["filed"],
    }


def total_indicator(latest_label, totals):
    labels = sorted(totals, key=quarter_sort_key)
    latest_value = totals[latest_label]
    previous_label = labels[labels.index(latest_label) - 1] if labels.index(latest_label) > 0 else None
    year_ago_label = f"{int(latest_label[:4]) - 1}Q{latest_label[-1]}"
    qoq = pct_change(latest_value, totals.get(previous_label))
    yoy = pct_change(latest_value, totals.get(year_ago_label))
    risk, risk_class, risk_score = risk_for_capex_growth(yoy, qoq)
    return {
        "id": "BIGTECH-CAPEX-TOTAL",
        "name": "Microsoft + Alphabet + Meta + Amazon Capex",
        "help": "Big Tech 4社の設備投資合計です。AIデータセンター投資の大きなproxyです。前年比が強ければAIインフラ需要はまだ強いと見ます。前年比0%割れ、または前四半期比-15%超の急減速はAI投資サイクル減速の警戒です。",
        "latest": format_usd(latest_value),
        "latestRaw": latest_value,
        "date": latest_label,
        "previousChange": format_pct(qoq),
        "previousChangeRaw": qoq,
        "yoy": format_pct(yoy),
        "yoyRaw": yoy,
        "risk": risk,
        "riskClass": risk_class,
        "riskScore": risk_score,
        "nextRelease": "Quarterly",
        "block": "demand",
    }


def signal_from_indicators(indicators):
    avg = sum(item["riskScore"] for item in indicators) / len(indicators)
    if avg >= 70:
        emoji, value = "🔴", "AI投資減速リスク上昇"
    elif avg >= 40:
        emoji, value = "🟡", "AI投資の減速に注意"
    else:
        emoji, value = "🟢", "AI投資は強い"
    return {
        "key": "demand",
        "label": "AI Demand",
        "emoji": emoji,
        "value": value,
        "help": "NVIDIAの需要指標とBig Techの設備投資を見ます。Big Tech CapexはAIデータセンター投資のproxyです。前年比や前四半期比が急減速すると、AI投資サイクルの減速シグナルです。",
    }


def risk_for_revenue_growth(yoy):
    if yoy is not None and yoy < 0:
        return "🔴", "risk-danger", 80
    if yoy is not None and yoy < 5:
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def risk_for_operating_margin(margin):
    if margin < 15:
        return "🔴", "risk-danger", 80
    if margin < 22:
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def sec_macro_indicators(latest_label, revenue_totals, operating_income_totals):
    labels = sorted(set(revenue_totals) & set(operating_income_totals), key=quarter_sort_key)
    latest_value = revenue_totals[latest_label]
    previous_label = labels[labels.index(latest_label) - 1] if labels.index(latest_label) > 0 else None
    year_ago_label = f"{int(latest_label[:4]) - 1}Q{latest_label[-1]}"
    revenue_qoq = pct_change(latest_value, revenue_totals.get(previous_label))
    revenue_yoy = pct_change(latest_value, revenue_totals.get(year_ago_label))
    operating_income = operating_income_totals[latest_label]
    operating_margin = operating_income / latest_value * 100 if latest_value else 0
    margin_previous = (
        operating_income_totals[previous_label] / revenue_totals[previous_label] * 100
        if previous_label and revenue_totals.get(previous_label)
        else None
    )
    margin_change = operating_margin - margin_previous if margin_previous is not None else None
    revenue_risk, revenue_class, revenue_score = risk_for_revenue_growth(revenue_yoy)
    margin_risk, margin_class, margin_score = risk_for_operating_margin(operating_margin)
    return [
        {
            "id": "BIGTECH-REVENUE-TOTAL",
            "name": "Microsoft + Alphabet + Meta + Amazon Revenue",
            "help": "Big Tech 4社の四半期売上合計です。株式市場では企業業績の底堅さを見る材料です。前年比が5%割れで注意、0%割れで業績悪化リスクを強く警戒します。",
            "latest": format_usd(latest_value),
            "latestRaw": latest_value,
            "date": latest_label,
            "previousChange": format_pct(revenue_qoq),
            "previousChangeRaw": revenue_qoq,
            "yoy": format_pct(revenue_yoy),
            "yoyRaw": revenue_yoy,
            "risk": revenue_risk,
            "riskClass": revenue_class,
            "riskScore": revenue_score,
            "nextRelease": "Quarterly",
            "block": "earnings",
        },
        {
            "id": "BIGTECH-OPERATING-MARGIN",
            "name": "Microsoft + Alphabet + Meta + Amazon Operating Margin",
            "help": "Big Tech 4社の営業利益率です。売上だけでなく収益性が保たれているかを見ます。22%割れで注意、15%割れで企業利益への強い逆風と見ます。",
            "latest": f"{operating_margin:.1f}%",
            "latestRaw": operating_margin,
            "date": latest_label,
            "previousChange": format_point(margin_change),
            "previousChangeRaw": margin_change,
            "yoy": "n/a",
            "yoyRaw": None,
            "risk": margin_risk,
            "riskClass": margin_class,
            "riskScore": margin_score,
            "nextRelease": "Quarterly",
            "block": "earnings",
        },
    ]


def format_point(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}pt"


def main():
    company_series = {}
    revenue_series = {}
    operating_income_series = {}
    company_tags = {}
    for index, company in enumerate(COMPANIES):
        if index:
            time.sleep(0.2)
        facts = fetch_companyfacts(company["cik"])
        tag, quarterly = extract_quarterly_capex(company, facts)
        revenue_tag, revenue_quarterly = extract_quarterly_usd_fact(company, facts, company["revenue_tags"])
        operating_tag, operating_quarterly = extract_quarterly_usd_fact(company, facts, company["operating_income_tags"])
        if not quarterly:
            raise RuntimeError(f"No quarterly capex extracted for {company['ticker']}")
        company_series[company["ticker"]] = quarterly
        revenue_series[company["ticker"]] = revenue_quarterly
        operating_income_series[company["ticker"]] = operating_quarterly
        company_tags[company["ticker"]] = {
            "capex": tag,
            "revenue": revenue_tag,
            "operatingIncome": operating_tag,
        }

    common_labels = sorted(
        set.intersection(*(set(series.keys()) for series in company_series.values())),
        key=quarter_sort_key,
    )
    if len(common_labels) < 5:
        raise RuntimeError("Not enough common Big Tech quarters")
    latest_label = common_labels[-1]
    totals = {
        label: sum(company_series[company["ticker"]][label]["value"] for company in COMPANIES)
        for label in common_labels
    }
    revenue_common_labels = sorted(
        set.intersection(*(set(series.keys()) for series in revenue_series.values())),
        key=quarter_sort_key,
    )
    operating_common_labels = sorted(
        set.intersection(*(set(series.keys()) for series in operating_income_series.values())),
        key=quarter_sort_key,
    )
    fundamentals_common_labels = sorted(set(revenue_common_labels) & set(operating_common_labels), key=quarter_sort_key)
    fundamentals_latest_label = fundamentals_common_labels[-1]
    revenue_totals = {
        label: sum(revenue_series[company["ticker"]][label]["value"] for company in COMPANIES)
        for label in fundamentals_common_labels
    }
    operating_income_totals = {
        label: sum(operating_income_series[company["ticker"]][label]["value"] for company in COMPANIES)
        for label in fundamentals_common_labels
    }

    indicators = [total_indicator(latest_label, totals)]
    for company in COMPANIES:
        labels = sorted(company_series[company["ticker"]], key=quarter_sort_key)
        latest = company_series[company["ticker"]][latest_label]
        latest_index = labels.index(latest_label)
        previous = company_series[company["ticker"]].get(labels[latest_index - 1]) if latest_index > 0 else None
        year_ago = company_series[company["ticker"]].get(f"{int(latest_label[:4]) - 1}Q{latest_label[-1]}")
        indicators.append(company_indicator(company, latest_label, latest, previous, year_ago))

    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "source": "SEC Companyfacts API",
        "sourceUrl": "https://www.sec.gov/edgar/sec-api-documentation",
        "latestQuarter": latest_label,
        "fundamentalsLatestQuarter": fundamentals_latest_label,
        "signal": signal_from_indicators(indicators),
        "indicators": indicators,
        "macroIndicators": sec_macro_indicators(fundamentals_latest_label, revenue_totals, operating_income_totals),
        "history": [
            {"date": label, "value": round(totals[label], 2)}
            for label in common_labels[-12:]
        ],
        "fundamentalsHistory": [
            {
                "date": label,
                "revenue": round(revenue_totals[label], 2),
                "operatingIncome": round(operating_income_totals[label], 2),
            }
            for label in fundamentals_common_labels[-12:]
        ],
        "companyTags": company_tags,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
