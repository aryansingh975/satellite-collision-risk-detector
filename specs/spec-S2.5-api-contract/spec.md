# Spec S2.5 — API Contract + Mock Server

## Overview
Freezes every REST endpoint's path, query parameters, and response schema into a machine-readable
`docs/api/openapi.yaml` and ships a lightweight mock server under `frontend/mock/` so that Student 2
can build the entire frontend in parallel with Student 1's backend implementation.  The mock server
returns schema-valid sample data for every endpoint — no backend process required to develop or
test the frontend.  This spec must be completed (and the contract frozen) before S7.2 (API client
layer) begins.

## Dependencies
- S2.4 — All Pydantic schemas (`SatelliteOut`, `SatelliteDetail`, `PositionSample`,
  `PositionsResponse`, `ConjunctionOut`, `OrbitalRegionStats`, `RiskRankingItem`, `ErrorDetail`)

## Target Location
- `docs/api/openapi.yaml` — frozen OpenAPI 3.1 specification
- `frontend/mock/fixtures/` — JSON fixture files (one per endpoint group)
- `frontend/mock/server.js` — Node script serving fixtures at the same paths as the live API
- `frontend/mock/package.json` — minimal deps (`express`) so mock runs standalone

---

## Functional Requirements

### FR-1: OpenAPI specification
- **What**: A valid OpenAPI 3.1 YAML document that precisely describes every API endpoint the
  frontend will consume.
- **Inputs**: The frozen endpoint list (below) and the S2.4 Pydantic schema shapes.
- **Outputs**: `docs/api/openapi.yaml` that passes `openapi-spec-validator` / `spectral` lint
  with zero errors.
- **Endpoints to document** (all read-only `GET`):

  | Path | Query params | Response schema |
  |------|-------------|-----------------|
  | `GET /health` | — | `{"status": "ok"}` |
  | `GET /satellites` | `group` (string, opt), `regime` (enum LEO/MEO/GEO/HEO, opt), `skip` (int≥0, default 0), `limit` (int 1–1000, default 100) | `SatelliteOut[]` |
  | `GET /satellites/{catalog_no}` | — | `SatelliteDetail` or 404 `ErrorDetail` |
  | `GET /satellites/{catalog_no}/positions` | `start` (ISO-8601 datetime, required), `stop` (ISO-8601 datetime, required), `step` (int seconds, default 60) | `PositionsResponse` |
  | `GET /positions` | `catalog_nos` (comma-sep ints, required), `start`, `stop`, `step` | `PositionsResponse[]` |
  | `GET /conjunctions` | `threshold` (float km, default 5.0), `window` (int hours, default 72) | `ConjunctionOut[]` |
  | `GET /conjunctions/{id}` | — | `ConjunctionOut` or 404 `ErrorDetail` |
  | `GET /stats/orbital-regions` | — | `OrbitalRegionStats` |
  | `GET /stats/risk-ranking` | `limit` (int, default 10) | `RiskRankingItem[]` |

- **Edge cases**: 404 responses documented with `ErrorDetail`; empty arrays (`[]`) are valid
  responses for list endpoints (not errors).

### FR-2: JSON fixture files
- **What**: Static JSON files under `frontend/mock/fixtures/` containing realistic sample data
  that validates against the schemas from S2.4.
- **Outputs**:
  - `satellites.json` — array of ≥5 `SatelliteOut` objects across all four regimes
  - `satellite_detail.json` — single `SatelliteDetail` for catalog_no 25544 (ISS)
  - `positions.json` — `PositionsResponse` for catalog_no 25544, ≥10 position samples
  - `positions_bulk.json` — array of `PositionsResponse` for ≥2 satellites
  - `conjunctions.json` — array of ≥3 `ConjunctionOut` objects, at least one with `miss_km ≤ 5`
  - `conjunction_detail.json` — single `ConjunctionOut`
  - `orbital_regions.json` — `OrbitalRegionStats` where `leo+meo+geo+heo == total`
  - `risk_ranking.json` — array of ≥5 `RiskRankingItem` objects, `rank` values 1-based sequential
- **Edge cases**: Malformed fixtures (total mismatch in `OrbitalRegionStats`, non-sequential ranks)
  must be caught by Vitest schema-validation tests.

### FR-3: Mock Express server
- **What**: `frontend/mock/server.js` — a minimal Express server that:
  1. Reads fixture JSON files at startup
  2. Serves them at the exact same URL paths as the live API
  3. Adds `Access-Control-Allow-Origin: *` so the Vite dev server can call it
  4. Logs each request to stdout
- **Inputs**: Node 18+; fixtures must exist at `frontend/mock/fixtures/`
- **Outputs**: Server binds to `MOCK_PORT` env var (default `8001`); responds with
  `Content-Type: application/json` and HTTP 200 for known routes, 404 with
  `{"detail": "not found"}` for unknown routes.
