# Checklist — Spec S8.2: Polyline Tracking

## Phase 1: Setup & Dependencies
- [x] Verify S8.1 is `done` and `npm --prefix frontend run test` passes with no failures
- [x] Confirm `frontend/src/risk.js` and `frontend/src/__tests__/risk.test.js` exist
- [x] No new npm packages needed (`CallbackProperty` is already part of `cesium`)

## Phase 2: Tests First (TDD)
- [x] Extend `frontend/src/__tests__/risk.test.js`:
  - [x] Add `MockCallbackProperty` to `vi.hoisted` block (stores `(cb, isConst)`)
  - [x] Add `CallbackProperty: MockCallbackProperty` to `vi.mock("cesium", ...)` factory
  - [x] N/A — timer tests use `mockFetchConjunctions` (already mocked) rather than a namespace spy; `vi.advanceTimersByTimeAsync` handles async resolution
  - [x] Write FR-1 tests (4): `buildCallbackPositions` happy path + two null branches + returns CallbackProperty
  - [x] Write FR-2 tests (2): positions is a CallbackProperty instance; missing-sat guard preserved
  - [x] Write FR-3 tests (3): repeated firing; stop cancellation (using `vi.useFakeTimers()`)
- [x] Run `npm --prefix frontend run test` — 9 tests fail as expected (Red)

## Phase 3: Implementation
- [x] In `risk.js`, implement FR-1: `buildCallbackPositions(entityA, entityB)`
  - Returns `new Cesium.CallbackProperty((time) => { ... }, false)`
  - Callback returns `[posA, posB]` or `undefined` if either position is null
- [x] In `risk.js`, update FR-2: modify `loadRiskPolylines` to:
  - Remove static `getValue` snapshot; remove `if (!posA || !posB) continue` guard
  - Keep `if (!entityA || !entityB) continue` guard
  - Call `buildCallbackPositions(entityA, entityB)` and use result as `polyline.positions`
- [x] In `risk.js`, implement FR-3: `startRiskRefresh(viewer, intervalMs = 120_000)` and `stopRiskRefresh(handle)`
- [x] Export `buildCallbackPositions`, `startRiskRefresh`, `stopRiskRefresh` from `risk.js`
- [x] Run `npm --prefix frontend run test` — 29/29 in risk.test.js pass (Green)
- [x] Verify S8.1 tests still pass — all 87 frontend tests pass (no regression)

## Phase 4: Integration
- [x] Wire `startRiskRefresh(viewer)` call in `frontend/src/main.js` after initial `fetchAndRenderRisk` call
- [x] Run lint: `npm --prefix frontend run lint` — all files clean
- [x] Run full frontend test suite: `npm --prefix frontend run test` — 87/87 pass

## Phase 5: Verification
- [x] All 9 tangible outcomes checked (see below)
- [x] No hardcoded secrets or tokens
- [x] Polylines visually track moving satellites as clock advances (manual verify with `make serve-frontend`)
- [x] Polylines rebuild after 2-minute refresh interval fires
- [x] Update roadmap.md status: `spec-written` → `done`

### Tangible Outcome Verification
- [x] Outcome 1: `buildCallbackPositions` exported from `risk.js` ✓
- [x] Outcome 2: `loadRiskPolylines` sets `polyline.positions` to a `CallbackProperty` instance ✓ (test_loadRiskPolylines_positions_is_callback_property)
- [x] Outcome 3: Callback returns `[posA, posB]` when both entities have positions ✓ (test_buildCallbackPositions_callback_returns_positions)
- [x] Outcome 4: Callback returns `undefined` when either entity position is null ✓ (tests for posA and posB null)
- [x] Outcome 5: Missing-entity guard preserved in `loadRiskPolylines` ✓ (test_loadRiskPolylines_missing_sat_guard_preserved)
- [x] Outcome 6: `startRiskRefresh` triggers `fetchAndRenderRisk` repeatedly ✓ (timer tests)
- [x] Outcome 7: `stopRiskRefresh` cancels further calls ✓ (test_stopRiskRefresh_prevents_further_calls)
- [x] Outcome 8: All S8.1 tests pass — 87/87 total ✓
- [x] Outcome 9: All new Vitest tests pass — 29/29 in risk.test.js ✓
