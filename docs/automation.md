# Automation

This project can update FRED-backed indicators, SEC NVIDIA demand data, SEC Big Tech Capex, and Polymarket odds automatically with GitHub Actions.

## What Is Automated

The workflow in `.github/workflows/update-fred-data.yml` runs `scripts/fetch_fred.py`, `scripts/fetch_polymarket.py`, `scripts/fetch_nvidia.py`, `scripts/fetch_big_tech_capex.py`, and `scripts/merge_external_data.py`. It commits fresh `data/latest.json`, `data/polymarket.json`, `data/nvidia.json`, and `data/big-tech-capex.json` files when values change.

Current automated blocks:

- Credit Expansion
- Market Stress
- Rates
- Liquidity
- AI Demand, automated through NVIDIA and Big Tech Capex
- Prediction Market

The NVIDIA portion of AI Demand is automatically fetched from SEC Companyfacts and NVIDIA's latest SEC filing. Big Tech Capex is automatically fetched from SEC Companyfacts.

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
