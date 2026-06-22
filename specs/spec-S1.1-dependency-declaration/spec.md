# Spec S1.1 — Dependency Declaration

## Overview
Declares all Python runtime and development dependencies for the satellite tracking system. Runtime deps are declared under `[project.dependencies]` in `pyproject.toml` and include: fastapi, uvicorn, skyfield, sgp4, numpy, scipy, sqlalchemy, apscheduler, httpx, pydantic-settings, and loguru. Dev/test extras (pytest, httpx, ruff, pytest-mock) are declared under `[project.optional-dependencies]` (group `dev`). An `.env.example` file provides a template of all required environment variable keys — no secrets, only key names with placeholder values.

## Dependencies
None — S1.1 has no prerequisite specs.

## Target Location
`pyproject.toml`, `.env.example`

---

## Functional Requirements

### FR-1: Runtime dependencies in pyproject.toml
- **What**: `[project.dependencies]` lists every runtime package the app needs, pinned to a minimum compatible version (e.g. `fastapi>=0.111`).
- **Inputs**: N/A — file is static.
- **Outputs**: Valid TOML; `uv pip install -r pyproject.toml` succeeds without error.
- **Required packages**: `fastapi`, `uvicorn[standard]`, `skyfield`, `sgp4`, `numpy`, `scipy`, `sqlalchemy`, `apscheduler`, `httpx`, `pydantic-settings`, `loguru`, `tenacity`
- **Edge cases**: No duplicate entries; no version pins that conflict with each other.

### FR-2: Dev extras in pyproject.toml
- **What**: `[project.optional-dependencies]` declares a `dev` group with all test/lint tools.
- **Inputs**: N/A — file is static.
- **Outputs**: `uv pip install -r pyproject.toml --extra dev` succeeds; `pytest`, `ruff`, and `pytest-mock` become importable.
- **Required packages**: `pytest`, `pytest-mock`, `ruff`, `respx`, `httpx` (test client)
- **Edge cases**: Dev extras must not bleed into the production install.

### FR-3: .env.example with all required keys
- **What**: `.env.example` at repo root lists every env var the app reads, with safe placeholder values (no real secrets).
- **Inputs**: N/A — file is static.
- **Required keys**: `CELESTRAK_BASE_URL`, `DEFAULT_GROUP`, `TLE_CACHE_DIR`, `TLE_MAX_AGE_HOURS`, `DATABASE_URL`, `SCREEN_WINDOW_HOURS`, `SCREEN_STEP_SECONDS`, `COARSE_RADIUS_KM`, `RISK_THRESHOLD_KM`, `CESIUM_ION_TOKEN`
- **Edge cases**: Values are illustrative only (e.g. `CESIUM_ION_TOKEN=your_token_here`). File must not contain actual secrets.

### FR-4: pyproject.toml project metadata
- **What**: `[project]` table includes `name`, `version`, `requires-python = ">=3.11"`, and `description`.
- **Inputs**: N/A.
- **Outputs**: `pip show <name>` returns correct metadata after install.
- **Edge cases**: `requires-python` must exclude Python < 3.11 to avoid silent incompatibilities.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` exits 0 (valid TOML).
- [ ] **Outcome 2**: Every package in FR-1 appears in `[project.dependencies]` in `pyproject.toml`.
- [ ] **Outcome 3**: Every package in FR-2 appears in `[project.optional-dependencies.dev]`.
- [ ] **Outcome 4**: `.env.example` exists at repo root and contains all keys listed in FR-3.
- [ ] **Outcome 5**: `requires-python` is set to `>=3.11` in `[project]`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_pyproject_is_valid_toml**: Parse `pyproject.toml` with `tomllib`; assert no exception.
2. **test_runtime_deps_declared**: Load `pyproject.toml`; assert each required runtime package name appears in `project.dependencies` (substring match on package name, case-insensitive).
3. **test_dev_extras_declared**: Assert each required dev package name appears in `project.optional-dependencies.dev`.
4. **test_requires_python**: Assert `project.requires-python` starts with `>=3.11`.
5. **test_env_example_exists**: Assert `.env.example` exists at repo root.
6. **test_env_example_keys**: Read `.env.example`; assert each key in FR-3 appears as a line prefix.

### Mocking Strategy
- No external I/O needed — tests read local files only.
- Use `pathlib.Path` to locate `pyproject.toml` and `.env.example` relative to the repo root (fixture: `repo_root = Path(__file__).parent.parent.parent` from `backend/tests/`).

### Coverage Expectation
- All six tests pass; no runtime packages omitted; no key missing from `.env.example`.

---

## References
- `roadmap.md` S1.1 row (Phase 1 table + Master Spec Index)
- `CLAUDE.md` — package manager is `uv`; single source of truth is `pyproject.toml` (no `requirements.txt`)
