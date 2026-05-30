const sampleData = {
  updatedAt: "2026-05-28T09:00:00+09:00",
  scoreHistory: [
    { date: "2026-01", score: 49 },
    { date: "2026-02", score: 53 },
    { date: "2026-03", score: 58 },
    { date: "2026-04", score: 65 },
    { date: "2026-05", score: 72 }
  ],
  creditYoy: [
    { date: "2026-01", value: 18.5 },
    { date: "2026-02", value: 20.2 },
    { date: "2026-03", value: 22.9 },
    { date: "2026-04", value: 26.0 },
    { date: "2026-05", value: 25.4 }
  ],
  signals: [
    { key: "credit", label: "Credit Expansion", emoji: "🔴", value: "ノンバンク向け貸出が高い伸び", help: "銀行からノンバンク金融機関への貸出など、信用仲介の拡大を見ます。前年比が高止まりすると過熱、急減速や残高減少に転じると信用収縮リスクです。" },
    { key: "stress", label: "Market Stress", emoji: "🟡", value: "ストレス指標は小幅上昇", help: "HYスプレッド、金融ストレス指数、VIXなどで市場が信用リスクを織り込み始めているかを見ます。同時に上昇すると危険度が上がります。" },
    { key: "demand", label: "AI Demand", emoji: "🟢", value: "AI需要・業績は強い", help: "NVIDIAやBig TechのAI関連売上・Capexを見ます。売上成長や設備投資計画が急減速すると、信用拡大を正当化しにくくなります。" },
    { key: "rates", label: "Rates", emoji: "🟠", value: "金利環境は重い", help: "長短金利や借入コストを見ます。高金利が続くほど、AIデータセンターやprivate creditの資金調達負担が増えます。" },
    { key: "liquidity", label: "Liquidity", emoji: "🟡", value: "流動性は中立から注意", help: "TGA、RRP、準備預金などの市場流動性を見ます。流動性が細ると、高レバレッジ投資や信用市場が不安定になりやすいです。" },
    { key: "prediction", label: "Prediction Market", emoji: "🟡", value: "予測市場は中程度", help: "Polymarket参加者がAIバブル崩壊リスクをどう価格付けしているかを見る市場心理指標です。実体データではないため、総合スコアへの影響は軽めにします。水準よりも24時間・7日での急変を重視します。" }
  ],
  indicators: [
    {
      id: "LNFACBM027SBOG",
      name: "Loans to Nondepository Financial Institutions",
      help: "銀行からノンバンク金融機関への貸出残高です。AI/private creditへお金が流れているかを見るproxyです。前年比+20%超は、経済成長よりかなり速く信用が膨らんでいる目安。高止まりは過熱、急減速や残高減少は信用収縮に注意です。",
      latest: "1.98T",
      previousChange: "+1.8%",
      yoy: "+25.4%",
      risk: "🔴",
      riskClass: "risk-danger",
      nextRelease: "Monthly"
    },
    {
      id: "BAMLH0A0HYM2",
      name: "ICE BofA High Yield OAS",
      help: "信用力が低めの企業が借りる時の追加金利です。4%超で投資家がリスクを意識、5.5%超で信用不安がはっきり、7%超でデフォルトや景気悪化を強く織り込む水準です。",
      latest: "3.95%",
      previousChange: "+0.12pt",
      yoy: "+0.34pt",
      risk: "🟡",
      riskClass: "risk-watch",
      nextRelease: "Daily"
    },
    {
      id: "STLFSI4",
      name: "St. Louis Fed Financial Stress Index",
      help: "金融市場全体の体温計のような指数です。マイナスなら平常、0超で平均よりストレス高め、0.8超で複数市場に不安、1.6超でかなり強いストレスと見ます。",
      latest: "-0.42",
      previousChange: "+0.08",
      yoy: "+0.16",
      risk: "🟡",
      riskClass: "risk-watch",
      nextRelease: "Weekly"
    },
    {
      id: "VIXCLS",
      name: "CBOE Volatility Index",
      help: "株式市場の不安度を見る指数です。20超で不安定、30超で投資家がかなり警戒、40超で急落・危機局面に近い水準です。HYスプレッドや金融ストレスと同時に上がると重要です。",
      latest: "18.7",
      previousChange: "+1.1",
      yoy: "+2.4",
      risk: "🟡",
      riskClass: "risk-watch",
      nextRelease: "Daily"
    },
    {
      id: "DGS10-DGS2",
      name: "10Y minus 2Y Treasury Spread",
      help: "長期金利と短期金利の差です。逆イールドや急なスティープ化は景気・金融環境の変化を示します。AI信用リスクでは、金利上昇と信用スプレッド拡大が同時に起きる時を警戒します。",
      latest: "+0.21pt",
      previousChange: "-0.03pt",
      yoy: "+0.44pt",
      risk: "🟠",
      riskClass: "risk-high",
      nextRelease: "Daily"
    },
    {
      id: "NVDA-DC-GROWTH",
      name: "NVIDIA Data Center Revenue Growth",
      help: "NVIDIAのデータセンター売上成長率です。AIインフラ需要の代表指標です。高成長なら信用拡大を支えますが、成長率が急減速するとAI投資の前提が弱くなります。",
      latest: "+92% YoY",
      previousChange: "slower",
      yoy: "+92%",
      risk: "🟢",
      riskClass: "risk-low",
      nextRelease: "Quarterly"
    }
  ]
};

