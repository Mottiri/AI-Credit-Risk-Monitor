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
OUT_PATH = ROOT / "data" / "semiconductor-cycle.json"
TREND_PRICE_HISTORY_PATH = ROOT / "data" / "trendforce-memory-prices.json"
SEC_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts"
TWSE_MONTHLY_REVENUE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
TRENDFORCE_DRAM_URL = "https://www.trendforce.com/price/dram/dram_spot"
TRENDFORCE_FLASH_URL = "https://www.trendforce.com/price/flash/flash_spot"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Credit-Risk-Monitor/1.0 contact@example.com",
)
TSMC_TWSE_CODE = "2330"
HYPERSCALER_STOCKS = [
    {"ticker": "MSFT", "name": "Microsoft"},
    {"ticker": "AMZN", "name": "Amazon"},
    {"ticker": "GOOGL", "name": "Alphabet"},
    {"ticker": "META", "name": "Meta"},
    {"ticker": "ORCL", "name": "Oracle"},
]
AI_SUPPLY_CHAIN_STOCKS = [
    {"ticker": "NVDA", "name": "NVIDIA"},
    {"ticker": "AVGO", "name": "Broadcom"},
    {"ticker": "AMD", "name": "AMD"},
    {"ticker": "MU", "name": "Micron"},
    {"ticker": "TSM", "name": "TSMC"},
    {"ticker": "ASML", "name": "ASML"},
    {"ticker": "AMAT", "name": "Applied Materials"},
    {"ticker": "LRCX", "name": "Lam Research"},
    {"ticker": "KLAC", "name": "KLA"},
]

TRENDFORCE_PRICE_SPECS = [
    {
        "id": "TF-DRAM-DDR5-16GB-SPOT",
        "name": "TrendForce DDR5 16Gb Spot Price",
        "page": "dram",
        "item": "DDR5 16Gb (2Gx8) 4800/5600",
        "latest_index": 5,
        "change_index": 6,
        "help": "TrendForce公開ページのDDR5 16Gb spot priceです。DRAM価格サイクルの短期方向感を見ます。上昇が続くほどメモリメーカーの価格決定力に追い風です。",
    },
    {
        "id": "TF-DRAM-DDR4-16GB-SPOT",
        "name": "TrendForce DDR4 16Gb Spot Price",
        "page": "dram",
        "item": "DDR4 16Gb (2Gx8) 3200",
        "latest_index": 5,
        "change_index": 6,
        "help": "TrendForce公開ページのDDR4 16Gb spot priceです。汎用DRAM価格の底打ち・上昇継続を見る補助指標です。",
    },
    {
        "id": "TF-DRAM-DDR5-SODIMM-CONTRACT",
        "name": "TrendForce DDR5 SO-DIMM Contract Price",
        "page": "dram",
        "item": "DDR5 8GB SO-DIMM",
        "latest_index": 3,
        "change_index": 4,
        "yoy_index": 5,
        "help": "TrendForce公開ページのDDR5 SO-DIMM contract priceです。契約価格はspotより更新頻度が低い一方、メモリメーカーの収益に効きやすい価格指標です。",
    },
    {
        "id": "TF-NAND-512GB-TLC-SPOT",
        "name": "TrendForce NAND 512Gb TLC Spot Price",
        "page": "flash",
        "item": "512Gb TLC",
        "latest_index": 5,
        "change_index": 6,
        "help": "TrendForce公開ページのNAND 512Gb TLC spot priceです。NAND価格の短期方向感を確認します。",
    },
    {
        "id": "TF-NAND-128GB-MLC-CONTRACT",
        "name": "TrendForce NAND 128Gb MLC Contract Price",
        "page": "flash",
        "item": "NAND 128Gb 16Gx8 MLC",
        "latest_index": 3,
        "change_index": 4,
        "yoy_index": 5,
        "help": "TrendForce公開ページのNAND contract priceです。NANDの契約価格が上昇しているかを見ます。",
    },
]

COMPANIES = [
    {
        "ticker": "AMD",
        "name": "Advanced Micro Devices",
        "cik": "0000002488",
        "yahoo": "AMD",
        "group": "ai_compute",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "MU",
        "name": "Micron Technology",
        "cik": "0000723125",
        "yahoo": "MU",
        "group": "memory",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "AMAT",
        "name": "Applied Materials",
        "cik": "0000006951",
        "yahoo": "AMAT",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "LRCX",
        "name": "Lam Research",
        "cik": "0000707549",
        "yahoo": "LRCX",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "KLAC",
        "name": "KLA",
        "cik": "0000319201",
        "yahoo": "KLAC",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
]


def request_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": SEC_USER_AGENT})
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url):
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 AI-Credit-Risk-Monitor/1.0",
        },
    )
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "ignore")


def fetch_companyfacts(cik):
    return request_json(f"{SEC_BASE_URL}/CIK{cik}.json")


def calendar_frame_to_label(frame):
    match = re.fullmatch(r"CY(\d{4})Q([1-4])I?", frame or "")
    if not match:
        return None
    return f"{match.group(1)}Q{match.group(2)}"


def quarter_sort_key(label):
    year, quarter = label.split("Q")
    return int(year) * 4 + int(quarter)


def preferred_usd_units(facts, tags):
    for tag in tags:
        units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
        if "USD" in units:
            return tag, units["USD"]
    return None, []


def extract_quarterly_usd(facts, tags):
    tag, units = preferred_usd_units(facts, tags)
    if not tag:
        return tag, {}
    latest = {}
    for item in units:
        label = calendar_frame_to_label(item.get("frame"))
        if not label or item.get("val") is None or item.get("form") not in ("10-Q", "10-K"):
            continue
        old = latest.get(label)
        if old is None or (item.get("filed") or "") > (old.get("filed") or ""):
            latest[label] = {
                "value": float(item["val"]),
                "filed": item.get("filed"),
                "tag": tag,
                "form": item.get("form"),
            }
    return tag, dict(sorted(latest.items(), key=lambda entry: quarter_sort_key(entry[0])))


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def format_usd(value):
    if value is None:
        return "n/a"
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    return f"${value / 1_000_000:.0f}M"


