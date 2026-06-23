# Checklist — Spec S6.4: Conjunctions Endpoints

## Phase 1: Setup & Dependencies
- [x] Verify S5.5 (risk scoring + persist) is `done` and its tests pass
- [x] Verify S2.4 (Pydantic schemas) is `done` — `ConjunctionOut` is already defined
- [x] Confirm `backend/app/api/conjunctions.py` stub is in place (router mounted in main.py)
- [x] No new packages needed — `sqlalchemy`, `fastapi`, `pydantic` already declared

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/api/test_conjunctions.py`
- [x] Add shared fixtures (satellite + conjunction factory helpers) to `conftest.py` or locally
- [x] Write `test_list_conjunctions_empty` — expect `[]` (Red)
- [x] Write `test_list_conjunctions_returns_rows` — sat names populated (Red)
- [x] Write `test_list_conjunctions_ordered_by_miss_km` — ascending order (Red)
- [x] Write `test_list_conjunctions_threshold_filter` — `?threshold=5` filters by miss_km (Red)
- [x] Write `test_list_conjunctions_window_filter` — `?window=1` excludes far-future TCA; `?window=0` disables filter (Red)
- [x] Write `test_list_conjunctions_limit` — `?limit=3` caps result (Red)
- [x] Write `test_get_conjunction_by_id` — 200 + correct body (Red)
- [x] Write `test_get_conjunction_not_found` — 404 (Red)
- [x] Run tests — expect ALL failures (Red) — 8 failed, 1 passed (empty-list stub passed)

## Phase 3: Implementation
- [x] Implement FR-1: `GET /conjunctions` with `threshold`, `window`, `limit` params
  - Join `Satellite` twice (aliased) for `sat_a_name` / `sat_b_name`
  - Default `threshold` from `settings.RISK_THRESHOLD_KM`
  - Default `window` from `settings.SCREEN_WINDOW_HOURS`; 0 → skip window filter
  - Clamp `limit` to max 500
  - Order by `miss_km` ascending
  - Return `list[ConjunctionOut]`; empty list on no rows
- [x] Implement FR-2: `GET /conjunctions/{pair_id}`
  - Same satellite-name join via ORM relationships
  - 404 with `{"detail": "Conjunction not found"}` on unknown id
- [x] Add Loguru `logger.debug(…)` with `request_id` context on each handler entry
- [x] Run tests — expect ALL pass (Green) — 9/9 passed

## Phase 4: Integration
- [x] Confirm router is already mounted at `/conjunctions` in `backend/app/main.py`
- [x] N/A — OpenAPI docs verified via test client (router correctly included)
- [x] Run lint: `make local-lint` — ruff check + format clean (100-char line length)
- [x] Run full test suite — 280/280 passed

## Phase 5: Verification
- [x] All 9 tests pass (Outcomes 1–7 covered)
- [x] `[]` returned (not error) when DB is empty — Outcome 1
- [x] Results ordered by `miss_km` ascending — Outcome 2 & 3
- [x] `threshold` filter works correctly — Outcome 3
- [x] `window` filter works correctly — Outcome 4
- [x] 404 returned for unknown id — Outcome 6
- [x] `sat_a_name` and `sat_b_name` non-empty on all rows — Outcome 7
- [x] No hardcoded secrets or tokens
- [x] `request_id` included in log context via `logger.contextualize`
- [x] Update roadmap.md status: `spec-written` → `done`
