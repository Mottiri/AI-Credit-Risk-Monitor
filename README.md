# AI Credit Risk Monitor

Personal dashboard for monitoring AI bubble risk through credit, market stress, AI demand, rates, liquidity, and prediction-market indicators.

The site works today with `data/latest.json`. The automated data job refreshes FRED, Polymarket, SEC NVIDIA demand data, and SEC Big Tech Capex data, then merges them into the dashboard data file.

## Run locally

```bash
python3 -m http.server 4173
```

Open `http://localhost:4173`.

## Fetch real FRED data

Copy the example env file and paste your FRED key locally:

```bash
cp .env.example .env
```

Edit `.env`:

```text
FRED_API_KEY=your_actual_key
```

Then run:

```bash
python3 scripts/fetch_fred.py
```

This overwrites `data/latest.json` with fresh FRED data for the dashboard.

## Fetch AI demand data

AI Demand combines automatically fetched NVIDIA demand data with automatically fetched Big Tech Capex data from the SEC APIs.

NVIDIA data uses SEC Companyfacts for total revenue and gross profit, plus NVIDIA's latest SEC filing text for Data Center revenue growth:

```bash
python3 scripts/fetch_nvidia.py
```

This writes `data/nvidia.json`. The older `data/ai-demand.json` file remains as a fallback, but the automated NVIDIA feed is preferred when available.

## Fetch Big Tech Capex

Big Tech Capex uses the SEC Companyfacts API and does not require an API key:

```bash
python3 scripts/fetch_big_tech_capex.py
```

This writes `data/big-tech-capex.json` for Microsoft, Alphabet, Meta, and Amazon. The values are treated as an AI infrastructure investment proxy.

## Fetch Polymarket odds

Polymarket prediction-market data does not require an API key for this read-only use case:

```bash
python3 scripts/fetch_polymarket.py
```

This writes `data/polymarket.json`. `scripts/merge_external_data.py` then merges NVIDIA, Big Tech Capex, and Polymarket data into `data/latest.json` so GitHub Pages can render the full dashboard from the main data file. The prediction-market signal has only a small weight in the total score and is mainly used to detect fast changes in market psychology.

## Automate data updates

GitHub Actions automation is included:

```text
.github/workflows/update-fred-data.yml
```

Add `FRED_API_KEY` as a GitHub Actions repository secret, then run the workflow manually once from the Actions tab. It fetches FRED, Polymarket, SEC NVIDIA data, and SEC Big Tech Capex data. It is scheduled for weekdays at `22:15 UTC`, or `07:15 Japan time` the next morning.

For local updates:

```bash
sh scripts/update_data.sh
```

See `docs/automation.md` for details.

## Data flow

```text
FRED / Fed / Treasury / SEC / Polymarket APIs
  -> data fetch script
  -> scoring and analysis generation
  -> data/latest.json
  -> static dashboard
  -> LINE notification, optional
```

## API keys you will need

- FRED API key for economic indicators.
- LINE Developers Messaging API channel token, later, for push notifications.
- No SEC API key is needed for NVIDIA or Big Tech Capex.
- No Polymarket key is needed for the current read-only prediction-market odds.
- Optional market data API if we add stock prices beyond public/free endpoints.

See `docs/api-setup.md` for setup steps.
