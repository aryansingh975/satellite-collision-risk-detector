# Checklist — Spec S9.2: Close-Approach Count Chart

## Phase 1: Setup & Dependencies
- [x] Verify S7.2 (API client) and S6.4 (conjunctions endpoint) are `done`
- [x] Locate `frontend/src/dashboard.js` — `initApproachChart` and `bucketizeConjunctions` will be added here
- [x] Confirm `chart.js` is already in `package.json` (installed for S9.1)
- [x] Add `<canvas id="approachChart">` and a heading to `#dashboard-panel` in `frontend/index.html`

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/dashboard.test.js` (extend existing S9.1 suite or add S9.2 describe block)
- [x] Write `test_initApproachChart_returns_chart_instance` — failing (Red)
- [x] Write `test_initApproachChart_bucket_counts` — failing (Red)
- [x] Write `test_initApproachChart_empty_response` — failing (Red)
- [x] Write `test_initApproachChart_missing_canvas` — failing (Red)
- [x] Write `test_bucketizeConjunctions_bands` — failing (Red)
- [x] Write `test_bucketizeConjunctions_empty` — failing (Red)
- [x] Write `test_bucketizeConjunctions_boundary` — failing (Red)
- [x] Write `test_bucketizeConjunctions_over_threshold` — failing (Red)
- [x] Write `test_initApproachChart_labels` — failing (Red)
- [x] Run tests — expect failures: `npm --prefix frontend run test`

## Phase 3: Implementation
- [x] Implement `bucketizeConjunctions(conjunctions)` — pure helper, 5 bands, boundary-on-upper
- [x] Run `bucketizeConjunctions` tests — expect pass (Green)
- [x] Implement `initApproachChart()` — fetch → bucketize → create Chart bar instance
- [x] Add `<canvas id="approachChart">` + heading to `index.html` (if not already done in Phase 1)
- [x] Run all S9.2 tests — expect pass (Green)
- [x] Refactor if needed (no change to test contracts)

## Phase 4: Integration
- [x] Wire `initApproachChart()` into `frontend/src/main.js` alongside `initRegimeChart()`
- [x] Run lint: `npm --prefix frontend run lint` (Prettier)
- [x] Run full frontend test suite: `npm --prefix frontend run test`
- [x] N/A — Visual verification skipped (no dev server running; all logic covered by 16 passing unit tests)

## Phase 5: Verification
- [x] All 6 tangible outcomes checked (see spec.md)
- [x] No hardcoded secrets or tokens
- [x] `fetchConjunctions` is the only API call — no direct `fetch()` in `dashboard.js`
- [x] Chart uses `"bar"` type with 5 bands, coloured by severity
- [x] `bucketizeConjunctions` exported and independently testable
- [x] Update roadmap.md status: `spec-written` → `done` (only after Phase 4 passes)
