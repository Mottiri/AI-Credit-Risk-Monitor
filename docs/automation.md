# Automation

This project can update FRED-backed indicators and Polymarket odds automatically with GitHub Actions.

## What Is Automated

The workflow in `.github/workflows/update-fred-data.yml` runs `scripts/fetch_fred.py`, `scripts/fetch_polymarket.py`, and `scripts/merge_external_data.py`. It commits fresh `data/latest.json` and `data/polymarket.json` files when values change.

Current automated blocks:

- Credit Expansion
- Market Stress
- Rates
- Liquidity
- Prediction Market

AI Demand is still maintained manually in `data/ai-demand.json` because the cleanest source is quarterly earnings data, not a stable FRED-style time series.

## GitHub Setup

1. Create a GitHub repository and push this project.
2. In the repository, open `Settings` -> `Secrets and variables` -> `Actions`.
3. Add a repository secret:

```text
FRED_API_KEY=your_actual_fred_key
```

4. Open `Actions` and enable workflows if GitHub asks.
5. Run `Update Market Data` manually once with `workflow_dispatch`.

The scheduled run is weekdays at `22:15 UTC`, which is `07:15 Japan time` the next morning.

## Local Run

Keep your local `.env` file:

```text
FRED_API_KEY=your_actual_fred_key
```

Then run:

```bash
sh scripts/update_data.sh
```

## Later

LINE notification can be added after this workflow is stable. The workflow can compare the previous score against the new score, then send a LINE Messaging API push only when the score changes meaningfully or crosses a threshold.
