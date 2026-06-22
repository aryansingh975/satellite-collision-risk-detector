---
description: Verify a spec is fully implemented — tests, lint, outcomes, wiring
argument-hint: spec-id (e.g., S3.2, S5.4)
allowed-tools: Read, Bash, Grep, Glob
---

Verify that spec $ARGUMENTS is fully and correctly implemented.

## Step 1: Load Spec Context

1. Find spec folder: `specs/spec-$ARGUMENTS*/`
2. Read `spec.md` — extract Tangible Outcomes and Functional Requirements
3. Read `checklist.md` — note any unchecked items
4. Read `roadmap.md` row for this spec — get Location, Feature, Notes
5. Determine backend (Python) vs frontend (JS)

## Step 2: Code Existence

- Check every file listed in the spec's **Target Location** exists
- Check each file is non-empty and has the expected public functions/classes mentioned in FRs
- Report: files found, missing files, missing functions

## Step 3: Test Suite

1. Find test files:
   - Backend: glob `backend/tests/**/test_*.py` matching the module
   - Frontend: glob `frontend/**/*.test.js` matching the module
2. Run tests:
   - Backend: `cd backend && python -m pytest {test_files} -v --tb=short`
   - Frontend: `npm --prefix frontend run test -- {test_files}`
3. Report: total tests, passed, failed, errors
4. If any failures: show the first 3 failure summaries

## Step 4: Lint

- Backend: `cd backend && python -m ruff check app/ --select E,F,W`
- Frontend: `npm --prefix frontend run lint`
Report: clean or list issues in this spec's files only

## Step 5: Tangible Outcomes Audit

For each Tangible Outcome listed in spec.md:
- Check if there is a corresponding test that verifies it
- Check if the implementation satisfies it (read the relevant code)
- Mark: PASS / FAIL / UNCLEAR

## Step 6: Integration Check

- If spec involves a **router**: verify it's included in `backend/app/main.py`
- If spec involves a **FastAPI dependency** (get_db, settings): verify it's used where expected
- If spec involves a **service function**: verify it's importable from its module
- If spec involves **config fields**: verify they exist in `config.py`
- If spec involves the **scheduler**: verify the job is registered in the lifespan
- If spec is **frontend**: verify the module is imported/used in `main.js` / `cesiumView.js` (entity added, polyline drawn, chart mounted)
- For **conjunction** specs: confirm the brute-force oracle (S5.6) passes — the trust anchor for the screen

## Step 7: Report

```
Verification Report — Spec {spec_id}: {feature}
────────────────────────────────────────────────
Code files:      ✓ All present
Tests:           ✓ 8/8 passing
Lint:            ✓ Clean
Outcomes:        ✓ 3/3 verified
Integration:     ✓ Wired into main.py
Checklist:       ⚠ 1 unchecked item (Phase 4 — lint)

VERDICT: PASS (with 1 minor item)
```

If PASS: suggest updating `roadmap.md` status from `spec-written` → `done` (in both the phase table and the Master Spec Index).
If FAIL: list exactly what needs to be fixed, in priority order.
