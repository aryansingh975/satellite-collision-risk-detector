# Spec S1.2 — Developer Commands

## Overview
Provides a `Makefile` with standardized targets so every developer (and CI) can bootstrap, run, test,
lint, and seed the project with a single command. Targets wrap the `uv`-based venv and package
manager, the FastAPI dev server, pytest, ruff, and the frontend Vite dev server. No external data
is required; this spec is about developer ergonomics only.

## Dependencies
None (no prerequisite specs — can be implemented in parallel with S1.1).

## Target Location
`Makefile` at the project root.

---

## Functional Requirements

### FR-1: `venv` target
- **What**: Creates a Python 3.11 virtual environment at `.venv/` using `uv`.
- **Inputs**: None (reads Python version from environment or pyproject.toml).
- **Outputs**: `.venv/` directory created at project root.
- **Edge cases**: If `.venv/` already exists the command should still succeed (idempotent).

### FR-2: `install` target
- **What**: Installs all production dependencies declared in `pyproject.toml` into `.venv/` via `uv pip install`.
- **Inputs**: `pyproject.toml`, active `.venv/`.
- **Outputs**: All production packages available inside `.venv/`.
- **Edge cases**: Should depend on `venv` so it is safe to run cold.

### FR-3: `install-dev` target
- **What**: Installs production + dev/test extras (`pytest`, `ruff`, `pytest-mock`, `respx`) into `.venv/`.
- **Inputs**: `pyproject.toml` (dev extras group), active `.venv/`.
- **Outputs**: Dev packages available inside `.venv/` in addition to production ones.
- **Edge cases**: Should depend on `install` (or `venv`) so it is safe to run cold.

### FR-4: `local-dev` target (also aliased as `dev`)
- **What**: Starts the FastAPI backend with uvicorn in hot-reload mode.
- **Command**: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000` (or equivalent via `.venv`).
- **Inputs**: `.venv/` with production deps installed; `backend/app/main.py` present.
- **Outputs**: Server listening on port 8000.
- **Edge cases**: N/A at Makefile level — uvicorn handles port conflict errors.

### FR-5: `local-test` target (also aliased as `test`)
- **What**: Runs the full pytest suite from the project root.
- **Command**: activates `.venv/` and runs `python -m pytest backend/tests/ -v --tb=short`.
- **Inputs**: `.venv/` with dev deps installed; test files under `backend/tests/`.
- **Outputs**: Pytest exit code 0 on success.
- **Edge cases**: Exits non-zero on test failure (default pytest behaviour — no suppression).

### FR-6: `local-lint` target (also aliased as `lint`)
- **What**: Runs `ruff check` and `ruff format --check` over the backend source.
- **Command**: `ruff check backend/ && ruff format --check backend/`.
- **Inputs**: `.venv/` with ruff installed; ruff config in `pyproject.toml`.
- **Outputs**: Exit 0 if no issues; non-zero + human-readable diff otherwise.
- **Edge cases**: Does not auto-fix; only checks (use `ruff format` manually to fix).

### FR-7: `seed` target
- **What**: Runs the initial data seed script: fetches TLEs from CelesTrak, screens conjunctions, and populates the SQLite DB.
- **Command**: `python backend/scripts/seed.py` (inside `.venv/`).
- **Inputs**: `.venv/` with deps; network access to CelesTrak (or cached copy).
- **Outputs**: SQLite DB populated; log output to stdout.
- **Edge cases**: Respects the 2-hour cache — running twice in quick succession must not re-fetch.

### FR-8: `refresh` target
- **What**: Forces a TLE refresh and re-screens conjunctions (outside the 2-hour scheduler).
- **Command**: e.g. `python -c "from backend.app.services.ingestion import force_refresh; ..."` or a dedicated refresh script.
- **Inputs**: `.venv/`; cached TLE files or live CelesTrak.
- **Outputs**: Updated DB rows; log output.
- **Edge cases**: Must still respect the 2-hour cadence check internally (ingestion.py decides).

### FR-9: `serve-frontend` target
- **What**: Starts the Vite dev server for the frontend.
- **Command**: `npm --prefix frontend run dev`.
- **Inputs**: `frontend/node_modules/` present (assumed installed separately via `npm install`).
- **Outputs**: Vite dev server listening (default port 5173).
- **Edge cases**: Fails clearly if `frontend/node_modules/` is absent — does not silently succeed.

### FR-10: `.PHONY` declarations
- **What**: All targets are declared `.PHONY` so Make never confuses them with files of the same name.
- **Inputs**: N/A.
- **Outputs**: Correct `.PHONY` line at the top of the Makefile.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `make venv` exits 0 and `.venv/` exists at project root.
- [ ] **Outcome 2**: `make install` exits 0 and `fastapi` is importable from `.venv`.
- [ ] **Outcome 3**: `make install-dev` exits 0 and `pytest`, `ruff`, `pytest-mock`, `respx` are importable.
- [ ] **Outcome 4**: `make local-test` (or `make test`) runs and exits 0 when the test suite passes.
- [ ] **Outcome 5**: `make local-lint` (or `make lint`) exits 0 on a clean codebase.
- [ ] **Outcome 6**: `make local-dev` (or `make dev`) launches uvicorn on port 8000 (manually verified).
- [ ] **Outcome 7**: `make seed` runs `backend/scripts/seed.py` without error (manually verified with network).
- [ ] **Outcome 8**: `make serve-frontend` starts the Vite dev server (manually verified).
- [ ] **Outcome 9**: All targets appear in `.PHONY` so repeated invocations are safe.

---

## Test-Driven Requirements

> The Makefile itself is a shell script — it cannot be unit-tested with pytest. Tests here validate
> that the *commands* the Makefile wraps work correctly, and a lightweight shell-level smoke test
> verifies target presence.

### Tests to Write First (Red → Green)

1. **test_makefile_has_required_targets**: Parse the Makefile and assert each required target
   (`venv`, `install`, `install-dev`, `local-dev`, `dev`, `local-test`, `test`, `local-lint`,
   `lint`, `seed`, `refresh`, `serve-frontend`) appears as a recipe target.
2. **test_makefile_phony_declares_all_targets**: Assert `.PHONY` lists all the above targets
   (or at least the non-file targets).
3. **test_makefile_venv_command_uses_uv**: Assert the `venv` recipe contains `uv` (not bare `python -m venv`).
4. **test_makefile_install_uses_uv_pip**: Assert the `install` recipe references `uv pip install`.
5. **test_makefile_dev_uses_uvicorn_reload**: Assert the `local-dev` / `dev` recipe contains
   `uvicorn` and `--reload`.
6. **test_makefile_test_runs_pytest**: Assert the `local-test` / `test` recipe contains `pytest`.
7. **test_makefile_lint_runs_ruff**: Assert the `local-lint` / `lint` recipe contains `ruff`.

### Mocking Strategy
- These are pure text-parsing tests — no external calls, no DB, no mocking required.
- Test file: `backend/tests/test_makefile.py`.
- Fixture: read `Makefile` from the project root using a path relative to `conftest.py` or via
  the `PROJECT_ROOT` env var / `pathlib.Path(__file__).parents[2]`.

### Coverage Expectation
- All 9 required Make targets verified for presence.
- `.PHONY` completeness verified.
- Key command-line flags verified (uv, uvicorn --reload, pytest, ruff).

---

## References
- `roadmap.md` spec row S1.2 and Phase 1 notes
- `CLAUDE.md`: "Package manager: uv — single source of truth: pyproject.toml", commands table, venv location
