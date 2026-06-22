# Checklist — Spec S1.2: Developer Commands

## Phase 1: Setup & Dependencies
- [x] Confirm S1.2 has no prerequisite specs (Depends On: —)
- [x] Confirm `pyproject.toml` exists (S1.1 done) so `uv pip install` targets have something to install
- [x] Confirm project root is the correct location for `Makefile`

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_makefile.py`
- [x] Write `test_makefile_has_required_targets` — assert all 9 targets present
- [x] Write `test_makefile_phony_declares_all_targets` — assert `.PHONY` covers all targets
- [x] Write `test_makefile_venv_command_uses_uv` — assert `uv` in `venv` recipe
- [x] Write `test_makefile_install_uses_uv_pip` — assert `uv pip install` in `install` recipe
- [x] Write `test_makefile_dev_uses_uvicorn_reload` — assert `uvicorn` + `--reload` in `local-dev`/`dev`
- [x] Write `test_makefile_test_runs_pytest` — assert `pytest` in `local-test`/`test`
- [x] Write `test_makefile_lint_runs_ruff` — assert `ruff` in `local-lint`/`lint`
- [x] Run tests — expect failures (Red) — `Makefile` does not exist yet

## Phase 3: Implementation
- [x] Create `Makefile` at project root
- [x] Add `.PHONY` line listing all targets
- [x] Implement `venv` target (`uv venv .venv --python 3.11`)
- [x] Implement `install` target (depends on `venv`; `uv pip install -e ".[dev]"`)
- [x] Implement `install-dev` target (depends on `install`)
- [x] Implement `local-dev` / `dev` alias (uvicorn with `--reload`)
- [x] Implement `local-test` / `test` alias (pytest backend/tests/)
- [x] Implement `local-lint` / `lint` alias (ruff check + ruff format --check)
- [x] Implement `seed` target (`python backend/scripts/seed.py`)
- [x] Implement `refresh` target (`python backend/scripts/refresh.py`)
- [x] Implement `serve-frontend` target (`npm --prefix frontend run dev`)
- [x] Run tests — expect pass (Green) — 10/10 passed
- [x] Refactor / tidy help text or target ordering if needed

## Phase 4: Integration
- [x] N/A — `make venv` / `make install` already present from S1.1; `.venv/` exists
- [x] Run full test suite: `python -m pytest backend/tests/ -v --tb=short` — 16/16 passed
- [x] Run lint: `ruff check backend/ && ruff format --check backend/` — LINT OK

## Phase 5: Verification
- [x] All 9 Tangible Outcomes checked off in spec.md (targets verified by tests; manual targets noted below)
- [x] No hardcoded secrets or tokens in Makefile
- [x] All targets declared in `.PHONY`
- [x] `make serve-frontend` — verified recipe calls `npm --prefix frontend run dev`
- [x] `make local-dev` — verified recipe calls uvicorn with `--reload` on port 8000
- [x] Update `roadmap.md` status: `spec-written` → `done`
