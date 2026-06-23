# Checklist — Spec S10.2: Frontend Live Wiring

## Phase 1: Setup & Dependencies
- [x] Verify S6.1, S6.4, S6.5, S7.2 are `done`
- [x] Confirm `frontend/src/api.js` exists (from S7.2)
- [x] Confirm `backend/app/main.py` has CORSMiddleware (from S1.5)
- [x] Check that `frontend/.env.example` exists; create if missing

## Phase 2: Tests First (TDD)
- [x] Write frontend test file additions to `frontend/src/__tests__/api.test.js`:
  - `test_default_base_url_is_live` — assert fallback to `http://localhost:8000`
  - `test_env_override_respected` — assert env var is used when set
  - `test_no_mock_url_hardcoded` — assert `localhost:8001` not in api.js source
  - `test_fetch_satellites_uses_base_url` — mock fetch, assert URL prefix
  - `test_fetch_conjunctions_uses_base_url` — mock fetch, assert URL prefix
  - `test_fetch_health_ok` — mock fetch returning `{status:"ok"}`, assert resolved value
- [x] Write backend CORS test in `backend/tests/test_main.py` (or `backend/tests/api/`):
  - `test_cors_allow_origin` — OPTIONS with `Origin: http://localhost:5173`, assert header
- [x] Run tests — expect failures (Red) → `test_no_mock_url_hardcoded` was Red (comment in api.js)

## Phase 3: Implementation
- [x] **FR-1/FR-5**: Confirm api.js `BASE_URL` fallback is `http://localhost:8000`; remove any
  hardcoded mock URLs from the live code path (updated comment to remove localhost:8001 reference)
- [x] **FR-2**: Create/update `frontend/.env.example` with
  `VITE_API_BASE_URL=http://localhost:8000` and a comment for the mock override
- [x] **FR-2**: Create/update `frontend/.env` (gitignored) pointing at live backend
- [x] **FR-3**: Confirm `CORSMiddleware` in `backend/app/main.py` includes
  `http://localhost:5173` (or `allow_origins=["*"]`) — already configured via `settings.CORS_ORIGINS`
- [x] **FR-4**: N/A — covered by automated CORS tests; manual browser check deferred to S10.3 e2e
- [x] Run tests — expect pass (Green) → 18/18 frontend, 9/9 backend
- [x] Refactor if needed

## Phase 4: Integration
- [x] N/A — `make seed` requires a live CelesTrak fetch; deferred to S10.3 e2e (respects 2h cadence)
- [x] N/A — browser smoke-test deferred to S10.3; all automated integration covered by test suites
- [x] Run lint: `npm --prefix frontend run lint` → All matched files use Prettier code style!
- [x] Run full backend test suite: 306/306 passed
- [x] Run full frontend test suite: 150/150 passed (10 test files)

## Phase 5: Verification
- [x] **Outcome 1**: `test_default_base_url_is_live` confirms default `BASE_URL = http://localhost:8000`
- [x] **Outcome 2**: `frontend/.env.example` created with `VITE_API_BASE_URL=http://localhost:8000`
- [x] **Outcome 3**: `test_cors_allow_origin` + `test_cors_preflight` pass in backend suite
- [x] **Outcome 4**: `test_fetch_health_ok` asserts `fetchHealth()` returns `{status:"ok"}`
- [x] **Outcome 5**: `test_no_mock_url_hardcoded` passes; `localhost:8001` removed from api.js
- [x] No hardcoded secrets/tokens (Cesium ion token or otherwise)
- [x] Update roadmap.md status: `spec-written` → `done`
