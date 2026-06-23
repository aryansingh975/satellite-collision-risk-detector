# Spec S7.1 — Cesium Globe Bootstrap

## Overview
Initialize a fully functional CesiumJS `Viewer` in `frontend/src/cesiumView.js` using **offline Natural Earth
imagery** so the globe renders without any ion token or network dependency. The viewer is configured to disable
UI widgets that are not needed (`baseLayerPicker`, `geocoder`) and exports an `initViewer(containerId)` function
that later specs (S7.3 – S7.5, S8.*) import and extend. No satellite entities are rendered yet — this spec
only establishes the globe container.

## Dependencies
- S1.6 (Cesium frontend scaffold — `index.html` `#cesiumContainer` + Vite + Vitest in place)

## Target Location
`frontend/src/cesiumView.js`

---

## Functional Requirements

### FR-1: Create Cesium Viewer with offline imagery
- **What**: `initViewer(containerId)` creates `new Cesium.Viewer(containerId, options)` and returns the viewer
  instance. The imagery provider must be `new Cesium.TileMapServiceImageryProvider({ url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII") })` — no ion token, no network tile fetch.
- **Inputs**: `containerId` — string DOM element id (e.g. `"cesiumContainer"`).
- **Outputs**: Cesium `Viewer` instance (returned synchronously after construction).
- **Edge cases**:
  - Container element does not exist → Cesium throws; do not swallow the error.
  - Called more than once with the same container → destroy previous viewer first to avoid duplicate canvases.

### FR-2: Disable unnecessary UI widgets
- **What**: The `Viewer` options object must set `baseLayerPicker: false` and `geocoder: false`. Additional
  recommended: `homeButton: false`, `sceneModePicker: false`, `navigationHelpButton: false`, `animation: false`,
  `timeline: false` (these will be re-enabled in later specs as needed).
- **Inputs**: passed as viewer constructor options.
- **Outputs**: Viewer DOM contains no geocoder input box and no base-layer-picker button.
- **Edge cases**: Later specs may override timeline/animation — keep `animation` and `timeline` as `false` here
  and let S7.4 re-enable them.

### FR-3: Export `initViewer` and expose viewer singleton
- **What**: The module exports a named function `initViewer(containerId)` and a module-level `let viewer = null`
  singleton that is set on first call. Subsequent imports of `cesiumView.js` share the same instance.
- **Inputs**: —
- **Outputs**: `export function initViewer(containerId)`, `export { viewer }` (or a getter).
- **Edge cases**: Calling `initViewer` before the DOM is ready → let the caller ensure DOM readiness (document
  `DOMContentLoaded` or Vite module deferred load); `cesiumView.js` does not add its own `DOMContentLoaded` listener.

### FR-4: Wire into `main.js`
- **What**: `frontend/src/main.js` imports `initViewer` from `./cesiumView.js` and calls it with `"cesiumContainer"` so the globe mounts on page load.
- **Inputs**: —
- **Outputs**: Globe renders in `#cesiumContainer` when `index.html` is opened.
- **Edge cases**: `main.js` should still call `initCesiumBaseUrl()` before `initViewer()` so asset paths resolve.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `initViewer("cesiumContainer")` returns a `Cesium.Viewer` instance without throwing.
- [ ] **Outcome 2**: The viewer's `baseLayerPicker` and `geocoder` options are `false` (inspectable on the
  constructed viewer's `options` / DOM).
- [ ] **Outcome 3**: The imagery provider URL contains `"NaturalEarthII"` — confirming offline tile source.
- [ ] **Outcome 4**: `viewer` singleton is exported and non-null after `initViewer` is called.
- [ ] **Outcome 5**: `main.js` calls `initViewer("cesiumContainer")` — wiring confirmed by test or import analysis.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

Test file: `frontend/src/__tests__/cesiumView.test.js`

1. **test_initViewer_returns_viewer**: Mock `Cesium.Viewer` constructor; call `initViewer("cesiumContainer")`; assert return value is the mock Viewer instance.
2. **test_initViewer_disables_baseLayerPicker**: Capture options passed to `Cesium.Viewer`; assert `baseLayerPicker === false`.
3. **test_initViewer_disables_geocoder**: Assert `geocoder === false` in captured options.
4. **test_initViewer_uses_NaturalEarth_imagery**: Assert the `imageryProvider` option is constructed with a URL
   containing `"NaturalEarthII"` (mock `TileMapServiceImageryProvider` + `buildModuleUrl`).
5. **test_initViewer_exports_singleton**: Call `initViewer` twice; assert the exported `viewer` equals the second
   call's return value (re-init destroys and recreates) OR assert it equals the first (idempotent) — document
   chosen behavior in spec.md.
6. **test_initViewer_no_ion_token**: Assert `Cesium.Ion.defaultAccessToken` is never set during `initViewer`.

### Mocking Strategy
- Mock the entire `cesium` module in Vitest: `vi.mock("cesium", ...)` returning stub constructors for
  `Viewer` and `TileMapServiceImageryProvider`, and a stub `buildModuleUrl` that returns its argument.
- Use `jsdom` (already configured via S1.6 Vitest setup) so `document` is available.
- No real CesiumJS rendering in unit tests — tests verify constructor call arguments only.

### Coverage Expectation
- All exported functions (`initViewer`) covered; edge cases for double-init and missing container covered.

---

## References
- roadmap.md — Phase 7, S7.1 row; Notes: `TileMapServiceImageryProvider` from `Assets/Textures/NaturalEarthII`, `baseLayerPicker:false`, `geocoder:false`, no ion token
- CLAUDE.md — "NEVER hardcode secrets/tokens"; Cesium ion token via `.env` only; this spec deliberately avoids the token
- S1.6 spec — frontend scaffold (Vite, Vitest, `#cesiumContainer`, CesiumJS npm package)
