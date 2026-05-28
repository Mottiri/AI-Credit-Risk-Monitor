#!/usr/bin/env python3
import json
import os
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "nvidia.json"
CIK = "0001045810"
CIK_INT = "1045810"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Credit-Risk-Monitor/1.0 contact@example.com",
)
COMPANYFACTS_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{CIK}.json"


def request_json(url):
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": SEC_USER_AGENT},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url):
    request = Request(
        url,
        headers={"Accept": "text/html", "User-Agent": SEC_USER_AGENT},
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def quarter_sort_key(label):
    year, quarter = label.split("Q")
    return int(year) * 4 + int(quarter)


def pct_change(current, previous):
    if previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def format_usd(value):
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    return f"${value / 1_000_000:.0f}M"


def format_pct(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def format_point(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}pt"


def calendar_frame_to_label(frame):
    match = re.fullmatch(r"CY(\d{4})Q([1-4])", frame or "")
    if not match:
        return None
    return f"{match.group(1)}Q{match.group(2)}"


def extract_quarterly_fact(companyfacts, tag):
    units = companyfacts["facts"]["us-gaap"][tag]["units"]["USD"]
    latest = {}
    for item in units:
        label = calendar_frame_to_label(item.get("frame"))
        if not label or item.get("val") is None or item.get("form") not in ("10-Q", "10-K"):
            continue
        old = latest.get(label)
        if old is None or (item.get("filed") or "") > (old.get("filed") or ""):
            latest[label] = item
    if not latest:
        raise RuntimeError(f"No quarterly fact found for {tag}")
    return dict(sorted(latest.items(), key=lambda entry: quarter_sort_key(entry[0])))


def latest_filing():
    submissions = request_json(SUBMISSIONS_URL)
    recent = submissions["filings"]["recent"]
    for index, form in enumerate(recent["form"]):
        if form not in ("10-Q", "10-K"):
            continue
        accession = recent["accessionNumber"][index]
        document = recent["primaryDocument"][index]
        filing_date = recent["filingDate"][index]
        accession_compact = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{CIK_INT}/{accession_compact}/{document}"
        return {
            "form": form,
            "accession": accession,
            "document": document,
            "filingDate": filing_date,
            "url": url,
        }
    raise RuntimeError("No NVIDIA 10-Q/10-K filing found")


def clean_html_text(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_data_center_revenue(filing):
    html = request_text(filing["url"])
    text = clean_html_text(html)
    match = re.search(
        r"Data Center revenue was \$([\d.]+)\s+billion,\s+up\s+([\d.]+)%\s+from a year ago and up\s+([\d.]+)%\s+sequentially",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        value = float(match.group(1)) * 1_000_000_000
        return {
            "value": value,
            "yoy": float(match.group(2)),
            "qoq": float(match.group(3)),
            "source": "filing-text",
        }

    # Fallback: locate the product-market table row and use the first amount
    # after "Data Center". Values in the table are in millions.
    row_match = re.search(r"Data Center\s+\$\s*([\d,]+)", text, flags=re.IGNORECASE)
    if row_match:
        value = float(row_match.group(1).replace(",", "")) * 1_000_000
        return {"value": value, "yoy": None, "qoq": None, "source": "filing-table"}

    raise RuntimeError("Could not extract NVIDIA Data Center revenue")


def risk_for_data_center_growth(yoy, qoq):
    if (yoy is not None and yoy < 15) or (qoq is not None and qoq < -10):
        return "🟠", "risk-high", 70
    if (yoy is not None and yoy < 30) or (qoq is not None and qoq < 0):
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def risk_for_gross_margin(margin, qoq):
    if margin < 65 or (qoq is not None and qoq < -5):
        return "🟠", "risk-high", 70
    if margin < 70 or (qoq is not None and qoq < -2):
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def risk_for_revenue_growth(yoy, qoq):
    if (yoy is not None and yoy < 15) or (qoq is not None and qoq < -10):
        return "🟠", "risk-high", 70
    if (yoy is not None and yoy < 30) or (qoq is not None and qoq < 0):
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def build_indicators():
    companyfacts = request_json(COMPANYFACTS_URL)
    revenue_series = extract_quarterly_fact(companyfacts, "Revenues")
    gross_series = extract_quarterly_fact(companyfacts, "GrossProfit")
    labels = sorted(set(revenue_series) & set(gross_series), key=quarter_sort_key)
    if len(labels) < 5:
        raise RuntimeError("Not enough NVIDIA quarterly data")

    latest_label = labels[-1]
    previous_label = labels[-2]
    year_ago_label = f"{int(latest_label[:4]) - 1}Q{latest_label[-1]}"
    latest_revenue = float(revenue_series[latest_label]["val"])
    previous_revenue = float(revenue_series[previous_label]["val"])
    year_ago_revenue = float(revenue_series[year_ago_label]["val"]) if year_ago_label in revenue_series else None
    latest_gross = float(gross_series[latest_label]["val"])
    previous_gross = float(gross_series[previous_label]["val"])
    previous_margin = previous_gross / previous_revenue * 100
    gross_margin = latest_gross / latest_revenue * 100
    gross_margin_qoq = gross_margin - previous_margin
    revenue_yoy = pct_change(latest_revenue, year_ago_revenue)
    revenue_qoq = pct_change(latest_revenue, previous_revenue)

    filing = latest_filing()
    time.sleep(0.2)
    dc = extract_data_center_revenue(filing)

    dc_risk, dc_class, dc_score = risk_for_data_center_growth(dc["yoy"], dc["qoq"])
    revenue_risk, revenue_class, revenue_score = risk_for_revenue_growth(revenue_yoy, revenue_qoq)
    margin_risk, margin_class, margin_score = risk_for_gross_margin(gross_margin, gross_margin_qoq)

    indicators = [
        {
            "id": "NVDA-DC-GROWTH",
            "name": "NVIDIA Data Center Revenue Growth",
            "help": "NVIDIAのData Center売上成長率です。AIインフラ需要の代表指標です。前年比+30%台以下へ急減速、または前四半期比マイナスに転じる場合はAI投資の前提が弱くなります。",
            "latest": format_usd(dc["value"]),
            "latestRaw": dc["value"],
            "date": latest_label,
            "previousChange": format_pct(dc["qoq"]),
            "previousChangeRaw": dc["qoq"],
            "yoy": format_pct(dc["yoy"]),
            "yoyRaw": dc["yoy"],
            "risk": dc_risk,
            "riskClass": dc_class,
            "riskScore": dc_score,
            "nextRelease": "Quarterly",
            "block": "demand",
            "source": dc["source"],
            "sourceUrl": filing["url"],
        },
        {
            "id": "NVDA-REVENUE",
            "name": "NVIDIA Total Revenue",
            "help": "NVIDIAの四半期総売上です。Data Centerだけではありませんが、AI需要全体の勢いを見る補助指標です。前年比や前四半期比が急減速すると注意です。",
            "latest": format_usd(latest_revenue),
            "latestRaw": latest_revenue,
            "date": latest_label,
            "previousChange": format_pct(revenue_qoq),
            "previousChangeRaw": revenue_qoq,
            "yoy": format_pct(revenue_yoy),
            "yoyRaw": revenue_yoy,
            "risk": revenue_risk,
            "riskClass": revenue_class,
            "riskScore": revenue_score,
            "nextRelease": "Quarterly",
            "block": "demand",
        },
        {
            "id": "NVDA-GROSS-MARGIN",
            "name": "NVIDIA Gross Margin",
            "help": "NVIDIAのGAAP粗利率です。高いほどAI半導体の価格決定力が強い状態です。70%割れで注意、65%割れや前四半期比の大幅低下は競争や在庫圧力を警戒します。",
            "latest": f"{gross_margin:.1f}%",
            "latestRaw": gross_margin,
            "date": latest_label,
            "previousChange": format_point(gross_margin_qoq),
            "previousChangeRaw": gross_margin_qoq,
            "yoy": "n/a",
            "yoyRaw": None,
            "risk": margin_risk,
            "riskClass": margin_class,
            "riskScore": margin_score,
            "nextRelease": "Quarterly",
            "block": "demand",
        },
    ]
    return latest_label, filing, indicators


def signal_from_indicators(indicators):
    avg = sum(item["riskScore"] for item in indicators) / len(indicators)
    if avg >= 70:
        emoji, value = "🔴", "NVIDIA需要減速リスク"
    elif avg >= 40:
        emoji, value = "🟡", "NVIDIA需要の鈍化に注意"
    else:
        emoji, value = "🟢", "NVIDIA需要は強い"
    return {
        "key": "demand",
        "label": "AI Demand",
        "emoji": emoji,
        "value": value,
        "help": "NVIDIAのData Center売上、総売上、粗利率をSEC提出資料から自動取得しています。Data Center成長率や粗利率が急減速するとAI需要リスクが上がります。",
    }


def main():
    latest_label, filing, indicators = build_indicators()
    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "source": "SEC Companyfacts and NVIDIA SEC filing",
        "sourceUrl": filing["url"],
        "latestQuarter": latest_label,
        "filing": filing,
        "signal": signal_from_indicators(indicators),
        "indicators": indicators,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
