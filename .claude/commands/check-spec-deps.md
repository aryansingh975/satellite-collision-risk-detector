---
description: Verify all prerequisite specs for a given spec are implemented and passing
argument-hint: spec-id (e.g., S5.1, S7.4)
allowed-tools: Read, Bash, Grep, Glob
---

Check whether all dependencies for spec $ARGUMENTS are satisfied.

## Step 1: Resolve Spec

1. Read `roadmap.md` and find the row for spec $ARGUMENTS
2. Extract the **Depends On** column (e.g., "S4.5, S4.6")
3. If "—" or empty, report "No dependencies — ready to implement" and stop

## Step 2: For Each Dependency Spec

For each dependency spec ID (e.g., S4.5):

### 2a. Check roadmap status
- Read the spec's row in `roadmap.md` → check Status column
- If not "done": flag as **BLOCKING**

### 2b. Check code file exists
- Read the spec's **Location** column (e.g., `backend/app/services/classification.py` or `frontend/src/cesiumView.js`)
- Glob for the file — if missing: flag as **BLOCKING**

### 2c. Check test file exists
- Backend: glob `backend/tests/**/test_*.py` corresponding to the code location
- Frontend: glob `frontend/**/*.test.js` (or `__tests__/`) corresponding to the module
- If no matching test file: flag as **WARNING** (some specs like data files, config-only, or AWS/host setup don't have unit tests)

### 2d. Check tests pass
- Backend: `cd backend && python -m pytest {test_file} -v --tb=short -q`
- Frontend: `npm --prefix frontend run test -- {test_file}` (or `npx vitest run {test_file}`)
- If tests fail: flag as **BLOCKING**

## Step 3: Report

Print a summary table:

```
Dependency Check for {spec_id}
─────────────────────────────
| Dep   | Status  | Code | Tests | Result    |
|-------|---------|------|-------|-----------|
| S4.5  | done    | ✓    | ✓ 6/6 | READY     |
| S4.6  | pending | ✓    | ✗ 2/4 | BLOCKING  |
```

Final verdict:
- **READY**: All deps satisfied → safe to implement
- **BLOCKED**: List which deps need work first, in dependency order

(For the conjunction engine especially, confirm S5.6 — the brute-force oracle — passes before trusting S5.3's cKDTree screen.)
