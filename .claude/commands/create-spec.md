---
description: Create spec.md and checklist.md for a Satellite Collision Risk Detector spec
argument-hint: spec-id [slug] or spec-id-slug (e.g., S5.1 apogee-perigee-sieve or S5.1-apogee-perigee-sieve)
allowed-tools: Read, Write, Edit, Grep
---

Create spec documentation for: $ARGUMENTS

## Step 1: Resolve Spec Identity

Parse from arguments:
- Two args (e.g. `S5.1 apogee-perigee-sieve`): spec_id=$1, slug=$2
- One arg (e.g. `S5.1-apogee-perigee-sieve`): parse as `spec-Sx.y-slug`, extract spec_id and slug

Read `roadmap.md` Master Spec Index or the phase tables to get:
- **Spec Location** (e.g., `specs/spec-S5.1-apogee-perigee-sieve/`)
- **Feature** (short name)
- **Location** (code file(s) — backend `backend/app/...` or frontend `frontend/src/...`)
- **Depends On** (prerequisites)
- **Notes** (constraints, formulas, thresholds, library calls)

Note whether this is a **backend** spec (Python, pytest) or a **frontend** spec (JS, Vitest) — it changes the test/lint tooling referenced below.

## Step 2: Create spec.md and checklist.md

Create the spec folder (e.g. `specs/spec-S5.1-apogee-perigee-sieve/`) and write both files. Use the templates below, substituting SPEC_ID, SLUG, and FEATURE_NAME (slug with hyphens→spaces).

**spec.md template:**
```markdown
# Spec SPEC_ID — FEATURE_NAME

## Overview
[One paragraph from roadmap Feature + Notes]

## Dependencies
[From roadmap "Depends On" column]

## Target Location
[From roadmap "Location" column]

---

## Functional Requirements

### FR-1: [Requirement name]
- **What**: Clear description of the behavior
- **Inputs**: Parameters, types, sources
- **Outputs**: Return type, side effects
- **Edge cases**: Invalid input, decayed satellite (SGP4 error code), empty/stale cache, HTTP 403, no candidate pairs, malformed TLE

### FR-2: [Add more as needed]

---

## Tangible Outcomes

- [ ] **Outcome 1**: Observable result (testable)
- [ ] **Outcome 2**: Verifiable state (testable)
- [ ] **Outcome 3**: Test assertion (testable)

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_{name}**: Description
2. **test_{name}**: ...

### Mocking Strategy
- CelesTrak HTTP: mock via `respx` / httpx `MockTransport` — never hit the live API
- Propagation: assert against known fixtures (ISS catalog 25544) and SGP4 verification vectors
- DB: in-memory SQLite
- Frontend specs: mock `fetch` / the api.js client; use a fixed positions/conjunctions fixture

### Coverage Expectation
- All public functions have at least one test; edge cases covered

---

## References
- roadmap.md (spec row + Notes), CLAUDE.md (project rules, constants, frame conventions)
```

**checklist.md template:**
```markdown
# Checklist — Spec SPEC_ID: FEATURE_NAME

## Phase 1: Setup & Dependencies
- [ ] Verify dependencies (Sx.y) are `done`
- [ ] Create or locate target files
- [ ] Add any new imports/dependencies to pyproject.toml (backend) or package.json (frontend) if needed

## Phase 2: Tests First (TDD)
- [ ] Write test file: backend/tests/.../test_{module}.py  OR  frontend/src/__tests__/{module}.test.js
- [ ] Write failing tests for each FR
- [ ] Run tests — expect failures (Red)

## Phase 3: Implementation
- [ ] Implement FR-1 — minimal code to pass its tests
- [ ] Implement FR-2 — ...
- [ ] Run tests — expect pass (Green)
- [ ] Refactor if needed

## Phase 4: Integration
- [ ] Wire into app (router include / FastAPI dependency / lifespan / Cesium entity / dashboard panel) if applicable
- [ ] Run lint (make local-lint  OR  npm --prefix frontend run lint)
- [ ] Run full test suite

## Phase 5: Verification
- [ ] All tangible outcomes checked
- [ ] No hardcoded secrets/tokens
- [ ] Logging includes request_id where applicable (backend)
- [ ] Conjunction math kept in TEME; geodetic only at display boundary (if applicable)
- [ ] Update roadmap.md status: spec-written → done (when ready)
```

## Step 3: Populate from Roadmap

Fill in the placeholders using roadmap data. Ensure:

- Overview, Dependencies, Target Location — from roadmap
- Functional Requirements — concrete, testable behaviors derived from Notes (e.g. for S5.1: the apogee/perigee rejection rule + pad; for S3.2: the 2h cadence + 403 fallback)
- Tangible Outcomes — each must be testable
- Tests to Write First — derived from FRs

## Step 4: Update Roadmap Status

After creating spec.md and checklist.md, update `roadmap.md`:
1. Find the spec row in **both** the Phase table and the Master Spec Index table
2. Change the Status column from `pending` to `spec-written` for this spec in **both** tables
3. Verify the edit — ensure no other rows were accidentally modified

## Rules

1. Extract from roadmap — do not invent; use Feature and Notes
2. Every FR must map to at least one test
3. Checklist items should be completable in 15–30 min
4. Spec folder path must match roadmap (e.g., `specs/spec-S5.1-apogee-perigee-sieve/`)
5. Always update roadmap.md status to `spec-written` — never leave it as `pending` after creating a spec

Report what was created, the path to the spec folder, and confirm roadmap.md was updated.
