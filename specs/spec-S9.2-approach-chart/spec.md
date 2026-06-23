# Spec S9.2 — Close-Approach Count Chart

## Overview
Renders a Chart.js bar chart that shows how many detected conjunction events fall into each
miss-distance band within the 0–5 km risk window. Data is fetched from `GET /conjunctions` via
the `fetchConjunctions()` API client. The window is divided into five 1-km-wide bands (`< 1 km`,
`1–2 km`, `2–3 km`, `3–4 km`, `4–5 km`), coloured from red (closest) to yellow (furthest) so the
severity gradient is immediately legible. The chart is the second panel of the Insights Dashboard
in `frontend/src/dashboard.js`.

## Dependencies
- **S7.2** — API client layer (`fetchConjunctions` implemented in `api.js`)
- **S6.4** — Conjunctions endpoint (`GET /conjunctions` live on the backend)

## Target Location
`frontend/src/dashboard.js`

---

## Functional Requirements

### FR-1: Fetch conjunction events
- **What**: Call `fetchConjunctions()` (no extra opts — uses the backend default threshold of 5 km
  and the configured screen window). Handle an empty array (no events) gracefully by rendering an
  all-zero bar chart.
- **Inputs**: None (no user-configurable parameters for this chart at this stage).
- **Outputs**: A `ConjunctionOut[]` array, possibly empty (never `null` — `api.js` returns `[]` on
  404).
- **Edge cases**: Empty array → all five bar values are 0; network error propagates but must not
  crash the page.

### FR-2: Bucket conjunctions by miss-distance band
- **What**: Export a pure helper `bucketizeConjunctions(conjunctions)` that groups a
  `ConjunctionOut[]` array into five 1-km-wide bands and returns an array of five counts
  `[n0, n1, n2, n3, n4]`.
- **Band definitions** (lower-inclusive, upper-exclusive):
  | Band index | Label    | Range            |
  |-----------|----------|-----------------|
  | 0         | `< 1 km` | `0 ≤ miss < 1`  |
  | 1         | `1–2 km` | `1 ≤ miss < 2`  |
  | 2         | `2–3 km` | `2 ≤ miss < 3`  |
  | 3         | `3–4 km` | `3 ≤ miss < 4`  |
  | 4         | `4–5 km` | `4 ≤ miss ≤ 5`  |
- **Inputs**: `ConjunctionOut[]` — each item has a `miss_km: float` field.
- **Outputs**: `number[]` of length 5, non-negative integers, summing to the count of events with
  `miss_km ≤ 5`. Events with `miss_km > 5` are silently dropped (the backend filters by threshold,
  but guard defensively).
- **Edge cases**: Empty input → `[0, 0, 0, 0, 0]`; a value exactly on a boundary (e.g. `miss_km =
  1.0`) falls into the higher band (band 1: `1–2 km`).

### FR-3: Render a Chart.js bar chart
- **What**: Create a Chart.js `"bar"` chart on a `<canvas id="approachChart">` element in
  `index.html`. Each bar represents one miss-distance band.
- **Inputs**: The 5-element count array from FR-2.
- **Outputs**: A visible bar chart with five bars, a legend, and a y-axis labelled "Conjunctions".
- **Configuration**:
  - Labels: `["< 1 km", "1–2 km", "2–3 km", "3–4 km", "4–5 km"]` (in that order).
  - Bar colours (by severity — most critical first):
    - `< 1 km` → `#f44336` (red)
    - `1–2 km` → `#ff7043` (deep orange)
    - `2–3 km` → `#ffa726` (orange)
    - `3–4 km` → `#ffca28` (amber)
    - `4–5 km` → `#d4e157` (lime)
  - `responsive: true`, `maintainAspectRatio: false`.
  - `scales.y.title.display: true`, `scales.y.title.text: "Conjunctions"`.
  - `scales.y.beginAtZero: true`.
  - Plugin tooltip shows band label + count, e.g. `"< 1 km: 3 events"`.
- **Edge cases**: All-zero counts → chart renders with zero-height bars (no empty-state error).

### FR-4: Export `initApproachChart()`
- **What**: Export a named async function `initApproachChart()` from `dashboard.js` that
  orchestrates FR-1 → FR-2 → FR-3 and returns the `Chart` instance.
