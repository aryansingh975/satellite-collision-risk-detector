# Checklist — Spec S2.3: Conjunction ORM Model

## Phase 1: Setup & Dependencies
- [x] Verify S2.1 (SQLAlchemy engine + session) is `done`
- [x] Verify S2.2 (Satellite ORM model) is `done`
- [x] Confirm `backend/app/db/models.py` exists and imports `Base` from `app.db.database`
- [x] No new packages needed — SQLAlchemy already declared in `pyproject.toml`

## Phase 2: Tests First (TDD)
- [x] Write `backend/tests/db/test_conjunction_model.py`
- [x] Write `test_conjunction_table_created` — table appears after `create_all`
- [x] Write `test_conjunction_columns` — all 8 columns present via `inspect`
- [x] Write `test_conjunction_miss_km_index` — `ix_conjunctions_miss_km` in `get_indexes`
- [x] Write `test_insert_conjunction_valid` — insert with valid FK sats succeeds
- [x] Write `test_conjunction_fk_enforced` — insert with unknown `sat_a` raises `IntegrityError` (requires `PRAGMA foreign_keys = ON`)
- [x] Write `test_conjunction_relationship` — `conj.satellite_a.name` resolves correctly
- [x] Write `test_computed_at_default` — `computed_at` auto-populated when omitted
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Add `ForeignKey`, `Index`, `relationship` imports to `models.py`
- [x] Implement FR-1: complete `Conjunction` class with all 8 columns
- [x] Implement FR-2: add `Index("ix_conjunctions_miss_km", ...)` via `__table_args__`
- [x] Implement FR-3: add `satellite_a` and `satellite_b` `relationship()` with explicit `foreign_keys`
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (naming, docstring, import order)

## Phase 4: Integration
- [x] Confirm `Base.metadata.create_all(engine)` picks up the new table (verified by `test_init_db_creates_tables` in test_database.py — 60/60 pass)
- [x] Run `make local-lint` (ruff check + format) — zero errors
- [x] Run full backend test suite: 60 passed, 0 failed

## Phase 5: Verification
- [x] All 5 tangible outcomes checked off in spec.md
- [x] No hardcoded secrets or tokens
- [x] `computed_at` default uses `datetime.utcnow` (function reference, not a call — evaluated at insert time)
- [x] `foreign_keys` parameter supplied on both relationships to avoid `AmbiguousForeignKeysError`
- [x] Update roadmap.md status: `spec-written` → `done` (after implement + verify pass)
