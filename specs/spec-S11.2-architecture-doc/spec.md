# Spec S11.2 — Architecture Diagram

## Overview
Produce a written architecture document (`docs/architecture.md`) that explains the full system pipeline: CelesTrak ingestion → TLE parsing → SGP4 propagation → conjunction screening → REST API → CesiumJS globe + Chart.js dashboard. The document must include a text-based system diagram, a data-flow narrative, and a clear note on coordinate frames (TEME for all conjunction math; geodetic lat/lon/alt only at the display boundary). This is a documentation deliverable, not a code deliverable, so the "implementation" is authoring the Markdown file with accurate, verifiable content drawn from the actual codebase.

## Dependencies
- S10.3 (end-to-end test) must be `done` — the architecture doc describes the live, integrated system, not a hypothetical design.

## Target Location
`docs/architecture.md`

---

## Functional Requirements

### FR-1: System diagram (ASCII / Mermaid)
- **What**: A diagram showing every major component and the data flowing between them, in pipeline order.
- **Inputs**: The actual codebase structure (services, API routers, frontend modules).
- **Outputs**: A readable, text-based diagram embedded in `docs/architecture.md`. Mermaid `graph LR` or plain ASCII are both acceptable.
- **Must show**: CelesTrak GP API → `ingestion.py` (2-h cache) → `tle_parser.py` → `db/models.py` (SQLite) → `propagation.py` (SGP4/skyfield) → `classification.py` → `conjunctions.py` (sieve → cKDTree → TCA → risk score) → FastAPI routers (`/satellites`, `/conjunctions`, `/stats`) → `api.js` (frontend client) → `cesiumView.js` (3D globe) + `dashboard.js` (Chart.js panels).
- **Edge cases**: Scheduler loop (`scheduler.py` → re-ingest + re-screen every 2 h) must be visible as a feedback path.

### FR-2: Data-flow narrative
- **What**: A prose walkthrough (one paragraph per stage) explaining what data enters, what transforms happen, and what exits — for every stage in the diagram.
- **Stages**: Fetch, cache, parse, propagate, classify, screen (sieve → cKDTree → TCA), risk score, persist, serve, render.
- **Edge cases**: Each stage's failure mode must be mentioned (e.g., HTTP 403 → fall back to cache; SGP4 error code → skip decayed satellite; no candidate pairs → empty conjunction list returned).

### FR-3: Coordinate-frame note
- **What**: A dedicated subsection ("Coordinate Frames") explaining that all conjunction math (distance, TCA, miss-distance, relative velocity) is performed in TEME/ECI, and that conversion to geodetic (lat/lon/alt via skyfield `wgs84.subpoint`) happens only at the display boundary in `propagation.py` before handing positions to the frontend.
- **Why this matters**: WGS-72 gravity constants are used in SGP4 (matches TLE generation); switching to WGS-84 would introduce errors.
- **Edge cases**: Must state that the tool reports **potential close approaches (miss distance)**, not collision probability, because TLEs carry no covariance data.

### FR-4: Tech-stack table
- **What**: A concise table mapping each concern to its library/tool and a one-line rationale — mirrors the tech stack in `roadmap.md` but scoped to what actually ships.
- **Columns**: Concern | Library/Tool | Rationale.
- **Rows to include**: Bulk propagation (`sgp4` `SatrecArray`), display positions (`skyfield` + `wgs84.subpoint`), neighbour search (`scipy.spatial.cKDTree`), storage (SQLite + SQLAlchemy), scheduling (APScheduler), HTTP client (httpx + tenacity), config (pydantic-settings), logging (Loguru), 3D globe (CesiumJS), charts (Chart.js).

### FR-5: Key thresholds & constants
- **What**: A table or bullet list of the numeric constants used throughout the system, so a reader can verify the implementation matches the spec.
- **Values**: μ = 398600.4418 km³/s²; Risk threshold = 5 km (matches CelesTrak SOCRATES); Coarse cKDTree radius ≈ 10–20 km; TCA dense-step ≈ 1 s; 2-h TLE cadence; regime boundaries (e≥0.25→HEO; n≥11.25→LEO; 1.2≤n<11.25→MEO; n<1.2→GEO).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `docs/architecture.md` exists and contains a system diagram (Mermaid or ASCII) that traces the full pipeline from CelesTrak fetch to Cesium rendering.
- [ ] **Outcome 2**: The document includes a "Coordinate Frames" subsection that correctly states TEME is used for conjunction math and geodetic is used only for display.
- [ ] **Outcome 3**: The document includes a tech-stack table with all 10 required rows.
- [ ] **Outcome 4**: The document includes a key constants/thresholds table with all values matching CLAUDE.md and the codebase.
- [ ] **Outcome 5**: The scheduler feedback loop (2-h re-ingest + re-screen) is shown in the diagram.
- [ ] **Outcome 6**: A test (`backend/tests/test_readme.py` or a new `backend/tests/test_architecture_doc.py`) asserts that `docs/architecture.md` exists and contains the required sections by heading name.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_architecture_doc_exists**: Assert `docs/architecture.md` exists as a file.
2. **test_architecture_doc_has_diagram_section**: Assert the file contains a heading (e.g. `## Architecture` or `## System Diagram`) and a Mermaid/ASCII diagram block.
3. **test_architecture_doc_has_coordinate_frame_section**: Assert the file contains a heading matching `Coordinate Frames` (case-insensitive) and the word `TEME`.
4. **test_architecture_doc_has_tech_stack_section**: Assert the file contains a `Tech Stack` heading and at least 8 table rows (pipe-separated Markdown table).
5. **test_architecture_doc_has_constants_section**: Assert the file contains `398600` (the μ constant) and `5 km` (risk threshold).
6. **test_architecture_doc_mentions_scheduler**: Assert the file mentions `scheduler` or `APScheduler` (the 2-h feedback loop).

### Mocking Strategy
- No external HTTP or DB calls required — these tests are pure filesystem reads (`open("docs/architecture.md")`).
- Run with `pytest backend/tests/ -v` from the project root (the test navigates to the repo root via `pathlib.Path(__file__).parents[N]`).

### Coverage Expectation
- All six test assertions pass; no test requires a real CelesTrak fetch or DB.

---

## References
- `roadmap.md` row S11.2 (Notes: system diagram + frame note)
- `CLAUDE.md` (frame conventions, constants, thresholds, tech stack)
- `backend/app/services/` (actual pipeline implementation to document accurately)
