# Spec S10.1 — Seed Script

## Overview
`backend/scripts/seed.py` is the one-shot bootstrapping script invoked via `make seed`. It initialises the SQLite schema, fetches TLE data from CelesTrak (honouring the 2-hour cache), parses and persists all satellites, then runs the full conjunction screen and persists the results. The script must be **idempotent** — running it a second time must not duplicate rows, and must fall back to the cached TLE copy rather than re-fetching. It exits with a non-zero code on fatal failure so `make seed` surfaces the error.

## Dependencies
- S3.5 — Persist satellites (`persist_satellites`, `ingest_tle_group`)
- S5.5 — Risk scoring + persist (`run_conjunction_screen`)

## Target Location
`backend/scripts/seed.py`

---

## Functional Requirements

### FR-1: DB initialisation
- **What**: Call `init_db()` to create all SQLAlchemy tables before touching the DB. Safe to call on an existing DB (idempotent via `CREATE TABLE IF NOT EXISTS`).
- **Inputs**: `DATABASE_URL` from `settings` (defaults to `sqlite:///satellite_tracking.db` at project root)
- **Outputs**: All tables exist in the DB file
- **Edge cases**: DB file already exists with existing data — must not drop or truncate tables

### FR-2: TLE ingestion
- **What**: Call `asyncio.run(ingest_tle_group(db, settings))` which internally honours the 2-hour file cache (S3.2) — downloads only if cache is stale or missing.
- **Inputs**: `db` (SQLAlchemy `Session`), `settings` (pydantic-settings instance)
- **Outputs**: Integer count of total upserted satellite records, logged at INFO level
- **Edge cases**: HTTP 403 from CelesTrak → fall back to stale cache (handled by S3.2); empty CSV → returns 0 gracefully; no `.env` → `settings` uses defaults

### FR-3: Conjunction screen
- **What**: Call `run_conjunction_screen(db, settings)` which runs the full sieve → cKDTree → TCA → risk-score → persist pipeline (S5.1–S5.5).
- **Inputs**: Same `db` session, `settings`
- **Outputs**: Integer count of persisted conjunction events, logged at INFO level
- **Edge cases**: Zero satellites in DB → screen returns 0 conjunctions; screen exceptions logged and re-raised so `make seed` exits non-zero

### FR-4: Idempotency
- **What**: Running `seed.py` twice must produce the same final DB state. Satellites are upserted (conflict on `catalog_no`). Conjunctions are keyed on `window_start` (S5.5 idempotent persist). No duplicate rows after a second run.
- **Inputs**: Existing DB with data from first run
- **Outputs**: Same row counts (modulo TLE data actually changing between runs)
- **Edge cases**: Clock skew or re-run within the same 2-hour cache window — cache hit, same TLEs, same upsert result

### FR-5: Exit codes and logging
- **What**: Script exits with code `0` on success, non-zero (`sys.exit(1)`) on any unhandled exception. Uses Loguru `logger` with `request_id` context set to `"seed"`.
- **Inputs**: N/A (no CLI args required; optional `--group` flag is a stretch goal)
- **Outputs**: Structured log lines including satellite count and conjunction count
- **Edge cases**: `init_db` failure (e.g. permissions) → log + `sys.exit(1)`; `ingest_tle_group` uncaught exception → log + `sys.exit(1)`

---

## Tangible Outcomes

- [ ] **Outcome 1**: `make seed` completes successfully on a clean checkout with no existing DB file, creating `satellite_tracking.db` with populated `satellites` and `conjunctions` tables.
- [ ] **Outcome 2**: Running `make seed` a second time completes without errors, does not double the row counts, and produces `inserted=0, updated=N` for satellites (all rows already exist).
- [ ] **Outcome 3**: With a mock CelesTrak returning sample CSV, `seed.py` logs satellite and conjunction counts at INFO level and exits `0`.
- [ ] **Outcome 4**: If `ingest_tle_group` raises an exception, `seed.py` exits non-zero (verified via `pytest.raises(SystemExit)` with `match="1"`).
- [ ] **Outcome 5**: `backend/scripts/seed.py` is importable as a module (no top-level side effects outside `if __name__ == "__main__"`).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_seed_creates_tables**: Patch `ingest_tle_group` and `run_conjunction_screen`; call `main()` on a fresh in-memory DB; assert `Satellite` and `Conjunction` tables exist.
2. **test_seed_calls_ingest_and_screen**: Assert `ingest_tle_group` and `run_conjunction_screen` are each called exactly once with a `Session` and `settings`.
3. **test_seed_idempotent**: Run `main()` twice with the same mocked ingestion returning the same satellite list; assert no DB row count doubles.
4. **test_seed_exits_nonzero_on_ingest_failure**: Patch `ingest_tle_group` to raise `RuntimeError`; assert `main()` raises `SystemExit` with code `1`.
5. **test_seed_exits_nonzero_on_screen_failure**: Patch `run_conjunction_screen` to raise `RuntimeError`; assert `main()` raises `SystemExit` with code `1`.
6. **test_seed_logs_counts**: Capture Loguru output; assert satellite and conjunction counts appear in logs.

### Mocking Strategy
- CelesTrak HTTP: not hit in tests — patch `ingest_tle_group` directly to return a count
- `run_conjunction_screen`: patched to return a count
- DB: in-memory SQLite (`sqlite:///:memory:`), engine created fresh per test, `init_db()` called on it
- Use `unittest.mock.patch` or `pytest-mock`'s `mocker.patch`

### Coverage Expectation
- All public functions (`main`, and the `seed` helper if extracted) have at least one test; all error paths (ingest failure, screen failure) covered

---

## References
- `roadmap.md` row S10.1 (Phase 10, Integration & Deployment)
- `CLAUDE.md` — CelesTrak rate-limit rules, idempotency requirement, logging with `request_id`
- `backend/app/services/ingestion.py` — `ingest_tle_group(db, settings) -> int`
- `backend/app/services/conjunctions.py` — `run_conjunction_screen(db, settings) -> int`
- `backend/app/db/database.py` — `init_db()`, `SessionLocal`
- `backend/app/services/scheduler.py` — reference implementation of the same orchestration pattern
