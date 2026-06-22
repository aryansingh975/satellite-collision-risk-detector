# Checklist — Spec S2.2: Satellite ORM Model

## Phase 1: Setup & Dependencies
- [x] Verify S2.1 is `done` (SQLAlchemy engine + `Base` + `get_db()` in `backend/app/db/database.py`)
- [x] Locate `backend/app/db/models.py` (create if absent)
- [x] Confirm `sqlalchemy` is listed in `pyproject.toml` (already declared via S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/db/test_satellite_model.py`
- [x] Write `test_satellite_table_created` — all 13 columns present after `create_all`
- [x] Write `test_satellite_insert_and_query` — full round-trip via PK
- [x] Write `test_satellite_pk_uniqueness` — duplicate `catalog_no` raises `IntegrityError`
- [x] Write `test_tle_lines_stored_verbatim` — ISS TLE lines read back byte-for-byte
- [x] Write `test_updated_at_defaults_to_now` — default timestamp is set automatically
- [x] Write `test_nullable_derived_fields` — optional columns accept `None`
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Define `Satellite` class inheriting from `Base` in `backend/app/db/models.py`
- [x] Add all 13 columns with correct types, nullability, and defaults
- [x] Set `catalog_no` as `Integer` primary key
- [x] Set `updated_at` default to `datetime.utcnow` (server-side or Python-side)
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (no logic here, just schema)

## Phase 4: Integration
- [x] Import `Satellite` in `backend/app/main.py` (or `database.py`) so `create_all` picks it up at startup
- [x] N/A — `make local-dev` not validated here; wiring confirmed via `main.py` import + full test suite pass
- [x] Run lint: `make local-lint`
- [x] Run full test suite: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [x] All 4 tangible outcomes confirmed (tests: table_created, insert_and_query, pk_uniqueness, tle_lines_stored_verbatim)
- [x] No hardcoded secrets or tokens
- [x] `line1`/`line2` stored exactly 69 chars, no modification (test_tle_lines_stored_verbatim)
- [x] `updated_at` auto-populated on insert (test_updated_at_defaults_to_now)
- [x] Update `roadmap.md` status: `spec-written` → `done` (after Phase 4 passes)
