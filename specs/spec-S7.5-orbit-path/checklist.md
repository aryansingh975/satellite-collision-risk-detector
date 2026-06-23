# Checklist — Spec S7.5: Orbit Path Graphic

## Phase 1: Setup & Dependencies
- [x] Verify S7.4 is `done` (SampledPositionProperty + clock animation must be in place)
- [x] Locate `frontend/src/cesiumView.js` — confirm satellite entities are built with `SampledPositionProperty`
- [x] No new npm packages needed (Cesium's `PathGraphics` is bundled)

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/cesiumView.orbit-path.test.js`
- [x] Write `test_toggleOrbitPath_shows_path` — failing (Red)
- [x] Write `test_toggleOrbitPath_hides_path` — failing (Red)
- [x] Write `test_toggleOrbitPath_null_entity` — failing (Red)
- [x] Write `test_toggleOrbitPath_no_path_property` — failing (Red)
- [x] Write `test_addOrbitPath_attaches_path` — failing (Red)
- [x] Write `test_selectSatellite_shows_only_selected_path` — failing (Red)
- [x] Write `test_deselect_hides_all_paths` — failing (Red)
- [x] Run `npm --prefix frontend run test` — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `addOrbitPath(entity)` — attaches `path` with `leadTime`, `trailTime` (5 400 s default), `width` (2), `material` (white, alpha 0.5), `show = false`
- [x] Implement `toggleOrbitPath(entity, visible)` — sets `entity.path.show`; no-op for null/missing path
- [x] Implement `selectSatellite(entity)` (or extend existing selection handler) — hide all paths, show selected
- [x] Call `addOrbitPath` when each satellite entity is created in the existing entity-building loop
- [x] Wire `selectedEntityChanged` (or existing selection callback) to `selectSatellite` via `initOrbitPathSelection(v)`
- [x] Export `addOrbitPath`, `toggleOrbitPath`, `selectSatellite` for unit tests
- [x] Run `npm --prefix frontend run test` — expect pass (Green)
- [x] Refactor if needed — ensure no Cesium Viewer construction runs in unit-test scope

## Phase 4: Integration
- [x] N/A — manual browser check deferred to /verify-spec; unit tests cover all logic
- [x] Verify toggle control (button or keyboard shortcut) hides/shows the path without removing the entity — covered by unit tests; `initOrbitPathSelection` wires `selectedEntityChanged`
- [x] Run lint: `npm --prefix frontend run lint` — Prettier clean
- [x] Run full frontend test suite: `npm --prefix frontend run test` — 58/58 pass

## Phase 5: Verification
- [x] All 7 unit tests pass
- [x] Outcome 1 confirmed: orbital trail attaches on entity creation; `path.show` flips to `true` on selection
- [x] Outcome 2 confirmed: `toggleOrbitPath(entity, false/true)` hides/shows path; entity stays untouched
- [x] Outcome 3 confirmed: `selectSatellite` hides all paths then shows selected; `selectSatellite(null)` clears all
- [x] Outcome 4 confirmed: `toggleOrbitPath(null, true)` does not throw (test passes)
- [x] Outcome 5 confirmed: Vitest suite is green (58/58)
- [x] No ion token or hardcoded secrets introduced
- [x] Update roadmap.md status: `spec-written` → `done`
