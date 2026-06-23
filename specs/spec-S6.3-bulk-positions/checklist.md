# Checklist — Spec S6.3: Bulk Positions / CZML

## Phase 1: Setup & Dependencies
- [x] Verify S4.3 (`propagate_array`, `build_satrec_array`) is `done`
- [x] Verify S4.4 (`teme_to_geodetic`) is `done`
- [x] Confirm `backend/app/api/satellites.py` and `backend/app/models/schemas.py` are the target files
- [x] No new packages required — `sgp4`, `skyfield`, `numpy` already declared in `pyproject.toml`

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/api/test_bulk_positions.py`
- [x] Write `test_bulk_positions_returns_two_satellites` — happy path, two known satellites
- [x] Write `test_bulk_positions_unknown_id_skipped` — partial match, unknown ID silently skipped
- [x] Write `test_bulk_positions_all_unknown_returns_empty` — `{"satellites": []}` not 404
- [x] Write `test_bulk_positions_start_gte_stop_422` — time window validation
- [x] Write `test_bulk_positions_empty_ids_422` — missing `ids` param → 422
- [x] Write `test_bulk_positions_too_many_ids_422` — >500 IDs → 422
- [x] Write `test_bulk_positions_window_too_large_422` — >30 days → 422
- [x] Write `test_bulk_positions_uses_propagate_array` — assert vectorised call used
- [x] Write `test_bulk_positions_error_satellite_excluded` — propagation failure excludes one sat
- [x] Write `test_bulk_positions_response_schema` — BulkPositionsResponse parse succeeds
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Add `BulkPositionsResponse` schema to `backend/app/models/schemas.py`
- [x] Add `GET /positions` route to `backend/app/api/satellites.py`:
  - Parse and validate `ids` (comma-separated, 1–500 entries)
  - Validate `start < stop` and window ≤ 30 days
  - Fetch DB rows for matching catalog numbers
  - Build time grid
  - Call `build_satrec_array` + `propagate_array` (vectorized, once for all sats)
  - Identify satellites with any non-zero error code; log + exclude them
  - Call `teme_to_geodetic` per surviving satellite
  - Assemble and return `BulkPositionsResponse`
- [x] Import `propagate_array`, `build_satrec_array` from `app.services.propagation` in the router
- [x] Run tests — expect pass (Green) — 10/10 passed
- [x] N/A — no refactor needed; code is clean

## Phase 4: Integration
- [x] Confirm the `/positions` route is reachable via the existing `router` included in `main.py`; placed before `/{sat_id}` to avoid routing conflict
- [x] Run lint — `ruff check` passes on all three modified files
- [x] Run full test suite — 271/271 passed
- [x] N/A — no seeded DB available locally; endpoint verified via unit tests with ISS TLE fixtures

## Phase 5: Verification
- [x] All 7 tangible outcomes in spec.md confirmed (10 tests covering all outcomes pass)
- [x] `BulkPositionsResponse` present in `schemas.py` and importable — confirmed by test_bulk_positions_response_schema
- [x] `propagate_array` called exactly once per bulk request — confirmed by test_bulk_positions_uses_propagate_array
- [x] No hardcoded secrets or tokens
- [x] All log statements include `request_id` via `logger.contextualize(request_id=request_id)`
- [x] Geodetic conversion only at the display boundary — `teme_to_geodetic` called per sat, TEME not exposed in response
- [x] Update `roadmap.md` status for S6.3: `spec-written` → `done`
