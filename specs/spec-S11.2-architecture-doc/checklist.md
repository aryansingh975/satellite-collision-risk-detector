# Checklist — Spec S11.2: Architecture Diagram

## Phase 1: Setup & Dependencies
- [x] Verify S10.3 (end-to-end test) is `done`
- [x] Create `docs/` directory if it doesn't exist
- [x] Confirm `docs/architecture.md` does not already exist (or is a stub to overwrite)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_architecture_doc.py`
- [x] Write `test_architecture_doc_exists` — asserts `docs/architecture.md` is a file
- [x] Write `test_architecture_doc_has_diagram_section` — asserts a diagram heading + Mermaid/ASCII block
- [x] Write `test_architecture_doc_has_coordinate_frame_section` — asserts `Coordinate Frames` heading + `TEME`
- [x] Write `test_architecture_doc_has_tech_stack_section` — asserts `Tech Stack` heading + ≥8 table rows
- [x] Write `test_architecture_doc_has_constants_section` — asserts `398600` and `5 km` present
- [x] Write `test_architecture_doc_mentions_scheduler` — asserts `scheduler` or `APScheduler` present
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Create `docs/` directory
- [x] Author `docs/architecture.md` with all required sections:
  - [x] FR-1: System diagram (Mermaid `graph LR` or ASCII, including scheduler feedback loop)
  - [x] FR-2: Data-flow narrative (one paragraph per stage, failure modes noted)
  - [x] FR-3: Coordinate Frames subsection (TEME for math, geodetic only at display boundary, WGS-72 note, no-covariance disclaimer)
  - [x] FR-4: Tech-stack table (10 rows: sgp4, skyfield, cKDTree, SQLite, APScheduler, httpx/tenacity, pydantic-settings, Loguru, CesiumJS, Chart.js)
  - [x] FR-5: Key thresholds & constants (μ, 5 km risk threshold, coarse radius, TCA step, 2-h cadence, regime boundaries)
- [x] Run tests — expect pass (Green)

## Phase 4: Integration
- [x] Verify `docs/architecture.md` is linkable from `README.md` (add a link in README if missing)
- [x] Run lint: `make local-lint` (backend ruff; doc is Markdown so no Python lint needed)
- [x] Run full backend test suite: `.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

## Phase 5: Verification
- [x] All 6 tangible outcomes checked off
- [x] No hardcoded secrets or tokens appear in the doc
- [x] Coordinate frame explanation is accurate (TEME math, geodetic display, WGS-72)
- [x] All numeric constants match CLAUDE.md and the actual codebase
- [x] Scheduler feedback loop visible in diagram
- [x] Update `roadmap.md` status: `spec-written` → `done` (after implementation + tests pass)
