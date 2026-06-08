const DATASETS = {
  latest: "data/latest.json",
  hype: "data/hype.json",
  broadcom: "data/broadcom.json",
  nvidia: "data/nvidia.json",
  "ai-demand": "data/ai-demand.json",
  polymarket: "data/polymarket.json",
  "big-tech-capex": "data/big-tech-capex.json"
};

const DEFAULT_SOURCE_BASE = "https://raw.githubusercontent.com/Mottiri/AI-Credit-Risk-Monitor/main";
const CACHE_TTL_SECONDS = 300;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }));
    }

    if (url.pathname === "/health") {
      return jsonResponse({ ok: true, datasets: Object.keys(DATASETS) });
    }

    if (url.pathname === "/admin/refresh") {
      return handleManualRefresh(request, env, ctx, url);
    }

    const dataset = datasetFromPath(url.pathname);
    if (!dataset) {
      return jsonResponse({ error: "Not found" }, 404);
    }

    const cached = await readCache(env, dataset);
    if (cached) {
      return jsonResponse(cached.body, 200, cached.meta);
    }

    const refreshed = await refreshDataset(env, dataset);
    return jsonResponse(refreshed.body, 200, refreshed.meta);
  },

  async scheduled(_event, env, ctx) {
    ctx.waitUntil(refreshAll(env));
  }
};

function datasetFromPath(pathname) {
  const dataMatch = pathname.match(/\/data\/([^/]+)\.json$/);
  if (dataMatch && DATASETS[dataMatch[1]]) return dataMatch[1];

  const apiMatch = pathname.match(/\/api\/data\/([^/]+)$/);
  if (apiMatch && DATASETS[apiMatch[1]]) return apiMatch[1];

  return null;
}

async function handleManualRefresh(request, env, ctx, url) {
  const configuredToken = env.REFRESH_TOKEN;
  if (configuredToken) {
    const providedToken = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "")
      || url.searchParams.get("token");
    if (providedToken !== configuredToken) {
      return jsonResponse({ error: "Unauthorized" }, 401);
    }
  }

  const dataset = url.searchParams.get("dataset");
  if (dataset) {
    if (!DATASETS[dataset]) return jsonResponse({ error: "Unknown dataset" }, 400);
    const refreshed = await refreshDataset(env, dataset);
    return jsonResponse({ ok: true, refreshed: [dataset], meta: refreshed.meta });
  }

  ctx.waitUntil(refreshAll(env));
  return jsonResponse({ ok: true, refreshing: Object.keys(DATASETS) });
}

async function refreshAll(env) {
  await Promise.all(Object.keys(DATASETS).map(dataset => refreshDataset(env, dataset)));
}

async function refreshDataset(env, dataset) {
  const sourceBase = String(env.SOURCE_BASE_URL || DEFAULT_SOURCE_BASE).replace(/\/$/, "");
  const sourceUrl = `${sourceBase}/${DATASETS[dataset]}?ts=${Date.now()}`;
  const response = await fetch(sourceUrl, {
    headers: { "user-agent": "AI-Credit-Risk-Monitor-Worker/1.0" },
    cf: { cacheTtl: CACHE_TTL_SECONDS, cacheEverything: true }
  });

  if (!response.ok) {
    throw new Error(`Failed to refresh ${dataset}: ${response.status}`);
  }

  const body = await response.json();
  const meta = {
    dataset,
    sourceUrl: sourceUrl.replace(/\?ts=.*/, ""),
    cachedAt: new Date().toISOString()
  };

  await writeCache(env, dataset, body, meta);
  return { body, meta };
}

async function readCache(env, dataset) {
  if (env.DASHBOARD_DATA) {
    const value = await env.DASHBOARD_DATA.get(cacheKey(dataset), "json");
    if (value) return value;
  }

  const response = await caches.default.match(cacheRequest(dataset));
  if (!response) return null;
  return response.json();
}

async function writeCache(env, dataset, body, meta) {
  const value = { body, meta };

  if (env.DASHBOARD_DATA) {
    await env.DASHBOARD_DATA.put(cacheKey(dataset), JSON.stringify(value));
  }

  await caches.default.put(
    cacheRequest(dataset),
    new Response(JSON.stringify(value), {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": `public, max-age=${CACHE_TTL_SECONDS}`
      }
    })
  );
}

function cacheKey(dataset) {
  return `dashboard:${dataset}`;
}

function cacheRequest(dataset) {
  return new Request(`https://ai-credit-risk-monitor.local/cache/${dataset}`);
}

function jsonResponse(body, status = 200, meta = {}) {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": `public, max-age=${CACHE_TTL_SECONDS}`,
    "x-dashboard-cache": meta.cachedAt ? "hit" : "miss"
  };
  if (meta.cachedAt) headers["x-dashboard-cached-at"] = meta.cachedAt;
  if (meta.sourceUrl) headers["x-dashboard-source"] = meta.sourceUrl;
  return withCors(new Response(JSON.stringify(body), { status, headers }));
}

function withCors(response) {
  const headers = new Headers(response.headers);
  headers.set("access-control-allow-origin", "*");
  headers.set("access-control-allow-methods", "GET, OPTIONS");
  headers.set("access-control-allow-headers", "authorization, content-type");
  return new Response(response.body, { status: response.status, headers });
}
