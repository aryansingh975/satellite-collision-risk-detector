# Checklist — Spec S2.5: API Contract + Mock Server

## Phase 1: Setup & Dependencies
- [x] Verify S2.4 (`specs/spec-S2.4-pydantic-schemas/`) is `done`
- [x] Create `docs/api/` directory
- [x] Create `frontend/mock/fixtures/` directory
- [x] Add `express` to `frontend/mock/package.json` (standalone deps, not the main frontend)

## Phase 2: Tests First (TDD)
- [x] Write `frontend/src/__tests__/mock.test.js` with all 8 tests listed in spec.md
- [x] Run `npm --prefix frontend run test` — expect failures (Red, because fixtures don't exist yet)

## Phase 3: Implementation

### 3a — OpenAPI YAML
- [x] Write `docs/api/openapi.yaml` covering all 9 endpoints (FR-1 table)
- [x] Define reusable `components/schemas` for every S2.4 type:
  `SatelliteOut`, `SatelliteDetail`, `PositionSample`, `PositionsResponse`,
  `ConjunctionOut`, `OrbitalRegionStats`, `RiskRankingItem`, `ErrorDetail`
- [x] Document all query params with types, defaults, and constraints
- [x] Document 404 `ErrorDetail` for `/{id}` and `/{catalog_no}` routes
- [x] N/A — `@redocly/cli` not installed; YAML is valid OpenAPI 3.1.0 (manually verified)

### 3b — Fixture files
- [x] Write `frontend/mock/fixtures/satellites.json` (≥5 satellites, all 4 regimes)
- [x] Write `frontend/mock/fixtures/satellite_detail.json` (catalog_no 25544, ISS)
- [x] Write `frontend/mock/fixtures/positions.json` (catalog_no 25544, ≥10 samples)
- [x] Write `frontend/mock/fixtures/positions_bulk.json` (≥2 satellites)
- [x] Write `frontend/mock/fixtures/conjunctions.json` (≥3 events, ≥1 with miss_km ≤ 5)
- [x] Write `frontend/mock/fixtures/conjunction_detail.json` (single ConjunctionOut)
- [x] Write `frontend/mock/fixtures/orbital_regions.json` (leo+meo+geo+heo == total)
- [x] Write `frontend/mock/fixtures/risk_ranking.json` (≥5 items, rank 1-based sequential)

### 3c — Mock server
- [x] Write `frontend/mock/server.js` (Express; FR-3 routing; CORS header; startup validation)
- [x] Write `frontend/mock/package.json` with `start` script: `node server.js`
- [x] Verify `node frontend/mock/server.js` starts cleanly
- [x] Smoke test: `curl http://localhost:8001/satellites` returns fixture array
- [x] Smoke test: `curl http://localhost:8001/stats/orbital-regions` returns object with `total`
- [x] Smoke test: `curl http://localhost:8001/health` returns `{"status":"ok"}`

## Phase 4: Integration
- [x] Run `npm --prefix frontend run test` — all 8 tests pass (Green) — 12/12 total
- [x] Confirm `VITE_API_BASE_URL=http://localhost:8001` convention is noted in server.js header
- [x] Run frontend lint: `npm --prefix frontend run lint` — zero errors
- [x] Confirm `docs/api/openapi.yaml` is committed and browsable (e.g. via Redoc or Swagger UI)

## Phase 5: Verification
- [x] All 5 tangible outcomes from spec.md checked off
- [x] No hardcoded secrets or tokens anywhere in fixtures or server
- [x] All 8 Vitest tests pass with no skips
- [x] N/A — `npx @redocly/cli lint` skipped; OpenAPI 3.1.0 YAML verified manually
- [x] Mock server exits non-zero on missing fixture (process.exit(1) on ENOENT)
- [x] Update roadmap.md status: `spec-written` → `done`
