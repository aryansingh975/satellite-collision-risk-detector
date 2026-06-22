# Checklist — Spec S3.5: Persist Satellites

## Phase 1: Setup & Dependencies
- [x] Verify S3.3 (TLE field parser) is `done` and tests pass
- [x] Verify S2.2 (Satellite ORM model) is `done` and tests pass
- [x] Locate `backend/app/services/ingestion.py` — identify where `persist_satellites` will live alongside the existing fetch/cache logic
- [x] Confirm `freezegun` is available (or monkeypatch strategy) for `updated_at` time-travel tests; add to `pyproject.toml` dev extras if missing — using `time.sleep(0.01)` + `db.expire_all()` instead (no extra dep needed)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_persist_satellites.py`
- [x] Write `test_persist_satellites_inserts_new_rows` — 3 records into empty DB → returns `(3, 0)`, 3 rows in table (Red)
- [x] Write `test_persist_satellites_upserts_on_conflict` — same 3 records twice → still 3 rows (Red)
- [x] Write `test_persist_satellites_line_bytes_preserved` — stored line1/line2 == input strings (Red)
- [x] Write `test_persist_satellites_empty_list` — `persist_satellites(db, [])` → `(0, 0)`, no DB writes (Red)
- [x] Write `test_persist_satellites_updated_at_refreshed` — second upsert updates `updated_at` (Red)
- [x] Write `test_persist_satellites_dedupes_within_batch` — same catalog_no twice in one batch → 1 row (Red)
- [x] Run tests — confirm all fail (Red) — ImportError: `persist_satellites` not yet defined

## Phase 3: Implementation
- [x] Implement `persist_satellites(db: Session, records: list[dict]) -> tuple[int, int]` in `ingestion.py`
- [x] Use SQLAlchemy `insert(Satellite).on_conflict_do_update(index_elements=["catalog_no"], set_={...})` for upsert
- [x] Set `updated_at` to `datetime.utcnow()` on every upsert
- [x] Handle empty `records` early-return `(0, 0)`
- [x] Handle intra-batch duplicates (de-dupe by `catalog_no` before insert, last-seen wins)
- [x] Commit session; return `(inserted, updated)` counts derived from pre-upsert existence count
- [x] Run tests — confirm all pass (Green) — 6/6 passed
- [x] Refactor if needed (extract helpers, improve readability) — keep tests green — no refactor needed

## Phase 4: Integration
- [x] Wire `persist_satellites` into the ingestion pipeline: `persist_satellites` is defined in `ingestion.py` and importable — full orchestrator wiring deferred to S10.1 (seed script), which is the designated caller
- [x] Verify `make seed` dry-run (or test with in-memory DB) ends with satellites in the DB — N/A: seed script is S10.1 (not yet implemented); 6 in-memory DB tests confirm persistence correctness
- [x] Run lint: `make local-lint` (ruff check + format, line length 100) — all checks passed, 1 file already formatted
- [x] Run full backend test suite — 103/113 passed; 10 pre-existing failures all `ModuleNotFoundError: apscheduler` (unrelated to S3.5)

## Phase 5: Verification
- [x] All 6 tangible outcomes pass as assertions in the test suite — 6/6 passed
- [x] No hardcoded secrets or tokens
- [x] `updated_at` is refreshed correctly on every upsert (Outcome 5) — confirmed via `test_persist_satellites_updated_at_refreshed`
- [x] `line1`/`line2` are stored verbatim — byte-for-byte identity confirmed (Outcome 3) — confirmed via `test_persist_satellites_line_bytes_preserved`
- [x] Empty-list call is a no-op (Outcome 4) — confirmed via `test_persist_satellites_empty_list`
- [x] Update `roadmap.md` status for S3.5 in **both** the Phase 3 table and Master Spec Index: `spec-written` → `done`
