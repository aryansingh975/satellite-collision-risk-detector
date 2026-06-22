# Checklist — Spec S2.1: SQLAlchemy Engine + Session

## Phase 1: Setup & Dependencies
- [x] Verify S1.3 (pydantic-settings config) is `done`
- [x] Verify S1.4 (FastAPI app factory) is `done`
- [x] Confirm `backend/app/db/` directory exists (create if missing)
- [x] Confirm `sqlalchemy` is listed in `pyproject.toml` (added in S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/db/test_database.py`
- [x] Write `test_engine_url_matches_settings` — failing (Red)
- [x] Write `test_session_local_is_configured` — failing (Red)
- [x] Write `test_init_db_creates_tables` — failing (Red)
- [x] Write `test_get_db_yields_session` — failing (Red)
- [x] Write `test_get_db_closes_on_exception` — failing (Red)
- [x] Run tests — expect all to fail: `python -m pytest backend/tests/db/test_database.py -v`

## Phase 3: Implementation
- [x] Implement FR-1: `engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})`
- [x] Implement FR-2: `Base = declarative_base()`
- [x] Implement FR-3: `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- [x] Implement FR-4: `get_db()` generator with `finally: db.close()`
- [x] Implement FR-5: `init_db()` calling `Base.metadata.create_all(bind=engine)`
- [x] Run tests — expect all to pass (Green): `python -m pytest backend/tests/db/test_database.py -v`
- [x] Refactor if needed (no logic to simplify here, but verify imports are clean)

## Phase 4: Integration
- [x] Confirm S1.4 `lifespan` already calls (or is updated to call) `init_db()` on startup
- [x] Confirm S1.4 includes `get_db` import path is correct
- [x] Run lint: `make local-lint`
- [x] Run full test suite: `python -m pytest backend/tests/ -v --tb=short`

## Phase 5: Verification
- [x] All 5 tangible outcomes checked manually
- [x] No hardcoded database paths — path comes from `settings.DATABASE_URL`
- [x] No `autocommit=True` or `autoflush=True`
- [x] `finally` block in `get_db()` confirmed present
- [x] Update roadmap.md status: `spec-written` → `done` (after implement + verify pass)
