# Spec S8.2 — Polyline Tracking

## Overview
Upgrade the risk polylines from S8.1 to use `Cesium.CallbackProperty` so that each polyline's
endpoints automatically follow the two satellite entities as the Cesium clock advances, instead
of being static Cartesian3 snapshots captured at load time. Also adds `startRiskRefresh` /
`stopRiskRefresh` to periodically re-fetch conjunction data and rebuild the polylines, keeping
the display in sync whenever the backend scheduler re-runs the conjunction screen.

## Dependencies
- S8.1 — Risk-pair polylines (`frontend/src/risk.js` exists with base functionality)

## Target Location
`frontend/src/risk.js` (extend existing file)

---

## Functional Requirements

### FR-1: Build a dynamic callback property for polyline positions
- **What**: `buildCallbackPositions(entityA, entityB)` returns a `Cesium.CallbackProperty` that,
  whenever Cesium evaluates it, reads both satellite entities' positions at the time argument
  supplied by the Cesium render loop.
- **Inputs**:
  - `entityA`, `entityB` — Cesium `Entity` objects with a `.position` property
    (`SampledPositionProperty`)
- **Outputs**: `Cesium.CallbackProperty` with `isConstant: false`
- **Callback logic** (the function passed to `new Cesium.CallbackProperty(fn, false)`):
  1. `posA = entityA.position.getValue(time)`
  2. `posB = entityB.position.getValue(time)`
  3. If either is `null` / `undefined` → return `undefined` (polyline hides gracefully)
  4. Otherwise return `[posA, posB]`
- **Edge cases**: Entity whose `SampledPositionProperty` has no sample for the queried time
  returns `undefined` from `getValue`; callback must return `undefined` in that case, never throw.

### FR-2: Update loadRiskPolylines to use callback positions
- **What**: `loadRiskPolylines(viewer, conjunctions)` is upgraded so that the polyline entity for
  each conjunction uses a `CallbackProperty` (from FR-1) rather than static Cartesian3 snapshots.
- **Change from S8.1**:
  - S8.1 called `entityA.position.getValue(viewer.clock.currentTime)` to capture a snapshot,
    then passed static `[posA, posB]` to `PolylineGraphics.positions`.
  - S8.2 calls `buildCallbackPositions(entityA, entityB)` and passes the resulting
    `CallbackProperty` as `PolylineGraphics.positions`.
- **Guard preserved**: still skip a conjunction if `viewer.entities.getById` returns `null` for
  either satellite (same as S8.1 FR-4). The static `getValue` null-check at load time is removed
  because the callback handles it at render time.
- **Outputs**: integer count of polylines added (unchanged).

### FR-3: Start / stop periodic risk refresh
- **What**: `startRiskRefresh(viewer, intervalMs)` sets up a recurring timer that calls
  `fetchAndRenderRisk(viewer)` each time it fires, keeping polylines current when the backend
  scheduler updates conjunction data.
- **Inputs**:
  - `viewer` — Cesium Viewer
  - `intervalMs` — polling interval in milliseconds; **default `120_000`** (2 minutes, matching
    the backend APScheduler cadence)
- **Outputs**: timer handle (return value of `setInterval`) so the caller can stop it.
- **Companion**: `stopRiskRefresh(handle)` calls `clearInterval(handle)`. Exported so callers
  can clean up on unmount / page unload.
- **Edge cases**: no internal validation of `intervalMs`; callers supply a positive value.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `buildCallbackPositions` is exported from `risk.js` and returns an instance
  of `Cesium.CallbackProperty`.
- [ ] **Outcome 2**: A polyline entity created by `loadRiskPolylines` has its
  `polyline.positions` set to a `CallbackProperty`, not a plain array.
- [ ] **Outcome 3**: The `CallbackProperty` callback returns `[posA, posB]` when both entities
  have positions at the queried time.
- [ ] **Outcome 4**: The callback returns `undefined` when either entity's `getValue` returns
  `null` or `undefined`.
- [ ] **Outcome 5**: `loadRiskPolylines` still skips a conjunction when `getById` returns `null`
  for either satellite (S8.1 guard preserved).
