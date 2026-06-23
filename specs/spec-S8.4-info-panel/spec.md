# Spec S8.4 — Info Panel

## Overview
When the user selects a satellite on the Cesium globe, an info panel slides in showing that
satellite's full orbital details (regime, semi-major axis, eccentricity, inclination, period)
and a list of any conjunction events it is involved in (partner name, TCA, miss distance,
relative velocity). Deselecting a satellite hides the panel. The panel is built in
`frontend/src/infoPanel.js` and wired into `cesiumView.js` via `viewer.selectedEntityChanged`.

## Dependencies
- S7.3 — Satellite entities (entities rendered on globe, `entity.properties.catalog_no` set)
- S6.1 — Satellites list + detail endpoint (`GET /satellites/{id}` → `SatelliteDetail`)

## Target Location
`frontend/src/infoPanel.js` (new file); `frontend/index.html` (new `#info-panel` div);
`frontend/src/main.js` (call `initInfoPanel` after globe + entities are ready)

---

## Functional Requirements

### FR-1: Show / hide on selection change
- **What**: Listen to `viewer.selectedEntityChanged`; when an entity with a `catalog_no`
  property is selected, show `#info-panel`; when the selection is cleared or the entity has
  no `catalog_no`, hide it (or show an empty-state placeholder).
- **Inputs**: `viewer` (Cesium Viewer), `fetchSatelliteFn`, `fetchConjunctionsFn` (injected
  for testability — defaults to `api.js` wrappers in production)
- **Outputs**: `#info-panel` CSS visibility toggled; panel content populated
- **Edge cases**: entity selected with no `catalog_no` → hide panel; `fetchSatellite` returns
  null (404) → show "Satellite not found" message; rapid re-selection (debounce not required,
  but stale responses must not overwrite a newer selection)

### FR-2: Display orbital details
- **What**: Populate the panel with the `SatelliteDetail` fields for the selected satellite.
  Fields to show: Name, NORAD ID (`catalog_no`), International Designator, Epoch (UTC),
  Regime, Semi-major axis (`a_km` km, 2 dp), Eccentricity (`ecc`, 6 dp),
  Inclination (`inc_deg`°, 2 dp), Orbital period (derived: `1440 / mean_motion` min, 2 dp).
- **Inputs**: `SatelliteDetail` JSON object from `GET /satellites/{id}`
- **Outputs**: DOM fields populated; null orbital elements shown as `—`
- **Edge cases**: `a_km`, `ecc`, `inc_deg`, `mean_motion` may all be null → render `—` for
  each; period is only computed when `mean_motion > 0`

### FR-3: List conjunctions involving the selected satellite
- **What**: Fetch all conjunctions and filter to those where `sat_a === catalogNo` or
  `sat_b === catalogNo`. Display each row: partner satellite name, TCA (ISO string, date
  portion is enough), miss distance (`miss_km` km, 3 dp), relative velocity
  (`rel_vel_kms` km/s, 3 dp). Sort ascending by `miss_km`.
- **Inputs**: `catalogNo` (int), conjunction list from `fetchConjunctions()`
- **Outputs**: `#info-conjunctions` list populated; if no matches, show "No conjunctions
  detected."
- **Edge cases**: empty conjunction array → "No conjunctions detected"; partner name derived
  from `sat_a_name` / `sat_b_name` depending on which side the selected satellite is on

### FR-4: Close / deselect button
- **What**: `#info-close` button inside the panel sets `viewer.selectedEntity = undefined`,
  which triggers FR-1 to hide the panel.
- **Inputs**: click event on `#info-close`
- **Outputs**: panel hidden; `viewer.selectedEntity` cleared

---

## Tangible Outcomes

- [ ] **Outcome 1**: Selecting a satellite entity on the globe shows `#info-panel` populated
  with name, NORAD ID, regime, a_km, ecc, inc_deg, and derived period.
- [ ] **Outcome 2**: The conjunction list shows only events involving the selected satellite,
  sorted by miss_km ascending.
- [ ] **Outcome 3**: Null orbital element fields (`a_km`, `ecc`, `inc_deg`, `mean_motion`)
  render as `—` instead of `null` or blank.
- [ ] **Outcome 4**: Deselecting (or clicking `#info-close`) hides `#info-panel`.
- [ ] **Outcome 5**: Selecting an entity whose `fetchSatellite` returns null shows "Satellite
  not found" and does not throw.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_show_hide_panel**: `initInfoPanel` with a mock viewer — emitting
   `selectedEntityChanged` with an entity that has `catalog_no` calls `fetchSatelliteFn`;
   removing selection hides the panel.
2. **test_populate_orbital_details**: given a full `SatelliteDetail` fixture, the rendered
   HTML contains the correct name, regime, formatted `a_km`, `ecc`, `inc_deg`, and computed
   period.
3. **test_null_elements_render_dash**: a `SatelliteDetail` with `a_km=null`, `ecc=null`,
   `inc_deg=null`, `mean_motion=null` renders `—` for all four fields.
4. **test_period_calculation**: `mean_motion=15.09` → period = `(1440 / 15.09).toFixed(2)` =
   `"95.43"` min — assert the panel contains that string.
5. **test_filters_conjunctions_by_catalog_no**: three conjunction fixtures (two involving
   sat 25544, one not) → only the two appear in the conjunction list.
6. **test_conjunction_partner_name**: when `sat_a === catalogNo`, partner name = `sat_b_name`;
   when `sat_b === catalogNo`, partner name = `sat_a_name`.
7. **test_no_conjunctions_message**: empty conjunction array → panel contains "No conjunctions
   detected."
8. **test_close_button_clears_selection**: clicking `#info-close` sets
   `viewer.selectedEntity = undefined`.
9. **test_satellite_not_found**: `fetchSatelliteFn` resolves to `null` → panel shows
   "Satellite not found" without throwing.

### Mocking Strategy
- Inject `fetchSatelliteFn` and `fetchConjunctionsFn` as arguments (not module-level imports)
  so tests can pass stubs directly — no module mocking needed.
- Mock `viewer` as a plain object with `selectedEntity`, a `flyTo` stub, and a fake
  `selectedEntityChanged` event bus (a simple callback array or EventEmitter shim).
- DOM: use jsdom (Vitest default) with a minimal HTML fixture containing `#info-panel`,
  `#info-close`, `#info-name`, `#info-catalog-no`, `#info-regime`, `#info-a-km`,
  `#info-ecc`, `#info-inc-deg`, `#info-period`, `#info-conjunctions`.

### Coverage Expectation
- All exported functions have at least one test; all nine tests above pass in red→green TDD order.

---

## References
- `roadmap.md` row S8.4; `CLAUDE.md` (project rules, orbital period formula `1440/n` min)
- `backend/app/models/schemas.py` — `SatelliteDetail`, `ConjunctionOut` field names
- `frontend/src/api.js` — `fetchSatellite`, `fetchConjunctions` signatures
- `frontend/src/search.js` — pattern for `entity.properties.catalog_no` access