- **Path routing**: Dynamic path params (`catalog_no`, `id`) are matched from the fixture arrays
  (return first matching element, or the single-object fixture for detail endpoints).
- **Edge cases**: Missing fixture file → log error + exit with non-zero code on startup (fail fast).

### FR-4: API client base-URL toggle
- **What**: Document (in `docs/api/openapi.yaml` servers block and in a comment in
  `frontend/mock/server.js`) that `VITE_API_BASE_URL=http://localhost:8001` points to the mock
  and `VITE_API_BASE_URL=http://localhost:8000` points to the live backend.  The toggle is
  implemented in S7.2 (api.js) — S2.5 only specifies the contract.
- **Edge cases**: No code in S2.5 reads `VITE_API_BASE_URL`; just the documented convention.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `docs/api/openapi.yaml` exists and all nine endpoints are documented with
  correct paths, parameters, and `$ref` schemas.
- [ ] **Outcome 2**: Every fixture file in `frontend/mock/fixtures/` parses as valid JSON and
  each object passes the corresponding S2.4 schema shape (validated by Vitest tests).
- [ ] **Outcome 3**: `node frontend/mock/server.js` starts without error, `curl
  http://localhost:8001/satellites` returns the satellites fixture as JSON, and
  `curl http://localhost:8001/stats/orbital-regions` returns a response where
  `leo+meo+geo+heo === total`.
- [ ] **Outcome 4**: `OrbitalRegionStats` fixture satisfies `leo+meo+geo+heo == total` (model
  validator rule from S2.4 enforced in the test).
- [ ] **Outcome 5**: Risk ranking fixture has `rank` values starting at 1, incrementing by 1
  (no gaps, no duplicates).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

All tests live in `frontend/src/__tests__/mock.test.js` (Vitest + jsdom, or plain Vitest).
Import fixture JSON directly — no server process needed.

1. **test_satellites_fixture_schema**: Load `satellites.json`; assert it is a non-empty array;
   for each item assert required fields (`catalog_no`, `name`, `epoch`, `updated_at`) are present
   and `regime` is one of `LEO | MEO | GEO | HEO | null`.
2. **test_satellite_detail_fixture_schema**: Load `satellite_detail.json`; assert it has `line1`,
   `line2`, and all `SatelliteOut` fields; `catalog_no` must equal 25544.
3. **test_positions_fixture_schema**: Load `positions.json`; assert `catalog_no === 25544`;
   assert `positions` array has ≥10 items; each item has `time` (ISO string), `lat` in [-90, 90],
   `lon` in [-180, 180], `alt_km > 0`.
4. **test_conjunctions_fixture_schema**: Load `conjunctions.json`; assert ≥3 items; each has
   `sat_a`, `sat_b`, `miss_km > 0`, `rel_vel_kms > 0`; at least one item has `miss_km ≤ 5`.
5. **test_orbital_regions_total**: Load `orbital_regions.json`; assert
   `leo + meo + geo + heo === total`.
6. **test_risk_ranking_sequential**: Load `risk_ranking.json`; assert `rank` values are
   `[1, 2, 3, ...]` with no gaps; assert `miss_km` is non-decreasing (sorted ascending).
7. **test_positions_bulk_fixture_schema**: Load `positions_bulk.json`; assert it is an array of
   ≥2 items; each item matches the `PositionsResponse` shape.
8. **test_all_regimes_represented**: Load `satellites.json`; assert at least one satellite per
   regime: LEO, MEO, GEO, HEO.

### Mocking Strategy
- **No HTTP in these tests** — import fixture JSON directly via `import` statements or `fs.readFileSync`.
  Vitest resolves JSON imports natively.
- **No server process** — the Express server (`server.js`) is tested manually / in E2E (S10.3).
  Unit tests validate the fixture data only.
- **OpenAPI lint** — validated via `npx @redocly/cli lint docs/api/openapi.yaml` in CI (documented
  in the checklist; not a Vitest test).

### Coverage Expectation
- Every fixture file has at least one dedicated test asserting schema-shape and data integrity.
- The `OrbitalRegionStats` total invariant has an explicit test.
- The risk-ranking `rank` sequence has an explicit test.

---

## References
- `roadmap.md` — S2.5 row (Phase 2, Data Layer)
- `CLAUDE.md` — API endpoint list, schema field names, 5 km risk threshold, TEME/geodetic boundary
- `backend/app/models/schemas.py` (S2.4) — authoritative field definitions
- CelesTrak rate-limit policy (one-download-per-update / 2h cadence) — not enforced by the mock
  but noted in the OpenAPI description fields
