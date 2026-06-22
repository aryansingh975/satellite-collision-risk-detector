# Checklist — Spec S1.5: CORS + Static Serving

## Phase 1: Setup & Dependencies
- [x] Verify S1.4 is `done` (FastAPI app factory exists in `backend/app/main.py`)
- [x] Confirm `fastapi` (includes `CORSMiddleware`, `StaticFiles`) is already in `pyproject.toml` — no new package needed
- [x] Locate `backend/app/core/config.py` (created by S1.3)

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/test_cors_static.py`
- [x] Write **test_cors_allowed_origin** (FR-1) — expect `Access-Control-Allow-Origin` header for whitelisted origin
- [x] Write **test_cors_preflight** (FR-1) — OPTIONS pre-flight returns 200 + CORS headers
- [x] Write **test_cors_disallowed_origin** (FR-1) — unknown origin gets no CORS header
- [x] Write **test_static_mount_serves_file** (FR-2) — tmp dir with `index.html`, `GET /static/index.html` → 200
- [x] Write **test_static_missing_file** (FR-2) — `GET /static/nonexistent.txt` → 404
- [x] Write **test_settings_cors_defaults** (FR-3) — default `cors_origins` and `static_dir` values
- [x] Write **test_settings_cors_override** (FR-3) — env var overrides `cors_origins`
- [x] Run tests — expect failures (Red): 4 failed (CORS headers absent, Settings attrs missing), 3 passed

## Phase 3: Implementation
- [x] **FR-3** — add `CORS_ORIGINS: list[str]` (default `["http://localhost:5173"]`) and `STATIC_DIR: str` (default `"frontend"`) to `backend/app/core/config.py` Settings class
- [x] Run settings tests — Green (2/2)
- [x] **FR-1** — add `app.add_middleware(CORSMiddleware, ...)` in `backend/app/main.py`, reading `settings.CORS_ORIGINS`
- [x] Run CORS tests — Green (3/3)
- [x] **FR-2** — add `app.mount("/static", StaticFiles(directory=...), name="static")` in `backend/app/main.py`; resolve relative paths from project root; `StaticFiles` raises if directory is missing
- [x] Run static-file tests — Green (2/2)
- [x] Refactor if needed (middleware registered before router includes; path resolution in main.py)

## Phase 4: Integration
- [x] N/A — `make local-dev` not started (no interactive shell); path resolution verified by test suite
- [x] Run full backend test suite: 41/41 passed, no regressions
- [x] Run lint: ruff check + format — all checks passed

## Phase 5: Verification
- [x] All 5 Tangible Outcomes in spec.md checked off (covered by 7 passing tests)
- [x] No hardcoded origins or paths — all from `settings`
- [x] `CORS_ORIGINS` and `STATIC_DIR` documented in `.env.example`
- [x] Update roadmap.md status: `spec-written` → `done` in both tables