def format_pct(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def format_ntd(value):
    if value is None:
        return "n/a"
    if abs(value) >= 1_000_000_000_000:
        return f"NT${value / 1_000_000_000_000:.2f}T"
    if abs(value) >= 1_000_000_000:
        return f"NT${value / 1_000_000_000:.1f}B"
    return f"NT${value / 1_000_000:.0f}M"


def format_point(value):
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}pt"


def parse_roc_month(value):
    raw = str(value or "")
    if len(raw) != 5:
        return raw or "n/a"
    year = int(raw[:3]) + 1911
    month = int(raw[3:])
    return f"{year}-{month:02d}"


def parse_float(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_percent_text(value):
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else None


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def growth_score(yoy, qoq):
    if yoy is None and qoq is None:
        return 50
    score = 50
    if yoy is not None:
        if yoy >= 50:
            score += 28
        elif yoy >= 25:
            score += 18
        elif yoy >= 10:
            score += 8
        elif yoy < 0:
            score -= 22
    if qoq is not None:
        if qoq >= 10:
            score += 10
        elif qoq < -10:
            score -= 15
        elif qoq < 0:
            score -= 7
    return max(0, min(100, score))


def price_reaction_score(change):
    if change is None:
        return 50
    if change >= 8:
        return 82
    if change >= 3:
        return 70
    if change >= 0:
        return 58
    if change <= -8:
        return 22
    if change <= -3:
        return 35
    return 45


def backlog_score(backlog_to_revenue, yoy):
    if backlog_to_revenue is None and yoy is None:
        return 50
    score = 45
    if backlog_to_revenue is not None:
        if backlog_to_revenue >= 0.8:
            score += 25
        elif backlog_to_revenue >= 0.4:
            score += 15
        elif backlog_to_revenue < 0.15:
            score -= 10
    if yoy is not None:
        if yoy >= 25:
            score += 18
        elif yoy >= 10:
            score += 10
        elif yoy < -10:
            score -= 16
    return max(0, min(100, score))


def memory_price_proxy_score(revenue_qoq, gross_margin_qoq, inventory_yoy):
    score = 50
    if revenue_qoq is not None:
        if revenue_qoq >= 20:
            score += 18
        elif revenue_qoq >= 5:
            score += 8
        elif revenue_qoq < 0:
            score -= 12
    if gross_margin_qoq is not None:
        if gross_margin_qoq >= 8:
            score += 22
        elif gross_margin_qoq >= 2:
            score += 12
        elif gross_margin_qoq < 0:
            score -= 15
    if inventory_yoy is not None:
        if inventory_yoy <= 0:
            score += 8
        elif inventory_yoy >= 25:
            score -= 12
    return max(0, min(100, score))


def memory_price_score(change, change_7d=None, change_30d=None):
    score = 50
    if change is not None:
        if change >= 3:
            score += 14
        elif change > 0:
            score += 7
        elif change <= -3:
            score -= 14
        elif change < 0:
            score -= 7
    if change_7d is not None:
        if change_7d >= 5:
            score += 16
        elif change_7d > 0:
            score += 8
        elif change_7d <= -5:
            score -= 16
        elif change_7d < 0:
            score -= 8
    if change_30d is not None:
        if change_30d >= 10:
            score += 20
        elif change_30d > 0:
            score += 10
        elif change_30d <= -10:
            score -= 20
        elif change_30d < 0:
            score -= 10
    return max(0, min(100, score))


def buyer_stress_score(hyperscaler_change, supply_chain_change, capex_yoy, capex_qoq):
    spread = None
    if hyperscaler_change is not None and supply_chain_change is not None:
        spread = supply_chain_change - hyperscaler_change
    stress = 25
    if hyperscaler_change is not None:
        if hyperscaler_change <= -15:
            stress += 28
        elif hyperscaler_change <= -8:
            stress += 18
        elif hyperscaler_change < 0:
            stress += 9
    if spread is not None:
        if spread >= 35:
            stress += 28
        elif spread >= 20:
            stress += 18
        elif spread >= 10:
            stress += 9
    if capex_yoy is not None:
        if capex_yoy >= 50:
            stress += 12
        elif capex_yoy >= 20:
            stress += 6
        elif capex_yoy < 0:
            stress -= 10
    if capex_qoq is not None:
        if capex_qoq <= -15:
            stress += 18
        elif capex_qoq < 0:
            stress += 8
        elif capex_qoq >= 10:
            stress -= 5
    return max(0, min(100, stress))


def margin_score(margin, qoq):
    if margin is None:
        return 50
    score = 45
    if margin >= 70:
        score += 35
    elif margin >= 55:
        score += 25
    elif margin >= 40:
        score += 12
    elif margin < 25:
        score -= 18
    if qoq is not None:
        if qoq >= 4:
            score += 12
        elif qoq >= 1:
            score += 6
        elif qoq <= -4:
            score -= 12
        elif qoq < 0:
            score -= 6
    return max(0, min(100, score))


def operating_margin_score(margin, qoq):
    if margin is None:
        return 50
    score = 45
    if margin >= 40:
        score += 30
    elif margin >= 25:
        score += 20
    elif margin >= 12:
        score += 10
    elif margin < 0:
        score -= 20
    if qoq is not None:
        if qoq >= 3:
            score += 10
        elif qoq <= -3:
            score -= 10
        elif qoq < 0:
            score -= 5
    return max(0, min(100, score))


def inventory_pressure(inventory_to_revenue, yoy):
    if inventory_to_revenue is None:
        return 40
    pressure = 20
    if inventory_to_revenue > 1.0:
        pressure += 35
    elif inventory_to_revenue > 0.7:
        pressure += 22
    elif inventory_to_revenue > 0.45:
        pressure += 12
    if yoy is not None:
        if yoy > 30:
            pressure += 20
        elif yoy > 15:
            pressure += 10
        elif yoy < -10:
            pressure -= 8
    return max(0, min(100, pressure))


def status_from_score(score, positive=True):
    if positive:
        if score >= 70:
            return "🟢", "risk-low"
        if score >= 45:
            return "🟡", "risk-watch"
        return "🟠", "risk-high"
    if score >= 70:
        return "🔴", "risk-danger"
    if score >= 45:
        return "🟠", "risk-high"
    if score >= 25:
        return "🟡", "risk-watch"
    return "🟢", "risk-low"


def clean_html_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def trendforce_last_update(document):
    match = re.search(r"Last Update\s+([^<]+)", document)
    return match.group(1).strip() if match else datetime.now(timezone.utc).date().isoformat()


def trendforce_rows(document):
    rows = {}
    for row in re.findall(r"<tr>\s*(.*?)\s*</tr>", document, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        values = [clean_html_text(cell) for cell in cells]
        if values:
            rows[values[0]] = values
    return rows


def format_price(value):
    if value is None:
        return "n/a"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def nearest_history_change(history, current_value, days):
    if current_value is None or not history:
        return None
    today = datetime.now(timezone.utc).date().toordinal()
    target = today - days
    candidates = []
    for row in history:
        value = row.get("value")
        date = parse_iso_date(row.get("date"))
        if value is None or not date:
            continue
        if date.toordinal() > target:
            continue
        candidates.append((abs(date.toordinal() - target), value))
    if not candidates:
        return None
    _, previous_value = min(candidates, key=lambda item: item[0])
    return pct_change(current_value, previous_value)


def update_trendforce_history(observations):
    today = datetime.now(timezone.utc).date().isoformat()
    history_data = load_json(TREND_PRICE_HISTORY_PATH) or {"updatedAt": None, "series": {}}
    series = history_data.setdefault("series", {})
    for item in observations:
        if item.get("latestRaw") is None or item.get("stale"):
            continue
        rows = series.setdefault(item["id"], [])
        rows = [row for row in rows if row.get("date") != today]
        rows.append({"date": today, "value": item["latestRaw"], "sourceDate": item.get("date")})
        series[item["id"]] = rows[-90:]
    history_data["updatedAt"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    TREND_PRICE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    TREND_PRICE_HISTORY_PATH.write_text(json.dumps(history_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return history_data


def fallback_trendforce_indicator(identifier):
    data = load_json(OUT_PATH)
    if not data:
        return None
    for item in data.get("indicators", []):
        if item.get("id") == identifier:
            output = dict(item)
            output["stale"] = True
            output["previousChange"] = output.get("previousChange") or "前回成功値"
            return output
    return None


def fetch_trendforce_memory_prices():
    documents = {
        "dram": request_text(TRENDFORCE_DRAM_URL),
        "flash": request_text(TRENDFORCE_FLASH_URL),
    }
    parsed = {key: trendforce_rows(value) for key, value in documents.items()}
    updates = {key: trendforce_last_update(value) for key, value in documents.items()}
    observations = []
    for spec in TRENDFORCE_PRICE_SPECS:
        row = parsed.get(spec["page"], {}).get(spec["item"])
        if not row:
            fallback = fallback_trendforce_indicator(spec["id"])
            if fallback:
                observations.append(fallback)
            continue
        latest = parse_float(row[spec["latest_index"]]) if len(row) > spec["latest_index"] else None
        page_change = parse_percent_text(row[spec["change_index"]]) if len(row) > spec["change_index"] else None
        yoy = parse_percent_text(row[spec["yoy_index"]]) if spec.get("yoy_index") is not None and len(row) > spec["yoy_index"] else None
        observations.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "help": spec["help"],
                "latest": format_price(latest),
                "latestRaw": latest,
                "date": updates.get(spec["page"]),
                "previousChange": format_pct(page_change),
                "previousChangeRaw": page_change,
                "yoy": format_pct(yoy) if yoy is not None else "n/a",
                "yoyRaw": yoy,
                "risk": "🟡",
                "riskClass": "risk-watch",
                "riskScore": 50,
                "cycleScore": 50,
                "nextRelease": "Daily",
                "block": "memory_price",
                "source": "TrendForce public price page",
                "sourceUrl": TRENDFORCE_DRAM_URL if spec["page"] == "dram" else TRENDFORCE_FLASH_URL,
            }
        )

    history_data = update_trendforce_history(observations)
    for item in observations:
        if item.get("latestRaw") is None:
            continue
        rows = history_data.get("series", {}).get(item["id"], [])
        change_7d = nearest_history_change(rows, item["latestRaw"], 7)
        change_30d = nearest_history_change(rows, item["latestRaw"], 30)
        if change_7d is not None:
            item["sevenDayChange"] = format_pct(change_7d)
            item["sevenDayChangeRaw"] = change_7d
        if change_30d is not None:
            item["thirtyDayChange"] = format_pct(change_30d)
            item["thirtyDayChangeRaw"] = change_30d
            item["yoy"] = format_pct(change_30d)
            item["yoyRaw"] = change_30d
        score = memory_price_score(item.get("previousChangeRaw"), item.get("sevenDayChangeRaw"), item.get("thirtyDayChangeRaw"))
        emoji, risk_class = status_from_score(score, positive=True)
        item["cycleScore"] = score
        item["riskScore"] = 100 - score
        item["risk"] = emoji
        item["riskClass"] = risk_class
    return observations


def indicator(identifier, name, help_text, latest, latest_raw, previous, previous_raw, yoy, yoy_raw, score, block, date):
    emoji, risk_class = status_from_score(score, positive=True)
    return {
        "id": identifier,
        "name": name,
        "help": help_text,
        "latest": latest,
        "latestRaw": latest_raw,
        "date": date,
        "previousChange": previous,
        "previousChangeRaw": previous_raw,
        "yoy": yoy,
        "yoyRaw": yoy_raw,
        "risk": emoji,
        "riskClass": risk_class,
        "riskScore": 100 - score,
        "cycleScore": score,
        "nextRelease": "Quarterly",
        "block": block,
    }


def fetch_tsmc_monthly_revenue():
    rows = request_json(TWSE_MONTHLY_REVENUE_URL)
    row = next((item for item in rows if item.get("公司代號") == TSMC_TWSE_CODE), None)
    if not row:
        return None

    latest_thousand_ntd = parse_float(row.get("營業收入-當月營收"))
    mom = parse_float(row.get("營業收入-上月比較增減(%)"))
    yoy = parse_float(row.get("營業收入-去年同月增減(%)"))
    ytd_yoy = parse_float(row.get("累計營業收入-前期比較增減(%)"))
    latest = latest_thousand_ntd * 1000 if latest_thousand_ntd is not None else None
    score = growth_score(yoy, mom)
    item = indicator(
        "TSMC-MONTHLY-REVENUE",
        "TSMC Monthly Revenue",
        "TSMCの月次売上です。GPU/HBM/AI acceleratorを支える先端ファウンドリ需要の先行確認に使います。前年比の鈍化や前月比マイナスが続く場合は、AI半導体サイクルの勢い低下に注意します。",
        format_ntd(latest),
        latest,
        format_pct(mom),
        mom,
        format_pct(yoy),
        yoy,
        score,
        "foundry_packaging",
        parse_roc_month(row.get("資料年月")),
    )
    item["source"] = "TWSE OpenAPI"
    item["sourceUrl"] = TWSE_MONTHLY_REVENUE_URL
    item["ytdYoy"] = format_pct(ytd_yoy)
    item["ytdYoyRaw"] = ytd_yoy
    return item


def fetch_yahoo_closes(symbol):
    data = request_json(YAHOO_CHART_URL.format(symbol=symbol))
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        rows.append({"date": date, "close": float(close)})
    return rows


def price_change_after_date(closes, start_date, trading_days=5):
    if not closes or not start_date:
        return None
    start = parse_iso_date(start_date)
    if not start:
        return None
    start_index = None
    for index, row in enumerate(closes):
        row_date = parse_iso_date(row["date"])
        if row_date and row_date >= start:
            start_index = index
            break
    if start_index is None:
        return None
    end_index = min(start_index + trading_days, len(closes) - 1)
    start_close = closes[start_index]["close"]
    end_close = closes[end_index]["close"]
    return pct_change(end_close, start_close)


def price_change_over_trading_days(closes, trading_days=60):
    if not closes or len(closes) < 2:
        return None
    start_index = max(0, len(closes) - 1 - trading_days)
    return pct_change(closes[-1]["close"], closes[start_index]["close"])


def fetch_stock_group_performance(stocks, trading_days=60):
    rows = []
    for stock in stocks:
        closes = fetch_yahoo_closes(stock["ticker"])
        change = price_change_over_trading_days(closes, trading_days=trading_days)
        rows.append({**stock, "change": change})
        time.sleep(0.05)
    return rows


def average_change(rows):
    return average([row.get("change") for row in rows], default=None)


def buyer_pressure_indicators():
    hyperscaler_rows = fetch_stock_group_performance(HYPERSCALER_STOCKS, trading_days=60)
    supply_rows = fetch_stock_group_performance(AI_SUPPLY_CHAIN_STOCKS, trading_days=60)
    hyperscaler_avg = average_change(hyperscaler_rows)
    supply_avg = average_change(supply_rows)
    spread = supply_avg - hyperscaler_avg if hyperscaler_avg is not None and supply_avg is not None else None
    capex = existing_indicator(ROOT / "data" / "big-tech-capex.json", "BIGTECH-CAPEX-TOTAL")
    capex_yoy = capex.get("yoyRaw") if capex else None
    capex_qoq = capex.get("previousChangeRaw") if capex else None
    stress = buyer_stress_score(hyperscaler_avg, supply_avg, capex_yoy, capex_qoq)
    stress_emoji, stress_class = status_from_score(stress, positive=False)
    latest_date = datetime.now(timezone.utc).date().isoformat()
    pressure = {
        "id": "HYPERSCALER-BUYER-STRESS",
        "name": "Hyperscaler Buyer Stress",
        "help": "Microsoft、Amazon、Alphabet、Meta、OracleなどAI投資の買い手側株価と、NVIDIA/Micron/ASMLなど供給側株価の相対パフォーマンスを見ます。買い手側が弱く、供給側だけが強い状態は、AI Capex継続が前提になった歪みとして監視します。",
        "latest": f"{stress:.0f}/100",
        "latestRaw": stress,
        "date": latest_date,
        "previousChange": f"Buyer {format_pct(hyperscaler_avg)}",
        "previousChangeRaw": hyperscaler_avg,
        "yoy": f"Supply {format_pct(supply_avg)}",
        "yoyRaw": supply_avg,
        "spread": format_pct(spread),
        "spreadRaw": spread,
        "risk": stress_emoji,
        "riskClass": stress_class,
        "riskScore": stress,
        "cycleScore": 100 - stress,
        "nextRelease": "Daily",
        "block": "buyer_pressure",
    }
    if capex:
        normalized_capex = normalize_existing_indicator(dict(capex), "buyer_pressure")
        normalized_capex["help"] = (
            "Big Tech 4社のCapex合計です。買い手側のAI投資余力を確認します。株価が重くてもCapexが維持される間は供給側の需要を支えますが、"
            "Capex減速が始まると製造側への波及を警戒します。"
        )
    else:
        normalized_capex = None
    return [item for item in [pressure, normalized_capex] if item], {
        "stress": stress,
        "hyperscalerAvg": hyperscaler_avg,
        "supplyAvg": supply_avg,
        "spread": spread,
        "capexYoy": capex_yoy,
        "capexQoq": capex_qoq,
    }


def company_metrics(company):
    facts = fetch_companyfacts(company["cik"])
    revenue_tag, revenue = extract_quarterly_usd(facts, company["revenue_tags"])
    gross_tag, gross = extract_quarterly_usd(facts, ["GrossProfit"])
    operating_tag, operating = extract_quarterly_usd(facts, ["OperatingIncomeLoss"])
    inventory_tag, inventory = extract_quarterly_usd(facts, ["InventoryNet", "InventoryFinishedGoodsNetOfReserves"])
    capex_tag, capex = extract_quarterly_usd(facts, ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"])
    backlog_tag, backlog = extract_quarterly_usd(
        facts,
        [
            "RemainingPerformanceObligation",
            "ContractWithCustomerLiabilityCurrent",
            "ContractWithCustomerLiability",
            "DeferredRevenueCurrent",
            "DeferredRevenue",
        ],
    )

    labels = sorted(revenue.keys(), key=quarter_sort_key)
    if len(labels) < 2:
        raise RuntimeError(f"Not enough revenue data for {company['ticker']}")
    latest_label = labels[-1]
    previous_label = labels[-2]
    year_ago_label = f"{int(latest_label[:4]) - 1}Q{latest_label[-1]}"
    latest_revenue = revenue[latest_label]["value"]
    previous_revenue = revenue[previous_label]["value"]
    year_ago_revenue = revenue.get(year_ago_label, {}).get("value")
    revenue_qoq = pct_change(latest_revenue, previous_revenue)
    revenue_yoy = pct_change(latest_revenue, year_ago_revenue)

    latest_gross = gross.get(latest_label, {}).get("value")
    previous_gross = gross.get(previous_label, {}).get("value")
    gross_margin = ratio(latest_gross, latest_revenue)
    gross_margin = gross_margin * 100 if gross_margin is not None else None
    previous_margin = ratio(previous_gross, previous_revenue)
    previous_margin = previous_margin * 100 if previous_margin is not None else None
    gross_margin_qoq = gross_margin - previous_margin if gross_margin is not None and previous_margin is not None else None

    latest_operating = operating.get(latest_label, {}).get("value")
    previous_operating = operating.get(previous_label, {}).get("value")
    operating_margin = ratio(latest_operating, latest_revenue)
    operating_margin = operating_margin * 100 if operating_margin is not None else None
    previous_operating_margin = ratio(previous_operating, previous_revenue)
    previous_operating_margin = previous_operating_margin * 100 if previous_operating_margin is not None else None
    operating_margin_qoq = (
        operating_margin - previous_operating_margin
        if operating_margin is not None and previous_operating_margin is not None
        else None
    )

    latest_inventory = inventory.get(latest_label, {}).get("value")
    year_ago_inventory = inventory.get(year_ago_label, {}).get("value")
    inventory_yoy = pct_change(latest_inventory, year_ago_inventory)
    inventory_to_revenue = ratio(latest_inventory, latest_revenue)

    latest_capex = capex.get(latest_label, {}).get("value")
    year_ago_capex = capex.get(year_ago_label, {}).get("value")
    capex_yoy = pct_change(latest_capex, year_ago_capex)

    latest_backlog = backlog.get(latest_label, {}).get("value")
    year_ago_backlog = backlog.get(year_ago_label, {}).get("value")
    backlog_yoy = pct_change(latest_backlog, year_ago_backlog)
    backlog_to_revenue = ratio(latest_backlog, latest_revenue)

    return {
        "company": company,
        "date": latest_label,
        "filed": revenue[latest_label].get("filed"),
        "revenue": latest_revenue,
        "revenueQoq": revenue_qoq,
        "revenueYoy": revenue_yoy,
        "grossMargin": gross_margin,
        "grossMarginQoq": gross_margin_qoq,
        "operatingMargin": operating_margin,
        "operatingMarginQoq": operating_margin_qoq,
        "inventory": latest_inventory,
        "inventoryYoy": inventory_yoy,
        "inventoryToRevenue": inventory_to_revenue,
        "capex": latest_capex,
        "capexYoy": capex_yoy,
        "backlog": latest_backlog,
        "backlogYoy": backlog_yoy,
        "backlogToRevenue": backlog_to_revenue,
        "tags": {
            "revenue": revenue_tag,
            "gross": gross_tag,
            "operating": operating_tag,
            "inventory": inventory_tag,
            "capex": capex_tag,
            "backlog": backlog_tag,
        },
    }


def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def existing_indicator(path, identifier):
    data = load_json(path)
    if not data:
        return None
    for item in data.get("indicators", []):
        if item.get("id") == identifier:
            return item
    return None


def normalize_existing_indicator(item, block, cycle_score=None):
    if not item:
        return None
    output = dict(item)
    output["block"] = block
    if cycle_score is not None:
        output["cycleScore"] = cycle_score
        output["riskScore"] = 100 - cycle_score
    elif "cycleScore" not in output:
        output["cycleScore"] = max(0, min(100, 100 - float(output.get("riskScore", 50))))
    return output


def average(values, default=50):
    usable = [value for value in values if value is not None]
    if not usable:
        return default
    return sum(usable) / len(usable)


def phase_from_scores(demand, memory, equipment, inventory):
    if demand >= 68 and memory >= 60 and inventory < 50 and equipment < 62:
        return "Supply Shortage", "需要が供給を上回り、価格決定力が強い局面"
    if demand >= 65 and equipment >= 62 and inventory < 58:
        return "Capacity Expansion", "AI需要を背景に供給能力を増やす局面"
    if demand >= 55 and memory >= 55:
        return "Demand Acceleration", "AIとメモリ需要が上向く拡大局面"
    if inventory >= 65 and demand < 55:
        return "Overbuild Risk", "供給増と在庫増が需要を上回り始める警戒局面"
    if demand < 40 and inventory >= 55:
        return "Downturn", "需要鈍化と在庫圧力が重なる調整局面"
    return "Recovery", "需要と利益率が底打ちから回復する局面"


def investment_map(current_phase):
    rows = [
        {
            "phase": "Recovery",
            "focus": "Memory / Equipment",
            "stance": "次サイクルを先取り",
            "note": "在庫調整が終わり、価格・受注が底打ちする局面ではメモリや装置が先に反応しやすいです。",
        },
        {
            "phase": "Demand Acceleration",
            "focus": "AI Compute / HBM / Networking",
            "stance": "成長の中心を重視",
            "note": "GPU、AI accelerator、HBM、AI networkingなど需要の伸びが最も強い領域が主役です。",
        },
        {
            "phase": "Supply Shortage",
            "focus": "GPU / HBM / Foundry / Packaging",
            "stance": "価格決定力を重視",
            "note": "供給制約がある間は、HBM、先端ファウンドリ、先端パッケージなど希少能力を持つ領域が強くなりやすいです。",
        },
        {
            "phase": "Capacity Expansion",
            "focus": "Equipment / Materials / Test",
            "stance": "設備投資の受益を確認",
            "note": "供給能力を増やす局面では、製造装置、検査、素材が受益しやすい一方、将来の供給過剰も監視します。",
        },
        {
            "phase": "Overbuild Risk",
            "focus": "Quality / Cash Flow / Defensive Leaders",
            "stance": "過熱を落とす",
            "note": "在庫増と粗利率低下が出る局面では、高粗利・高キャッシュ・シェアの強い大型企業を相対的に重視します。",
        },
        {
            "phase": "Downturn",
            "focus": "Cash / Next Cycle Watchlist",
            "stance": "守りながら底打ち待ち",
            "note": "需要減速と在庫調整の局面では無理に追わず、次の回復サインを待つ局面です。",
        },
    ]
    for row in rows:
        row["active"] = row["phase"] == current_phase
    return rows


def build():
    metrics = []
    for company in COMPANIES:
        try:
            metrics.append(company_metrics(company))
            time.sleep(0.15)
        except Exception as exc:
            print(f"Warning: {company['ticker']} skipped: {exc}")

    indicators = []
    company_by_ticker = {item["company"]["ticker"]: item for item in metrics}

    nvidia_dc = normalize_existing_indicator(
        existing_indicator(ROOT / "data" / "nvidia.json", "NVDA-DC-GROWTH"),
        "ai_compute",
    )
    broadcom_ai = normalize_existing_indicator(
        existing_indicator(ROOT / "data" / "broadcom.json", "AVGO-AI-REVENUE"),
        "ai_compute",
    )
    nvidia_outlook = normalize_existing_indicator(
        existing_indicator(ROOT / "data" / "ai-demand.json", "NVDA-REVENUE-OUTLOOK"),
        "guidance",
    )
    broadcom_ai_guidance = normalize_existing_indicator(
        existing_indicator(ROOT / "data" / "broadcom.json", "AVGO-AI-GUIDANCE"),
        "guidance",
    )
    broadcom_revenue_guidance = normalize_existing_indicator(
        existing_indicator(ROOT / "data" / "broadcom.json", "AVGO-REVENUE-GUIDANCE"),
        "guidance",
    )
    for item in [nvidia_dc, broadcom_ai, nvidia_outlook, broadcom_ai_guidance, broadcom_revenue_guidance]:
        if item:
            indicators.append(item)

    tsmc_monthly = None
    try:
        tsmc_monthly = fetch_tsmc_monthly_revenue()
        if tsmc_monthly:
            indicators.append(tsmc_monthly)
    except Exception as exc:
        print(f"Warning: TSMC monthly revenue skipped: {exc}")

    trendforce_prices = []
    try:
        trendforce_prices = fetch_trendforce_memory_prices()
        indicators.extend(trendforce_prices)
    except Exception as exc:
        print(f"Warning: TrendForce memory prices skipped: {exc}")
        for spec in TRENDFORCE_PRICE_SPECS:
            fallback = fallback_trendforce_indicator(spec["id"])
            if fallback:
                trendforce_prices.append(fallback)
                indicators.append(fallback)

    buyer_pressure = {"stress": 50, "hyperscalerAvg": None, "supplyAvg": None, "spread": None, "capexYoy": None, "capexQoq": None}
    try:
        buyer_pressure_items, buyer_pressure = buyer_pressure_indicators()
        indicators.extend(buyer_pressure_items)
    except Exception as exc:
        print(f"Warning: hyperscaler buyer pressure skipped: {exc}")

    for item in metrics:
        company = item["company"]
        ticker = company["ticker"]
        block = company["group"]
        rev_score = growth_score(item["revenueYoy"], item["revenueQoq"])
        mar_score = margin_score(item["grossMargin"], item["grossMarginQoq"])
        inv_pressure = inventory_pressure(item["inventoryToRevenue"], item["inventoryYoy"])
        inv_score = 100 - inv_pressure

        indicators.append(
            indicator(
                f"{ticker}-REVENUE",
                f"{company['name']} Revenue",
                f"{company['name']}の四半期売上です。半導体サイクルでは需要の強さを見る基本指標です。前年比・前四半期比が同時に鈍化すると注意します。",
                format_usd(item["revenue"]),
                item["revenue"],
                format_pct(item["revenueQoq"]),
                item["revenueQoq"],
                format_pct(item["revenueYoy"]),
                item["revenueYoy"],
                rev_score,
                block,
                item["date"],
            )
        )
        indicators.append(
            indicator(
                f"{ticker}-GROSS-MARGIN",
                f"{company['name']} Gross Margin",
                f"{company['name']}の粗利率です。価格決定力、需給、製品ミックスを見る指標です。改善が続けばサイクル上向き、低下に転じると在庫・価格圧力に注意します。",
                f"{item['grossMargin']:.1f}%" if item["grossMargin"] is not None else "n/a",
                item["grossMargin"],
                format_point(item["grossMarginQoq"]),
                item["grossMarginQoq"],
                "n/a",
                None,
                mar_score,
                "inventory_margin",
                item["date"],
            )
        )
        op_score = operating_margin_score(item["operatingMargin"], item["operatingMarginQoq"])
        indicators.append(
            indicator(
                f"{ticker}-OPERATING-MARGIN",
                f"{company['name']} Operating Margin",
                f"{company['name']}の営業利益率です。AI/半導体需要が売上だけでなく利益にも波及しているかを見ます。粗利率と同時に低下するとサイクル鈍化の警戒材料です。",
                f"{item['operatingMargin']:.1f}%" if item["operatingMargin"] is not None else "n/a",
                item["operatingMargin"],
                format_point(item["operatingMarginQoq"]),
                item["operatingMarginQoq"],
                "n/a",
                None,
                op_score,
                "inventory_margin",
                item["date"],
            )
        )
        indicators.append(
            indicator(
                f"{ticker}-INVENTORY",
                f"{company['name']} Inventory Pressure",
                f"{company['name']}の在庫圧力です。在庫/売上比率と在庫前年比を見ます。売上が伸びているのに在庫が急増すると、将来の供給過剰リスクが高まります。",
                f"{item['inventoryToRevenue']:.2f}x revenue" if item["inventoryToRevenue"] is not None else "n/a",
                item["inventoryToRevenue"],
                format_pct(item["inventoryYoy"]),
                item["inventoryYoy"],
                format_usd(item["inventory"]),
                item["inventory"],
                inv_score,
                "inventory_margin",
                item["date"],
            )
        )
        if item["capex"] is not None:
            capex_score = growth_score(item["capexYoy"], None)
            indicators.append(
                indicator(
                    f"{ticker}-CAPEX",
                    f"{company['name']} Capex",
                    f"{company['name']}の設備投資です。強いCapexは供給能力拡大を示し、短期では需要の強さ、将来では供給過剰リスクの材料になります。",
                    format_usd(item["capex"]),
                    item["capex"],
                    "n/a",
                    None,
                    format_pct(item["capexYoy"]),
                    item["capexYoy"],
                    capex_score,
                    "equipment" if block == "equipment" else "capacity",
                    item["date"],
                )
            )
        if item["backlog"] is not None:
            backlog_cycle_score = backlog_score(item["backlogToRevenue"], item["backlogYoy"])
            indicators.append(
                indicator(
                    f"{ticker}-ORDER-BACKLOG-PROXY",
                    f"{company['name']} Order Backlog Proxy",
                    f"{company['name']}の受注残・新規受注を直接取れない場合のproxyです。Remaining performance obligation、契約負債、繰延収益などSECで取得できる受注関連残高を売上比率と前年比で見ます。",
                    f"{item['backlogToRevenue']:.2f}x revenue" if item["backlogToRevenue"] is not None else format_usd(item["backlog"]),
                    item["backlogToRevenue"],
                    "n/a",
                    None,
                    format_pct(item["backlogYoy"]),
                    item["backlogYoy"],
                    backlog_cycle_score,
                    "orders",
                    item["date"],
                )
            )
        if ticker == "MU":
            proxy_score = memory_price_proxy_score(item["revenueQoq"], item["grossMarginQoq"], item["inventoryYoy"])
            indicators.append(
                indicator(
                    "MU-MEMORY-PRICE-PROXY",
                    "Micron Memory Price Cycle Proxy",
                    "DRAM/NAND/HBMのうち、HBM実価格は無料APIでは安定取得しづらいため、Micronの売上前期比、粗利率変化、在庫前年比からHBMを含むメモリ価格サイクルをproxyします。売上増と粗利率改善、在庫抑制が重なるほど価格環境は強いと見ます。",
                    f"{proxy_score:.0f}/100",
                    proxy_score,
                    f"GM {format_point(item['grossMarginQoq'])}",
                    item["grossMarginQoq"],
                    f"Rev QoQ {format_pct(item['revenueQoq'])}",
                    item["revenueQoq"],
                    proxy_score,
                    "memory_price",
                    item["date"],
                )
            )
        try:
            closes = fetch_yahoo_closes(company["yahoo"])
            reaction = price_change_after_date(closes, item["filed"], trading_days=5)
        except Exception as exc:
            print(f"Warning: {ticker} price reaction skipped: {exc}")
            reaction = None
        reaction_score = price_reaction_score(reaction)
        indicators.append(
            indicator(
                f"{ticker}-POST-FILING-REACTION",
                f"{company['name']} Post-Filing Price Reaction",
                f"{company['name']}の決算・10-Q/10-K提出後5営業日の株価反応です。好決算でも株価が上がらない場合は、期待値が高すぎる、またはサイクル後半の警戒サインとして見ます。",
                format_pct(reaction),
                reaction,
                "5 trading days",
                None,
                f"filed {item['filed'] or 'n/a'}",
                None,
                reaction_score,
                "market_reaction",
                item["filed"] or item["date"],
            )
        )

    ai_compute_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "ai_compute"])
    memory_items = [item for item in indicators if item.get("id", "").startswith("MU-") or item.get("block") == "memory_price"]
    memory_score = average([item.get("cycleScore") for item in memory_items])
    equipment_score = average([item.get("cycleScore") for item in indicators if item.get("block") in ("equipment", "capacity")])
    foundry_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "foundry_packaging"])
    guidance_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "guidance"])
    orders_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "orders"])
    market_reaction_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "market_reaction"])
    buyer_pressure_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "buyer_pressure"])
    buyer_stress = buyer_pressure.get("stress") if buyer_pressure.get("stress") is not None else 100 - buyer_pressure_score
    inventory_pressure_score = average(
        [100 - item.get("cycleScore") for item in indicators if item.get("block") == "inventory_margin" and item.get("id", "").endswith("-INVENTORY")],
        default=40,
    )
    margin_score_avg = average(
        [
            item.get("cycleScore")
            for item in indicators
            if item.get("id", "").endswith("-GROSS-MARGIN") or item.get("id", "").endswith("-OPERATING-MARGIN")
        ]
    )

    current_phase, phase_description = phase_from_scores(
        ai_compute_score,
        memory_score,
        equipment_score,
        inventory_pressure_score,
    )
    cycle_score = round(
        ai_compute_score * 0.20
        + memory_score * 0.18
        + equipment_score * 0.14
        + foundry_score * 0.09
        + guidance_score * 0.14
        + orders_score * 0.08
        + market_reaction_score * 0.06
        + buyer_pressure_score * 0.05
        + margin_score_avg * 0.04
        + (100 - inventory_pressure_score) * 0.02
    )

    signals = [
        {
            "key": "AI COMPUTE",
            "label": "AI Compute",
            "emoji": status_from_score(ai_compute_score)[0],
            "value": "NVIDIA/Broadcom需要を確認",
            "help": "NVIDIA Data CenterとBroadcom AI semiconductor revenueでAI accelerator、AI networking需要を見ます。",
        },
        {
            "key": "MEMORY",
            "label": "Memory / HBM",
            "emoji": status_from_score(memory_score)[0],
            "value": "TrendForce + Micronを確認",
            "help": "TrendForceのDRAM/NAND公開価格、Micronの売上、粗利率、在庫でメモリサイクルの方向感を見ます。HBM実価格は公開性が弱いためMicron指標でproxyします。",
        },
        {
            "key": "EQUIPMENT",
            "label": "Equipment",
            "emoji": status_from_score(equipment_score)[0],
            "value": "装置・能力拡大を確認",
            "help": "AMAT、Lam Research、KLAの売上・粗利・在庫・Capexで供給能力拡大の局面を見ます。",
        },
        {
            "key": "INVENTORY",
            "label": "Inventory / Margin",
            "emoji": status_from_score(inventory_pressure_score, positive=False)[0],
            "value": "在庫と粗利率で転換点を監視",
            "help": "在庫/売上比率、在庫前年比、粗利率の同時悪化は半導体サイクルのピークアウト警戒です。",
        },
        {
            "key": "FOUNDRY",
            "label": "Foundry / Packaging",
            "emoji": status_from_score(foundry_score)[0],
            "value": f"TSMC月次売上 {tsmc_monthly['yoy']}" if tsmc_monthly else "TSMC/CoWoSは次段階で接続",
            "help": "TSMC月次売上で先端ファウンドリ需要を見ます。HPC比率、CoWoS能力は今後追加対象です。GPU/HBMの供給制約を見る重要領域です。",
        },
        {
            "key": "MARKET",
            "label": "Market Reaction",
            "emoji": status_from_score(market_reaction_score)[0],
            "value": "決算後5営業日反応を確認",
            "help": "好決算・決算提出後に株価が素直に上がるかを見ます。好材料でも上がらない場合は、期待値が高すぎるサイクル後半の警戒材料です。",
        },
        {
            "key": "GUIDANCE",
            "label": "Guidance",
            "emoji": status_from_score(guidance_score)[0],
            "value": "NVIDIA/Broadcom見通しを確認",
            "help": "次四半期売上、AI semiconductor revenue、粗利率やCapex見通しを重視します。半導体株は過去決算より今後のガイダンスで動きやすいです。",
        },
        {
            "key": "ORDERS",
            "label": "Orders / Backlog",
            "emoji": status_from_score(orders_score)[0],
            "value": "受注残proxyを確認",
            "help": "直接の新規受注や受注残が取れない場合、SECのRPO、契約負債、繰延収益などをproxyとして使います。装置株では受注増と利益率改善が揃うかを重視します。",
        },
        {
            "key": "BUYER",
            "label": "Buyer Stress",
            "emoji": status_from_score(buyer_stress, positive=False)[0],
            "value": f"買い手側ストレス {buyer_stress:.0f}/100",
            "help": "ハイパースケーラーなどAI投資の買い手側が株価・FCF・Capex面で重くなっていないかを見ます。買い手が弱く、供給側だけが強い場合は、後のCapex減速・発注延期リスクを警戒します。",
        },
    ]

    latest_revenue_yoy = company_by_ticker.get("MU", {}).get("revenueYoy")
    latest_margin = company_by_ticker.get("MU", {}).get("grossMargin")
    latest_margin_text = f"{latest_margin:.1f}%" if latest_margin is not None else "n/a"
    dram_ddr5 = next((item for item in trendforce_prices if item.get("id") == "TF-DRAM-DDR5-16GB-SPOT"), None)
    nand_tlc = next((item for item in trendforce_prices if item.get("id") == "TF-NAND-512GB-TLC-SPOT"), None)
    main = (
        f"現在地は「{current_phase}」寄りです。{phase_description}。"
        f"AI ComputeはNVIDIA/Broadcomの既存データで確認し、Memory/HBMはTrendForceのDRAM/NAND価格とMicronの売上・粗利率・在庫で確認します。"
        f"DDR5 spotは{dram_ddr5['latest'] if dram_ddr5 else 'n/a'}、NAND 512Gb TLC spotは{nand_tlc['latest'] if nand_tlc else 'n/a'}です。"
        f"FoundryはTSMC月次売上{tsmc_monthly['latest'] if tsmc_monthly else 'n/a'}、前年比{tsmc_monthly['yoy'] if tsmc_monthly else 'n/a'}で確認します。"
        f"Micronの売上前年比は{format_pct(latest_revenue_yoy)}、粗利率は{latest_margin_text}です。"
        f"ガイダンススコアは{guidance_score:.0f}/100、決算後株価反応スコアは{market_reaction_score:.0f}/100です。"
        f"買い手側ストレスは{buyer_stress:.0f}/100で、ハイパースケーラー株価と供給側株価の乖離を監視します。"
        "設備投資・装置企業の売上が強い間は供給能力拡大局面ですが、在庫増と粗利率低下が重なる場合はOverbuild Riskへ警戒を引き上げます。"
    )

    output = {
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),
        "phase": current_phase,
        "phaseDescription": phase_description,
        "scoreHistory": [
            {"date": "Recovery", "score": 38},
            {"date": "Demand", "score": 58},
            {"date": "Shortage", "score": 70},
            {"date": "Capacity", "score": cycle_score},
        ],
        "signals": signals,
        "indicators": indicators,
        "investmentMap": investment_map(current_phase),
        "analysis": {
            "main": main,
            "up": [
                f"AI Computeスコアは{ai_compute_score:.0f}/100",
                f"Memory/HBMスコアは{memory_score:.0f}/100",
                f"Equipment/Capacityスコアは{equipment_score:.0f}/100",
                f"Foundry/Packagingスコアは{foundry_score:.0f}/100",
                f"Guidanceスコアは{guidance_score:.0f}/100",
            ],
            "risks": [
                f"在庫圧力スコアは{inventory_pressure_score:.0f}/100",
                f"決算後株価反応スコアは{market_reaction_score:.0f}/100",
                f"買い手側ストレスは{buyer_stress:.0f}/100、ハイパースケーラー60日平均は{format_pct(buyer_pressure.get('hyperscalerAvg'))}、供給側60日平均は{format_pct(buyer_pressure.get('supplyAvg'))}",
                "HBM実価格、SOX/SMH相対パフォーマンスは未接続",
                "TrendForce公開ページの構造変更時は前回成功値を維持",
                "Capex拡大が需要成長を上回る場合は将来の供給過剰に注意",
            ],
            "watch": [
                "Micronの粗利率改善が続くか",
                "TrendForceのDRAM/NAND価格が7日・30日で上向き続けるか",
                "Micron在庫/売上比率が悪化しないか",
                "NVIDIA/BroadcomのAI売上ガイダンスが鈍化しないか",
                "ハイパースケーラー株が弱いままBig Tech Capexが減速しないか",
                "AMAT/LRCX/KLACの受注・売上がピークアウトしないか",
                "TSMC月次売上とCoWoS供給制約の変化",
                "SOX/SMHが好決算に反応し続けるか",
            ],
        },
        "source": "SEC Companyfacts + TrendForce public price pages + Yahoo Finance chart data + existing NVIDIA/Broadcom feeds",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


def main():
    build()


if __name__ == "__main__":
    main()