const dataVersion = "14";

function dataUrl(path) {
  return `${path}?v=${dataVersion}`;
}

function getRiskMeta(score) {
  if (score >= 80) return { emoji: "🔴", label: "Danger", phase: "信用収縮警戒", className: "risk-danger" };
  if (score >= 60) return { emoji: "🟠", label: "High Risk", phase: "高めの監視局面", className: "risk-high" };
  if (score >= 35) return { emoji: "🟡", label: "Watch", phase: "注意局面", className: "risk-watch" };
  return { emoji: "🟢", label: "Calm", phase: "平常", className: "risk-low" };
}

function getMacroRiskMeta(score) {
  if (score >= 75) return { emoji: "🔴", label: "Danger", phase: "株式に強い逆風", className: "risk-danger" };
  if (score >= 55) return { emoji: "🟠", label: "High Watch", phase: "高めの警戒局面", className: "risk-high" };
  if (score >= 25) return { emoji: "🟡", label: "Watch", phase: "注意局面", className: "risk-watch" };
  return { emoji: "🟢", label: "Calm", phase: "平常", className: "risk-low" };
}

const helpText = {
  credit: "銀行からノンバンク金融機関への貸出など、信用仲介の拡大を見ます。前年比が高止まりすると過熱、急減速や残高減少に転じると信用収縮リスクです。",
  stress: "HYスプレッド、金融ストレス指数、VIXなどで市場が信用リスクを織り込み始めているかを見ます。同時に上昇すると危険度が上がります。",
  demand: "NVIDIAやBig TechのAI関連売上・Capexを見ます。売上成長や設備投資計画が急減速すると、信用拡大を正当化しにくくなります。",
  rates: "長短金利や借入コストを見ます。高金利が続くほど、AIデータセンターやprivate creditの資金調達負担が増えます。",
  liquidity: "TGA、RRP、準備預金などの市場流動性を見ます。流動性が細ると、高レバレッジ投資や信用市場が不安定になりやすいです。",
  prediction: "Polymarket参加者がAIバブル崩壊リスクをどう価格付けしているかを見る市場心理指標です。実体データではないため、総合スコアへの影響は軽めにします。水準よりも24時間・7日での急変を重視します。",
  LNFACBM027SBOG: "銀行からノンバンク金融機関への貸出残高です。AI/private creditへお金が流れているかを見るproxyです。前年比+20%超は、経済成長よりかなり速く信用が膨らんでいる目安。高止まりは過熱、急減速や残高減少は信用収縮に注意です。",
  BAMLH0A0HYM2: "信用力が低めの企業が借りる時の追加金利です。4%超で投資家がリスクを意識、5.5%超で信用不安がはっきり、7%超でデフォルトや景気悪化を強く織り込む水準です。",
  STLFSI4: "金融市場全体の体温計のような指数です。マイナスなら平常、0超で平均よりストレス高め、0.8超で複数市場に不安、1.6超でかなり強いストレスと見ます。",
  VIXCLS: "株式市場の不安度を見る指数です。20超で不安定、30超で投資家がかなり警戒、40超で急落・危機局面に近い水準です。HYスプレッドや金融ストレスと同時に上がると重要です。",
  DGS10: "米10年国債利回りです。長期の借入コストの目安です。4.5%超で資金調達が重くなり始め、5%超でデータセンター投資の採算に圧力、5.5%超で借金依存の成長にかなり厳しい水準です。",
  DGS2: "米2年国債利回りです。今後数年の高金利見通しに敏感です。高止まりすると短期借入や借り換えコストが重くなり、AIインフラやprivate creditの負担になります。",
  "DGS10-DGS2": "長期金利と短期金利の差です。逆イールドや急なスティープ化は景気・金融環境の変化を示します。AI信用リスクでは、金利上昇と信用スプレッド拡大が同時に起きる時を警戒します。",
  WTREGEN: "米財務省のFRB口座残高です。TGAが増えると、市場から資金を吸い上げやすくなります。800B超で注意、1T超で高リスク、1.2T超で流動性の重さを強く警戒します。",
  RRPONTSYD: "マネーマーケット資金がFRBに退避している残高です。多い時は余剰流動性のクッションになります。250B割れで注意、100B割れで高リスク、25B割れでクッション枯渇を警戒します。",
  WRESBAL: "銀行がFRBに置いている準備預金です。金融システムの余裕を示します。3.2T割れで注意、3.0T割れで高リスク、2.8T割れで流動性の薄さを強く警戒します。",
  "NVDA-DC-GROWTH": "NVIDIAのデータセンター売上成長率です。AIインフラ需要の代表指標です。高成長なら信用拡大を支えますが、+30%台以下へ急減速するとAI投資の前提が弱くなります。",
  "NVDA-REVENUE": "NVIDIAの四半期総売上です。Data Centerだけではありませんが、AI需要全体の勢いを見る補助指標です。前年比や前四半期比が急減速すると注意です。",
  "NVDA-GROSS-MARGIN": "NVIDIAの収益性を見る指標です。粗利率が高いほどAI半導体の価格決定力が強い状態です。70%割れで注意、65%割れで競争や在庫圧力を警戒します。",
  "NVDA-REVENUE-OUTLOOK": "次四半期の売上ガイダンスです。AI需要の先行ヒントとして見ます。前四半期比で大きく鈍化、または市場期待を下回る場合はAI需要の減速シグナルです。",
  "POLYMARKET-AI-BUBBLE": "Polymarket上のAIバブル崩壊予測です。Yes確率が上がるほど、市場参加者がAI関連の急な調整を意識していることを示します。20%超で注意、35%超で高めの警戒、50%超で予測市場も本格警戒と見ます。24hで+5pt、7日で+10ptのような急上昇は特に重要です。",
  CPIAUCSL: "米国の消費者物価指数です。前年比が3%を超えるとインフレ再燃を意識しやすく、4%超で株式市場には金利高止まりリスク、5%超でかなり強い逆風と見ます。",
  CPILFESL: "食品とエネルギーを除いた物価指数です。粘着的なインフレを見るため重要です。前年比3%超で注意、4%超で金融引き締め長期化、5%超で株式市場には強い逆風と見ます。",
  PPIACO: "企業側の仕入れ・生産コストを見る物価指数です。CPIに先行してインフレ圧力を示すことがあります。前年比3%超で注意、5%超で高リスク、8%超で強いインフレ圧力と見ます。",
  FEDFUNDS: "米国の実効政策金利です。高いほど株式市場にとっては資金調達・割引率の重荷です。4.5%超で注意、5%超で高リスク、5.5%超でかなり強い逆風と見ます。",
  UNRATE: "米国の失業率です。低すぎる時は利下げしにくく、高すぎる時は景気悪化懸念になります。ここでは景気悪化リスクとして4.5%超で注意、5%超で高リスク、6%超で危険水準と見ます。",
  A191RL1Q225SBEA: "米国の実質GDP成長率、四半期年率です。株式市場では景気の体温計として見ます。0%割れで景気後退リスクに注意、-1%割れで高リスク、-2%割れで企業業績への強い逆風と見ます。",
  PAYEMS: "米国の非農業部門雇用者数です。前月からの増加幅で雇用の勢いを見ます。+100K割れで注意、0K割れで高リスク、-100K割れで景気後退リスクを強く警戒します。",
  ICSA: "新規失業保険申請件数です。雇用悪化の早めのサインとして見ます。250K超で注意、300K超で高リスク、350K超で景気悪化を強く警戒します。",
  RSAFS: "米国の小売売上高です。消費の強さを見ます。前年比0%割れで注意、-2%割れで高リスク、-5%割れで消費悪化を強く警戒します。",
  T10YIE: "市場が織り込む10年期待インフレ率です。2.5%超でインフレ期待の高まりに注意、3%超で高リスク、3.5%超で金利上昇圧力を強く警戒します。",
  "BIGTECH-REVENUE-TOTAL": "Big Tech 4社の四半期売上合計です。株式市場では企業業績の底堅さを見る材料です。前年比が5%割れで注意、0%割れで業績悪化リスクを強く警戒します。",
  "BIGTECH-OPERATING-MARGIN": "Big Tech 4社の営業利益率です。売上だけでなく収益性が保たれているかを見ます。22%割れで注意、15%割れで企業利益への強い逆風と見ます。"
};

