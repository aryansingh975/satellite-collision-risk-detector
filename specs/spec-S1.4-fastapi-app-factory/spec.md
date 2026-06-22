# Spec S1.4 — FastAPI App Factory

## Overview
Creates the FastAPI application entry point in `backend/app/main.py`. The app uses a `lifespan` async context manager to initialise the SQLite database (create all ORM tables) and start the APScheduler on startup, then shut both down cleanly. The factory registers the three API routers (satellites, conjunctions, stats) and exposes a `GET /health` liveness probe returning `{"status": "ok"}`. No external data is fetched at this stage — that happens via the scheduler (S6.6) and the seed script (S10.1).

## Dependencies
- **S1.3** — pydantic-settings config (`Settings`, `get_settings`) must be importable before `main.py` is created.

## Target Location
`backend/app/main.py`

---

## Functional Requirements

### FR-1: FastAPI application instance
- **What**: A module-level `app = FastAPI(...)` (or a `create_app()` factory) is the ASGI enterable exported from `main.py`. The `lifespan` parameter is wired to the context manager in FR-2.
- **Inputs**: Settings loaded via `get_settings()` (title, version, description from config or hardcoded literals).
- **Outputs**: A valid `FastAPI` instance that uvicorn can serve.
- **Edge cases**: Import errors from missing modules surface at import time, not at first request.

### FR-2: Lifespan — database initialisation
- **What**: On `startup`, call `Base.metadata.create_all(bind=engine)` so all ORM tables (satellites, conjunctions — even if the model files are stubs at this stage) are created in SQLite before the first request is served.
- **Inputs**: `engine` from `backend/app/db/database.py`; `Base` from the same module.
- **Outputs**: SQLite file (path from `DATABASE_URL` setting) contains the expected tables after startup.
- **Edge cases**: If `DATABASE_URL` points to an in-memory DB (`:memory:`), tables exist for the lifetime of the process; teardown is a no-op. If the DB file directory doesn't exist, SQLAlchemy raises — document that the directory must exist (handled by config default).

### FR-3: Lifespan — APScheduler lifecycle
- **What**: On `startup`, create a `BackgroundScheduler` (or `AsyncIOScheduler`) and start it. On `shutdown` (after the `yield` in the lifespan), call `scheduler.shutdown(wait=False)` so the process exits promptly.
- **Inputs**: Scheduler instance created inside the lifespan; no jobs are added here (jobs are added in S6.6). The instance may be stored on `app.state` so downstream code can attach jobs.
- **Outputs**: Scheduler is running between startup and shutdown; `.running` is `True` after startup and `False` after shutdown.
- **Edge cases**: If `scheduler.start()` raises (e.g., already started), propagate the exception — do not swallow it. Shutdown is always called even if startup raised, so use `try/finally` or the `yield` pattern correctly.

### FR-4: Router registration
- **What**: Include the three API routers with appropriate prefixes so their endpoints are reachable:
  - `satellites` router → prefix `/satellites` (or `/api/satellites`)
  - `conjunctions` router → prefix `/conjunctions` (or `/api/conjunctions`)
  - `stats` router → prefix `/stats` (or `/api/stats`)
- **Inputs**: Router objects imported from `backend/app/api/satellites.py`, `backend/app/api/conjunctions.py`, `backend/app/api/stats.py`. These files may be stubs (empty `APIRouter()`) at this phase.
- **Outputs**: `app.routes` contains entries for each router prefix. FastAPI's OpenAPI schema lists the prefixes.
- **Edge cases**: If a router module doesn't exist yet, the import fails — create stub router files as part of this spec's setup phase.

### FR-5: Health endpoint
- **What**: `GET /health` returns HTTP 200 with body `{"status": "ok"}`.
- **Inputs**: No parameters.
- **Outputs**: `{"status": "ok"}` JSON, `Content-Type: application/json`.
- **Edge cases**: Endpoint must respond even if the scheduler or DB are not yet initialised (define it before the lifespan runs or at module level). No authentication required.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /health` returns `200 {"status": "ok"}` via the FastAPI `TestClient`.
- [ ] **Outcome 2**: After `TestClient` context entry (startup), `Base.metadata.tables` contains at least the `satellites` and `conjunctions` table names (or the tables are present in the SQLite file).
- [ ] **Outcome 3**: After `TestClient` context entry, the scheduler stored on `app.state.scheduler` (or equivalent) has `.running == True`; after context exit it has `.running == False`.
- [ ] **Outcome 4**: `GET /satellites`, `GET /conjunctions`, and `GET /stats/orbital-regions` all return something other than `404` (may be `200 []`, `422`, or `501` — just not a routing 404).
- [ ] **Outcome 5**: `uvicorn backend.app.main:app --reload` starts without import errors in a fresh venv.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_health_ok** — `TestClient(app).get("/health")` → `200`, body `{"status": "ok"}`.
2. **test_db_tables_created_on_startup** — After client startup, verify `"satellites"` in `Base.metadata.tables` (or query the in-memory SQLite engine for table names).
3. **test_scheduler_starts_on_startup** — After client startup, `app.state.scheduler.running is True`.
4. **test_scheduler_stops_on_shutdown** — After client context exits, `app.state.scheduler.running is False`.
5. **test_satellites_router_mounted** — `GET /satellites` (or `/api/satellites`) does not return `404`; any other status is acceptable at this phase.
6. **test_conjunctions_router_mounted** — `GET /conjunctions` does not return `404`.
7. **test_stats_router_mounted** — `GET /stats/orbital-regions` does not return `404`.

### Mocking Strategy
- Use an **in-memory SQLite** database (`sqlite:///:memory:`) for all tests — override `get_settings()` or the engine fixture in `conftest.py`.
- Do **not** start a real APScheduler job that hits CelesTrak — the scheduler is started (so `.running` can be asserted) but no jobs are added in this spec.
- Use `httpx.TestClient(app)` (or FastAPI's `TestClient` from `starlette.testclient`) with `with TestClient(app) as client:` to trigger lifespan events.

### Coverage Expectation
- All five FRs have at least one test.
- Happy path + shutdown path covered for the scheduler.
- Router mounting verified for all three routers.

---

## References
- `roadmap.md` — Phase 1 row for S1.4; Notes column.
- `CLAUDE.md` — async/sync rules, Loguru logging, pydantic-settings convention, `DATABASE_URL` from `.env`.