- [ ] **Outcome 6**: `startRiskRefresh(viewer, intervalMs)` triggers `fetchAndRenderRisk` after
  `intervalMs` elapses and again on each subsequent interval (verified with `vi.useFakeTimers()`).
- [ ] **Outcome 7**: `stopRiskRefresh` prevents any further calls to `fetchAndRenderRisk`.
- [ ] **Outcome 8**: All S8.1 tests still pass — no regression to `buildDescription`,
  `severityColor`, `buildPolylineEntity`, `clearRiskPolylines`, or `fetchAndRenderRisk`.
- [ ] **Outcome 9**: All new Vitest tests pass (`npm --prefix frontend run test`).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
Extend `frontend/src/__tests__/risk.test.js`.

1. **test_buildCallbackPositions_returns_callback_property** — returns a `Cesium.CallbackProperty`
   instance (i.e. `MockCallbackProperty` was called).
2. **test_buildCallbackPositions_callback_returns_positions** — when both entities return non-null
   from `getValue`, invoking the stored callback returns `[posA, posB]`.
3. **test_buildCallbackPositions_callback_returns_undefined_when_posA_null** — entityA's
   `getValue` returns `null`; callback returns `undefined`.
4. **test_buildCallbackPositions_callback_returns_undefined_when_posB_null** — entityB's
   `getValue` returns `null`; callback returns `undefined`.
5. **test_loadRiskPolylines_positions_is_callback_property** — the entity added by
   `loadRiskPolylines` has `polyline.positions` equal to the `MockCallbackProperty` instance.
6. **test_loadRiskPolylines_missing_sat_guard_preserved** — `getById` returns `null` for one
   satellite → that conjunction skipped (count = 1 when there are 2 conjunctions, one invalid).
7. **test_startRiskRefresh_calls_fetchAndRender_after_interval** — `vi.useFakeTimers()`, advance
   by `intervalMs` → `fetchAndRenderRisk` (spied) called once.
8. **test_startRiskRefresh_calls_repeatedly** — advance by `2 × intervalMs` →
   `fetchAndRenderRisk` called twice.
9. **test_stopRiskRefresh_prevents_further_calls** — start refresh; advance halfway; stop;
   advance again → `fetchAndRenderRisk` called exactly once total.

### Mocking Strategy
- **Cesium**: extend the `vi.hoisted` block to add
  `MockCallbackProperty = vi.fn().mockImplementation((cb, isConst) => ({ _cb: cb, isConstant: isConst }))`.
  Add `CallbackProperty: MockCallbackProperty` to the `vi.mock("cesium", ...)` factory.
- **fetchAndRenderRisk** (timer tests): spy via
  `vi.spyOn(riskModule, "fetchAndRenderRisk").mockResolvedValue(0)` after importing the module
  under a namespace import (`import * as riskModule from "../risk.js"`).
- **Timer tests**: `vi.useFakeTimers()` in `beforeEach`; `vi.useRealTimers()` in `afterEach` of
  the timer describe-block to avoid leaking fake timers into other suites.
- **Viewer stub**: reuse the existing `makeViewer()` factory; no changes needed.
- **Satellite entity stubs**: reuse `makeSatEntity()` from S8.1 tests.

### Coverage Expectation
- `buildCallbackPositions`: both null branches + happy path covered.
- `loadRiskPolylines`: callback-property path + missing-entity guard confirmed.
- `startRiskRefresh` / `stopRiskRefresh`: repeated firing + stop cancellation covered.

---

## References
- [roadmap.md](../../roadmap.md) — Phase 8, S8.2 row
- [CLAUDE.md](../../.claude/CLAUDE.md) — project rules
- [frontend/src/risk.js](../../frontend/src/risk.js) — S8.1 implementation to extend
- [frontend/src/__tests__/risk.test.js](../../frontend/src/__tests__/risk.test.js) — extend this test file
- [frontend/src/main.js](../../frontend/src/main.js) — integration point for `startRiskRefresh`
