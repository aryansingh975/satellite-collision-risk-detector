# Spec S9.3 — Risk Ranking Table

## Overview
Renders an HTML table inside `#dashboard-panel` showing the top-N riskiest conjunction pairs,
fetched from `GET /stats/risk-ranking`. Rows are already sorted ascending by `miss_km`
server-side (rank 1 = closest approach). Clicking a row selects one satellite of the pair
on the Cesium globe (`viewer.selectedEntity`) and flies to it — wiring both the dashboard and
the globe together. Follows the `viewer`-as-parameter pattern established in S8.3 (`search.js`).

## Dependencies
- **S7.2** — `fetchRiskRanking(limit)` already present in `api.js`
- **S6.5** — `/stats/risk-ranking` backend endpoint

## Target Location
`frontend/src/dashboard.js` (new `initRiskTable` export + `renderRiskTable` pure helper)
`frontend/index.html` — add `<table id="riskTable">` inside `#dashboard-panel`

---

## Functional Requirements

### FR-1: Fetch and render the risk ranking table
- **What**: `initRiskTable(viewer, limit = 10)` fetches `fetchRiskRanking(limit)` and calls
  `renderRiskTable(items, viewer, tableEl)` to populate the `<table id="riskTable">` element.
- **Inputs**: `viewer` — Cesium Viewer (or compatible stub); `limit` — max rows (default 10).
- **Outputs**: Populates the table with one `<tr>` per `RiskRankingItem`. Columns (in order):
  Rank · Satellite A · Satellite B · Miss Distance (km) · Rel. Velocity (km/s) · TCA (UTC).
  Miss distance shown to 3 decimal places; rel. velocity to 2 decimal places; TCA as ISO-8601
  date-time string (first 19 chars, space-separated, e.g. `2026-06-23 14:32:01`).
- **Edge cases**: `miss_km` is already ≤ 5 km (server-side filter); TCA is an ISO-8601 string.

### FR-2: Row click → select satellite A on globe
- **What**: Each `<tr>` gets a click listener that calls `selectAndFly(entityA, viewer)` where
  `entityA = viewer.entities.getById("sat-{sat_a}")`. If the entity is not found (satellite not
  loaded in viewer), the click is silently ignored (no error thrown).
- **Inputs**: `viewer.entities.getById("sat-{item.sat_a}")`.
- **Outputs**: Sets `viewer.selectedEntity` and calls `viewer.flyTo(entityA)`.
- **Edge cases**: Entity not found → skip silently; `viewer` is null/undefined → skip silently.

### FR-3: Empty response → "No risk events" message
- **What**: When `fetchRiskRanking` returns `[]`, `renderRiskTable` inserts a single `<tr>` with
  a `<td colspan="6">No risk events detected</td>` message instead of data rows.
- **Inputs**: Empty array.
- **Outputs**: Table body has exactly one row containing the no-data message.

### FR-4: Missing `<table id="riskTable">` → throw descriptive error
- **What**: `initRiskTable` checks for the table element before fetching. If absent, throws
  `Error("#riskTable element not found in DOM")`.
- **Inputs**: DOM without `#riskTable`.
- **Outputs**: Throws; no network call is made.

### FR-5: `renderRiskTable` is a pure DOM helper (testable without network)
- **What**: Extract `renderRiskTable(items, viewer, tableEl)` as an exported pure function that
  accepts an array of `RiskRankingItem`-shaped objects and a real or stub `tableEl`. This keeps
  tests fast (no `fetchRiskRanking` mock needed for rendering logic).
- **Inputs**: `items` array, `viewer` stub, `tableEl` DOM element.
- **Outputs**: Mutates `tableEl.innerHTML` / `<tbody>`.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `initRiskTable(viewer)` resolves without error when `#riskTable` is present
  and the API returns valid data.
- [ ] **Outcome 2**: `renderRiskTable` produces the correct number of `<tr>` rows for a
  non-empty fixture, with miss_km formatted to 3 decimal places.
- [ ] **Outcome 3**: `renderRiskTable([])` produces a single row containing "No risk events".
- [ ] **Outcome 4**: `initRiskTable` throws when `#riskTable` is absent from the DOM.
- [ ] **Outcome 5**: Clicking a rendered row calls `viewer.entities.getById("sat-{sat_a}")` and
  triggers `viewer.flyTo` (verified via spy).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_renderRiskTable_row_count**: `renderRiskTable` with 3 items → 3 `<tr>` rows in tbody.
2. **test_renderRiskTable_miss_km_format**: miss_km `1.23456` → cell text `"1.235"` (3 d.p.).
3. **test_renderRiskTable_rel_vel_format**: rel_vel_kms `7.123` → cell text `"7.12"` (2 d.p.).
4. **test_renderRiskTable_tca_format**: TCA `"2026-06-23T14:32:01.000Z"` → cell contains
   `"2026-06-23 14:32:01"`.
5. **test_renderRiskTable_empty**: `renderRiskTable([])` → single row, text includes
   "No risk events".
6. **test_renderRiskTable_row_click_selects**: click on a row → `viewer.entities.getById` called
   with `"sat-{sat_a}"`; `viewer.flyTo` called with returned entity.
7. **test_renderRiskTable_entity_not_found**: `getById` returns `null` → no error thrown.
8. **test_initRiskTable_missing_table**: no `#riskTable` in DOM → `initRiskTable` throws
   containing `"#riskTable"`.
9. **test_initRiskTable_calls_fetch**: `#riskTable` present → `fetchRiskRanking` called once
   with default limit 10.

### Mocking Strategy
- Mock `../api.js` via `vi.mock` — expose `mockFetchRiskRanking` spy (follow the pattern already
  used in `dashboard.test.js` for `mockFetchOrbitalRegions`).
- `viewer` stub: plain object `{ entities: { getById: vi.fn() }, flyTo: vi.fn(), selectedEntity: undefined }`.
- `tableEl`: real jsdom `<table>` created in `beforeEach` via `document.createElement("table")`.
  No canvas or Chart.js stub needed for S9.3 tests.
- `selectAndFly` is re-exported from `search.js` — no separate mock needed; test through the
  click handler's observable effect on the `viewer` stub.

### Coverage Expectation
- All five FRs have at least one test; edge cases (entity not found, empty response, missing DOM)
  are covered.

---

## References
- `roadmap.md` S9.3 row — Feature, Notes, Depends On
- `CLAUDE.md` — project rules, frame conventions, test patterns
- `frontend/src/api.js:83` — `fetchRiskRanking(limit)`
- `frontend/src/search.js:41` — `selectAndFly(entity, viewer)` reuse pattern
- `backend/app/models/schemas.py:130` — `RiskRankingItem` shape
- `frontend/src/__tests__/dashboard.test.js` — existing vi.mock pattern to extend
