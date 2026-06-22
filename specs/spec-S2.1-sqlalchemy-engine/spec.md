# Spec S2.1 — SQLAlchemy Engine + Session

## Overview
Creates the SQLAlchemy database engine and session infrastructure for the project. This module
provides a `create_engine` call targeting the SQLite database path from settings, a `SessionLocal`
factory, a declarative `Base` for ORM models, and a `get_db()` FastAPI dependency that yields a
session and closes it on teardown. All downstream ORM models (S2.2, S2.3) and API endpoints
import from this module.

## Dependencies
- S1.3 — pydantic-settings config (provides `DATABASE_URL`)
- S1.4 — FastAPI app factory (consumes `get_db()` via Depends)

## Target Location
`backend/app/db/database.py`

---

## Functional Requirements

### FR-1: SQLAlchemy engine creation
- **What**: Create a SQLAlchemy engine bound to the SQLite URL from `settings.DATABASE_URL`
- **Inputs**: `settings.DATABASE_URL` (e.g. `sqlite:///./data/satellites.db`)
- **Outputs**: A `sqlalchemy.engine.Engine` instance exported as `engine`
- **Edge cases**: Directory for the SQLite file may not exist — engine creation should not silently fail; the seed script is responsible for creating the file path before `init_db()` is called

### FR-2: Declarative Base
- **What**: Export a `Base = declarative_base()` that all ORM models (S2.2, S2.3) inherit from
- **Inputs**: None
- **Outputs**: `Base` class
- **Edge cases**: Must be importable before any model is imported; no circular imports

### FR-3: SessionLocal factory
- **What**: A `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- **Inputs**: Bound to `engine` from FR-1
- **Outputs**: A session factory callable
- **Edge cases**: `autocommit=False` and `autoflush=False` are mandatory — explicit commits keep conjunction writes atomic

### FR-4: `get_db()` FastAPI dependency
- **What**: A generator function `get_db()` that yields a `SessionLocal()` instance, then closes it in a `finally` block
- **Inputs**: None (called via `Depends(get_db)`)
- **Outputs**: Yields `Session`; side effect: session closed on exit
- **Edge cases**: Session must be closed even if the endpoint raises an exception (guaranteed by `finally`)

### FR-5: `init_db()` helper
- **What**: A function `init_db()` that calls `Base.metadata.create_all(bind=engine)` to create all tables
- **Inputs**: None
- **Outputs**: Side effect — DDL emitted to SQLite; idempotent (safe to call multiple times)
- **Edge cases**: Must be called after all model modules are imported so `Base.metadata` is populated; the FastAPI lifespan (S1.4) calls this on startup

---

## Tangible Outcomes

- [ ] **Outcome 1**: Importing `from backend.app.db.database import engine, Base, SessionLocal, get_db, init_db` succeeds without error
- [ ] **Outcome 2**: `init_db()` against an in-memory SQLite (`sqlite:///:memory:`) creates tables without raising
- [ ] **Outcome 3**: `get_db()` yields a session and the session is closed (not in `Session.identity_map`) after the generator is exhausted
- [ ] **Outcome 4**: `engine.url` matches the value of `settings.DATABASE_URL`

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_engine_url_matches_settings**: Assert `str(engine.url)` equals `settings.DATABASE_URL`
2. **test_session_local_is_configured**: Assert `SessionLocal.kw["autocommit"] is False` and `SessionLocal.kw["autoflush"] is False`
3. **test_init_db_creates_tables**: Call `init_db()` against in-memory SQLite; assert `engine.dialect.has_table(conn, "satellites")` (after S2.2 is imported)
4. **test_get_db_yields_session**: Drive the `get_db()` generator; assert the yielded object is a `Session`; assert it is closed after `next()` + `close()`/exhaustion
5. **test_get_db_closes_on_exception**: Simulate an exception mid-request; assert session is still closed in the `finally` block

### Mocking Strategy
- Use `sqlite:///:memory:` for all tests — override `settings.DATABASE_URL` via monkeypatch or a test-scoped engine
- No CelesTrak HTTP calls needed here
- Import models (S2.2, S2.3) in the `init_db` test to ensure `Base.metadata` is populated

### Coverage Expectation
- All five FRs have at least one passing test
- The `get_db()` finally-close path is explicitly tested

---

## References
- `roadmap.md` — Phase 2 row for S2.1; Notes column
- `CLAUDE.md` — DATABASE_URL setting, async-free SQLAlchemy rule, `get_db()` convention
