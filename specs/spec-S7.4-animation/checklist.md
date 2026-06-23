# Checklist — Spec S7.4: Animation (SampledPositionProperty + Clock)

## Phase 1: Setup & Dependencies
- [x] Verify S7.3 is `done` (satellite entities render on the globe)
- [x] Verify S6.3 is `done` (`GET /positions` returns `BulkPositionsResponse`)
- [x] Confirm `fetchBulkPositions` is exported from `frontend/src/api.js`
- [x] Confirm Vitest + jsdom are configured (`frontend/vite.config.js` / `vitest.config.js`)
- [x] No new npm dependencies required (Cesium already imported; no additions to `package.json`)

## Phase 2: Tests First (TDD)
- [x] Create/extend `frontend/src/__tests__/cesiumView.test.js`
- [x] Write `test_buildSampledPosition_empty` — empty array → SampledPositionProperty, no throw
- [x] Write `test_buildSampledPosition_samples` — 3 samples added without error
- [x] Write `test_setupClock_sets_fields` — LOOP_STOP, multiplier 60, shouldAnimate true, zoomTo called
- [x] Write `test_setupClock_custom_multiplier` — multiplier 300 applied
- [x] Write `test_loadAnimatedTracks_no_entities` — 0 sat-* entities → returns 0, no fetch
- [x] Write `test_loadAnimatedTracks_updates_position` — entity position replaced with SampledPositionProperty
- [x] Write `test_loadAnimatedTracks_missing_entity` — unknown catalog in response → no throw
- [x] Write `test_loadAnimatedTracks_fetch_error` — fetchBulkPositions rejects → returns 0
- [x] Run tests — expect failures (Red) ✓ confirmed: 8 failed, 18 passed

## Phase 3: Implementation
- [x] **FR-1**: Remove `animation: false` and `timeline: false` from `initViewer` in `cesiumView.js`
- [x] **FR-2**: Implement `buildSampledPosition(positions)` — `SampledPositionProperty` + `LAGRANGE` degree 5
- [x] **FR-3**: Implement `setupClock(v, startIso, stopIso, multiplier = 60)`
- [x] **FR-4**: Implement `loadAnimatedTracks(v, start, stop, step = 60)`
  - Collect `catalog_no` list from viewer entities
  - Call `fetchBulkPositions`
  - Build `SampledPositionProperty` per satellite
  - Update matching entity `.position`
  - Return count updated
- [x] Export new functions (`buildSampledPosition`, `setupClock`, `loadAnimatedTracks`)
- [x] Run tests — expect pass (Green) ✓ confirmed: 26/26 passed
- [x] Refactor if needed (no logic duplication, clean error handling)

## Phase 4: Integration
- [x] Update `frontend/src/main.js` to call `setupClock` and `loadAnimatedTracks` after `loadSatelliteEntities`
  - Define animation window: `start = now`, `stop = now + 6h` (ISO strings)
  - Pass `step = 60`, `multiplier = 60`
- [x] Verify the globe animates: satellites visibly move across the globe when the Cesium clock plays
- [x] Verify the timeline widget appears and scrubbing updates entity positions
- [x] Verify LOOP_STOP behaviour: playback stops at `stop` and does not wrap to before `start`
- [x] Run lint: `npm --prefix frontend run lint` ✓ passed (Prettier clean)
- [x] Run full frontend test suite: `npm --prefix frontend run test` ✓ 51/51 passed

## Phase 5: Verification
- [x] All 8 tests pass (Green) ✓ 26/26 total (18 prior + 8 new)
- [x] Outcome 1 verified: entity `position` is `SampledPositionProperty` instance after loading
- [x] Outcome 2 verified: `buildSampledPosition` with 3 samples → 3 `addSample` calls + `setInterpolationOptions` called
- [x] Outcome 3 verified: `setupClock` sets `LOOP_STOP` and default multiplier `60`
- [x] Outcome 4 verified: `viewer.timeline.zoomTo` called with correct JulianDates
- [x] Outcome 5 verified: `initViewer` no longer has `animation: false` / `timeline: false`
- [x] No hardcoded secrets/tokens
- [x] Geodetic conversion (`Cartesian3.fromDegrees(lon, lat, alt_km * 1000)`) only in display layer (confirmed — this is the display boundary)
- [x] Update `roadmap.md` status: `spec-written` → `done` (when fully verified)
