# Checklist — Spec S7.2: API Client Layer

## Phase 1: Setup & Dependencies
- [x] Verify S2.5 is `done` (mock server + fixtures exist in `frontend/mock/`)
- [x] Locate (or create) `frontend/src/api.js`
- [x] Confirm Vitest is configured in `frontend/` (`npm --prefix frontend run test` works)
- [x] No new npm packages required — uses native `fetch` and `import.meta.env`

## Phase 2: Tests First (TDD)
- [x] Write `frontend/src/__tests__/api.test.js`
- [x] test_fetchSatellites_success — success path returns array with `catalog_no` + `regime`
- [x] test_fetchSatellites_empty — empty array response returns `[]`
- [x] test_fetchSatellite_found — detail found → `catalog_no === 25544`
- [x] test_fetchSatellite_not_found — 404 → `null`
- [x] test_fetchSatellite_server_error — 500 → throws `Error` with `"500"` in message
- [x] test_fetchPositions_success — positions array has `lat`, `lon`, `alt_km`
- [x] test_fetchBulkPositions_query_param — URL contains `catalog_nos=25544,43013` (comma-joined)
- [x] test_fetchConjunctions_success — at least one item with `miss_km ≤ 5`
- [x] test_fetchConjunction_not_found — 404 → `null`
- [x] test_fetchOrbitalRegions — `leo + meo + geo + heo === total`
- [x] test_fetchRiskRanking — array sorted by `miss_km` ascending
- [x] test_base_url_default — URL starts with `http://localhost:8000` when env var unset
- [x] test_no_undefined_query_params — query string never contains literal `undefined`
- [x] Run tests — expect failures (Red) ✓ confirmed

## Phase 3: Implementation
- [x] FR-1: Read `import.meta.env.VITE_API_BASE_URL`, fall back to `http://localhost:8000`
- [x] FR-2: Implement `fetchSatellites`, `fetchSatellite`, `fetchPositions`, `fetchBulkPositions`
- [x] FR-3: Implement `fetchConjunctions`, `fetchConjunction`
- [x] FR-4: Implement `fetchOrbitalRegions`, `fetchRiskRanking`
- [x] FR-5: Implement shared error handler — 404 → null/[], 4xx/5xx → throw, network error → rethrow
- [x] FR-6: Implement `fetchHealth`
- [x] Ensure no `undefined` literals ever appear in query strings
- [x] Run tests — expect pass (Green) ✓ 13/13 passing
- [x] Refactor if needed (shared `apiFetch` helper to reduce duplication)

## Phase 4: Integration
- [x] Import `api.js` in `frontend/src/main.js` to verify no import errors — N/A (api.js is standalone; imported by test suite successfully)
- [x] Run `npm --prefix frontend run lint` (Prettier / ESLint) — fix any issues ✓ clean
- [x] Run full frontend test suite: `npm --prefix frontend run test` ✓ 31/31 passing

## Phase 5: Verification
- [x] All 13 tangible outcomes checked against actual test assertions
- [x] No hardcoded base URLs or secrets in `api.js`
- [x] `VITE_API_BASE_URL` toggle confirmed in comment at top of `api.js`
- [x] Empty-array and null return values documented (one-line comments per function)
- [x] Update `roadmap.md` status: `spec-written` → `done`
