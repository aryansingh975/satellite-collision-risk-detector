// API client layer — S7.2 / S10.2
// Base URL defaults to the live FastAPI backend. Override via VITE_API_BASE_URL in frontend/.env.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Build a query string from a params object, omitting null/undefined values.
function buildUrl(base, params) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      qs.set(key, String(value));
    }
  }
  const query = qs.toString();
  return query ? `${base}?${query}` : base;
}

// Shared fetch helper.
// on404: value to return when the server responds 404 (null for detail endpoints, [] for lists).
// Network failures propagate as-is; non-404 error status throws Error("API error {status}: {url}").
async function apiFetch(url, on404 = null) {
  const res = await fetch(url);
  if (res.status === 404) return on404;
  if (!res.ok) throw new Error(`API error ${res.status}: ${url}`);
  return res.json();
}

// GET /health → { status: "ok" }
export async function fetchHealth() {
  return apiFetch(`${BASE_URL}/health`, null);
}

// GET /satellites — returns SatelliteOut[]; empty array when no results.
export async function fetchSatellites(opts = {}) {
  const params = {};
  if (opts.group != null) params.group = opts.group;
  if (opts.regime != null) params.regime = opts.regime;
  if (opts.skip != null) params.skip = opts.skip;
  if (opts.limit != null) params.limit = opts.limit;
  return apiFetch(buildUrl(`${BASE_URL}/satellites`, params), []);
}

// GET /satellites/{catalog_no} → SatelliteDetail, or null on 404.
export async function fetchSatellite(catalogNo) {
  return apiFetch(`${BASE_URL}/satellites/${catalogNo}`, null);
}

// GET /satellites/{catalog_no}/positions → PositionsResponse, or null on 404.
export async function fetchPositions(catalogNo, start, stop, step = 60) {
  const params = { start, stop, step };
  return apiFetch(
    buildUrl(`${BASE_URL}/satellites/${catalogNo}/positions`, params),
    null,
  );
}

// GET /positions → BulkPositionsResponse; batches in chunks of 500 (backend limit).
export async function fetchBulkPositions(catalogNos, start, stop, step = 60) {
  const CHUNK = 500;
  const allSatellites = [];
  for (let i = 0; i < catalogNos.length; i += CHUNK) {
    const chunk = catalogNos.slice(i, i + CHUNK);
    const params = { ids: chunk.join(","), start, stop, step };
    const res = await apiFetch(buildUrl(`${BASE_URL}/satellites/positions`, params), null);
    if (res?.satellites) allSatellites.push(...res.satellites);
  }
  return { satellites: allSatellites };
}

// GET /conjunctions → ConjunctionOut[]; empty array when no results.
export async function fetchConjunctions(opts = {}) {
  const params = {};
  if (opts.threshold != null) params.threshold = opts.threshold;
  if (opts.window != null) params.window = opts.window;
  return apiFetch(buildUrl(`${BASE_URL}/conjunctions`, params), []);
}

// GET /conjunctions/{id} → ConjunctionOut, or null on 404.
export async function fetchConjunction(id) {
  return apiFetch(`${BASE_URL}/conjunctions/${id}`, null);
}

// GET /stats/orbital-regions → OrbitalRegionStats.
export async function fetchOrbitalRegions() {
  return apiFetch(`${BASE_URL}/stats/orbital-regions`, null);
}

// GET /stats/risk-ranking → RiskRankingItem[], sorted ascending by miss_km.
export async function fetchRiskRanking(limit = 10) {
  return apiFetch(buildUrl(`${BASE_URL}/stats/risk-ranking`, { limit }), []);
}
