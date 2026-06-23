# Checklist — Spec S11.1: README

## Phase 1: Setup & Dependencies
- [x] Verify S10.3 (end-to-end test) is `done`
- [x] Read the current `README.md` to identify gaps against FR-1 through FR-7
- [x] Identify which sections already exist and which must be added or rewritten

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_readme.py`
- [x] Write failing assertions for each FR:
  - [x] `test_readme_problem_statement` — checks disclaimer prose
  - [x] `test_readme_celestrak_attribution` — checks CelesTrak, 2h, 403/cache
  - [x] `test_readme_architecture` — checks ingestion, SGP4, TEME, geodetic
  - [x] `test_readme_setup_commands` — checks `make seed`, `make local-dev`
  - [x] `test_readme_api_endpoints` — checks all 9 endpoint paths present
  - [x] `test_readme_no_placeholders` — checks no unchecked `- [ ]` items or "Planned Features" remain
- [x] Run tests — expect failures (Red) — 4 failed, 2 passed ✓

## Phase 3: Implementation
- [x] **FR-1**: Write/rewrite "Overview" section with problem statement + miss-distance disclaimer
- [x] **FR-2**: Write/rewrite "Data Sources" section with CelesTrak attribution, 2h cadence, 403-fallback note
- [x] **FR-3**: Write "Architecture" section with ingestion→screen→API→frontend flow + tech stack table
- [x] **FR-4**: Write "Getting Started" with local-dev steps and Docker steps; include env-var table
- [x] **FR-5**: Write "API Reference" with all endpoints in a markdown table
- [x] **FR-6**: Write "Screenshots" section (placeholder links — S11.3 will populate them)
- [x] **FR-7**: Verify/update "Deployment" section (Render Blueprint + Docker local + env vars)
- [x] Remove all "Planned Features", unchecked `- [ ]` todo items, and "Current Status: Prototype" language
- [x] Run tests — all 6 passed (Green)

## Phase 4: Integration
- [x] Re-read the full README end-to-end for readability and accuracy
- [x] Cross-check API endpoint list against `backend/app/api/` route definitions
- [x] Verify all `make` commands referenced in README exist in `Makefile`
- [x] Run full backend test suite — 335 passed, 2 skipped; `test_readme.py` passes with all others

## Phase 5: Verification
- [x] All 7 tangible outcomes checked (each section present + no placeholder language)
- [x] No hardcoded secrets/tokens in README (env vars referenced via `.env.example`)
- [x] CelesTrak 2-hour cache policy clearly stated (not omitted)
- [x] Disclaimer: "miss distance, not collision probability" present
- [x] TEME frame note present in architecture section
- [x] Screenshots section present (placeholder links until S11.3)
- [x] Update roadmap.md status: `spec-written` → `done`
