# Spec S11.1 — README

## Overview

Write the final, publication-quality `README.md` for the Satellite Collision Risk Detector. The README is the project's front door: it must explain the problem, credit the data source (CelesTrak) with the 2-hour caching policy, show the architecture in prose/ASCII, give copy-paste setup instructions, document every REST endpoint, and embed or link to screenshots. This is a graded deliverable — quality, completeness, and accuracy are evaluated.

## Dependencies

- S10.3 (end-to-end test passing — the system must be fully working before the README is finalised)

## Target Location

`README.md` (project root)

---

## Functional Requirements

### FR-1: Problem Statement
- **What**: A concise opening section that explains what the tool does and why it matters, including the key caveat that this reports *potential close approaches* (miss distance), not collision probability, because TLEs carry no covariance data.
- **Inputs**: None (static prose)
- **Outputs**: Sections "Overview" and "Disclaimer" in README.md
- **Edge cases**: Must not overstate the tool's capabilities; must not mention Space-Track or probability anywhere unless clearly marked out-of-scope

### FR-2: Data Sources & CelesTrak Attribution
- **What**: A dedicated "Data Sources" section that attributes CelesTrak GP API, notes data is updated every **2 hours**, and explains the one-download-per-update cache policy (HTTP 403 fallback to cached copy).
- **Inputs**: None (static prose, derived from CLAUDE.md policy)
- **Outputs**: "Data Sources" section with CelesTrak attribution, 2-hour cadence note, 403-fallback note
- **Edge cases**: Must not imply real-time data; must not omit the caching note

### FR-3: Architecture Section
- **What**: A clear description of the data flow from CelesTrak → ingestion → SGP4 propagation → conjunction screening → REST API → frontend globe + dashboard. Mention TEME frame for math and geodetic for display. Include the tech stack table.
- **Inputs**: None (derived from CLAUDE.md Core Flow)
- **Outputs**: "Architecture" section with prose/ASCII flow diagram and tech stack table
- **Edge cases**: Frame conventions (TEME vs geodetic) must be correctly stated

### FR-4: Setup Instructions
- **What**: Step-by-step instructions for both local dev (uv/venv path) and Docker (docker-compose) that a reader can follow without prior knowledge of the project.
- **Inputs**: Commands from CLAUDE.md and Makefile
- **Outputs**: "Getting Started" section with Local Dev and Docker sub-sections; environment variable table referencing `.env.example`
- **Edge cases**: Windows path differences where relevant; note that `uv` is the package manager (no pip/requirements.txt); seed step must be called out explicitly

### FR-5: API Reference
- **What**: A table or sub-sections covering every REST endpoint: path, method, query params, and a one-line description. Endpoints: `GET /health`, `GET /satellites`, `GET /satellites/{id}`, `GET /satellites/{id}/positions`, `GET /positions`, `GET /conjunctions`, `GET /conjunctions/{pair_id}`, `GET /stats/orbital-regions`, `GET /stats/risk-ranking`.
- **Inputs**: Endpoints from Phase 6 specs and `backend/app/api/`
- **Outputs**: "API Reference" section with a markdown table for each endpoint group
- **Edge cases**: Pagination params for `/satellites`; query params for `/positions` (`start`, `stop`, `step`); threshold/window params for `/conjunctions`

### FR-6: Screenshots Section
- **What**: A section that embeds or links screenshots/GIFs of the running app: the 3D globe with animated satellites and red risk polylines, and the dashboard panels. Placeholder paths acceptable if images are not yet captured.
- **Inputs**: Image files from `docs/screenshots/` (may be placeholders if S11.3 not yet done)
- **Outputs**: "Screenshots" section with markdown image references
- **Edge cases**: If no images exist yet, use placeholder links with a note that S11.3 will populate them

### FR-7: Deployment Section
- **What**: Instructions for deploying on Render.com (one-click Blueprint via `render.yaml`) and optionally Docker locally. Must reference the existing `render.yaml`.
- **Inputs**: Existing deployment docs in README + `render.yaml`
- **Outputs**: "Deployment" section (already partially present — must be verified complete and accurate)
- **Edge cases**: Cold-start note for Render free-tier spin-down; seed step on cold boot

---

## Tangible Outcomes

- [ ] **Outcome 1**: `README.md` contains a "Problem Statement" / "Overview" section that mentions miss-distance-based screening and explicitly disclaims collision probability.
- [ ] **Outcome 2**: `README.md` contains a "Data Sources" section with CelesTrak attribution, 2-hour update cadence, and 403-fallback cache note.
- [ ] **Outcome 3**: `README.md` contains an "Architecture" section with the ingestion→propagation→screen→API→frontend flow and a tech stack table.
- [ ] **Outcome 4**: `README.md` contains a "Getting Started" section with working local-dev commands (`make venv`, `make install`, `make seed`, `make local-dev`) and Docker commands.
- [ ] **Outcome 5**: `README.md` contains an "API Reference" section covering all 9+ endpoints with method, path, and description.
- [ ] **Outcome 6**: `README.md` contains a "Screenshots" section (even if placeholder links until S11.3 is done).
- [ ] **Outcome 7**: `README.md` removes all "planned features" / "current status" placeholder language from the original draft — the system is implemented.

---

## Test-Driven Requirements

Because this spec produces documentation (not executable code), the "tests" are checklist assertions verified by reading the file.

### Tests to Write First (Red → Green)
1. **test_readme_problem_statement**: Assert `README.md` contains the word "miss distance" or "close approach" and "not collision probability" (or equivalent disclaimer).
2. **test_readme_celestrak_attribution**: Assert `README.md` mentions "CelesTrak" and "2 hours" (cadence) and "403" or "cache" (fallback).
3. **test_readme_architecture**: Assert `README.md` contains "ingestion" and "propagation" and "SGP4" and "TEME" (or "geodetic") in the architecture section.
4. **test_readme_setup_commands**: Assert `README.md` contains `make seed` and `make local-dev` (or equivalent Docker commands).
5. **test_readme_api_endpoints**: Assert `README.md` mentions `/conjunctions`, `/satellites`, `/stats/orbital-regions`, `/stats/risk-ranking`, `/health`.
6. **test_readme_no_placeholders**: Assert `README.md` does NOT contain "Planned Features", "[ ]" checkbox items (unchecked TODOs), or "Current Status: Prototype".

These can be implemented as a lightweight pytest file at `backend/tests/test_readme.py` that reads `README.md` and checks string assertions.

### Mocking Strategy
- No external HTTP needed — just file I/O on `README.md`

### Coverage Expectation
- All 6 test assertions above pass

---

## References
- roadmap.md row S11.1 (Phase 11, Feature: README, Notes: problem statement; CelesTrak attribution + 2h caching note; architecture; setup instructions; API reference; screenshots)
- CLAUDE.md (project rules, CelesTrak policy, frame conventions, tech stack)
- CLAUDE.md Core Flow (ingestion → parse → propagate → classify → screen → API → frontend)
