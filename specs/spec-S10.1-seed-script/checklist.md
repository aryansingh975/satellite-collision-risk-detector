# Checklist — Spec S10.1: Seed Script

## Phase 1: Setup & Dependencies
- [x] Verify S3.5 (persist satellites) is `done`
- [x] Verify S5.5 (risk scoring + persist) is `done`
- [x] Create `backend/scripts/` directory and `backend/scripts/__init__.py` (empty, marks as package)
- [x] Create `backend/scripts/seed.py` stub
- [x] Confirm `make seed` target in `Makefile` points to `backend/scripts/seed.py` (already wired)

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/scripts/test_seed.py` (no `__init__.py` — avoids shadowing `backend/scripts/`)
- [x] Write `test_seed_creates_tables` — assert DB tables exist after `main()`
- [x] Write `test_seed_calls_ingest_and_screen` — assert both pipeline functions called once
- [x] Write `test_seed_idempotent` — run twice, assert no row count doubling
- [x] Write `test_seed_exits_nonzero_on_ingest_failure` — patch ingest to raise, assert `SystemExit(1)`
- [x] Write `test_seed_exits_nonzero_on_screen_failure` — patch screen to raise, assert `SystemExit(1)`
- [x] Write `test_seed_logs_counts` — capture Loguru output, assert counts logged
- [x] Run tests — confirmed failures (Red): `AttributeError: module has no attribute 'init_db'` on stub

## Phase 3: Implementation
- [x] Implement `main()` in `seed.py`:
  - [x] FR-1: Call `init_db()` (imports ORM models first so tables register)
  - [x] FR-2: Open `SessionLocal()`, call `asyncio.run(ingest_tle_group(db, settings))`
  - [x] FR-3: Call `run_conjunction_screen(db, settings)`
  - [x] FR-4: Idempotency is guaranteed by upsert in S3.5 + keyed persist in S5.5 — no extra work
  - [x] FR-5: Wrap in try/except; `sys.exit(1)` on failure; bind `logger` with `request_id="seed"`
- [x] Guard with `if __name__ == "__main__": main()`
- [x] Run tests — all 6 pass (Green)
- [x] Refactor N/A — `_run_seed(db)` helper already extracted for clean testability

## Phase 4: Integration
- [x] N/A — Live CelesTrak fetch not run in CI (would violate 2h cadence rule); verified via mocked tests
- [x] Run lint: `ruff check backend/scripts/seed.py backend/tests/scripts/test_seed.py` — all checks passed
- [x] Run full test suite: 304/304 passed

## Phase 5: Verification
- [x] All 6 tangible outcomes checked (tests cover outcomes 2–5; outcome 1 verified manually via `make seed`)
- [x] No hardcoded secrets or tokens
- [x] Loguru `request_id="seed"` present in log context (`logger.contextualize(request_id="seed")`)
- [x] Script exits with code 0 on success, 1 on failure (`sys.exit(1)` in both except blocks)
- [x] `backend/scripts/seed.py` has no top-level side effects (guarded by `if __name__ == "__main__"`)
- [x] Update `roadmap.md` status: `spec-written` → `done`
