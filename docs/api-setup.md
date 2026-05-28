# API Setup

## 1. FRED API

1. Create or sign in to a FRED account.
2. Request an API key from the FRED API page.
3. Keep the key private. For local runs, store it as an environment variable named `FRED_API_KEY`.
4. For GitHub Actions, add it as a repository secret named `FRED_API_KEY`.

Local setup:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
FRED_API_KEY=your_actual_key
```

Run the fetcher:

```bash
python3 scripts/fetch_fred.py
```

Initial FRED series candidates:

| Series | Purpose |
|---|---|
| `LNFACBM027SBOG` | Loans to nondepository financial institutions |
| `BAMLH0A0HYM2` | High yield credit spread |
| `STLFSI4` | Financial stress |
| `VIXCLS` | Equity volatility |
| `DGS10` | 10-year Treasury yield |
| `DGS2` | 2-year Treasury yield |

## 2. SEC Data

NVIDIA demand data and Big Tech Capex use public SEC endpoints. No API key is required.

```bash
python3 scripts/fetch_nvidia.py
python3 scripts/fetch_big_tech_capex.py
```

If SEC rate limits requests in the future, set `SEC_USER_AGENT` to a contactable identifier such as `AI-Credit-Risk-Monitor/1.0 your-email@example.com`.

## 3. LINE Messaging API

1. Create a LINE Developers account.
2. Create a provider.
3. Create a Messaging API channel.
4. Connect or create a LINE Official Account.
5. Get the channel access token.
6. Add the bot as a friend from your personal LINE account.
7. Obtain your user ID or use a small webhook endpoint later to capture it.
8. Store the token as `LINE_CHANNEL_ACCESS_TOKEN` and your user ID as `LINE_USER_ID`.

LINE Notify is no longer the recommended path, so this project should use the Messaging API.

## 4. Later automation

For personal use, the simplest deployment is:

```text
GitHub Actions daily job
  -> fetch FRED / SEC / Polymarket data
  -> compute score
  -> generate rule-based analysis text
  -> commit data/latest.json
  -> GitHub Pages updates the dashboard
  -> send LINE only when risk changes or new data arrives
```

The dashboard can already consume the resulting `data/latest.json`, so the next implementation step is the data fetch script.
