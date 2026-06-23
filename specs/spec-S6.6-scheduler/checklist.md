# Checklist — Spec S6.6: Scheduled Refresh

## Phase 1: Setup & Dependencies
- [x] Verify S3.2 (TLE cache) is `done` — `get_cached_group()` available in `ingestion.py`
- [x] Verify S5.5 (Risk scoring + persist) is `done` — `score_and_persist()` available in `conjunctions.py`
- [x] Create `backend/app/services/scheduler.py` (new file)
- [x] Confirm `apscheduler` is already in `pyproject.toml` (confirmed — added in S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_scheduler.py`
- [x] Write `test_scheduler_job_calls_ingest_then_screen` — expect failure (Red)
- [x] Write `test_scheduler_job_logs_counts` — expect failure (Red)
- [x] Write `test_scheduler_job_ingest_failure_isolated` — expect failure (Red)
- [x] Write `test_scheduler_job_screen_failure_isolated` — expect failure (Red)
- [x] Write `test_start_scheduler_registers_job` — expect failure (Red)
- [x] Write `test_lifespan_starts_and_stops_scheduler` — expect failure (Red)
- [x] Run tests — 5 fail (ModuleNotFoundError — scheduler.py missing), 1 pass (Red confirmed)

## Phase 3: Implementation
- [x] Implement `scheduler.py`:
  - [x] FR-1: `BackgroundScheduler` with `IntervalTrigger(hours=2)`, `replace_existing=True`
  - [x] FR-2: Job body — `asyncio.run(ingest_tle_group())` then `run_conjunction_screen()`; log counts
  - [x] FR-3: `try/except Exception` wrapping entire job body; log ERROR via `logger.exception`, swallow
  - [x] FR-4: `start_scheduler(settings, session_factory)` → creates fresh scheduler, starts, returns instance
- [x] Add `ingest_tle_group(db, cfg)` to `ingestion.py` — CSV parse + classify + persist pipeline
- [x] Add `run_conjunction_screen(db, cfg)` to `conjunctions.py` — full conjunction pipeline
- [x] Run tests — 6/6 pass (Green)
- [x] Refactor N/A — code is clean

## Phase 4: Integration
- [x] Wire into `backend/app/main.py` lifespan:
  - [x] `start_scheduler(settings, _db.SessionLocal)` in startup block
  - [x] `application.state.scheduler.shutdown(wait=False)` in shutdown block
- [x] Run `make local-lint` (Ruff, line length 100) — fixed pre-existing F401, all clean
- [x] Run full test suite: 298/298 passed
- [x] Confirm no existing tests broken

## Phase 5: Verification
- [x] All 5 tangible outcomes checked off
- [x] No hardcoded secrets/tokens
- [x] Loguru logging includes `job_id` in job context
- [x] Scheduler does not bypass S3.2's 2-hour file cache (`ingest_tle_group` calls `get_cached_group`)
- [x] `scheduler.shutdown(wait=False)` called in lifespan teardown (no hang on Ctrl-C)
- [x] Update `roadmap.md` status: `spec-written` → `done` (after implement + verify pass)