function helpButton(text) {
  if (!text) return "";
  return `<button class="help-button" type="button" aria-label="説明" data-tooltip="${escapeHtml(text)}">?</button>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function generateAnalysis(data) {
  const latestScore = data.scoreHistory.at(-1).score;
  const previousScore = data.scoreHistory.at(-2)?.score ?? latestScore;
  const delta = latestScore - previousScore;
  const creditYoy = data.creditYoy.at(-1)?.value ?? 0;
  const meta = getRiskMeta(latestScore);

  const direction = delta > 2 ? "前回からリスクは上昇しています" : delta < -2 ? "前回からリスクは低下しています" : "前回から大きな変化はありません";
  const creditText = creditYoy >= 20
    ? "ノンバンク向け貸出の前年比は高水準で、AIインフラ投資を支える信用拡大が続いている可能性があります"
    : "ノンバンク向け貸出の伸びは過熱水準からはやや離れています";
  const prediction = data.indicators.find(item => item.id === "POLYMARKET-AI-BUBBLE");
  const predictionText = prediction
    ? `予測市場ではAIバブル崩壊確率が${prediction.latest}、24時間変化は${prediction.previousChange}です`
    : "予測市場データは未接続です";
  const bigTechCapex = data.indicators.find(item => item.id === "BIGTECH-CAPEX-TOTAL");
  const capexText = bigTechCapex
    ? `Big Tech 4社のCapex合計は${bigTechCapex.latest}、前年比${bigTechCapex.yoy}で、AIインフラ投資はまだ強い状態です`
    : "Big Tech Capexデータは未接続です";

  const main = `${meta.phase}です。${creditText}。一方で、ハイイールドスプレッドや金融ストレスは危機的な急拡大までは示しておらず、現時点では「崩壊直前」ではなく「信用面の過熱を監視する段階」と見ます。${capexText}。${predictionText}。${direction}。AI需要とBig Techの設備投資が強い間は信用拡大が正当化されやすい一方、貸出の急減速、スプレッド拡大、AI Capexの下方修正、予測市場での急なリスク再評価が重なる場合は警戒度を引き上げます。`;

  return {
    main,
    up: [
      `LNFACBM027SBOGの前年比が${creditYoy.toFixed(1)}%`,
      "金利環境がAIインフラ投資の資金調達負担になりやすい",
      delta > 0 ? `総合スコアが前回比+${delta}pt` : "信用拡大指標の水準がまだ高い"
    ],
    down: [
      "金融ストレス指数はまだ危機局面を示していない",
      "NVIDIA Data Center成長はAI需要の強さを示している",
      bigTechCapex ? `Big Tech Capex合計が前年比${bigTechCapex.yoy}` : "Big Tech Capexデータは未接続",
      "VIXとHYスプレッドは急激な信用収縮までは示していない"
    ],
    watch: [
      "LNFACBM027SBOGの高止まり、または残高減少への転換",
      "Big TechのAI Capexガイダンス下方修正",
      "HYスプレッドとSTLFSI4の同時悪化",
      "PolymarketのAIバブル確率が24hで+5pt以上、または7日で+10pt以上に急上昇",
      "NVIDIA Data Center売上成長率と粗利率の鈍化"
    ]
  };
}

function getMacroData(data) {
  if (data.macro) return data.macro;
  const macroIndicators = data.indicators.filter(item => ["DGS10", "DGS2", "VIXCLS"].includes(item.id));
  return {
    scoreHistory: data.scoreHistory.map(item => ({ ...item })),
    cpiYoy: [],
    signals: [
      { key: "inflation", label: "Inflation", emoji: "⚪", value: "CPI/PPI接続待ち", help: "CPI、Core CPI、PPIでインフレ圧力を見ます。" },
      { key: "rates", label: "Rates", emoji: "🟡", value: "金利データのみ接続", help: "10年金利、2年金利、政策金利で割引率と資金調達コストを見ます。" },
      { key: "growth", label: "Growth", emoji: "⚪", value: "GDP/雇用データ接続待ち", help: "実質GDP成長率と失業率で景気悪化リスクを見ます。" },
      { key: "volatility", label: "Market Volatility", emoji: "🟢", value: "VIXは落ち着き", help: "VIXで株式市場の不安度を見ます。" }
    ],
    indicators: macroIndicators
  };
}

function generateMacroAnalysis(macro) {
  const latestScore = macro.scoreHistory.at(-1)?.score ?? 30;
  const previousScore = macro.scoreHistory.at(-2)?.score ?? latestScore;
  const delta = latestScore - previousScore;
  const meta = getMacroRiskMeta(latestScore);
  const byId = Object.fromEntries(macro.indicators.map(item => [item.id, item]));
  const cpi = byId.CPIAUCSL;
  const coreCpi = byId.CPILFESL;
  const ppi = byId.PPIACO;
  const dgs10 = byId.DGS10;
  const fedFunds = byId.FEDFUNDS;
  const unrate = byId.UNRATE;
  const gdpGrowth = byId.A191RL1Q225SBEA;
  const payrolls = byId.PAYEMS;
  const joblessClaims = byId.ICSA;
  const retailSales = byId.RSAFS;
  const breakevenInflation = byId.T10YIE;
  const bigTechRevenue = byId["BIGTECH-REVENUE-TOTAL"];
  const bigTechMargin = byId["BIGTECH-OPERATING-MARGIN"];
  const vix = byId.VIXCLS;
  const direction = delta > 2 ? "前回からマクロ警戒度は上昇しています" : delta < -2 ? "前回からマクロ警戒度は低下しています" : "前回から大きな変化はありません";

  const inflationText = cpi
    ? `CPI前年比は${cpi.yoy}、Core CPIは${coreCpi?.yoy ?? "n/a"}、10年期待インフレ率は${breakevenInflation?.latest ?? "n/a"}で、インフレが株式市場に与える圧力を確認する局面です`
    : "CPI/Core CPIデータはまだ接続されていません";
  const ratesText = dgs10
    ? `10年金利は${dgs10.latest}、政策金利は${fedFunds?.latest ?? "n/a"}です`
    : "金利データはまだ接続されていません";
  const growthText = unrate
    ? `実質GDP成長率は${gdpGrowth?.latest ?? "n/a"}、雇用者数の前月比は${payrolls?.previousChange ?? "n/a"}、失業保険申請は${joblessClaims?.latest ?? "n/a"}、小売売上前年比は${retailSales?.yoy ?? "n/a"}です`
    : "雇用データはまだ接続されていません";
  const volatilityText = vix
    ? `VIXは${vix.latest}で、市場心理のストレスを示します`
    : "VIXデータはまだ接続されていません";
  const earningsText = bigTechRevenue
    ? `Big Tech売上合計は${bigTechRevenue.latest}、前年比${bigTechRevenue.yoy}、営業利益率は${bigTechMargin?.latest ?? "n/a"}です`
    : "SEC企業業績データはまだ接続されていません";

  const up = [];
  if ((cpi?.yoyRaw ?? 0) >= 3) up.push(`CPI前年比が${cpi.yoy}でインフレ再燃に注意`);
  if ((coreCpi?.yoyRaw ?? 0) >= 3) up.push(`Core CPI前年比が${coreCpi.yoy}で粘着的な物価圧力に注意`);
  if ((ppi?.yoyRaw ?? 0) >= 3) up.push(`PPI前年比が${ppi.yoy}で企業コスト上昇に注意`);
  if ((breakevenInflation?.latestRaw ?? 0) >= 2.5) up.push(`10年期待インフレ率が${breakevenInflation.latest}で金利上昇圧力に注意`);
  if ((dgs10?.latestRaw ?? 0) >= 4.5) up.push(`10年金利が${dgs10.latest}で株式バリュエーションの重荷`);
  if ((fedFunds?.latestRaw ?? 0) >= 4.5) up.push(`政策金利が${fedFunds.latest}で金融環境はまだ引き締まり気味`);
  if ((unrate?.latestRaw ?? 0) >= 4.5) up.push(`失業率が${unrate.latest}で景気悪化リスクに注意`);
  if ((gdpGrowth?.latestRaw ?? 99) < 0) up.push(`実質GDP成長率が${gdpGrowth.latest}で景気減速に注意`);
  if ((payrolls?.previousChangeRaw ?? 999) < 100) up.push(`雇用者数の前月比が${payrolls.previousChange}で雇用の勢いに注意`);
  if ((joblessClaims?.latestRaw ?? 0) >= 250000) up.push(`新規失業保険申請が${joblessClaims.latest}で雇用悪化の早期サインに注意`);
  if ((retailSales?.yoyRaw ?? 99) < 0) up.push(`小売売上前年比が${retailSales.yoy}で消費減速に注意`);
  if ((bigTechRevenue?.yoyRaw ?? 99) < 5) up.push(`Big Tech売上前年比が${bigTechRevenue.yoy}で企業業績の鈍化に注意`);
  if ((bigTechMargin?.latestRaw ?? 99) < 22) up.push(`Big Tech営業利益率が${bigTechMargin.latest}で収益性低下に注意`);
  if ((vix?.latestRaw ?? 0) >= 20) up.push(`VIXが${vix.latest}で市場心理が不安定`);

  const down = [];
  if ((cpi?.yoyRaw ?? 99) < 3) down.push(`CPI前年比は${cpi?.yoy ?? "n/a"}で過度なインフレ警戒ではない`);
  if ((breakevenInflation?.latestRaw ?? 99) < 2.5) down.push(`10年期待インフレ率は${breakevenInflation?.latest ?? "n/a"}で市場のインフレ期待は抑制的`);
  if ((dgs10?.latestRaw ?? 99) < 4.5) down.push(`10年金利は${dgs10?.latest ?? "n/a"}で警戒水準を下回る`);
  if ((vix?.latestRaw ?? 99) < 20) down.push(`VIXは${vix?.latest ?? "n/a"}で市場心理は比較的落ち着き`);
  if ((unrate?.latestRaw ?? 99) < 4.5) down.push(`失業率は${unrate?.latest ?? "n/a"}で雇用悪化はまだ限定的`);
  if ((gdpGrowth?.latestRaw ?? -99) >= 1.5) down.push(`実質GDP成長率は${gdpGrowth.latest}で景気はまだ底堅い`);
  if ((retailSales?.yoyRaw ?? -99) >= 2) down.push(`小売売上前年比は${retailSales.yoy}で消費は底堅い`);
  if ((bigTechRevenue?.yoyRaw ?? -99) >= 5) down.push(`Big Tech売上前年比は${bigTechRevenue.yoy}で企業業績は底堅い`);
  if ((bigTechMargin?.latestRaw ?? 0) >= 22) down.push(`Big Tech営業利益率は${bigTechMargin.latest}で収益性は維持されている`);

  return {
    main: `${meta.phase}です。${inflationText}。${ratesText}。${growthText}。${earningsText}。${volatilityText}。${direction}。株式市場を見るうえでは、インフレ鈍化と金利低下は追い風、インフレ再加速・金利上昇・雇用悪化・企業業績鈍化・VIX上昇が重なる場合は警戒度を引き上げます。`,
    up: up.length ? up : ["現時点で強い逆風は限定的です"],
    down: down.length ? down : ["株式を明確に支えるマクロ要因はまだ限定的です"],
    watch: [
      "CPI/Core CPI/PPIの前年比が再加速するか",
      "10年期待インフレ率が2.5%を超えて上昇するか",
      "10年金利が4.5%を明確に上回って定着するか",
      "GDP成長率の鈍化、雇用者数の減速、失業保険申請の増加が同時に起きるか",
      "小売売上が前年比マイナスへ転じるか",
      "Big Techの売上成長率と営業利益率が同時に悪化するか",
      "VIXが20超、30超へ急上昇するか",
      "利下げ期待が株式市場を支えられるか"
    ]
  };
}

async function loadData() {
  try {
    const response = await fetch(dataUrl("data/latest.json"), { cache: "no-store" });
    if (!response.ok) throw new Error("latest.json not found");
    let data = await response.json();
    try {
      const nvidiaResponse = await fetch(dataUrl("data/nvidia.json"), { cache: "no-store" });
      if (!nvidiaResponse.ok) throw new Error("nvidia.json not found");
      if (!(data.externalDataMerged ?? []).includes("nvidia") && !(data.externalDataMerged ?? []).includes("ai-demand")) {
        data = mergeAiDemand(data, await nvidiaResponse.json());
      }
    } catch {
    }
    try {
      const aiResponse = await fetch(dataUrl("data/ai-demand.json"), { cache: "no-store" });
      if (!aiResponse.ok) throw new Error("ai-demand.json not found");
      if (!(data.externalDataMerged ?? []).includes("nvidia") && !(data.externalDataMerged ?? []).includes("ai-demand")) {
        data = mergeAiDemand(data, await aiResponse.json());
      }
    } catch {
    }
    try {
      const polymarketResponse = await fetch(dataUrl("data/polymarket.json"), { cache: "no-store" });
      if (!polymarketResponse.ok) throw new Error("polymarket.json not found");
      if (!(data.externalDataMerged ?? []).includes("polymarket")) {
        data = mergePolymarket(data, await polymarketResponse.json());
      }
    } catch {
    }
    return data;
  } catch {
    return sampleData;
  }
}

function mergeAiDemand(data, aiDemand) {
  const indicators = [
    ...data.indicators.filter(item => item.block !== "demand"),
    ...(aiDemand.indicators ?? [])
  ];
  const demandScores = (aiDemand.indicators ?? [])
    .map(item => item.riskScore)
    .filter(score => Number.isFinite(score));
  const demandScore = demandScores.length
    ? demandScores.reduce((sum, score) => sum + score, 0) / demandScores.length
    : 30;

  const scoreHistory = data.scoreHistory.map(item => ({ ...item }));
  if (scoreHistory.length) {
    const latest = scoreHistory.at(-1);
    latest.score = Math.round(latest.score * 0.9 + demandScore * 0.1);
  }

  return {
    ...data,
    scoreHistory,
    signals: data.signals.map(signal => signal.key === "demand" ? aiDemand.signal : signal),
    indicators
  };
}

function mergePolymarket(data, polymarket) {
  const indicators = [
    ...data.indicators.filter(item => item.block !== "prediction"),
    ...(polymarket.indicators ?? [])
  ];
  const predictionScore = (polymarket.indicators ?? [])
    .map(item => item.riskScore)
    .find(score => Number.isFinite(score)) ?? 30;

  const scoreHistory = data.scoreHistory.map(item => ({ ...item }));
  if (scoreHistory.length) {
    const latest = scoreHistory.at(-1);
    latest.score = Math.round(latest.score * 0.95 + predictionScore * 0.05);
  }

  const withoutPrediction = data.signals.filter(signal => signal.key !== "prediction");
  return {
    ...data,
    scoreHistory,
    signals: [...withoutPrediction, polymarket.signal],
    indicators
  };
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function getNextScheduledUpdate(now = new Date()) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
  const parts = Object.fromEntries(formatter.formatToParts(now).map(part => [part.type, part.value]));
  const jstToday = new Date(`${parts.year}-${parts.month}-${parts.day}T00:00:00+09:00`);
  const currentMinutes = Number(parts.hour) * 60 + Number(parts.minute);
  const scheduledMinutes = 7 * 60 + 15;
  let candidate = new Date(jstToday.getTime() + (currentMinutes < scheduledMinutes ? 0 : 1) * 24 * 60 * 60 * 1000);

  while (candidate.getDay() === 0 || candidate.getDay() === 6) {
    candidate = new Date(candidate.getTime() + 24 * 60 * 60 * 1000);
  }

  candidate = new Date(candidate.getTime() + scheduledMinutes * 60 * 1000);
  return `${formatDate(candidate.toISOString())}頃`;
}

function renderSignals(signals, selector = "#signal-grid") {
  document.querySelector(selector).innerHTML = signals.map(signal => `
    <article class="signal-card">
      <div class="signal-top">
        <span class="section-label">${signal.key}</span>
        <div class="signal-actions">
          ${helpButton(signal.help ?? helpText[signal.key])}
          <span class="signal-emoji">${signal.emoji}</span>
        </div>
      </div>
      <p class="signal-title">${signal.label}</p>
      <p class="signal-value">${signal.value}</p>
    </article>
  `).join("");
}

function renderTable(indicators, selector = "#indicator-table") {
  document.querySelector(selector).innerHTML = indicators.map(item => `
    <tr>
      <td>
        <div class="indicator-name">
          <div>
            <strong>${item.id}</strong>
            <small>${item.name}</small>
          </div>
          ${helpButton(item.help ?? helpText[item.id])}
        </div>
      </td>
      <td>${item.latest}</td>
      <td>${item.previousChange}</td>
      <td>${item.yoy}</td>
      <td class="${item.riskClass}">${item.risk}</td>
      <td>${item.nextRelease}</td>
    </tr>
  `).join("");
}

function renderList(selector, items) {
  document.querySelector(selector).innerHTML = items.map(item => `<li>${item}</li>`).join("");
}

function pointsFor(data, key) {
  const values = data.map(item => item[key]);
  const width = 640;
  const height = 230;
  const plot = { left: 46, right: 118, top: 24, bottom: 42 };
  const max = Math.max(...values);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  return data.map((item, index) => {
    const x = plot.left + (index / Math.max(data.length - 1, 1)) * (width - plot.left - plot.right);
    const y = plot.top + ((max - item[key]) / range) * (height - plot.top - plot.bottom);
    return { x, y, label: item.date, value: item[key] };
  });
}

function renderLineChart(selector, data, key, options = {}) {
  const chart = document.querySelector(selector);
  const width = 640;
  const height = 230;
  const plot = { left: 46, right: 118, top: 24, bottom: 42 };
  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const pts = pointsFor(data, key);
  const path = pts.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const last = pts.at(-1);
  const valueText = `${last.value}${options.suffix ?? ""}`;
  const labelX = Math.min(width - 82, last.x + 18);
  const labelY = Math.max(plot.top + 12, Math.min(height - plot.bottom - 8, last.y + 4));
  const labelWidth = Math.max(42, valueText.length * 8 + 16);
  const thresholds = options.thresholds ? `
    <rect x="${plot.left}" y="${plot.top}" width="${plotWidth}" height="${plotHeight * 0.25}" fill="#fce8e8" />
    <rect x="${plot.left}" y="${plot.top + plotHeight * 0.25}" width="${plotWidth}" height="${plotHeight * 0.25}" fill="#fff0df" />
    <rect x="${plot.left}" y="${plot.top + plotHeight * 0.5}" width="${plotWidth}" height="${plotHeight * 0.25}" fill="#fff8d9" />
    <rect x="${plot.left}" y="${plot.top + plotHeight * 0.75}" width="${plotWidth}" height="${plotHeight * 0.25}" fill="#e8f6ee" />
  ` : "";

  chart.innerHTML = `
    <svg viewBox="0 0 640 230" role="img" aria-label="${options.label ?? "line chart"}">
      ${thresholds}
      <g stroke="#dfe5ef" stroke-width="1">
        <line x1="${plot.left}" y1="${plot.top}" x2="${plot.left}" y2="${height - plot.bottom}" />
        <line x1="${plot.left}" y1="${height - plot.bottom}" x2="${plot.left + plotWidth}" y2="${height - plot.bottom}" />
        <line x1="${plot.left}" y1="${plot.top + plotHeight * 0.25}" x2="${plot.left + plotWidth}" y2="${plot.top + plotHeight * 0.25}" />
        <line x1="${plot.left}" y1="${plot.top + plotHeight * 0.5}" x2="${plot.left + plotWidth}" y2="${plot.top + plotHeight * 0.5}" />
        <line x1="${plot.left}" y1="${plot.top + plotHeight * 0.75}" x2="${plot.left + plotWidth}" y2="${plot.top + plotHeight * 0.75}" />
      </g>
      <path d="${path}" fill="none" stroke="${options.color ?? "#2f6fed"}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      ${pts.map(point => `<circle cx="${point.x}" cy="${point.y}" r="5" fill="${options.color ?? "#2f6fed"}" />`).join("")}
      ${pts.map((point, index) => {
        const shouldShow = data.length <= 8 || index % 2 === 0 || index === data.length - 1;
        return shouldShow ? `<text x="${point.x}" y="222" text-anchor="middle" fill="#687387" font-size="12">${point.label.slice(5)}</text>` : "";
      }).join("")}
      <g>
        <rect x="${labelX - 8}" y="${labelY - 16}" width="${labelWidth}" height="22" rx="6" fill="#ffffff" stroke="#dfe5ef" />
        <text x="${labelX}" y="${labelY}" fill="${options.color ?? "#2f6fed"}" font-size="14" font-weight="800">${valueText}</text>
      </g>
    </svg>
  `;
}

function renderSparkline(data) {
  renderLineChart("#sparkline", data, "score", { color: "#e66f2d", label: "risk sparkline" });
}

function initTabs() {
  document.querySelectorAll(".tab-button").forEach(button => {
    button.addEventListener("click", () => {
      const target = button.dataset.tab;
      document.querySelectorAll(".tab-button").forEach(item => {
        item.classList.toggle("is-active", item === button);
      });
      document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("is-active", panel.id === `${target}-panel`);
      });
    });
  });
}

async function render() {
  const data = await loadData();
  const macro = getMacroData(data);
  const latestScore = data.scoreHistory.at(-1).score;
  const meta = getRiskMeta(latestScore);
  const analysis = generateAnalysis(data);
  const macroScore = macro.scoreHistory.at(-1)?.score ?? 30;
  const macroMeta = getMacroRiskMeta(macroScore);
  const macroAnalysis = generateMacroAnalysis(macro);

  document.querySelector("#last-updated").textContent = formatDate(data.updatedAt);
  document.querySelector("#next-update").textContent = getNextScheduledUpdate();
  document.querySelector("#risk-emoji").textContent = meta.emoji;
  document.querySelector("#risk-score").textContent = latestScore;
  document.querySelector("#risk-label").textContent = meta.label;
  document.querySelector("#phase-label").textContent = meta.phase;
  document.querySelector("#status-summary").textContent = analysis.main.split("。").slice(0, 2).join("。") + "。";
  document.querySelector("#analysis-main").textContent = analysis.main;

  renderSignals(data.signals);
  renderSparkline(data.scoreHistory);
  renderLineChart("#risk-chart", data.scoreHistory, "score", { color: "#e66f2d", suffix: "", thresholds: true });
  renderLineChart("#credit-chart", data.creditYoy, "value", { color: "#2f6fed", suffix: "%" });
  renderTable(data.indicators);
  renderList("#risk-up-list", analysis.up);
  renderList("#risk-down-list", analysis.down);
  renderList("#watch-list", analysis.watch);

  document.querySelector("#macro-emoji").textContent = macroMeta.emoji;
  document.querySelector("#macro-score").textContent = macroScore;
  document.querySelector("#macro-label").textContent = macroMeta.label;
  document.querySelector("#macro-phase-label").textContent = macroMeta.phase;
  document.querySelector("#macro-status-summary").textContent = macroAnalysis.main.split("。").slice(0, 2).join("。") + "。";
  document.querySelector("#macro-analysis-main").textContent = macroAnalysis.main;
  renderSignals(macro.signals, "#macro-signal-grid");
  renderLineChart("#macro-sparkline", macro.scoreHistory, "score", { color: "#2f6fed", label: "macro sparkline" });
  renderLineChart("#macro-risk-chart", macro.scoreHistory, "score", { color: "#2f6fed", suffix: "", thresholds: true });
  renderLineChart("#macro-cpi-chart", macro.cpiYoy.length ? macro.cpiYoy : [{ date: "2026-01", value: 0 }], "value", { color: "#e66f2d", suffix: "%" });
  renderTable(macro.indicators, "#macro-indicator-table");
  renderList("#macro-risk-up-list", macroAnalysis.up);
  renderList("#macro-risk-down-list", macroAnalysis.down);
  renderList("#macro-watch-list", macroAnalysis.watch);
}

initTabs();
render();
