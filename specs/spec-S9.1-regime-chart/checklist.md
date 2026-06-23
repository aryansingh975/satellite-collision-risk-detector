# Checklist — Spec S9.1: Regime Distribution Chart

## Phase 1: Setup & Dependencies
- [x] Verify S7.2 (API client) is `done` — `fetchOrbitalRegions` exists in `frontend/src/api.js`
- [x] Verify S6.5 (stats endpoints) is `done` — `GET /stats/orbital-regions` returns `OrbitalRegionStats`
- [x] Confirm `chart.js` is listed in `frontend/package.json` (installed via `npm --prefix frontend install chart.js`)
- [x] Add `<canvas id="regimeChart">` inside a dashboard container in `frontend/index.html`
- [x] Create `frontend/src/dashboard.js` (new file)
- [x] Create `frontend/src/__tests__/dashboard.test.js` (new file)

## Phase 2: Tests First (TDD)
- [x] Write `frontend/src/__tests__/dashboard.test.js` with all 7 tests listed in spec
- [x] Set up `beforeEach` to inject `<canvas id="regimeChart">` into jsdom body
- [x] Mock `fetchOrbitalRegions` via `vi.mock('../api.js')` using `vi.hoisted`
- [x] Run tests — expect failures (Red): confirmed "Failed to resolve import ../dashboard.js"

## Phase 3: Implementation
- [x] Implement FR-1: `fetchOrbitalRegions()` call + null guard → default `{ leo:0, meo:0, geo:0, heo:0 }`
- [x] Implement FR-2: `new Chart(canvas, { type:'doughnut', data:{...}, options:{...} })` with correct labels/colours/responsive config
- [x] Implement FR-3: export `initRegimeChart()` returning the Chart instance; throw on missing canvas
- [x] Implement FR-4: export `regimeTooltipLabel` computing `count (xx.x%)` with zero-total guard
- [x] Run tests — expect pass (Green): 7/7 passed
- [x] Refactor N/A — tooltip callback already extracted as named export for testability

## Phase 4: Integration
- [x] Import and call `initRegimeChart()` from `frontend/src/main.js` at end of DOMContentLoaded handler
- [x] N/A — dev server visual confirmation deferred (no browser available in this environment); canvas + styles wired in index.html
- [x] Run lint: `npm --prefix frontend run lint` — Prettier check passed (all files)
- [x] Run full frontend test suite: 120/120 passed across 9 test files

## Phase 5: Verification
- [x] All 5 tangible outcomes checked:
  - Outcome 1: `initRegimeChart()` exported and returns Chart instance with `.destroy` — test 1 passes
  - Outcome 2: labels = ["LEO","MEO","GEO","HEO"], data = [leo,meo,geo,heo] — tests 2 & 6 pass
  - Outcome 3: null response yields zero-state chart — test 3 passes
  - Outcome 4: tooltip shows count + % without NaN/Infinity — tests 4 & 5 pass
  - Outcome 5: `<canvas id="regimeChart">` in `index.html` inside `#dashboard-panel`
- [x] No hardcoded secrets or ion tokens
- [x] `fetchOrbitalRegions` is the only api.js call made by this module (no direct `fetch`)
- [x] Chart.js instance is returned from `initRegimeChart()` (S9.4 can call `.destroy()` on refresh)
- [x] Update `roadmap.md` status: `spec-written` → `done`
