# Checklist — Spec S6.2: Positions Endpoint

## Phase 1: Setup & Dependencies
- [x] Verify S4.2 (single-sat propagation) is `done`
- [x] Verify S4.4 (TEME→geodetic conversion) is `done`
- [x] Confirm `PositionSample` and `PositionsResponse` schemas exist in `backend/app/models/schemas.py` (added in S2.4)
- [x] Confirm `teme_to_geodetic` is importable from `backend/app/services/propagation.py`
- [x] No new pyproject.toml dependencies needed (all libs already present)

## Phase 2: Tests First (TDD)
- [x] Create test file `backend/tests/api/test_positions.py`
- [x] Write `test_positions_iss_basic` — 200, correct catalog_no, ≥1 position samples
- [x] Write `test_positions_step_respected` — step=300 yields ≤13 samples over 1h window
- [x] Write `test_positions_unknown_satellite` — 404
- [x] Write `test_positions_start_not_before_stop` — 422 with "start must be before stop"
- [x] Write `test_positions_window_too_large` — 422 for 31-day window
- [x] Write `test_positions_step_out_of_range` — 422 for step=0 and step=7200
- [x] Write `test_positions_decayed_satellite` — mock `teme_to_geodetic` → returns `[]`; expect 200 with empty positions
- [x] Write `test_positions_response_schema` — response parses as `PositionsResponse`
- [x] Run tests — expect **Red** (route doesn't exist yet) — 11/11 FAILED ✓

## Phase 3: Implementation
- [x] Add `from datetime import timedelta` and needed imports to `backend/app/api/satellites.py`
- [x] Import `teme_to_geodetic` from `app.services.propagation`
- [x] Import `PositionsResponse`, `PositionSample` from `app.models.schemas`
- [x] Implement `get_satellite_positions` handler:
  - [x] FR-1: Query DB for satellite; 404 if missing
  - [x] FR-1: Validate `start < stop`; raise HTTP 422 if not
  - [x] FR-1: Validate window ≤ 30 days; raise HTTP 422 if exceeded
  - [x] FR-2: Build time grid (`start` to `stop` step `step` seconds, inclusive)
  - [x] FR-3: Call `teme_to_geodetic(sat.line1, sat.line2, times)`; wrap in try/except for ValueError → HTTP 500
  - [x] FR-3: Map returned dicts to `PositionSample` objects
  - [x] FR-4: Bind `request_id` via `logger.contextualize`; emit DEBUG log
  - [x] Return `PositionsResponse(catalog_no=..., name=..., positions=[...])`
- [x] Run tests — expect **Green** — 11/11 PASSED ✓
- [x] Refactor if needed (no behavioural changes)

## Phase 4: Integration
- [x] Confirm the new route is reachable via the existing `router` in `satellites.py` (no extra include needed — router already mounted at `/satellites` in `main.py`)
- [x] Run `make local-lint` (ruff check + format) — fixed formatting; pre-existing F401 in test_propagation_bulk.py not introduced by S6.2
- [x] Run full test suite: `.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short` — 261/261 passed ✓
- [x] N/A — spot-check with live server (covered by tests)

## Phase 5: Verification
- [x] All 6 tangible outcomes from spec.md checked off (covered by 11 passing tests)
- [x] No hardcoded secrets or tokens
- [x] Logging includes `request_id` in every handler invocation
- [x] Geodetic conversion is only done inside `teme_to_geodetic` (TEME never leaks past the display boundary)
- [x] Step `Query` constraint (`ge=1, le=3600`) enforced by FastAPI — no manual validation needed for range
- [x] Update `roadmap.md` status: `spec-written` → `done`
