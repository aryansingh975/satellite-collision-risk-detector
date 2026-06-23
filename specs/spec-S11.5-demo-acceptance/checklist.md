# Checklist — Spec S11.5: Demo & Acceptance

## Phase 1: Setup & Dependencies
- [x] Verify S11.1 (README) is `done`
- [x] Verify S11.3 (Screenshots/GIFs) is `done` — `docs/screenshots/` contains globe + dashboard images
- [x] Confirm `docs/` directory exists (created by S11.2)
- [x] No new pyproject.toml or package.json entries needed (pure markdown + one test file)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_acceptance_doc.py`
- [x] Write `test_acceptance_doc_exists` — file present and non-empty
- [x] Write `test_acceptance_doc_has_five_dimensions` — five graded dimension headings present
- [x] Write `test_acceptance_doc_has_all_phases` — Phase 1 through Phase 11 referenced
- [x] Write `test_acceptance_doc_has_demo_steps` — at least seven numbered demo steps present
- [x] Write `test_acceptance_doc_has_signoff` — sign-off table with Reviewer/Date/Verdict present
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Create `docs/acceptance.md` with five graded-dimension checklist sections (FR-1)
- [x] Add all-specs-done gate section covering Phase 1–11 (FR-2)
- [x] Write demo walkthrough script with ≥7 numbered steps (FR-3)
- [x] Add sign-off table at bottom (FR-4)
- [x] Run tests — expect pass (Green)
- [x] Refactor markdown if needed (headings, links, formatting)

## Phase 4: Integration
- [x] Verify all items in the acceptance doc against the live running app (golden path smoke)
- [x] Confirm all five graded-dimension items are actually met (not placeholder unchecked)
- [x] Run lint: `npm --prefix frontend run lint` (frontend unchanged; backend ruff check still clean)
- [x] Run full backend test suite: `.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

## Phase 5: Verification
- [x] All five tangible outcomes checked
- [x] No hardcoded secrets/tokens in acceptance.md
- [x] `docs/acceptance.md` renders correctly in GitHub markdown preview
- [x] Update roadmap.md status for S11.5: `spec-written` → `done` (after implementation passes)
