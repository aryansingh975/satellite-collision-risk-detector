# Checklist — Spec S9.3: Risk Ranking Table

## Phase 1: Setup & Dependencies
- [x] Verify S7.2 (`api.js` with `fetchRiskRanking`) is `done`
- [x] Verify S6.5 (`/stats/risk-ranking` endpoint) is `done`
- [x] Confirm `frontend/index.html` has (or will get) `<table id="riskTable">` inside `#dashboard-panel`
- [x] No new npm packages needed — uses existing jsdom/Vitest and reuses `selectAndFly` from `search.js`

## Phase 2: Tests First (TDD)
- [x] Extend `frontend/src/__tests__/dashboard.test.js` with S9.3 tests
- [x] Add `mockFetchRiskRanking` to the `vi.hoisted` block and `vi.mock("../api.js", ...)` map
- [x] Write `test_renderRiskTable_row_count` — 3 items → 3 `<tr>` rows (Red)
- [x] Write `test_renderRiskTable_miss_km_format` — `1.23456` → `"1.235"` (Red)
- [x] Write `test_renderRiskTable_rel_vel_format` — `7.123` → `"7.12"` (Red)
- [x] Write `test_renderRiskTable_tca_format` — ISO string → `"2026-06-23 14:32:01"` (Red)
- [x] Write `test_renderRiskTable_empty` — `[]` → "No risk events" row (Red)
- [x] Write `test_renderRiskTable_row_click_selects` — click triggers `getById` + `flyTo` (Red)
- [x] Write `test_renderRiskTable_entity_not_found` — `getById` returns `null` → no throw (Red)
- [x] Write `test_initRiskTable_missing_table` — no `#riskTable` → throws (Red)
- [x] Write `test_initRiskTable_calls_fetch` — resolves and calls `fetchRiskRanking` once (Red)
- [x] Run `npm --prefix frontend run test` — expect failures (Red) ✓ 9 failing, 16 passing

## Phase 3: Implementation
- [x] Add `<h4>Risk Ranking</h4>` and `<table id="riskTable"><thead>…</thead><tbody></tbody></table>` to `frontend/index.html` inside `#dashboard-panel`
- [x] In `frontend/src/dashboard.js`:
  - [x] Add `fetchRiskRanking` to existing `import { ... } from "./api.js"` line
  - [x] Add `import { selectAndFly } from "./search.js"`
  - [x] Implement `export function renderRiskTable(items, viewer, tableEl)`
  - [x] Implement `export async function initRiskTable(viewer, limit = 10)`
- [x] Run tests — expect pass (Green) ✓ 25/25 dashboard tests

## Phase 4: Integration
- [x] Wire `initRiskTable(viewer)` in `frontend/src/main.js` after `viewer` is ready
- [x] Run lint: `npm --prefix frontend run lint` ✓ (Prettier clean)
- [x] Run full test suite: `npm --prefix frontend run test` ✓ 138/138 passed

## Phase 5: Verification
- [x] All 5 tangible outcomes from spec.md are checked
- [x] No hardcoded secrets or tokens
- [x] No Chart.js import needed for this feature (plain HTML table)
- [x] `selectAndFly` reused from `search.js`, not duplicated
- [x] `renderRiskTable` is exported and testable independently of `initRiskTable`
- [x] Update `roadmap.md` status: `spec-written` → `done`
