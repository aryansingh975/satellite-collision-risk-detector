# Spec S10.2 — Frontend Live Wiring

## Overview
Switch the frontend API client from the S2.5 mock server to the live FastAPI backend. This involves
setting `VITE_API_BASE_URL` to point at the running backend (`http://localhost:8000`), confirming
that FastAPI's CORS middleware permits the Vite dev-server origin, and verifying that each api.js
wrapper returns real data — not mock fixtures — from the seeded SQLite database.

## Dependencies
- S6.1 — Satellites list + detail endpoints live
- S6.4 — Conjunctions endpoint live
- S6.5 — Stats endpoints live
- S7.2 — API client layer (api.js) implemented

## Target Location
`frontend/src/api.js`, `frontend/.env` (and `frontend/.env.example`)

---

## Functional Requirements

### FR-1: Live base URL default
- **What**: `api.js` must default to the live backend URL (`http://localhost:8000`) when
  `VITE_API_BASE_URL` is absent. The mock server URL (`http://localhost:8001`) must not appear
  anywhere in the production code path.
- **Inputs**: Vite build environment (presence or absence of `VITE_API_BASE_URL`)
- **Outputs**: All fetch calls resolve against `http://localhost:8000` by default
- **Edge cases**: If `VITE_API_BASE_URL` is set to the mock URL, calls go there; the default is
  always live

### FR-2: `frontend/.env` documents the live URL
- **What**: A `frontend/.env` file (gitignored) and a `frontend/.env.example` (committed) both
  define `VITE_API_BASE_URL`. The `.env.example` shows the live value (`http://localhost:8000`)
  with a comment for the mock override.
- **Inputs**: `frontend/.env.example`
- **Outputs**: Developer onboarding requires no manual env setup for the happy path
- **Edge cases**: If `.env` is absent the fallback in api.js covers the live URL

### FR-3: CORS allows the Vite dev-server origin
- **What**: The FastAPI `CORSMiddleware` configured in S1.5 must permit requests from
  `http://localhost:5173` (Vite default) and respond with the correct
  `Access-Control-Allow-Origin` header.
- **Inputs**: Preflight `OPTIONS` or simple cross-origin request from the frontend
- **Outputs**: Response carries `Access-Control-Allow-Origin: http://localhost:5173` (or `*`)
- **Edge cases**: Both `GET` and `OPTIONS` must succeed; 403 / missing header means CORS is broken

### FR-4: `/health` smoke check passes
- **What**: `fetchHealth()` against the live backend returns `{"status": "ok"}`.
- **Inputs**: Live backend running (seeded or empty DB)
- **Outputs**: `{ status: "ok" }` JSON object
- **Edge cases**: Network failure throws; 5xx throws `"API error {status}: …"`

### FR-5: All api.js wrappers route correctly to the live backend
- **What**: Every exported function in api.js (`fetchSatellites`, `fetchSatellite`,
  `fetchPositions`, `fetchBulkPositions`, `fetchConjunctions`, `fetchConjunction`,
  `fetchOrbitalRegions`, `fetchRiskRanking`) must construct URLs against `BASE_URL` — no
  hardcoded localhost:8001 paths remain.
- **Inputs**: Live backend, seeded DB (post `make seed`)
- **Outputs**: Each call returns schema-valid data or the documented fallback (`null` / `[]`)
- **Edge cases**: Empty DB → list endpoints return `[]`; unknown ID → `null`

---

## Tangible Outcomes

- [ ] **Outcome 1**: `import.meta.env.VITE_API_BASE_URL` is absent → `BASE_URL` equals
  `http://localhost:8000` (verified in unit test with env mock)
- [ ] **Outcome 2**: `frontend/.env.example` exists and contains `VITE_API_BASE_URL=http://localhost:8000`
- [ ] **Outcome 3**: FastAPI CORS OPTIONS preflight to `http://localhost:5173` returns 200 with the
  correct allow-origin header (verified via backend test or manual `curl`)
- [ ] **Outcome 4**: `fetchHealth()` against the running backend returns `{ status: "ok" }`
- [ ] **Outcome 5**: No occurrence of `localhost:8001` in `frontend/src/api.js` (the mock URL is
  purely a dev override, never a default)

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_default_base_url_is_live**: Mock `import.meta.env.VITE_API_BASE_URL` as `undefined`;
   assert `BASE_URL` resolves to `"http://localhost:8000"`.
2. **test_env_override_respected**: Set `import.meta.env.VITE_API_BASE_URL` to
   `"http://localhost:8001"`; assert `BASE_URL` equals that value.
3. **test_no_mock_url_hardcoded**: Read the source of api.js; assert the string
   `"localhost:8001"` does not appear.
4. **test_fetch_satellites_uses_base_url**: Mock `fetch`; call `fetchSatellites()`; assert the
   captured URL starts with `BASE_URL`.
5. **test_fetch_conjunctions_uses_base_url**: Same pattern for `fetchConjunctions()`.
6. **test_fetch_health_ok**: Mock `fetch` to return `{ status: "ok" }`; assert
   `fetchHealth()` resolves to that object.
7. **test_cors_allow_origin** *(backend, pytest)*: Use FastAPI `TestClient`, send an OPTIONS
   request with `Origin: http://localhost:5173`; assert response contains
   `Access-Control-Allow-Origin`.

### Mocking Strategy
- Frontend unit tests: mock `fetch` via `vi.stubGlobal('fetch', vi.fn())` in Vitest
- `import.meta.env` mocking: use `vi.stubEnv` or override in `beforeEach` / restore in
  `afterEach`
- Backend CORS test: FastAPI `TestClient` (no external HTTP needed)
- Never hit the live API or live backend in automated tests

### Coverage Expectation
- Every exported api.js function has at least one test asserting the URL shape
- CORS check covered in backend tests
- Default-URL fallback explicitly asserted

---

## References
- roadmap.md S10.2 row; CLAUDE.md (no secrets hardcoded, CORS in S1.5)
- S7.2 spec (api.js implementation)
- S1.5 spec (CORSMiddleware configuration)
