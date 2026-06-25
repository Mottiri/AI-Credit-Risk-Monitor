# Cloudflare Worker Data Cache

This Worker is a data gateway for the dashboard.

The static site can keep reading `data/latest.json`, `data/hype.json`, and the other JSON files. In production, route those paths through the Worker so the Worker returns cached JSON first and refreshes from the repository source when needed.

## What It Does

- Serves dashboard JSON from KV or the Worker Cache API.
- Refreshes cached data every 15 minutes with a scheduled trigger.
- Falls back to the GitHub raw JSON source when a cache key is missing.
- Supports a manual refresh endpoint.

The Worker does not replace the Python scoring scripts yet. The current source of truth is still the committed `data/*.json` files. This keeps the migration small and makes it easy to move individual feeds, such as HYPE, to direct Worker-side API fetching later.

## Deploy Steps

1. Install and log in to Wrangler:

```bash
npm install -g wrangler
wrangler login
```

2. Create a KV namespace:

```bash
wrangler kv namespace create DASHBOARD_DATA
```

3. Copy the returned namespace id into `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "DASHBOARD_DATA"
id = "your_namespace_id"
```

4. Deploy:

```bash
wrangler deploy
```

5. Configure a Worker route in Cloudflare:

```text
https://your-domain.example/data/*
```

If the site remains under a path such as `/AI-Credit-Risk-Monitor/`, use:

```text
https://your-domain.example/AI-Credit-Risk-Monitor/data/*
```

## Optional Cross-Origin Setup

If the Worker uses a different domain, edit `config.js`:

```js
window.DASHBOARD_DATA_BASE = "https://your-worker.your-subdomain.workers.dev";
```

The site will then request:

```text
https://your-worker.your-subdomain.workers.dev/data/latest.json
https://your-worker.your-subdomain.workers.dev/data/hype.json
https://your-worker.your-subdomain.workers.dev/data/semiconductor-cycle.json
```

## Manual Refresh

Without a token:

```bash
curl "https://your-worker.your-subdomain.workers.dev/admin/refresh"
```

With a token:

```bash
wrangler secret put REFRESH_TOKEN
curl -H "Authorization: Bearer YOUR_TOKEN" "https://your-worker.your-subdomain.workers.dev/admin/refresh"
```

Refresh one dataset:

```bash
curl "https://your-worker.your-subdomain.workers.dev/admin/refresh?dataset=hype"
```

## Endpoints

- `/data/latest.json`
- `/data/hype.json`
- `/data/broadcom.json`
- `/data/nvidia.json`
- `/data/ai-demand.json`
- `/data/polymarket.json`
- `/data/big-tech-capex.json`
- `/data/semiconductor-cycle.json`
- `/api/data/latest`
- `/api/data/hype`
- `/api/data/semiconductor-cycle`
- `/health`
