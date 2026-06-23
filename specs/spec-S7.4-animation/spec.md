# Spec S7.4 — Animation (SampledPositionProperty + Clock)

## Overview
Bring the satellite entities to life by replacing their static snapshot positions with time-dynamic
`SampledPositionProperty` objects built from the bulk `/positions` API (`GET /positions` — S6.3).
Configure the Cesium clock to loop over the track window with a configurable speed multiplier and
zoom the timeline widget to the animation range so the user can scrub the playhead.

## Dependencies
- **S7.3** — Satellite entities (static point rendering, `buildSatelliteEntity`, `loadSatelliteEntities`)
- **S6.3** — Bulk positions endpoint (`GET /positions` → `BulkPositionsResponse`)

## Target Location
`frontend/src/cesiumView.js`

---

## Functional Requirements

### FR-1: Viewer initialization enables animation + timeline widgets
- **What**: `initViewer` must enable the Cesium animation widget and timeline bar.
- **Inputs**: `containerId` string (unchanged).
- **Outputs**: `Cesium.Viewer` created with `animation: true` and `timeline: true` (remove the
  `false` overrides added for S7.1/S7.3). All other S7.1 options remain unchanged.
- **Edge cases**: Must not break S7.3 entity rendering; re-initialization (`viewer.destroy()` guard)
  must still function correctly.

### FR-2: Build SampledPositionProperty from a position track
- **What**: `buildSampledPosition(positions)` converts a `PositionSample[]` array into a
  `Cesium.SampledPositionProperty`.
- **Inputs**: `positions` — array of `{ time: string (ISO 8601), lat: number, lon: number, alt_km: number }`.
- **Outputs**: `Cesium.SampledPositionProperty` with:
  - One `addSample(julianDate, Cartesian3.fromDegrees(lon, lat, alt_km * 1000))` call per entry.
  - `LAGRANGE` interpolation, degree 5 (`setInterpolationOptions`).
- **Edge cases**: Empty array → returns a `SampledPositionProperty` with zero samples (no error
  thrown; callers handle missing coverage by checking `positions.length`).

### FR-3: Configure the Cesium clock for animated playback
- **What**: `setupClock(v, startIso, stopIso, multiplier = 60)` configures the viewer clock.
- **Inputs**:
  - `v` — Cesium Viewer instance.
  - `startIso` / `stopIso` — ISO 8601 strings defining the animation window.
  - `multiplier` — clock speed (real-seconds per sim-second, default `60`).
- **Outputs / Side-effects**:
  - `v.clock.startTime` = `Cesium.JulianDate.fromIso8601(startIso)`.
  - `v.clock.stopTime` = `Cesium.JulianDate.fromIso8601(stopIso)`.
  - `v.clock.currentTime` = startTime (rewind to beginning).
  - `v.clock.clockRange` = `Cesium.ClockRange.LOOP_STOP`.
  - `v.clock.multiplier` = `multiplier`.
  - `v.clock.shouldAnimate` = `true`.
  - `v.timeline.zoomTo(startTime, stopTime)`.
- **Edge cases**: `stopIso ≤ startIso` — function applies values without throwing; the caller is
  responsible for passing a sensible window.

### FR-4: Fetch bulk tracks and update entity positions
- **What**: `loadAnimatedTracks(v, start, stop, step = 60)` fetches bulk position tracks for all
  satellite entities currently in the viewer and replaces each entity's static `position` with an
  animated `SampledPositionProperty`.
- **Inputs**:
  - `v` — Cesium Viewer.
  - `start` / `stop` — ISO 8601 strings (the animation window, same as FR-3).
  - `step` — sample interval in seconds (default `60`).
- **Behaviour**:
  1. Collect `catalog_no` values from every entity whose `id` starts with `"sat-"`.
  2. Call `fetchBulkPositions(catalogNos, start, stop, step)`.
  3. For each `PositionsResponse` in `response.satellites`:
     - Build a `SampledPositionProperty` via `buildSampledPosition`.
     - Find the entity by `"sat-{catalog_no}"` and set `entity.position = sampledProp`.
  4. Return the count of entities successfully updated.
