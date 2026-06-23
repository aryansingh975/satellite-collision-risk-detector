# Checklist — Spec S9.4: Dashboard Refresh Wiring

## Phase 1: Setup & Dependencies
- [x] Verify S9.1, S9.2, S9.3 are `done`
- [x] Locate `frontend/src/dashboard.js` (target file — extend, do not replace)
- [x] Confirm `#refreshBtn` and `#lastUpdated` elements exist in `frontend/index.html`; add them if missing

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/dashboard.refresh.test.js`
- [x] `test_refreshDashboard_updates_both_charts` — mock all three fetches; assert `.update()` called
- [x] `test_refreshDashboard_partial_failure_isolation` — reject `fetchOrbitalRegions`; assert others still ran
- [x] `test_refreshDashboard_empty_data` — stubs return `{}`/`[]`; assert no throw, `.update()` called
- [x] `test_refreshBtn_disabled_during_refresh` — button disabled in-flight, re-enabled after
- [x] `test_updateTimestamp_sets_text` — `#lastUpdated` text starts with `"Last updated:"`
- [x] `test_updateTimestamp_missing_element` — no DOM element; no exception
- [x] `test_startAutoRefresh_returns_id_and_fires` — fake timers; assert interval fires `refreshDashboard`
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `updateTimestamp()` — writes `"Last updated: HH:MM:SS"` to `#lastUpdated` if present
- [x] Implement `refreshDashboard(charts, viewer)`:
  - [x] `Promise.allSettled` across all three fetches (isolation of failures)
  - [x] Update `charts.regime.data.datasets[0].data` + call `.update()`
  - [x] Update `charts.approach.data.datasets[0].data` + call `.update()`
  - [x] Re-render risk table via `renderRiskTable`
  - [x] Call `updateTimestamp()` on success
- [x] Wire `#refreshBtn` click handler: disable → `refreshDashboard` → re-enable
- [x] Implement `startAutoRefresh(charts, viewer, intervalMs = 120_000)` — returns interval ID
- [x] Export all four functions
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (keep each function ≤ 25 lines)

## Phase 4: Integration
- [x] Call `startAutoRefresh(charts, viewer)` in `frontend/src/main.js` after charts are initialised
- [x] Verify `#refreshBtn` is present in `frontend/index.html` with appropriate label
- [x] Run lint: `npm --prefix frontend run lint`
- [x] Run full frontend test suite: `npm --prefix frontend run test`

## Phase 5: Verification
- [x] All five tangible outcomes checked (see spec.md)
- [x] No hardcoded secrets/tokens
- [x] No live API calls in tests (all mocked via `vi.mock`)
- [x] Button debounce works: rapid double-click does not fire two concurrent refreshes
- [x] Update roadmap.md status: `spec-written` → `done` (after verify-spec passes)
