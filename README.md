# AI Credit Risk Monitor

Personal dashboard for monitoring AI bubble risk through credit, market stress, AI demand, rates, liquidity, and prediction-market indicators.

The site works today with `data/latest.json`. Later, an automated data job can replace that file with fresh API results and Codex-generated analysis.

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

## Update AI demand data

AI Demand is currently maintained manually in `data/ai-demand.json` because NVIDIA segment revenue and Big Tech AI Capex are quarterly earnings data rather than clean FRED-style time series.

Update it after quarterly earnings:

```text
data/ai-demand.json
```

The dashboard merges this file with `data/latest.json` automatically.

## Fetch Polymarket odds

Polymarket prediction-market data does not require an API key for this read-only use case:

```bash
python3 scripts/fetch_polymarket.py
```

This writes `data/polymarket.json`, which the dashboard merges with the main data. The prediction-market signal has only a small weight in the total score and is mainly used to detect fast changes in market psychology.

## Automate data updates

GitHub Actions automation is included:

```text
.github/workflows/update-fred-data.yml
```

Add `FRED_API_KEY` as a GitHub Actions repository secret, then run the workflow manually once from the Actions tab. It fetches FRED and Polymarket data. It is scheduled for weekdays at `22:15 UTC`, or `07:15 Japan time` the next morning.

For local updates:

```bash
sh scripts/update_data.sh
```

See `docs/automation.md` for details.

## Data flow

```text
FRED / Fed / Treasury / Polymarket APIs
  -> data fetch script
  -> scoring and analysis generation
  -> data/latest.json
  -> static dashboard
  -> LINE notification, optional
```

## API keys you will need

- FRED API key for economic indicators.
- LINE Developers Messaging API channel token, later, for push notifications.
- No Polymarket key is needed for the current read-only prediction-market odds.
- Optional market data API if we add stock prices beyond public/free endpoints.

See `docs/api-setup.md` for setup steps.