- **Edge cases**:
  - No entities in viewer → return `0` immediately (no fetch).
  - Entity in bulk response but not in viewer → skip silently.
  - `fetchBulkPositions` throws → `console.error`, return `0`.
  - `response.satellites` is empty → return `0`.

---

## Tangible Outcomes

- [ ] **Outcome 1**: After `loadAnimatedTracks` completes, a satellite entity's `position` is an
  instance of `Cesium.SampledPositionProperty` (not `Cesium.Cartesian3`).
- [ ] **Outcome 2**: `buildSampledPosition` with 10 samples returns a property whose
  `getValueInReferenceFrame` resolves at the first and last sample times.
- [ ] **Outcome 3**: `setupClock` sets `v.clock.clockRange === Cesium.ClockRange.LOOP_STOP` and
  `v.clock.multiplier === 60` (default).
- [ ] **Outcome 4**: `viewer.timeline.zoomTo` is called with the correct start/stop JulianDates.
- [ ] **Outcome 5**: `initViewer` no longer sets `animation: false` or `timeline: false`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_buildSampledPosition_empty**: `buildSampledPosition([])` returns a
   `SampledPositionProperty` instance without throwing.
2. **test_buildSampledPosition_samples**: Given 3 `PositionSample` objects, the returned property
   has `_property._times.length === 3` (or equivalent internal count check); alternatively, confirm
   the property is not null and `positions.length` samples were passed.
3. **test_setupClock_sets_fields**: Given a mock Cesium Viewer with spy on `clock` and `timeline`,
   `setupClock(v, "2025-01-01T00:00:00Z", "2025-01-01T06:00:00Z")` sets
   `LOOP_STOP`, multiplier `60`, `shouldAnimate true`, and calls `zoomTo`.
4. **test_setupClock_custom_multiplier**: Passing `multiplier=300` sets `v.clock.multiplier === 300`.
5. **test_loadAnimatedTracks_no_entities**: When viewer has no `sat-*` entities, returns `0` and
   does not call `fetchBulkPositions`.
6. **test_loadAnimatedTracks_updates_position**: Given a viewer with one `sat-25544` entity and a
   mocked `fetchBulkPositions` returning a `BulkPositionsResponse` with one `PositionsResponse` for
   catalog 25544, after `loadAnimatedTracks` the entity's `position` is a
   `SampledPositionProperty`.
7. **test_loadAnimatedTracks_missing_entity**: Bulk response includes a catalog not in the viewer —
   no error is thrown and the function returns the count of those that *were* updated.
8. **test_loadAnimatedTracks_fetch_error**: `fetchBulkPositions` rejects — `loadAnimatedTracks`
   returns `0` without rethrowing.

### Mocking Strategy
- **Cesium module**: Use Vitest's `vi.mock("cesium", ...)` providing stub implementations for
  `SampledPositionProperty`, `JulianDate.fromIso8601`, `Cartesian3.fromDegrees`,
  `ClockRange.LOOP_STOP`, and `InterpolationAlgorithm.LAGRANGE`.
- **api.js**: `vi.mock("./api.js")` to stub `fetchBulkPositions`; inject test fixture data.
- **Viewer**: Plain JS object with `clock`, `timeline.zoomTo`, and `entities.values` spy/stub.

### Coverage Expectation
- All four public functions (`buildSampledPosition`, `setupClock`, `loadAnimatedTracks`, updated
  `initViewer`) have at least one passing test. Edge cases (empty, error, missing entity) covered.

---

## References
- `roadmap.md` row S7.4 (Phase 7 table and Master Spec Index)
- `CLAUDE.md` — TEME/geodetic frame rule (geodetic only at display boundary; S7.4 is display)
- `frontend/src/api.js` — `fetchBulkPositions(catalogNos, start, stop, step)`
- `backend/app/models/schemas.py` — `BulkPositionsResponse`, `PositionsResponse`, `PositionSample`
- CesiumJS docs: `SampledPositionProperty`, `ClockRange`, `JulianDate`, `Viewer.timeline`