- **Inputs**: None (reads the DOM and calls `api.js`).
- **Outputs**: The created `Chart` instance so callers (S9.4 refresh wiring) can call
  `chart.destroy()` / re-initialise.
- **Edge cases**: Called before `<canvas id="approachChart">` exists → throw
  `Error("#approachChart canvas element not found in DOM")`; called twice → caller is responsible
  for destroying the previous instance.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `initApproachChart()` is exported from `dashboard.js` and, when called with a
  valid canvas in the DOM, returns a Chart.js instance without throwing.
- [ ] **Outcome 2**: The five bar values equal the counts from `bucketizeConjunctions()` applied to
  the data returned by `fetchConjunctions()`.
- [ ] **Outcome 3**: When `fetchConjunctions()` returns `[]`, all five bars have value 0 (no error
  thrown).
- [ ] **Outcome 4**: `bucketizeConjunctions` correctly sorts a known fixture into the right bands
  (unit-testable without the DOM).
- [ ] **Outcome 5**: Called before the `<canvas id="approachChart">` is in the DOM →
  `initApproachChart()` rejects/throws with `"#approachChart"` in the message.
- [ ] **Outcome 6**: `<canvas id="approachChart">` and a heading exist in `index.html` inside
  `#dashboard-panel`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_initApproachChart_returns_chart_instance**: Mock `fetchConjunctions` to return two
   sample events (`miss_km: 0.5` and `miss_km: 2.3`). Call `initApproachChart()`. Assert the
   return value has `.data` and a `.destroy` method.

2. **test_initApproachChart_bucket_counts**: Mock `fetchConjunctions` to return events with
   `miss_km` values `[0.5, 1.5, 2.5, 3.5, 4.5]` (one per band). Assert
   `chart.data.datasets[0].data` equals `[1, 1, 1, 1, 1]`.

3. **test_initApproachChart_empty_response**: Mock `fetchConjunctions` to return `[]`. Assert
   `initApproachChart()` resolves without throwing and all bar values are `0`.

4. **test_initApproachChart_missing_canvas**: Remove `<canvas id="approachChart">` from the DOM.
   Assert `initApproachChart()` rejects/throws with a message containing `"#approachChart"`.

5. **test_bucketizeConjunctions_bands**: Pass `[{miss_km:0.5}, {miss_km:1.5}, {miss_km:2.5},
   {miss_km:3.5}, {miss_km:4.5}]`. Assert result is `[1,1,1,1,1]`.

6. **test_bucketizeConjunctions_empty**: Pass `[]`. Assert result is `[0,0,0,0,0]`.

7. **test_bucketizeConjunctions_boundary**: Pass `[{miss_km:1.0}, {miss_km:2.0}]`. Assert result
   is `[0,1,1,0,0]` — values on a boundary go into the upper band.

8. **test_bucketizeConjunctions_over_threshold**: Pass `[{miss_km:5.1}]`. Assert result is
   `[0,0,0,0,0]` (out-of-range event silently dropped).

9. **test_initApproachChart_labels**: Mock `fetchConjunctions` with any data. Assert
   `chart.data.labels` equals `["< 1 km", "1–2 km", "2–3 km", "3–4 km", "4–5 km"]`.

### Mocking Strategy
- Mock `fetchConjunctions` via Vitest `vi.mock("../api.js", ...)` — never hit the live API.
- Mock Chart.js with the same lightweight constructor stub used in `dashboard.test.js` for S9.1
  (store constructor args on `this`, expose `.data`, `.destroy`).
- Provide `<canvas id="approachChart">` in jsdom via `document.body.innerHTML` in `beforeEach`.
- `bucketizeConjunctions` is a pure function — test it directly without any DOM setup.

### Coverage Expectation
- All four FRs covered; happy path, empty input, boundary values, and missing-canvas edge case
  tested.

---

## References
- `roadmap.md` row S9.2 (Phase 9, Insights Dashboard)
- `CLAUDE.md` — frontend testing: Vitest + jsdom; mock `fetch`; no live API calls in tests
- `frontend/src/api.js:65-70` — `fetchConjunctions()` implementation (returns `[]` on 404)
- `backend/app/models/schemas.py:89-101` — `ConjunctionOut` schema (`miss_km: float`)
- `specs/spec-S9.1-regime-chart/` — reference for dashboard pattern (Chart stub, mock strategy)
- Chart.js docs: `"bar"` chart type, `scales.y`, per-bar `backgroundColor` array
