#!/usr/bin/env python3
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "semiconductor-cycle.json"
SEC_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts"
TWSE_MONTHLY_REVENUE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Credit-Risk-Monitor/1.0 contact@example.com",
)
TSMC_TWSE_CODE = "2330"

COMPANIES = [
    {
        "ticker": "AMD",
        "name": "Advanced Micro Devices",
        "cik": "0000002488",
        "group": "ai_compute",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "MU",
        "name": "Micron Technology",
        "cik": "0000723125",
        "group": "memory",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "AMAT",
        "name": "Applied Materials",
        "cik": "0000006951",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "LRCX",
        "name": "Lam Research",
        "cik": "0000707549",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
    {
        "ticker": "KLAC",
        "name": "KLA",
        "cik": "0000319201",
        "group": "equipment",
        "revenue_tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    },
]


def request_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": SEC_USER_AGENT})
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


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
    if previous in (None, 0):
        return None
    return (current / previous - 1) * 100


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


def company_metrics(company):
    facts = fetch_companyfacts(company["cik"])
    revenue_tag, revenue = extract_quarterly_usd(facts, company["revenue_tags"])
    gross_tag, gross = extract_quarterly_usd(facts, ["GrossProfit"])
    operating_tag, operating = extract_quarterly_usd(facts, ["OperatingIncomeLoss"])
    inventory_tag, inventory = extract_quarterly_usd(facts, ["InventoryNet", "InventoryFinishedGoodsNetOfReserves"])
    capex_tag, capex = extract_quarterly_usd(facts, ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"])

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
    gross_margin = latest_gross / latest_revenue * 100 if latest_gross is not None else None
    previous_margin = previous_gross / previous_revenue * 100 if previous_gross is not None else None
    gross_margin_qoq = gross_margin - previous_margin if gross_margin is not None and previous_margin is not None else None

    latest_operating = operating.get(latest_label, {}).get("value")
    previous_operating = operating.get(previous_label, {}).get("value")
    operating_margin = latest_operating / latest_revenue * 100 if latest_operating is not None else None
    previous_operating_margin = previous_operating / previous_revenue * 100 if previous_operating is not None else None
    operating_margin_qoq = (
        operating_margin - previous_operating_margin
        if operating_margin is not None and previous_operating_margin is not None
        else None
    )

    latest_inventory = inventory.get(latest_label, {}).get("value")
    year_ago_inventory = inventory.get(year_ago_label, {}).get("value")
    inventory_yoy = pct_change(latest_inventory, year_ago_inventory)
    inventory_to_revenue = latest_inventory / latest_revenue if latest_inventory is not None else None

    latest_capex = capex.get(latest_label, {}).get("value")
    year_ago_capex = capex.get(year_ago_label, {}).get("value")
    capex_yoy = pct_change(latest_capex, year_ago_capex)

    return {
        "company": company,
        "date": latest_label,
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
        "tags": {
            "revenue": revenue_tag,
            "gross": gross_tag,
            "operating": operating_tag,
            "inventory": inventory_tag,
            "capex": capex_tag,
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
    for item in [nvidia_dc, broadcom_ai]:
        if item:
            indicators.append(item)

    tsmc_monthly = None
    try:
        tsmc_monthly = fetch_tsmc_monthly_revenue()
        if tsmc_monthly:
            indicators.append(tsmc_monthly)
    except Exception as exc:
        print(f"Warning: TSMC monthly revenue skipped: {exc}")

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

    ai_compute_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "ai_compute"])
    memory_items = [item for item in indicators if item.get("id", "").startswith("MU-")]
    memory_score = average([item.get("cycleScore") for item in memory_items])
    equipment_score = average([item.get("cycleScore") for item in indicators if item.get("block") in ("equipment", "capacity")])
    foundry_score = average([item.get("cycleScore") for item in indicators if item.get("block") == "foundry_packaging"])
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
        ai_compute_score * 0.25
        + memory_score * 0.22
        + equipment_score * 0.17
        + foundry_score * 0.11
        + margin_score_avg * 0.13
        + (100 - inventory_pressure_score) * 0.12
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
            "value": "Micronでメモリサイクルを確認",
            "help": "Micronの売上、粗利率、在庫でHBM/DRAMサイクルの方向感を見ます。HBMの詳細コメントは今後追加対象です。",
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
            "label": "Market Signal",
            "emoji": "⚪",
            "value": "SOX/SMHは次段階で接続",
            "help": "SOX、SMH、NVDA、MU、TSM、ASMLなどの相対パフォーマンスを今後接続します。",
        },
    ]

    latest_revenue_yoy = company_by_ticker.get("MU", {}).get("revenueYoy")
    latest_margin = company_by_ticker.get("MU", {}).get("grossMargin")
    main = (
        f"現在地は「{current_phase}」寄りです。{phase_description}。"
        f"AI ComputeはNVIDIA/Broadcomの既存データで確認し、Memory/HBMはMicronの売上・粗利率・在庫でproxyします。"
        f"FoundryはTSMC月次売上{tsmc_monthly['latest'] if tsmc_monthly else 'n/a'}、前年比{tsmc_monthly['yoy'] if tsmc_monthly else 'n/a'}で確認します。"
        f"Micronの売上前年比は{format_pct(latest_revenue_yoy)}、粗利率は{latest_margin:.1f}%です。"
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
            ],
            "risks": [
                f"在庫圧力スコアは{inventory_pressure_score:.0f}/100",
                "HBM価格、SOX相対パフォーマンスは未接続",
                "Capex拡大が需要成長を上回る場合は将来の供給過剰に注意",
            ],
            "watch": [
                "Micronの粗利率改善が続くか",
                "Micron在庫/売上比率が悪化しないか",
                "NVIDIA/BroadcomのAI売上ガイダンスが鈍化しないか",
                "AMAT/LRCX/KLACの受注・売上がピークアウトしないか",
                "TSMC月次売上とCoWoS供給制約の変化",
                "SOX/SMHが好決算に反応し続けるか",
            ],
        },
        "source": "SEC Companyfacts + existing NVIDIA/Broadcom feeds",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


def main():
    build()


if __name__ == "__main__":
    main()
