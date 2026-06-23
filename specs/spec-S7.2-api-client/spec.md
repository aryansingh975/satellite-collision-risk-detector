# Spec S7.2 — API Client Layer

## Overview
Implements `frontend/src/api.js` — a thin, typed fetch wrapper layer that abstracts every REST
endpoint the frontend consumes.  The base URL is read from the `VITE_API_BASE_URL` environment
variable so a single environment-variable flip switches the frontend between the S2.5 mock server
(`http://localhost:8001`) and the live FastAPI backend (`http://localhost:8000`).  Every function
returns a plain JS value or array (never a `Response` object), handles 404 as a null/empty-array
return rather than an exception, and propagates network errors and 5xx status codes as thrown
`Error` objects so callers can display an error state.

## Dependencies
- S2.5 — API contract + mock server (frozen endpoint paths, query params, response schemas, mock
  fixtures, and the `VITE_API_BASE_URL` base-URL convention)

## Target Location
- `frontend/src/api.js` — all fetch wrappers

---

## Functional Requirements

### FR-1: Base URL configuration
- **What**: Read `import.meta.env.VITE_API_BASE_URL` (Vite convention) at module load time;
  fall back to `http://localhost:8000` if the variable is absent.
- **Inputs**: `VITE_API_BASE_URL` env var set in `frontend/.env` or shell before Vite starts.
- **Outputs**: A module-level constant `BASE_URL` used by all fetch calls; never hard-coded.
- **Edge cases**: Missing env var → silently use the default live URL (no error thrown).

### FR-2: Fetch wrappers — satellites
- **What**: Exported async functions covering every satellite-related endpoint.

  | Function | HTTP | Path | Parameters |
  |----------|------|------|-----------|
  | `fetchSatellites(opts)` | GET | `/satellites` | `opts.group` (string, opt), `opts.regime` (enum, opt), `opts.skip` (int, default 0), `opts.limit` (int, default 100) |
  | `fetchSatellite(catalogNo)` | GET | `/satellites/{catalog_no}` | — |
  | `fetchPositions(catalogNo, start, stop, step)` | GET | `/satellites/{catalog_no}/positions` | `start`/`stop` ISO-8601 strings, `step` int seconds (default 60) |
  | `fetchBulkPositions(catalogNos, start, stop, step)` | GET | `/positions` | `catalogNos` int[], joined as comma-sep `catalog_nos` param |

- **Inputs**: Function arguments as described; falsy / undefined optional params must be omitted
  from the query string (no `?group=undefined`).
- **Outputs**: Parsed JSON matching the S2.4 schema shapes (`SatelliteOut[]`, `SatelliteDetail`,
  `PositionsResponse`, `PositionsResponse[]`).
- **Edge cases**:
  - `fetchSatellite` → 404: return `null` (caller checks).
  - `fetchSatellites` → empty array: return `[]` (not an error).
  - `fetchPositions` → 404 (unknown catalog_no): return `null`.

### FR-3: Fetch wrappers — conjunctions
- **What**: Exported async functions for conjunction endpoints.

  | Function | HTTP | Path | Parameters |
  |----------|------|------|-----------|
  | `fetchConjunctions(opts)` | GET | `/conjunctions` | `opts.threshold` (float km, default 5.0), `opts.window` (int hours, default 72) |
  | `fetchConjunction(id)` | GET | `/conjunctions/{id}` | — |

- **Outputs**: `ConjunctionOut[]` or `ConjunctionOut`; empty array on no results.
- **Edge cases**: `fetchConjunction` → 404: return `null`.

### FR-4: Fetch wrappers — stats
- **What**: Exported async functions for stats endpoints.

  | Function | HTTP | Path | Parameters |
  |----------|------|------|-----------|
  | `fetchOrbitalRegions()` | GET | `/stats/orbital-regions` | — |
  | `fetchRiskRanking(limit)` | GET | `/stats/risk-ranking` | `limit` int (default 10) |

- **Outputs**: `OrbitalRegionStats` object; `RiskRankingItem[]`.

### FR-5: Error handling
- **What**: Consistent error semantics across all wrappers.
  - HTTP 404 → return `null` (detail endpoints) or `[]` (list endpoints).
  - HTTP 4xx (not 404) or 5xx → throw `Error` with message `"API error {status}: {url}"`.
  - Network failure (fetch rejects) → re-throw as-is so callers see a real `Error`.
- **Inputs**: The `Response` object from `fetch`.
- **Outputs**: Never returns a `Response`; always parses JSON before returning.
- **Edge cases**: Non-JSON error body → throw `Error("API error {status}: {url}")` without
  attempting to parse the body.

