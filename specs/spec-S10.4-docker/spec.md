# Spec S10.4 — Containerization

## Overview
Package the satellite collision risk detector into Docker containers for reproducible, portable deployment. A multi-stage `Dockerfile` builds the FastAPI backend efficiently (builder stage installs deps, runtime stage copies only the minimal artifact). A `docker-compose.yml` orchestrates backend + static frontend together with a persistent SQLite volume, all config flowing through `.env` — no hardcoded secrets.

## Dependencies
- S1.1 (Dependency declaration — pyproject.toml is the install source)

## Target Location
`Dockerfile`, `docker-compose.yml`, `.dockerignore`

---

## Functional Requirements

### FR-1: Multi-stage Dockerfile for backend
- **What**: A two-stage Dockerfile that produces a lean runtime image
  - **Stage 1 (`builder`)**: Python 3.11 slim image; install `uv`; run `uv pip install --system -r pyproject.toml` into `/install`
  - **Stage 2 (`runtime`)**: Python 3.11 slim image; copy installed packages from builder; copy `backend/` source; set `WORKDIR /app`; expose port `8000`; default CMD runs `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- **Inputs**: `pyproject.toml` at repo root, `backend/` source tree
- **Outputs**: Docker image tagged `satellite-backend`
- **Edge cases**: Build must succeed from a clean state (no local `.venv`); any secret env vars must come in at runtime, not baked into the image

### FR-2: docker-compose.yml with backend + frontend services
- **What**: Compose file defining two services
  - `backend`: built from `Dockerfile`; maps `8000:8000`; mounts a named volume `db_data` at `/app/data` for the SQLite file; reads env from `.env` via `env_file`; has a health check on `GET http://localhost:8000/health`
  - `frontend`: uses `nginx:alpine`; serves the built `frontend/` static files from a bind mount (or copies them in); maps `3000:80`
- **Inputs**: `.env` file (user-supplied, never committed)
- **Outputs**: `docker compose up --build` starts both services; `http://localhost:3000` serves the globe; `http://localhost:8000` serves the API
- **Edge cases**: Missing `.env` → compose should warn but not crash (services get defaults); SQLite volume preserves data across `docker compose down` + `up`

### FR-3: Environment variable handling
- **What**: All configurable values flow through environment variables — never hardcoded in Dockerfile or compose
  - `DATABASE_URL` defaults to `sqlite:////app/data/satellite_tracking.db` (inside the volume)
  - `CELESTRAK_BASE_URL`, `TLE_CACHE_DIR`, `SCREEN_WINDOW_HOURS`, `RISK_THRESHOLD_KM`, `CESIUM_ION_TOKEN` all come from `.env`
  - `TLE_CACHE_DIR` should be a path inside the container (e.g. `/app/data/tle_cache`)
- **Inputs**: `.env` at repo root (gitignored); `.env.example` documents all expected keys
- **Outputs**: Container reads settings via pydantic-settings `config.py`; no secrets appear in image layers
- **Edge cases**: `CESIUM_ION_TOKEN` is optional and may be empty string

### FR-4: .dockerignore to keep image lean
- **What**: A `.dockerignore` at repo root excludes files that should not enter the build context
  - Exclude: `.venv/`, `**/__pycache__/`, `*.pyc`, `.env`, `satellite_tracking.db`, `frontend/node_modules/`, `.git/`, `specs/`, `docs/`
- **Inputs**: Repo root file tree
- **Outputs**: Build context sent to daemon is significantly smaller; no secrets accidentally included
- **Edge cases**: Must not exclude `pyproject.toml`, `backend/`, or `frontend/` (needed in build)

---

## Tangible Outcomes

- [ ] **Outcome 1**: `docker build -t satellite-backend .` succeeds from repo root with no errors
- [ ] **Outcome 2**: `docker compose up --build` starts both `backend` and `frontend` services; `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] **Outcome 3**: The SQLite database is written to the named volume; running `docker compose down && docker compose up` retains previously seeded data
- [ ] **Outcome 4**: No secrets or `.env` values are baked into the Docker image (verify with `docker history` / `docker inspect`)
- [ ] **Outcome 5**: `docker compose config` parses `docker-compose.yml` without errors

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_dockerignore_excludes_secrets**: Parse `.dockerignore` and assert `.env`, `satellite_tracking.db`, and `.venv/` patterns are present
2. **test_dockerfile_multistage**: Read `Dockerfile` text; assert it contains at least two `FROM` directives (builder + runtime stages)
3. **test_dockerfile_no_hardcoded_secrets**: Assert `Dockerfile` does not contain literal token strings (regex for common secret patterns)
4. **test_compose_services**: Load `docker-compose.yml` as YAML; assert `services.backend` and `services.frontend` keys exist with required `ports` and `volumes`/`image` fields
5. **test_compose_backend_healthcheck**: Assert `services.backend.healthcheck` is defined and references `/health`
6. **test_compose_env_file**: Assert `services.backend.env_file` references `.env` (not inline secrets)
7. **test_compose_volume_defined**: Assert a named volume `db_data` (or equivalent) is declared under top-level `volumes:`

### Mocking Strategy
- These are file-content tests — no HTTP mocking needed
- Load files with `pathlib.Path(...).read_text()` and PyYAML; no DB or CelesTrak interaction
- Optional integration test: `subprocess.run(["docker", "compose", "config"])` and assert returncode == 0 (requires Docker in CI)

### Coverage Expectation
- All Dockerfile and compose structural requirements have at least one test
- Secret-exclusion tests must pass (negative assertions are as important as positive)

---

## References
- `roadmap.md` S10.4 row (Phase 10, Integration & Deployment)
- `CLAUDE.md` — project rules: never hardcode secrets; build context = repo root; `pyproject.toml` is the single install source
- Docker multi-stage build docs: `FROM ... AS builder` / `COPY --from=builder`
