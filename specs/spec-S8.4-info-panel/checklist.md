# Checklist — Spec S8.4: Info Panel

## Phase 1: Setup & Dependencies
- [x] Verify S7.3 (satellite entities) is `done` — entities have `catalog_no` property
- [x] Verify S6.1 (`GET /satellites/{id}`) is `done` — returns `SatelliteDetail`
- [x] Create `frontend/src/infoPanel.js` (new file)
- [x] Add `#info-panel` div + child elements to `frontend/index.html`
- [x] No new npm packages needed (jsdom already in Vitest; no extra deps)

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/infoPanel.test.js`
- [x] Write `test_show_hide_panel` — failing (Red)
- [x] Write `test_populate_orbital_details` — failing (Red)
- [x] Write `test_null_elements_render_dash` — failing (Red)
- [x] Write `test_period_calculation` — failing (Red)
- [x] Write `test_filters_conjunctions_by_catalog_no` — failing (Red)
- [x] Write `test_conjunction_partner_name` — failing (Red)
- [x] Write `test_no_conjunctions_message` — failing (Red)
- [x] Write `test_close_button_clears_selection` — failing (Red)
- [x] Write `test_satellite_not_found` — failing (Red)
- [x] Run `npm --prefix frontend run test` — 9 failures confirmed (Red)

## Phase 3: Implementation
- [x] Implement FR-1: `initInfoPanel(viewer, fetchSatelliteFn, fetchConjunctionsFn)` —
  listen to `selectedEntityChanged`, show/hide `#info-panel`
- [x] Implement FR-2: populate orbital detail fields; derive period from `mean_motion`;
  render `—` for null fields
- [x] Implement FR-3: filter conjunctions by `catalog_no`; display partner name + TCA +
  miss_km + rel_vel_kms; sort by miss_km; show "No conjunctions detected." if empty
- [x] Implement FR-4: `#info-close` click → `viewer.selectedEntity = undefined`
- [x] Run `npm --prefix frontend run test` — all 9 pass (Green)
- [x] Refactor display helpers (`fmt`, `computePeriod`, `set`) — no duplication

## Phase 4: Integration
- [x] Add `#info-panel` HTML + CSS to `frontend/index.html` (position: absolute, right side,
  z-index above globe, hidden by default)
- [x] Import and call `initInfoPanel(viewer, fetchSatellite, fetchConjunctions)` in
  `frontend/src/main.js` after globe and entities are initialized
- [x] Run `npm --prefix frontend run lint` (Prettier) — no errors
- [x] Run full frontend test suite `npm --prefix frontend run test` — all 113 pass
- [x] N/A — dev server manual test deferred to verify-spec; logic covered by 9 unit tests

## Phase 5: Verification
- [x] Outcome 1: selecting a satellite shows the panel with orbital details (test_populate_orbital_details)
- [x] Outcome 2: conjunction list shows only events for the selected satellite, sorted by miss_km (test_filters_conjunctions_by_catalog_no)
- [x] Outcome 3: null orbital elements display as `—` (test_null_elements_render_dash)
- [x] Outcome 4: deselect / close button hides the panel (test_show_hide_panel, test_close_button_clears_selection)
- [x] Outcome 5: 404 response from `fetchSatellite` shows "Satellite not found" (test_satellite_not_found)
- [x] No hardcoded secrets or tokens
- [x] `fetchSatelliteFn` and `fetchConjunctionsFn` injected (not hard-imported) in
  `infoPanel.js` — testable without module mocks
- [x] Update `roadmap.md` status: `spec-written` → `done`
