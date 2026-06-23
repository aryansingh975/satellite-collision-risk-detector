# Spec S7.3 — Satellite Entities

## Overview
Add one Cesium `Entity` per satellite onto the globe by calling the API client's `fetchSatellites()` function (S7.2) and placing a coloured point at each satellite's current geodetic position (lat/lon/alt). Points are coloured by orbital regime (LEO/MEO/GEO/HEO) so the viewer can instantly read the population distribution on the globe. A hover label shows the satellite's name and regime when the mouse rests over a point. All entity management is exposed through clean, testable functions exported from `cesiumView.js`.

## Dependencies
- S7.1 — Cesium globe bootstrap (`initViewer` in `frontend/src/cesiumView.js`)
- S7.2 — API client layer (`fetchSatellites` in `frontend/src/api.js`)

## Target Location
`frontend/src/cesiumView.js`

---

## Functional Requirements

### FR-1: Regime colour map
- **What**: A fixed mapping from regime string to `Cesium.Color` used to colour point entities.
- **Inputs**: Regime string — one of `"LEO"`, `"MEO"`, `"GEO"`, `"HEO"`, or unknown/null.
- **Outputs**: A `Cesium.Color` instance. Suggested palette:
  - `LEO` → `Cesium.Color.YELLOW`
  - `MEO` → `Cesium.Color.GREEN`
  - `GEO` → `Cesium.Color.CYAN`
  - `HEO` → `Cesium.Color.RED`
  - unknown/null → `Cesium.Color.WHITE`
- **Edge cases**: Unrecognised regime string returns the fallback colour (WHITE), not an error.

### FR-2: Build a single satellite entity
- **What**: `buildSatelliteEntity(sat)` creates and returns a `Cesium.Entity` for one `SatelliteOut` object.
- **Inputs**: `sat` — a `SatelliteOut` object with fields: `catalog_no`, `name`, `regime`, `lat_deg`, `lon_deg`, `alt_km`.
- **Outputs**: A `Cesium.Entity` configured with:
  - `id`: `"sat-{catalog_no}"` (unique, stable)
  - `name`: satellite name
  - `position`: `Cesium.Cartesian3.fromDegrees(lon_deg, lat_deg, alt_km * 1000)` (Cesium expects metres)
  - `point`: `PointGraphics` with `pixelSize: 6`, colour from FR-1, `outlineWidth: 0`
  - `label`: `LabelGraphics` with the satellite name + regime, `show: false` (revealed on hover)
  - `properties`: store the original `sat` object for retrieval in downstream specs (S8.3, S8.4)
- **Edge cases**: Missing `lat_deg`/`lon_deg`/`alt_km` (null/undefined) — skip or place at `(0,0,0)`; do not throw.

### FR-3: Load all satellites onto the viewer
- **What**: `loadSatelliteEntities(viewer)` fetches all satellites, clears any previously loaded satellite entities, and adds fresh entities to `viewer.entities`.
- **Inputs**: `viewer` — a live `Cesium.Viewer` instance.
- **Outputs**: Returns the array of added `Cesium.Entity` objects. Side effect: entities added to `viewer.entities`.
- **Edge cases**:
  - API returns empty array → clear entities, return `[]`, no error.
  - API rejects (network error) → log the error, leave previous entities in place, do not crash.

### FR-4: Hover label
- **What**: `initHoverLabel(viewer)` attaches a `ScreenSpaceEventHandler` for `MOUSE_MOVE`. When the mouse rests over a satellite entity the entity's label is made visible; when the mouse leaves (or lands on empty space) the label is hidden.
- **Inputs**: `viewer` — the live `Cesium.Viewer`.
- **Outputs**: Returns the `ScreenSpaceEventHandler` instance (allows cleanup in tests). Side effect: labels toggle on hover.
- **Edge cases**:
  - Non-satellite entity under cursor (e.g. a future polyline from S8.1) — skip (no label shown, no error).
  - Multiple rapid moves — only the last entity's label is shown; previously shown label is hidden first.

---

## Tangible Outcomes

- [ ] **Outcome 1**: Calling `loadSatelliteEntities(viewer)` with a mock API response of two satellites adds exactly two entities to `viewer.entities`, with ids `"sat-{catalog_no}"`.
- [ ] **Outcome 2**: Each entity's `point.color.getValue()` matches the colour for its regime as defined in the colour map.
- [ ] **Outcome 3**: Each entity's `label.show` starts as `false`; after a synthetic `MOUSE_MOVE` over the entity it becomes `true`; after moving away it returns to `false`.
- [ ] **Outcome 4**: An empty API response clears all satellite entities without throwing.
- [ ] **Outcome 5**: A satellite with `regime: "UNKNOWN"` (or null) gets the fallback WHITE colour without error.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_regime_colour_known**: Each of LEO/MEO/GEO/HEO returns the correct `Cesium.Color`.
2. **test_regime_colour_unknown**: An unrecognised regime string returns `Cesium.Color.WHITE`.
3. **test_build_entity_id**: `buildSatelliteEntity` produces an entity with `id === "sat-25544"`.
4. **test_build_entity_position**: Entity position is `Cesium.Cartesian3.fromDegrees(lon, lat, alt*1000)`.
5. **test_build_entity_point_colour**: Entity `point.color` matches the regime colour.
6. **test_build_entity_label_hidden**: Entity `label.show` is `false` on creation.
7. **test_load_entities_adds_to_viewer**: `loadSatelliteEntities` with two-satellite fixture adds two entities.
8. **test_load_entities_clears_previous**: Calling `loadSatelliteEntities` twice replaces, not appends, entities.
9. **test_load_entities_empty**: Empty API array yields zero entities, no error.
10. **test_load_entities_api_error**: Network rejection is caught; viewer entities unchanged, no throw.
11. **test_hover_shows_label**: Simulated `MOUSE_MOVE` over a satellite entity makes `label.show === true`.
12. **test_hover_hides_label_on_leave**: Moving to empty space hides the previously shown label.

### Mocking Strategy
- Mock `fetch` / the `api.js` `fetchSatellites` function with a fixed two-satellite fixture (ISS `25544` + a GEO dummy).
- Mock `Cesium.Viewer`, `viewer.entities`, and `viewer.scene` minimally using plain objects in jsdom — do not import the full Cesium runtime in Vitest (it requires a browser GPU context). Use Vitest's `vi.mock('cesium', ...)` to stub the classes.
- For hover tests, simulate the `ScreenSpaceEventHandler` callback directly with a synthetic `movement` object and a stubbed `scene.pick()`.

### Coverage Expectation
- All four exported functions (`regimeColour` / `buildSatelliteEntity` / `loadSatelliteEntities` / `initHoverLabel`) covered; all edge cases (empty, error, unknown regime, hover in/out) tested.

---

## References
- roadmap.md — S7.3 row (Phase 7 table + Master Spec Index)
- CLAUDE.md — project rules; geodetic conversion only at display boundary; no ion token; WGS-72 constants
- S7.1 spec — `initViewer` signature and viewer options
- S7.2 spec — `fetchSatellites` signature and `SatelliteOut` schema
- S2.4 spec — `SatelliteOut` Pydantic schema (fields used: `catalog_no`, `name`, `regime`, `lat_deg`, `lon_deg`, `alt_km`)
