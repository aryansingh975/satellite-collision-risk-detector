# Checklist — Spec S7.3: Satellite Entities

## Phase 1: Setup & Dependencies
- [x] Verify S7.1 (`initViewer`) is `done` and its Vitest suite passes
- [x] Verify S7.2 (`fetchSatellites`) is `done` and its Vitest suite passes
- [x] Confirm `frontend/src/cesiumView.js` exists (from S7.1)
- [x] Confirm `frontend/src/api.js` exists (from S7.2)
- [x] No new npm dependencies needed (Cesium + Vitest already declared)

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/cesiumView.test.js`
- [x] Add Cesium mock: `vi.mock('cesium', ...)` stub for Color, Cartesian3, Entity, PointGraphics, LabelGraphics, Viewer, ScreenSpaceEventHandler, ScreenSpaceEventType
- [x] Add `fetchSatellites` mock via `vi.mock('../api.js', ...)`
- [x] Write failing test: `test_regime_colour_known` — LEO/MEO/GEO/HEO each return expected Color
- [x] Write failing test: `test_regime_colour_unknown` — unknown regime → WHITE
- [x] Write failing test: `test_build_entity_id` — entity id is `"sat-25544"`
- [x] Write failing test: `test_build_entity_position` — position from degrees/alt
- [x] Write failing test: `test_build_entity_point_colour` — point color matches regime
- [x] Write failing test: `test_build_entity_label_hidden` — label.show is false
- [x] Write failing test: `test_load_entities_adds_to_viewer` — two entities added for two-sat fixture
- [x] Write failing test: `test_load_entities_clears_previous` — second call replaces, not appends
- [x] Write failing test: `test_load_entities_empty` — empty array, no throw
- [x] Write failing test: `test_load_entities_api_error` — rejection caught, no throw
- [x] Write failing test: `test_hover_shows_label` — MOUSE_MOVE over entity shows label
- [x] Write failing test: `test_hover_hides_label_on_leave` — MOUSE_MOVE to empty space hides label
- [x] Run tests — expect failures (Red): `npm --prefix frontend run test`

## Phase 3: Implementation
- [x] Export `regimeColour(regime)` from `cesiumView.js` — fixed colour map + WHITE fallback
- [x] Export `buildSatelliteEntity(sat)` — creates `Cesium.Entity` with id, position, point, label, properties
- [x] Export `loadSatelliteEntities(viewer)` — fetches, clears old sat entities, adds new ones, returns array
- [x] Export `initHoverLabel(viewer)` — attaches MOUSE_MOVE handler; show/hide entity labels on hover
- [x] Run tests — expect pass (Green): `npm --prefix frontend run test`
- [x] Refactor if needed (no behaviour change)

## Phase 4: Integration
- [x] Wire `loadSatelliteEntities` and `initHoverLabel` into `frontend/src/main.js` after `initViewer`
- [x] N/A — manual browser verify deferred to spec verify step; no live backend available in this session
- [x] Run lint: `npm --prefix frontend run lint`
- [x] Run full test suite: `npm --prefix frontend run test`

## Phase 5: Verification
- [x] All five tangible outcomes checked (entity count, colours, label toggle, empty case, unknown regime)
- [x] No hardcoded Cesium ion token
- [x] Positions use `alt_km * 1000` (km → metres for Cesium)
- [x] Geodetic coordinates (`lat_deg`, `lon_deg`, `alt_km`) come from the API response — no propagation in frontend
- [x] Update roadmap.md status: `spec-written` → `done` (after implement + verify pass)
