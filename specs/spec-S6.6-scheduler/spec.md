# Spec S6.6 — Scheduled Refresh

## Overview
An APScheduler background job runs every 2 hours inside the FastAPI lifespan to re-ingest
TLEs from CelesTrak (respecting the 2-hour cadence enforced by S3.2's cache), re-run the full
conjunction screen (S5.5), and persist updated results to SQLite. Job failures must be isolated
so that a network timeout or screening error does not crash the running FastAPI app.

## Dependencies
- S3.2 — TLE cache (2-hour cadence): provides `ingest_tle_group()` respecting the cache;
  the scheduler calls this — never bypasses it.
- S5.5 — Risk scoring + persist: provides `run_conjunction_screen()` writing to the
  Conjunction table; the scheduler calls this after a successful ingest.

## Target Location
`backend/app/services/scheduler.py`
Wired into `backend/app/main.py` lifespan (start on startup, shutdown cleanly).

---

## Functional Requirements

### FR-1: APScheduler job registered at 2-hour interval
- **What**: An `AsyncIOScheduler` (or `BackgroundScheduler`) is configured with a single job
  that triggers at a fixed 2-hour interval (`IntervalTrigger(hours=2)`).
- **Inputs**: A SQLAlchemy `SessionLocal` factory and the app `Settings` object (from `config.py`).
- **Outputs**: Side effect — updated Satellite rows + new/updated Conjunction rows in SQLite.
- **Edge cases**: Job must not be registered twice if the lifespan runs more than once (e.g.
  hot-reload); guard with `scheduler.get_jobs()` check or `replace_existing=True`.

### FR-2: Job body — ingest then screen
- **What**: Each execution calls S3.2's ingest (which honours the 2-hour file cache — a
  no-op if the file is fresh) followed by S5.5's screening function.
- **Inputs**: DB session obtained inside the job via `SessionLocal()`.
- **Outputs**: Persisted satellites + conjunctions. Loguru log lines with job timing and
  counts (satellites upserted, conjunctions persisted).
- **Edge cases**: If ingest returns 0 satellites (empty response or stale-cache fallback), the
  screen must still run against whatever is in the DB — do not skip the screen step entirely.

### FR-3: Failure isolation
- **What**: Any exception raised inside the job (HTTP timeout, SGP4 error, DB error) must be
  caught, logged at `ERROR` level with a `request_id` / `job_id` tag, and swallowed — the
  scheduler continues to fire on schedule and the app stays alive.
- **Inputs**: Exception from any step in FR-2.
- **Outputs**: Loguru `ERROR` log. No propagation to the ASGI stack.
- **Edge cases**: Consecutive failures (network down for hours) — the job keeps firing without
  memory leak; each run opens and closes its own DB session.

### FR-4: Lifespan integration (start + shutdown)
- **What**: `start_scheduler(app_settings, session_factory)` is called in `main.py`'s
  `lifespan` startup block; `scheduler.shutdown(wait=False)` in the shutdown block.
- **Inputs**: `Settings`, `SessionLocal`.
- **Outputs**: Running scheduler on startup; clean stop on SIGTERM / `make local-dev` restart.
- **Edge cases**: `scheduler.start()` called only once; `shutdown()` called only when the
  scheduler is actually running.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `scheduler.py` exports `start_scheduler()` and a module-level
  `scheduler` instance; both are importable without side effects.
- [ ] **Outcome 2**: `main.py` lifespan calls `start_scheduler()` on startup and
  `scheduler.shutdown()` on teardown — confirmed by a test that mocks both.
- [ ] **Outcome 3**: A test that runs the job function directly triggers ingest + screen in
  order and records counts in logs (Loguru caplog or monkeypatched calls).
- [ ] **Outcome 4**: A test that injects a failing ingest confirms the exception is caught,
  logged at ERROR, and does not propagate — scheduler does not crash.
- [ ] **Outcome 5**: `make local-lint` passes (Ruff, line length 100) after implementation.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_scheduler_job_calls_ingest_then_screen**: Patch `ingest_tle_group` and
   `run_conjunction_screen`; call the job function directly; assert both were called in order
   with the correct DB session.
2. **test_scheduler_job_logs_counts**: After a successful run, assert Loguru captured an INFO
   line containing the satellite count and conjunction count.
3. **test_scheduler_job_ingest_failure_isolated**: Patch `ingest_tle_group` to raise
   `httpx.TimeoutException`; call the job function; assert no exception escapes and Loguru
   captured an ERROR line.
4. **test_scheduler_job_screen_failure_isolated**: Patch `run_conjunction_screen` to raise
   `RuntimeError`; assert no exception escapes and ERROR is logged.
5. **test_start_scheduler_registers_job**: Call `start_scheduler()` with mocked settings and
   a dummy session factory; assert the scheduler has exactly one job with a 2-hour interval.
6. **test_lifespan_starts_and_stops_scheduler**: Use FastAPI `TestClient` (or `lifespan` async
   context manager) to exercise startup + shutdown; assert `scheduler.running` is `True` after
   start and `False` after stop (mock the actual job so it doesn't run).

### Mocking Strategy
- CelesTrak HTTP: already behind `ingest_tle_group` — mock that function directly via
  `unittest.mock.patch` or `pytest-mock`'s `mocker.patch`.
- DB: in-memory SQLite `SessionLocal` from the shared `conftest.py`.
- Scheduler clock: do NOT advance real time; call the job function directly in unit tests.
- Frontend specs: N/A (this is a backend spec).

### Coverage Expectation
- All public functions (`start_scheduler`, the job body) have at least one test.
- Both failure modes (ingest failure, screen failure) are covered.
- Lifespan wiring is covered by at least one integration-level test.

---

## References
- roadmap.md S6.6 row (Phase 6 table + Master Spec Index)
- CLAUDE.md — APScheduler, Loguru, async-vs-sync rules, CelesTrak cadence constraint
- S3.2 spec — 2-hour file-cache contract
- S5.5 spec — `run_conjunction_screen()` interface