### FR-6: Health check
- **What**: `fetchHealth()` → `GET /health` → returns the parsed object (`{ status: "ok" }`).
- Used by the app startup to verify backend availability before rendering.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `import { fetchSatellites } from './api.js'` works in Vitest; calling it
  with a mocked `fetch` that returns the satellites fixture resolves to an array of objects.
- [ ] **Outcome 2**: `fetchSatellite('99999')` against a 404 mock resolves to `null` (not throws).
- [ ] **Outcome 3**: Any wrapper called against a 500 mock rejects with an `Error` containing the
  status code in the message.
- [ ] **Outcome 4**: `fetchSatellites({ group: 'active', regime: 'LEO' })` builds the URL
  `BASE_URL/satellites?group=active&regime=LEO` (no `skip` or `limit` appended when defaults
  are not overridden — or they are appended with correct default values; test must verify the
  query string is well-formed and contains no `undefined` literals).
- [ ] **Outcome 5**: `fetchBulkPositions([25544, 43013], start, stop)` sends
  `catalog_nos=25544,43013` as a single query param.
- [ ] **Outcome 6**: `BASE_URL` defaults to `http://localhost:8000` when
  `import.meta.env.VITE_API_BASE_URL` is not defined.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_fetchSatellites_success**: Mock `fetch` → satellites fixture; assert resolved value is
   an array with `catalog_no` and `regime` fields.
2. **test_fetchSatellites_empty**: Mock `fetch` → `[]`; assert resolved value is `[]`.
3. **test_fetchSatellite_found**: Mock `fetch` → satellite_detail fixture; assert
   `catalog_no === 25544`.
4. **test_fetchSatellite_not_found**: Mock `fetch` → HTTP 404; assert resolves to `null`.
5. **test_fetchSatellite_server_error**: Mock `fetch` → HTTP 500; assert rejects with an
   `Error` whose message contains `"500"`.
6. **test_fetchPositions_success**: Mock `fetch` → positions fixture; assert `positions` array
   has items with `lat`, `lon`, `alt_km`.
7. **test_fetchBulkPositions_query_param**: Spy on `fetch`; call `fetchBulkPositions([25544,
   43013], start, stop)`; assert the URL contains `catalog_nos=25544%2C43013` or
   `catalog_nos=25544,43013`.
8. **test_fetchConjunctions_success**: Mock → conjunctions fixture; assert ≥1 item with
   `miss_km ≤ 5`.
9. **test_fetchConjunction_not_found**: Mock → 404; assert resolves to `null`.
10. **test_fetchOrbitalRegions**: Mock → orbital_regions fixture; assert `leo + meo + geo + heo
    === total`.
11. **test_fetchRiskRanking**: Mock → risk_ranking fixture; assert array sorted by `miss_km`
    ascending.
12. **test_base_url_default**: Unset `import.meta.env.VITE_API_BASE_URL`; call any wrapper with
    a `fetch` spy; assert URL starts with `http://localhost:8000`.
13. **test_no_undefined_query_params**: Call `fetchSatellites({})` (no opts); spy on `fetch`;
    assert query string does not contain the literal `undefined`.

### Mocking Strategy
- **Mock `fetch`** globally in each test using `vi.stubGlobal('fetch', ...)` (Vitest) or
  `globalThis.fetch = vi.fn(...)`.
- Return `new Response(JSON.stringify(fixture), { status: 200, headers: { 'Content-Type':
  'application/json' } })` for success cases.
- Return `new Response('{"detail":"not found"}', { status: 404 })` for 404 cases.
- Import fixture data directly from `../../mock/fixtures/*.json` — no server process needed.
- Mock `import.meta.env` via Vitest's `vi.stubEnv` or by setting `import.meta.env.VITE_API_BASE_URL`
  in the test setup.

### Coverage Expectation
- Every exported function has at least one success test and one error/edge-case test.
- The `undefined`-in-query-string guard is explicitly tested.

---

## References
- `roadmap.md` — S7.2 row (Phase 7, Frontend Globe)
- `CLAUDE.md` — endpoint list, `VITE_API_BASE_URL` convention, no hardcoded tokens
- `specs/spec-S2.5-api-contract/spec.md` — frozen endpoint paths, params, response schemas
- `frontend/mock/server.js` — base URL convention comment (mock port 8001 vs live 8000)
- `frontend/mock/fixtures/` — fixture data for test assertions
