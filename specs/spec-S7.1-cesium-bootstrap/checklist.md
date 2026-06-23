# Checklist — Spec S7.1: Cesium Globe Bootstrap

## Phase 1: Setup & Dependencies
- [x] Verify S1.6 is `done` (frontend scaffold: `index.html`, `main.js`, Vite, Vitest configured)
- [x] Confirm `cesium` npm package is installed (`frontend/package.json`)
- [x] Confirm Vitest + jsdom are available for unit tests
- [x] Create `frontend/src/cesiumView.js` (new file)

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/cesiumView.test.js`
- [x] Add `vi.mock("cesium", ...)` stub for `Viewer`, `TileMapServiceImageryProvider`, `buildModuleUrl`
- [x] Write failing test: `test_initViewer_returns_viewer`
- [x] Write failing test: `test_initViewer_disables_baseLayerPicker`
- [x] Write failing test: `test_initViewer_disables_geocoder`
- [x] Write failing test: `test_initViewer_uses_NaturalEarth_imagery`
- [x] Write failing test: `test_initViewer_exports_singleton`
- [x] Write failing test: `test_initViewer_no_ion_token`
- [x] Run `npm --prefix frontend run test` — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `frontend/src/cesiumView.js`:
  - `let viewer = null` module singleton
  - `export function initViewer(containerId)` — construct `TileMapServiceImageryProvider` with `NaturalEarthII`
  - Pass `baseLayerPicker: false`, `geocoder: false` (and other disabled widgets) to `Viewer` constructor
  - Assign return value to `viewer` singleton; destroy previous if re-init
  - Export `viewer` reference
- [x] Update `frontend/src/main.js`:
  - Import `initViewer` from `./cesiumView.js`
  - Call `initCesiumBaseUrl()` then `initViewer("cesiumContainer")` (via DOMContentLoaded listener)
- [x] Run `npm --prefix frontend run test` — expect pass (Green)
- [x] Refactor if needed (extract options constant, improve readability)

## Phase 4: Integration
- [x] Run `make serve-frontend` (or `npm --prefix frontend run dev`) and verify globe renders offline
- [x] Confirm no browser console errors about missing ion token
- [x] Confirm `baseLayerPicker` and `geocoder` widgets are absent from the DOM
- [x] Run `npm --prefix frontend run lint` (Prettier)
- [x] Run full frontend test suite — all tests green

## Phase 5: Verification
- [x] All 5 tangible outcomes checked (viewer returned, options confirmed, NaturalEarthII, singleton non-null, main.js wired)
- [x] No Cesium ion token hardcoded anywhere in `cesiumView.js` or `main.js`
- [x] `Cesium.Ion.defaultAccessToken` is NOT set in these files
- [x] `cesiumView.js` does not add its own `DOMContentLoaded` listener
- [x] Update `roadmap.md` status: `spec-written` → `done` for S7.1 in **both** the Phase 7 table and the Master Spec Index
