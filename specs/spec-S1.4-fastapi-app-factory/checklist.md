# Checklist — Spec S1.4: FastAPI App Factory

## Phase 1: Setup & Dependencies
- [x] Verify S1.3 (pydantic-settings config) is `done` and `backend/app/core/config.py` is importable
- [x] Create stub router files if they don't exist: `backend/app/api/satellites.py`, `backend/app/api/conjunctions.py`, `backend/app/api/stats.py` — each just `from fastapi import APIRouter; router = APIRouter()`
- [x] Confirm `backend/app/db/database.py` exports `engine`, `Base`, `get_db` (or create stubs)
- [x] Confirm `apscheduler` is listed in `pyproject.toml` (added in S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_main.py`
- [x] Write `test_health_ok` — GET /health → 200, `{"status": "ok"}`
- [x] Write `test_db_tables_created_on_startup` — tables present after lifespan startup
- [x] Write `test_scheduler_starts_on_startup` — `app.state.scheduler.running is True` after startup
- [x] Write `test_scheduler_stops_on_shutdown` — `.running is False` after client context exits
- [x] Write `test_satellites_router_mounted` — GET /satellites not 404
- [x] Write `test_conjunctions_router_mounted` — GET /conjunctions not 404
- [x] Write `test_stats_router_mounted` — GET /stats/orbital-regions not 404
- [x] Run tests — expect failures (Red) — confirmed 7/7 failed before implementation

## Phase 3: Implementation
- [x] Implement FR-1 — `app = FastAPI(lifespan=lifespan)` in `backend/app/main.py`
- [x] Implement FR-2 — `Base.metadata.create_all(bind=engine)` inside the lifespan startup block
- [x] Implement FR-3 — `BackgroundScheduler` start on startup, `shutdown(wait=False)` after yield; store on `app.state.scheduler`
- [x] Implement FR-4 — `app.include_router(satellites_router, ...)`, conjunctions, stats
- [x] Implement FR-5 — `@app.get("/health")` returning `{"status": "ok"}`
- [x] Run tests — expect pass (Green) — confirmed 7/7 passed
- [x] Refactor if needed (extract lifespan to a separate function for readability)

## Phase 4: Integration
- [x] N/A — `make local-dev` manual start not run in CI; confirmed via tests
- [x] N/A — curl manual check not run in CI; covered by test_health_ok
- [x] Run lint: ruff check + format — passed (1 auto-format applied to test file)
- [x] Run full test suite: 34/34 passed (11 config + 7 main + 11 makefile + 5 project-setup)

## Phase 5: Verification
- [x] All 7 tangible outcomes checked (health, DB tables, scheduler start/stop, 3 routers)
- [x] No hardcoded secrets or tokens in `main.py`
- [x] Loguru logger imported and used for startup/shutdown log messages
- [x] Scheduler stored on `app.state.scheduler` so downstream specs (S6.6) can attach jobs
- [x] Update `roadmap.md` status: `spec-written` → `done` for S1.4 in **both** tables
