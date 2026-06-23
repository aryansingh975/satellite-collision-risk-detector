# Spec S10.3 — End-to-end Test

## Overview
Playwright end-to-end tests that exercise the fully integrated system: a seeded FastAPI backend
serving live SQLite data, and the Vite frontend connected to it. The suite covers two layers —
API smoke tests (all endpoints return correct shapes) and browser tests (satellites render on the
Cesium globe, a conjunction polyline appears for at-risk pairs, and the Chart.js dashboard
counts match the API responses). Backend and frontend are started via Playwright's `webServer`
config before the tests run.

## Dependencies
- S10.2 — Frontend live wiring (api.js points at live backend, CORS verified)
- S9.4 — Dashboard refresh wiring (all chart panels functional)

## Target Location
`tests/e2e/` (Playwright), `playwright.config.js` (project root)

---

## Functional Requirements

### FR-1: Playwright project scaffold
- **What**: `@playwright/test` installed as a dev dependency; `playwright.config.js` at the
  project root configures `baseURL`, two `webServer` entries (backend on 8000, frontend on
  5173), and a reasonable `timeout` (30 s for API tests, 60 s for browser tests).
- **Inputs**: `package.json` (root or frontend), `playwright.config.js`
- **Outputs**: `npx playwright test` discovers and runs all specs under `tests/e2e/`
- **Edge cases**: `webServer` must wait until the server is accepting connections before
  starting tests; use `reuseExistingServer: true` so local dev servers aren't killed

### FR-2: API smoke — all endpoints respond with correct shapes
- **What**: Using Playwright's `request` context (no browser), verify every REST endpoint:
  - `GET /health` → 200, `{ status: "ok" }`
  - `GET /satellites` → 200, array (empty if unseeded, no 5xx)
  - `GET /satellites/{id}` → 200 or 404, never 5xx
  - `GET /satellites/{id}/positions` → 200 or 404, never 5xx
  - `GET /positions` → 200, array
  - `GET /conjunctions` → 200, array
  - `GET /stats/orbital-regions` → 200, object with keys `leo`, `meo`, `geo`, `heo`, `total`
  - `GET /stats/risk-ranking` → 200, array
- **Inputs**: Running backend on `http://localhost:8000`
- **Outputs**: All assertions pass; no endpoint returns 4xx (except 404 on unknown IDs) or 5xx
- **Edge cases**: Empty DB → list endpoints return `[]`, not errors; unknown catalog_no → 404

### FR-3: Frontend loads with Cesium container
- **What**: Navigating to `http://localhost:5173` results in a page where the `#cesiumContainer`
  element exists in the DOM and is non-empty (Cesium has rendered a canvas).
- **Inputs**: Running frontend on `http://localhost:5173`, any backend state
- **Outputs**: `#cesiumContainer canvas` selector is visible within timeout
- **Edge cases**: Page must load without JS errors that prevent rendering

### FR-4: Satellites render from live data (requires seeded DB)
- **What**: After `make seed`, the globe shows at least one satellite entity. Verified by
  checking that `window.__cesiumEntities` (a test-exposed handle) or the entity count is > 0,
  OR by asserting that the satellite list API returns data and the DOM shows at least one label.
- **Inputs**: Seeded SQLite DB (`satellite_tracking.db` populated by `make seed`)
- **Outputs**: At least one satellite entity visible on globe; dashboard regime total > 0
- **Edge cases**: If seed has not been run, test should skip or report the unseeded condition
  rather than fail with an obscure error

### FR-5: Dashboard counts match API (requires seeded DB)
- **What**: The dashboard regime chart's displayed total matches `total` from
  `/stats/orbital-regions`. The risk-ranking table row count matches the length of
  `/stats/risk-ranking`.
- **Inputs**: Seeded DB; page fully loaded with Chart.js panels rendered
- **Outputs**: DOM total text (or aria-label) equals API total; table rows equal API array length
- **Edge cases**: Empty DB → both should show 0, not crash

### FR-6: Conjunction risk polyline visible (requires seeded DB with conjunctions)
- **What**: If `/conjunctions` returns at least one entry with `miss_km ≤ 5`, a Polyline entity
  (risk link) is visible on the globe. This can be verified by checking that the
  `#cesiumContainer` contains a red-coloured element, or by inspecting the JS entity collection.
- **Inputs**: Seeded DB with at least one conjunction within threshold
- **Outputs**: Risk polyline rendered; `fetchConjunctions()` count > 0 visible in DOM
- **Edge cases**: Zero conjunctions → no polyline expected; test should assert the count shown
  in the approach chart is 0, not throw

---

## Tangible Outcomes

- [ ] **Outcome 1**: `npx playwright test tests/e2e/` exits 0 (all tests pass) against a seeded backend
- [ ] **Outcome 2**: `GET /health` smoke test returns `{status:"ok"}` in < 1 s
- [ ] **Outcome 3**: All 8 endpoint smoke tests pass (correct status codes, correct schema shapes)
- [ ] **Outcome 4**: `#cesiumContainer canvas` is visible in the browser after page load
- [ ] **Outcome 5**: Dashboard regime `total` in DOM matches `/stats/orbital-regions` JSON `total`
- [ ] **Outcome 6**: `playwright.config.js` exists at project root with `webServer` wiring both servers

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

**File: `tests/e2e/smoke.spec.js`** (API-only, no browser)
1. **test_health_ok**: `GET /health` → `{ status: "ok" }`
2. **test_satellites_returns_array**: `GET /satellites` → 200, result is array
3. **test_positions_no_5xx**: `GET /positions?catalog_nos=25544&start=...&stop=...` → 200 or 404
4. **test_conjunctions_returns_array**: `GET /conjunctions` → 200, result is array
5. **test_orbital_regions_schema**: `GET /stats/orbital-regions` → 200, has `leo`,`meo`,`geo`,`heo`,`total` keys
6. **test_risk_ranking_returns_array**: `GET /stats/risk-ranking` → 200, result is array
7. **test_unknown_satellite_404**: `GET /satellites/9999999` → 404

**File: `tests/e2e/browser.spec.js`** (browser, requires seeded DB)
8. **test_cesium_container_visible**: navigate to `/`, `#cesiumContainer canvas` present
9. **test_dashboard_total_matches_api**: fetch orbital-regions API, compare to DOM text
10. **test_conjunction_count_matches_api**: fetch conjunctions API, compare count shown in approach chart

### Mocking Strategy
- **No mocking** in e2e tests — the entire point is exercising the live stack
- Backend uses cached CelesTrak data (respect 2h cadence; run `make seed` once before tests)
- Browser tests run against Chromium (Playwright default); WebGL must be enabled for Cesium
- `reuseExistingServer: true` in `playwright.config.js` allows running tests against already-running dev servers

### Coverage Expectation
- Every REST endpoint hit at least once (smoke)
- Browser render verified (canvas present)
- At least one data-driven assertion (dashboard count = API count)

---

## References
- roadmap.md S10.3 row; CLAUDE.md (CelesTrak 2h cadence, no secrets, WGS-72)
- S10.2 spec (live wiring) — CORS and base URL must be correct before these tests run
- S9.4 spec (dashboard refresh) — panels must be mounted for DOM count assertions
- Playwright docs: `webServer`, `request` context, `page.evaluate()`
