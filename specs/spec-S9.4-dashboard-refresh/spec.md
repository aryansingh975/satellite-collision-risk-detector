# Spec S9.4 — Dashboard Refresh Wiring

## Overview
All three dashboard panels (regime doughnut, approach bar chart, risk ranking table) are initialised
once on page load. S9.4 adds a **refresh loop** so the panels stay current as the backend
re-ingests TLEs every two hours. Refresh can be driven two ways: a **manual "Refresh" button** the
user can click at any time, and an optional **auto-poll interval** that fires automatically.
On each refresh the charts are updated in-place (Chart.js `.update()`) rather than destroyed and
recreated, and the risk table is re-rendered. A visible **last-updated timestamp** and a brief
loading indicator give the user feedback.

## Dependencies
- S9.1 (`initRegimeChart`) — done
- S9.2 (`initApproachChart`) — done
- S9.3 (`initRiskTable`, `renderRiskTable`) — done

## Target Location
`frontend/src/dashboard.js`

---

## Functional Requirements

### FR-1: `refreshDashboard(charts, viewer)` — coordinated panel refresh
- **What**: Async function that re-fetches all three data sources in parallel and updates every panel.
- **Inputs**:
  - `charts` — `{ regime: Chart, approach: Chart }` instances returned by `initRegimeChart` /
    `initApproachChart`.
  - `viewer` — Cesium `Viewer` (or `null` / any falsy value in tests); passed straight through to
    `renderRiskTable`.
- **Outputs**:
  - Regime chart `.data.datasets[0].data` updated; `.update()` called.
  - Approach chart `.data.datasets[0].data` updated; `.update()` called.
  - Risk table DOM re-rendered via `renderRiskTable`.
  - Returns `void` (or resolves with `undefined`).
- **Edge cases**:
  - Any single fetch failure must **not** abort the others — catch per-fetch and treat failed
    panels as no-ops (leave stale data).
  - Empty arrays / zero counts are valid data — do not skip the update.

### FR-2: Manual refresh button
- **What**: A `<button id="refreshBtn">` in the dashboard UI triggers `refreshDashboard`.
- **Inputs**: Click event on `#refreshBtn`.
- **Outputs**: All panels refresh; `#refreshBtn` is disabled (and shows "Refreshing…") during the
  async call, then re-enabled.
- **Edge cases**: Rapid double-clicks do not trigger two concurrent refreshes (debounce via the
  disabled state).

### FR-3: Last-updated timestamp
- **What**: `updateTimestamp()` writes the current local time into a `<span id="lastUpdated">`.
- **Inputs**: none (reads `new Date()`).
- **Outputs**: `#lastUpdated` text set to `"Last updated: HH:MM:SS"` (24-hour local time).
- **Edge cases**: If `#lastUpdated` is absent, silently skip (no throw).

### FR-4: `startAutoRefresh(charts, viewer, intervalMs)` — optional polling loop
- **What**: Calls `refreshDashboard` on a repeating interval.
- **Inputs**:
  - `charts`, `viewer` — forwarded to `refreshDashboard`.
  - `intervalMs` — milliseconds between refreshes (default `120_000`, i.e. 2 minutes).
- **Outputs**: Returns the interval ID so the caller can `clearInterval` it.
- **Edge cases**: `intervalMs ≤ 0` should still be accepted (behaviour is `setInterval`'s own).

---

## Tangible Outcomes

- [ ] **Outcome 1**: Calling `refreshDashboard(charts, viewer)` re-fetches all three APIs and
  mutates `charts.regime.data.datasets[0].data` and `charts.approach.data.datasets[0].data`
  (verified by spying on Chart `update()`).
- [ ] **Outcome 2**: If one API fetch throws, the other panels still update (partial-failure
  isolation verified by rejecting one mock and asserting the others ran).
- [ ] **Outcome 3**: `#refreshBtn` is disabled while `refreshDashboard` is in-flight and re-enabled
  after it resolves.
- [ ] **Outcome 4**: `#lastUpdated` contains `"Last updated:"` after a refresh.
- [ ] **Outcome 5**: `startAutoRefresh` returns a numeric interval ID; `clearInterval` stops calls.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_refreshDashboard_updates_both_charts**: Stub `fetchOrbitalRegions`,
   `fetchConjunctions`, `fetchRiskRanking`; call `refreshDashboard`; assert both chart
   `.update()` mocks were called and dataset data matches the stubs.
2. **test_refreshDashboard_partial_failure_isolation**: Make `fetchOrbitalRegions` reject;
   assert approach chart and risk table still updated.
3. **test_refreshDashboard_empty_data**: All stubs return `{}` / `[]`; assert `.update()` still
   called (no throw).
4. **test_refreshBtn_disabled_during_refresh**: Attach a button to jsdom; call handler; assert
   button disabled during async, enabled after.
5. **test_updateTimestamp_sets_text**: Attach `<span id="lastUpdated">`; call `updateTimestamp()`;
   assert text starts with `"Last updated:"`.
6. **test_updateTimestamp_missing_element**: No `#lastUpdated` in DOM; call `updateTimestamp()`;
   assert no exception thrown.
7. **test_startAutoRefresh_returns_id_and_fires**: Use fake timers; assert `refreshDashboard` is
   called after one tick of the interval.

### Mocking Strategy
- Mock `fetchOrbitalRegions`, `fetchConjunctions`, `fetchRiskRanking` from `api.js` using
  `vi.mock('./api.js', …)` — never hit the live backend.
- Spy on Chart instances' `.update()` method (pass synthetic chart objects `{ data: { datasets:
  [{ data: [] }] }, update: vi.fn() }`).
- Use `vi.useFakeTimers()` / `vi.advanceTimersByTime()` for polling tests.
- jsdom provides a minimal DOM for button and span tests.

### Coverage Expectation
- All four exported functions have at least one test; partial-failure and empty-data edges covered.

---

## References
- roadmap.md S9.4 row; CLAUDE.md (frontend testing conventions — Vitest + jsdom; no live API calls)
