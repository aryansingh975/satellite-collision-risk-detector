# Spec S11.5 — Demo & Acceptance

## Overview
The final acceptance gate for the Satellite Collision Risk Detector prototype. This spec produces
`docs/acceptance.md`, a structured evaluation-criteria checklist that confirms every deliverable
criterion is met before the project is submitted. The checklist covers five grading dimensions —
creativity, technical implementation, web-app quality, GitHub usage, and documentation clarity —
and asserts that every upstream spec is in `done` status. Reviewers (instructors or peers) use
this document to walk through the live demo systematically.

## Dependencies
- S11.1 (README) — must be complete with CelesTrak attribution, setup instructions, API reference, and screenshots
- S11.3 (Screenshots/GIFs) — `docs/screenshots/` must contain globe + dashboard images that are embedded in the README

## Target Location
`docs/acceptance.md`

---

## Functional Requirements

### FR-1: Evaluation-Criteria Checklist
- **What**: `docs/acceptance.md` contains a checklist section for each of the five graded dimensions, with concrete, verifiable acceptance items under each
- **Inputs**: roadmap.md spec statuses; README.md; docs/architecture.md; docs/screenshots/; the running app
- **Outputs**: A markdown file with five checklist sections, each item either checked (met) or unchecked (not yet met)
- **Edge cases**: If any upstream spec is not `done`, the relevant checklist item remains unchecked and a note explains what is missing

### FR-2: All-Specs-Done Gate
- **What**: A dedicated section confirms that every spec in roadmap.md has status `done`
- **Inputs**: Master Spec Index table in roadmap.md
- **Outputs**: A checklist row per spec group (Phase 1–11) asserting all specs in that phase are `done`; a final summary row
- **Edge cases**: Any spec still in `pending` or `spec-written` state must be called out explicitly as a blocking item

### FR-3: Demo Walkthrough Script
- **What**: A numbered walkthrough that a demo presenter can follow live, covering: start backend + frontend, seed data, load globe, animate satellites, observe risk polylines, use search/info panel, view dashboard panels
- **Inputs**: The running app (backend on port 8000, frontend on Vite dev server)
- **Outputs**: Step-by-step script with expected observable outcomes at each step
- **Edge cases**: Notes for demo failure modes (empty DB, no conjunctions found, CORS error) and recovery steps

### FR-4: Acceptance Signature Block
- **What**: A sign-off block at the bottom of `docs/acceptance.md` with fields for reviewer name, date, and overall pass/fail verdict
- **Inputs**: (Manual review)
- **Outputs**: Blank fields that the reviewer fills in; formatted as a markdown table

---

## Tangible Outcomes

- [ ] **Outcome 1**: `docs/acceptance.md` exists and renders valid markdown with no broken links
- [ ] **Outcome 2**: All five graded dimensions have a dedicated checklist section with at least three verifiable items each
- [ ] **Outcome 3**: The all-specs-done section lists every phase (1–11) and asserts each is `done`
- [ ] **Outcome 4**: The demo walkthrough script has at least seven numbered steps matching the app's golden path
- [ ] **Outcome 5**: The sign-off table is present with reviewer name, date, and verdict columns
- [ ] **Outcome 6**: A test (`backend/tests/test_acceptance_doc.py` or similar) asserts the file exists, contains all five dimension headings, and all spec phases are referenced

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_acceptance_doc_exists**: Assert `docs/acceptance.md` is present and non-empty
2. **test_acceptance_doc_has_five_dimensions**: Assert all five graded dimension headings are present (`Creativity`, `Technical Implementation`, `Web-App Quality`, `GitHub Usage`, `Documentation Clarity`)
3. **test_acceptance_doc_has_all_phases**: Assert phase labels Phase 1 through Phase 11 all appear in the acceptance doc
4. **test_acceptance_doc_has_demo_steps**: Assert the demo walkthrough section contains at least seven numbered steps
5. **test_acceptance_doc_has_signoff**: Assert the sign-off table with `Reviewer`, `Date`, `Verdict` columns is present

### Mocking Strategy
- No external HTTP calls needed — tests read the filesystem only
- Use `pathlib.Path` to locate `docs/acceptance.md` relative to the project root
- No DB or propagation fixtures required

### Coverage Expectation
- All five FRs have at least one test; content assertions are string-based (presence of headings/keywords)

---

## References
- roadmap.md (S11.5 row, Phase 11 table, Master Spec Index)
- CLAUDE.md (project rules — never overstate collision probability; deliverable is a working web app + GitHub repo)
