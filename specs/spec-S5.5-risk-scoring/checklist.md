# Checklist — Spec S5.5: Risk Scoring + Persist

## Phase 1: Setup & Dependencies
- [x] Verify S5.4 (TCA refinement) is `done` and tests pass
- [x] Verify S2.3 (Conjunction ORM model) is `done`
- [x] Locate `backend/app/services/conjunctions.py` (add `score_and_persist` here)
- [x] Confirm `backend/app/db/models.py` Conjunction model has all needed columns
      (`id`, `sat_a`, `sat_b`, `tca`, `miss_km`, `rel_vel_kms`, `window_start`, `computed_at`)
- [x] No new packages needed — SQLAlchemy, loguru already declared in `pyproject.toml`

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/services/test_risk_scoring.py`
- [x] Write `conftest` fixtures: in-memory SQLite engine, two Satellite rows,
      `TCARefinement` factory helper
- [x] Write `test_filter_by_threshold` — only events with `miss_km ≤ threshold` survive
- [x] Write `test_filter_all_none` — list of Nones returns `[]`
- [x] Write `test_filter_zero_threshold` — threshold 0.0 → nothing passes
- [x] Write `test_rank_by_miss_then_vel` — ascending miss, descending rel_vel tie-break
- [x] Write `test_persist_idempotent` — calling twice same window = same count, not doubled
- [x] Write `test_persist_empty_clears_old` — all-None input clears old rows for that window
- [x] Write `test_persist_tca_naive` — timezone-aware TCA stored as naive UTC in DB
- [x] Write `test_persist_catalog_order` — sat_a < sat_b canonical ordering enforced
- [x] Write `test_score_and_persist_full_pipeline` — end-to-end correct count, order, catalog nos
- [x] Run tests — expect failures (Red) — confirmed ImportError

## Phase 3: Implementation
- [x] Implement FR-1: filter `None` entries + `miss_km > threshold` entries
- [x] Run `test_filter_by_threshold`, `test_filter_all_none` — Green
- [x] Implement FR-2: sort ascending `miss_km`, tie-break descending `rel_vel_kms`
- [x] Run `test_rank_by_miss_then_vel` — Green
- [x] Implement FR-3: index mapping `sat_a_idx` / `sat_b_idx` → catalog numbers, enforce
      `catalog_no_a < catalog_no_b`
- [x] Run `test_persist_catalog_order` — Green
- [x] Implement FR-4: idempotent delete-then-insert within a transaction; strip tzinfo from `tca`
      and `window_start_dt` before storing; set `computed_at = datetime.utcnow()`
- [x] Run `test_persist_idempotent`, `test_persist_empty_clears_old`, `test_persist_tca_naive`
      — Green
- [x] Implement FR-5: `score_and_persist(...)` composing FR-1 → FR-2 → FR-3 → FR-4
- [x] Run `test_score_and_persist_full_pipeline` — Green
- [x] Run full test file — 9/9 Green
- [x] Refactor if needed — loguru logging added; no further refactor needed

## Phase 4: Integration
- [x] Update module docstring in `conjunctions.py` to mention S5.5
- [x] Verify `score_and_persist` is importable from `app.services.conjunctions`
- [x] Wire into `backend/scripts/seed.py` (S10.1) and `backend/app/services/scheduler.py`
      (S6.6) — N/A at this stage; both specs are `pending`; caller wiring deferred
- [x] Run lint: ruff check passed (0 errors) on conjunctions.py and test_risk_scoring.py
- [x] Run full backend test suite: 234/234 passed

## Phase 5: Verification
- [x] All 9 tests in `test_risk_scoring.py` pass (8 spec-required + 1 extra edge-case)
- [x] All 6 tangible outcomes verified via tests
- [x] No hardcoded `RISK_THRESHOLD_KM` value — passed as `risk_threshold_km` parameter
- [x] No collision-probability language anywhere in code or docstrings
- [x] Conjunction math stays in TEME; no geodetic conversion in this module
- [x] Loguru logging: logs filtered count and persisted count per call
- [x] Update roadmap.md status column: `spec-written` → `done`
