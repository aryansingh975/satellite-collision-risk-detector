# Spec S7.5 — Orbit Path Graphic

## Overview
Adds a Cesium `path` graphic to the selected satellite's entity, rendering its orbital trajectory as a visible trail on the 3D globe. The path is driven by the entity's existing `SampledPositionProperty` (from S7.4) so it moves with the animation clock. A toggle control shows or hides the path without removing the underlying entity.

## Dependencies
- S7.4 — SampledPositionProperty + clock animation (path requires a sampled position to trace)

## Target Location
`frontend/src/cesiumView.js`

---

## Functional Requirements

### FR-1: Path graphic on entity
- **What**: When a satellite entity is created (or when it is selected), attach a Cesium `path` property to it that renders the satellite's orbital trail.
- **Inputs**: A Cesium entity that already has a `SampledPositionProperty` as its `position`; Cesium clock `currentTime`.
- **Outputs**: The entity gains a `path` graphic with configured `leadTime`, `trailTime`, `material` (color + alpha), and `width`. The path traces the full orbital period (≈ `trailTime = period_seconds`, `leadTime = period_seconds`) or a fixed window (e.g. 5 400 s ≈ 90 min for LEO as a sensible default).
- **Edge cases**: Entity has no `SampledPositionProperty` → skip path attachment. Viewer clock not yet set → path renders zero-length until clock advances.

### FR-2: Toggle path visibility
- **What**: `toggleOrbitPath(entity, visible)` sets `entity.path.show` to the given boolean, toggling the graphic on or off without destroying the entity or its `SampledPositionProperty`.
- **Inputs**: `entity` (Cesium Entity), `visible` (boolean).
- **Outputs**: `entity.path.show` is updated. If `entity.path` does not exist, the function is a no-op (no throw).
- **Edge cases**: Called with `null` / `undefined` entity → no-op, no exception.

### FR-3: Show path only for selected satellite
- **What**: When `viewer.selectedEntity` changes, the path for the previously selected entity is hidden (`show = false`) and the newly selected entity's path is shown (`show = true`). All other entities keep `path.show = false`.
- **Inputs**: Cesium `viewer.selectedEntityChanged` event or explicit `selectSatellite(entity)` call from S7.3.
- **Outputs**: Exactly one entity (the selected one) has `path.show = true`; all others have `path.show = false`.
- **Edge cases**: Deselecting (new selection is `undefined` / `null`) → all paths hidden.

### FR-4: Default path appearance
- **What**: Paths are styled consistently — white or regime-matched color, semi-transparent (alpha ≈ 0.5), 2 px wide, `leadTime` and `trailTime` each covering one full revolution (≈ 5 400 s for LEO; use a fixed default of 5 400 s if period is unavailable).
- **Inputs**: None beyond the entity.
- **Outputs**: `entity.path.material` is a `Cesium.ColorMaterialProperty`; `entity.path.width` is 2; `entity.path.leadTime` and `entity.path.trailTime` are `ConstantProperty(5400)`.
- **Edge cases**: No per-satellite period data available → default 5 400 s.

---

## Tangible Outcomes

- [ ] **Outcome 1**: Selecting a satellite on the globe causes a visible orbit trail to appear tracing the satellite's position forward and backward in time.
- [ ] **Outcome 2**: Clicking the toggle control (or calling `toggleOrbitPath(entity, false)`) hides the path; calling with `true` shows it again — the entity itself remains visible throughout.
- [ ] **Outcome 3**: Only the selected satellite shows its path; deselecting removes all paths.
- [ ] **Outcome 4**: `toggleOrbitPath(null, true)` does not throw an exception.
- [ ] **Outcome 5**: Unit tests for `toggleOrbitPath` and `selectSatellite` path-management logic pass under Vitest/jsdom.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_toggleOrbitPath_shows_path**: Given an entity with `path.show = false`, calling `toggleOrbitPath(entity, true)` sets `entity.path.show` to `true`.
2. **test_toggleOrbitPath_hides_path**: Given an entity with `path.show = true`, calling `toggleOrbitPath(entity, false)` sets `entity.path.show` to `false`.
3. **test_toggleOrbitPath_null_entity**: Calling `toggleOrbitPath(null, true)` does not throw.
4. **test_toggleOrbitPath_no_path_property**: Entity has no `path` property → `toggleOrbitPath` is a no-op, no throw.
5. **test_addOrbitPath_attaches_path**: `addOrbitPath(entity)` attaches a `path` object with `leadTime`, `trailTime`, `width`, and `material` properties.
6. **test_selectSatellite_shows_only_selected_path**: After `selectSatellite(entityB)` when `entityA` was previously selected, `entityA.path.show` is `false` and `entityB.path.show` is `true`.
7. **test_deselect_hides_all_paths**: `selectSatellite(null)` hides paths on all tracked entities.

### Mocking Strategy
- No real Cesium viewer needed: use a plain JS object as a mock entity with `path.show`, `path.leadTime`, `path.trailTime`, `path.material`, `path.width` properties.
- Tests run under Vitest + jsdom; Cesium globals are not available — import only the pure logic functions (`toggleOrbitPath`, `addOrbitPath`, `selectSatellite`), not the Viewer constructor.
- Export these three functions from `cesiumView.js` (or a small helper module) to make them unit-testable.

### Coverage Expectation
- All three exported functions have tests covering normal path and edge cases (null entity, missing `path` property, deselect).

---

## References
- roadmap.md S7.5 row (Phase 7 table + Master Spec Index)
- CLAUDE.md — frontend spec tooling: Vitest + jsdom; no ion token; offline Natural Earth imagery
- Cesium docs: `Entity.path`, `PathGraphics`, `SampledPositionProperty`, `ColorMaterialProperty`
