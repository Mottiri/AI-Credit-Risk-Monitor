#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "broadcom.json"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Credit-Risk-Monitor/1.0 contact@example.com",
)
NEWS_URL = "https://investors.broadcom.com/news-releases"
BROADCOM_RELEASE_URL = os.environ.get("BROADCOM_RELEASE_URL")
FALLBACK_RELEASE_URLS = [
    "https://www.prnewswire.com/news-releases/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial-results-and-quarterly-dividend-302790698.html",
    "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial",
]


def request_text(url, timeout=45):
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": SEC_USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "ignore")


def clean_html_text(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text)


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


def latest_broadcom_results_release():
    if BROADCOM_RELEASE_URL:
        return BROADCOM_RELEASE_URL, clean_html_text(request_text(BROADCOM_RELEASE_URL))

    candidates = []
    try:
        html = request_text(NEWS_URL, timeout=20)
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]*Financial Results[^<]*)', html, flags=re.IGNORECASE)
        if not links:
            links = re.findall(r'href="([^"]+)"[^>]*>([^<]*Results[^<]*)', html, flags=re.IGNORECASE)
        candidates.extend(
            urljoin(NEWS_URL, href)
            for href, title in links
            if "broadcom" in title.lower() and "financial results" in title.lower()
        )
    except (HTTPError, URLError, TimeoutError, OSError):
        pass

    candidates.extend(FALLBACK_RELEASE_URLS)
    seen = set()
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        try:
            return url, clean_html_text(request_text(url))
        except (HTTPError, URLError, TimeoutError, OSError):
            continue
    raise RuntimeError("Could not locate Broadcom financial results release")


