# Spec S9.1 — Regime Distribution Chart

## Overview
Renders a Chart.js doughnut (or bar) chart that visualises the breakdown of tracked satellites by
orbital regime (LEO / MEO / GEO / HEO). Data is fetched from `GET /stats/orbital-regions`, which
returns an `OrbitalRegionStats` object whose `leo + meo + geo + heo` fields are guaranteed to sum
to `total`. The chart is the first panel of the Insights Dashboard exposed in `frontend/src/dashboard.js`.

## Dependencies
- **S7.2** — API client layer (`fetchOrbitalRegions` already implemented in `api.js`)
- **S6.5** — Stats endpoints (`GET /stats/orbital-regions` live on the backend)

## Target Location
`frontend/src/dashboard.js`

---

## Functional Requirements

### FR-1: Fetch orbital-region stats
- **What**: Call `fetchOrbitalRegions()` from `api.js` to retrieve regime counts; handle a `null` response (backend unavailable / 404) gracefully by displaying an empty / zero-state chart.
- **Inputs**: None (no user-configurable parameters for this chart).
- **Outputs**: A resolved `OrbitalRegionStats` object `{ leo, meo, geo, heo, total }`, or `null`.
- **Edge cases**: `null` response → render chart with all-zero data and a "No data" label overlay; network error propagates but must not crash the page.

### FR-2: Render a Chart.js doughnut chart
- **What**: Create (or update) a Chart.js `"doughnut"` chart on a `<canvas id="regimeChart">` element in `index.html`. Each slice represents one regime.
- **Inputs**: `{ leo, meo, geo, heo }` counts from FR-1.
- **Outputs**: A visible doughnut chart with four labelled slices and a legend.
- **Configuration**:
  - Labels: `["LEO", "MEO", "GEO", "HEO"]` (in that order).
  - Slice colours: LEO `#4fc3f7`, MEO `#aed581`, GEO `#ffb74d`, HEO `#f06292` (or similar — must be distinguishable).
  - Plugin `legend.position: "bottom"`.
  - Plugin `tooltip` shows count + percentage of total.
  - `responsive: true`, `maintainAspectRatio: false` so the canvas fills its container.
- **Edge cases**: All-zero data → chart renders with zero-length arcs; add centre-text or title showing "No data available" if total is 0.

### FR-3: Export an initialisation function
- **What**: Export a named function `initRegimeChart()` from `dashboard.js` that orchestrates FR-1 + FR-2 and returns the Chart instance (or `null` on failure).
- **Inputs**: None (reads the DOM and calls `api.js`).
- **Outputs**: The created `Chart` instance so callers (S9.4 refresh wiring) can call `chart.destroy()` / re-initialise.
- **Edge cases**: Called before the `<canvas>` element exists → throw a descriptive error (not a silent failure); called twice → caller is responsible for destroying the previous instance before re-calling.

### FR-4: Percentage tooltip
- **What**: Each doughnut slice tooltip must display both the raw satellite count and its percentage of the total (rounded to one decimal place).
- **Inputs**: Chart.js tooltip callback receives `context.parsed` (the raw count) and `context.dataset.data` (all counts).
- **Outputs**: Tooltip label string, e.g. `"LEO: 3 421 (72.1%)"`.
- **Edge cases**: Total is 0 → show `"0 (0%)"` rather than `NaN%` or division-by-zero.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `initRegimeChart()` is exported from `dashboard.js` and, when called with a valid canvas in the DOM, returns a Chart.js instance without throwing.
- [ ] **Outcome 2**: The chart renders four slices labelled LEO / MEO / GEO / HEO whose data values equal the counts from `fetchOrbitalRegions()`.
- [ ] **Outcome 3**: When `fetchOrbitalRegions()` returns `null`, `initRegimeChart()` still returns a Chart instance (not `null` / throws) with all-zero data.
- [ ] **Outcome 4**: The tooltip callback for a non-zero total returns a string containing both the count and a `%` character; for total = 0 it does not produce `NaN` or `Infinity`.
- [ ] **Outcome 5**: The canvas element `#regimeChart` exists in `index.html` inside a dashboard container.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_initRegimeChart_returns_chart_instance**: Mock `fetchOrbitalRegions` to return `{ leo:10, meo:2, geo:5, heo:1, total:18 }`. Call `initRegimeChart()`. Assert the return value is a Chart instance (has `.data`, `.destroy` method).

2. **test_initRegimeChart_data_matches_api**: Same mock. Assert `chart.data.datasets[0].data` equals `[10, 2, 5, 1]` in LEO/MEO/GEO/HEO order.

3. **test_initRegimeChart_null_response**: Mock `fetchOrbitalRegions` to return `null`. Assert `initRegimeChart()` resolves without throwing and the dataset data is `[0, 0, 0, 0]`.

4. **test_tooltip_percentage_normal**: Call the tooltip label callback with count=10, dataset data=[10,2,5,1] (total=18). Assert result contains `"10"` and `"55.6%"`.

5. **test_tooltip_percentage_zero_total**: Call the tooltip label callback with count=0, dataset data=[0,0,0,0] (total=0). Assert result does not contain `"NaN"` or `"Infinity"` and contains `"0%"`.

6. **test_initRegimeChart_labels**: Assert `chart.data.labels` equals `["LEO", "MEO", "GEO", "HEO"]`.

7. **test_initRegimeChart_missing_canvas**: Remove the `<canvas id="regimeChart">` from the DOM. Assert `initRegimeChart()` rejects or throws with a descriptive message.

### Mocking Strategy
- Mock `fetch` (or the `api.js` named export `fetchOrbitalRegions`) via Vitest's `vi.mock` / `vi.spyOn` — never hit the live API.
- Provide a minimal `<canvas id="regimeChart">` in the jsdom environment via `document.body.innerHTML` setup in `beforeEach`.
- Mock Chart.js with a lightweight stub (store constructor args) or import the real library — depends on Vitest config; prefer the real library if already installed, stub if it causes jsdom issues.

### Coverage Expectation
- All four FRs covered; both happy path and null/zero-total edge cases tested.

---

## References
- `roadmap.md` row S9.1 (Phase 9, Insights Dashboard)
- `CLAUDE.md` — frontend testing: Vitest + jsdom; mock `fetch`; no live API calls in tests
- `frontend/src/api.js:77-79` — `fetchOrbitalRegions()` implementation
- `backend/app/models/schemas.py:109-127` — `OrbitalRegionStats` schema (total = leo+meo+geo+heo)
- Chart.js docs: `"doughnut"` chart type, tooltip callbacks
