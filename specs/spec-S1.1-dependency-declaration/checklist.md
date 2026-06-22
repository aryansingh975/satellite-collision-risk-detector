# Checklist — Spec S1.1: Dependency Declaration

## Phase 1: Setup & Dependencies
- [x] No prerequisite specs (S1.1 has no Depends On)
- [x] Confirm `pyproject.toml` does not yet exist (or is a stub to be replaced)
- [x] Confirm `.env.example` does not yet exist at repo root

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_project_setup.py`
- [x] Write `test_pyproject_is_valid_toml` — parse pyproject.toml with tomllib, assert no exception
- [x] Write `test_runtime_deps_declared` — assert all FR-1 packages appear in `project.dependencies`
- [x] Write `test_dev_extras_declared` — assert all FR-2 packages appear in `project.optional-dependencies.dev`
- [x] Write `test_requires_python` — assert `project.requires-python` == `>=3.11`
- [x] Write `test_env_example_exists` — assert `.env.example` exists at repo root
- [x] Write `test_env_example_keys` — assert all FR-3 keys appear in `.env.example`
- [x] Run tests — expect failures (Red) ✓ 6/6 failed as expected

## Phase 3: Implementation
- [x] Create `pyproject.toml` with `[project]` metadata (`name`, `version`, `requires-python = ">=3.11"`, `description`)
- [x] Add all FR-1 packages to `[project.dependencies]` with `>=` minimum versions
- [x] Add all FR-2 packages to `[project.optional-dependencies] [dev]`
- [x] Create `.env.example` at repo root with all FR-3 keys and placeholder values
- [x] Run tests — expect pass (Green) ✓ 6/6 passed
- [x] Refactor: tidy version ranges if any conflict — N/A, no conflicts

## Phase 4: Integration
- [x] Run `uv pip install -r pyproject.toml` — assert 0 exit code ✓
- [x] Run `uv pip install -r pyproject.toml --extra dev` — assert 0 exit code ✓
- [x] Run lint: `ruff check backend/tests/test_project_setup.py` — All checks passed ✓
- [x] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short` — 6/6 passed ✓

## Phase 5: Verification
- [x] All 5 Tangible Outcomes checked off ✓
- [x] `.env.example` contains no real secrets or tokens ✓ (placeholder values only)
- [x] `pyproject.toml` is the single source of truth — no `requirements.txt` created ✓
- [x] Update `roadmap.md` status: `spec-written` → `done` (after Phase 4 passes)