def extract_release_quarter(release_text):
    match = re.search(
        r"(first|second|third|fourth) quarter fiscal year (\d{4})",
        release_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "Latest quarter"
    quarter_map = {
        "first": "Q1",
        "second": "Q2",
        "third": "Q3",
        "fourth": "Q4",
    }
    return f"{quarter_map[match.group(1).lower()]} FY{match.group(2)}"


def extract_total_revenue(release_text):
    match = re.search(
        r"Revenue of \$([\d,]+)\s+million.*?up\s+([\d.]+)\s+percent from the prior year period",
        release_text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"consolidated revenue grew\s+([\d.]+)%\s+year-over-year to .*?\$([\d.]+)\s+billion",
            release_text,
            flags=re.IGNORECASE,
        )
        if match:
            return {
                "value": float(match.group(2)) * 1_000_000_000,
                "yoy": float(match.group(1)),
            }
        raise RuntimeError("Could not extract Broadcom total revenue")
    return {
        "value": float(match.group(1).replace(",", "")) * 1_000_000,
        "yoy": float(match.group(2)),
    }


def extract_adjusted_ebitda_margin(release_text):
    match = re.search(
        r"Adjusted EBITDA of \$([\d,]+)\s+million.*?or\s+([\d.]+)\s+percent of revenue",
        release_text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"Adjusted EBITDA increased\s+[\d.]+%\s+year-over-year to .*?\$([\d.]+)\s+billion, representing\s+([\d.]+)%\s+of revenue",
            release_text,
            flags=re.IGNORECASE,
        )
        if match:
            return {
                "value": float(match.group(2)),
                "ebitda": float(match.group(1)) * 1_000_000_000,
            }
        return None
    return {
        "value": float(match.group(2)),
        "ebitda": float(match.group(1).replace(",", "")) * 1_000_000,
    }


def extract_revenue_guidance(release_text):
    match = re.search(
        r"revenue guidance of approximately \$([\d.]+)\s+billion,\s+an increase of\s+([\d.]+)\s+percent from the prior year period",
        release_text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"expect consolidated revenue growth to increase\s+([\d.]+)%\s+year-over-year to \$([\d.]+)\s+billion",
            release_text,
            flags=re.IGNORECASE,
        )
        if match:
            return {
                "value": float(match.group(2)) * 1_000_000_000,
                "yoy": float(match.group(1)),
            }
        return None
    return {
        "value": float(match.group(1)) * 1_000_000_000,
        "yoy": float(match.group(2)),
    }


def extract_ai_revenue(release_text):
    patterns = [
        r"AI semiconductor revenue (?:hit|was|of|to|reached)\s+\$([\d.]+)\s+billion.*?(?:grew|up)\s+([\d.]+)%\s+year-over-year",
        r"AI revenue of\s+\$([\d.]+)\s+billion\s+grew\s+([\d.]+)%\s+year-over-year",
        r"AI semiconductor revenue.*?\$([\d.]+)\s+billion.*?([\d.]+)%\s+year-over-year",
    ]
    for pattern in patterns:
        match = re.search(pattern, release_text, flags=re.IGNORECASE)
        if match:
            return {
                "value": float(match.group(1)) * 1_000_000_000,
                "yoy": float(match.group(2)),
                "source": "ir-release",
            }
    raise RuntimeError("Could not extract Broadcom AI semiconductor revenue")


def extract_ai_guidance(release_text):
    match = re.search(
        r"expect(?:s)?\s+(?:semiconductor revenue from )?AI(?: semiconductor revenue)?\s+to\s+(?:grow\s+(?:over\s+)?([\d.]+)\s+percent\s+year-over-year\s+to\s+)?\$([\d.]+)\s+billion",
        release_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    yoy = float(match.group(1)) if match.group(1) else None
    return {"value": float(match.group(2)) * 1_000_000_000, "yoy": yoy}


def risk_for_ai_growth(yoy):
    if yoy is not None and yoy < 30:
        return "🟠", "risk-high", 70
    if yoy is not None and yoy < 60:
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def risk_for_revenue_growth(yoy, qoq):
    if (yoy is not None and yoy < 5) or (qoq is not None and qoq < -10):
        return "🟠", "risk-high", 70
    if (yoy is not None and yoy < 15) or (qoq is not None and qoq < 0):
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def risk_for_margin(margin):
    if margin < 35:
        return "🟠", "risk-high", 70
    if margin < 50:
        return "🟡", "risk-watch", 45
    return "🟢", "risk-low", 20


def build_indicators():
    release_url, release_text = latest_broadcom_results_release()
    latest_label = extract_release_quarter(release_text)
    ai = extract_ai_revenue(release_text)
    revenue = extract_total_revenue(release_text)
    ebitda_margin = extract_adjusted_ebitda_margin(release_text)
    guidance = extract_ai_guidance(release_text)
    revenue_guidance = extract_revenue_guidance(release_text)

    ai_risk, ai_class, ai_score = risk_for_ai_growth(ai["yoy"])
    revenue_risk, revenue_class, revenue_score = risk_for_revenue_growth(revenue["yoy"], None)

    indicators = [
        {
            "id": "AVGO-AI-REVENUE",
            "name": "Broadcom AI Semiconductor Revenue",
            "help": "BroadcomのAI semiconductor revenueです。カスタムAI acceleratorとAI networking需要を見る指標です。前年比+60%割れで注意、+30%割れでAI投資サイクル鈍化を警戒します。",
            "latest": format_usd(ai["value"]),
            "latestRaw": ai["value"],
            "date": latest_label,
            "previousChange": "n/a",
            "previousChangeRaw": None,
            "yoy": format_pct(ai["yoy"]),
            "yoyRaw": ai["yoy"],
            "risk": ai_risk,
            "riskClass": ai_class,
            "riskScore": ai_score,
            "nextRelease": "Quarterly",
            "block": "demand",
            "source": ai["source"],
            "sourceUrl": release_url,
        },
        {
            "id": "AVGO-REVENUE",
            "name": "Broadcom Total Revenue",
            "help": "Broadcomの四半期総売上です。AI半導体だけでなく、VMwareを含む全体の成長とキャッシュ創出力を確認します。前年比や前四半期比が急減速すると注意です。",
            "latest": format_usd(revenue["value"]),
            "latestRaw": revenue["value"],
            "date": latest_label,
            "previousChange": "n/a",
            "previousChangeRaw": None,
            "yoy": format_pct(revenue["yoy"]),
            "yoyRaw": revenue["yoy"],
            "risk": revenue_risk,
            "riskClass": revenue_class,
            "riskScore": revenue_score,
            "nextRelease": "Quarterly",
            "block": "demand",
            "sourceUrl": release_url,
        },
    ]

    if ebitda_margin:
        margin_risk, margin_class, margin_score = risk_for_margin(ebitda_margin["value"])
        indicators.append(
            {
                "id": "AVGO-ADJUSTED-EBITDA-MARGIN",
                "name": "Broadcom Adjusted EBITDA Margin",
                "help": "BroadcomのAdjusted EBITDA marginです。AI半導体とインフラソフトウェアを含む収益性を見ます。50%割れで注意、35%割れで成長投資を支える利益余力の低下を警戒します。",
                "latest": f"{ebitda_margin['value']:.1f}%",
                "latestRaw": ebitda_margin["value"],
                "date": latest_label,
                "previousChange": "n/a",
                "previousChangeRaw": None,
                "yoy": "n/a",
                "yoyRaw": None,
                "risk": margin_risk,
                "riskClass": margin_class,
                "riskScore": margin_score,
                "nextRelease": "Quarterly",
                "block": "demand",
                "sourceUrl": release_url,
            }
        )

    if guidance:
        guidance_risk, guidance_class, guidance_score = risk_for_ai_growth(guidance["yoy"])
        indicators.append(
            {
                "id": "AVGO-AI-GUIDANCE",
                "name": "Broadcom AI Semiconductor Revenue Guidance",
                "help": "Broadcomの次四半期AI semiconductor revenue見通しです。実績よりも先行性があるため、急な鈍化はAIインフラ投資の警戒シグナルです。",
                "latest": format_usd(guidance["value"]),
                "latestRaw": guidance["value"],
                "date": "Next quarter",
                "previousChange": "n/a",
                "previousChangeRaw": None,
                "yoy": format_pct(guidance["yoy"]),
                "yoyRaw": guidance["yoy"],
                "risk": guidance_risk,
                "riskClass": guidance_class,
                "riskScore": guidance_score,
                "nextRelease": "Quarterly",
                "block": "demand",
                "sourceUrl": release_url,
            }
        )

    if revenue_guidance:
        revenue_guidance_risk, revenue_guidance_class, revenue_guidance_score = risk_for_revenue_growth(
            revenue_guidance["yoy"],
            None,
        )
        indicators.append(
            {
                "id": "AVGO-REVENUE-GUIDANCE",
                "name": "Broadcom Next Quarter Revenue Guidance",
                "help": "Broadcomの次四半期売上ガイダンスです。AI需要とVMware統合を含む全体の成長見通しです。前年比+15%割れで注意、+5%割れで需要減速を警戒します。",
                "latest": format_usd(revenue_guidance["value"]),
                "latestRaw": revenue_guidance["value"],
                "date": "Next quarter",
                "previousChange": "n/a",
                "previousChangeRaw": None,
                "yoy": format_pct(revenue_guidance["yoy"]),
                "yoyRaw": revenue_guidance["yoy"],
                "risk": revenue_guidance_risk,
                "riskClass": revenue_guidance_class,
                "riskScore": revenue_guidance_score,
                "nextRelease": "Quarterly",
                "block": "demand",
                "sourceUrl": release_url,
            }
        )

    return latest_label, release_url, indicators


def signal_from_indicators(indicators):
    avg = sum(item["riskScore"] for item in indicators) / len(indicators)
    if avg >= 70:
        emoji, value = "🔴", "Broadcom AI需要減速リスク"
    elif avg >= 40:
        emoji, value = "🟡", "Broadcom AI需要の鈍化に注意"
    else:
        emoji, value = "🟢", "Broadcom AI需要は強い"
    return {
        "key": "demand",
        "label": "AI Demand",
        "emoji": emoji,
        "value": value,
        "help": "BroadcomのAI semiconductor revenue、総売上、Adjusted EBITDA margin、次四半期ガイダンスを見ます。カスタムAIチップとAI networking需要の確認材料です。",
    }


def main():
    latest_label, release_url, indicators = build_indicators()
    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "source": "Broadcom IR release",
        "sourceUrl": release_url,
        "latestQuarter": latest_label,
        "signal": signal_from_indicators(indicators),
        "indicators": indicators,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
