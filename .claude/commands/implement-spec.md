---
description: Implement a Satellite Collision Risk Detector spec following TDD and best practices
argument-hint: spec-id (e.g., S3.2, S5.1, S7.4)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

Implement spec: $1

## Step 1: Load Spec Context

1. Find the spec folder: search for `specs/spec-$1*` or look up in `roadmap.md` Master Spec Index
2. Read `specs/spec-{id}-{slug}/spec.md` — requirements, outcomes, TDD notes
3. Read `specs/spec-{id}-{slug}/checklist.md` — phases to follow
4. Read `roadmap.md` phase-table row for this spec — Location, Feature, Notes
5. Read `CLAUDE.md` for project rules (TEME frame, WGS-72, 2h cache, no hardcoded tokens, etc.)

## Step 2: Verify Prerequisites

- Dependencies (Depends On) are `done` (run `/check-spec-deps $1` if unsure)
- Target files/locations exist or can be created
- Determine backend (Python/pytest) vs frontend (JS/Vitest)

## Step 3: Follow TDD Strictly

**Red → Green → Refactor**

1. **Red**: Write failing tests first.
   - Backend: `backend/tests/` mirroring app structure. Mock CelesTrak HTTP (`respx`/`MockTransport`); use in-memory SQLite; assert propagation against ISS fixtures / SGP4 verification vectors. Run `make local-test` — expect failures.
   - Frontend: `frontend/src/__tests__/`. Mock `fetch`/api.js; use fixed positions & conjunctions fixtures. Run `npm --prefix frontend run test` — expect failures.
   - For the conjunction screen (S5.3), write the **brute-force oracle** test (S5.6) and assert the cKDTree result equals all-pairs on a small set.
2. **Green**: Implement minimal code to pass tests. No extra features beyond spec.
3. **Refactor**: Clean up; re-run tests after each change.

**Checklist updates**: After completing each phase (Setup, Tests, Implementation, Integration), immediately update `checklist.md` — change `- [ ]` to `- [x]` for every item completed in that phase. Do not wait until the end.

## Step 4: Implementation Rules

| Rule | Action |
|------|--------|
| Concurrency | Async for I/O (CelesTrak fetch, endpoints); sync NumPy/SciPy for propagation + screening; offload long screens off the event loop |
| Config | All URLs/thresholds/tokens from `config.py`, never hardcode |
| CelesTrak | Respect 2h cadence + one-download-per-update; cache; handle HTTP 403 by using cache |
| Retries | Tenacity (3 attempts, exponential backoff) on the CelesTrak fetch |
| Frames | Conjunction math in TEME; convert to geodetic only for display |
| SGP4 | WGS-72 gravity constants; surface nonzero error codes (decayed sats) |
| Logging | Loguru with request_id where applicable (backend) |
| Models | Pydantic for all in/out; use `backend/app/models/schemas.py` |
| Secrets | Never commit the Cesium ion token or any key; `.env` only |
| Lint | Ruff line length 100 (backend); Prettier/ESLint (frontend); run before done |

## Step 5: Verification

- [ ] All tests pass: `make local-test` (backend) / `npm --prefix frontend run test` (frontend)
- [ ] Lint passes: `make local-lint` (backend) / `npm --prefix frontend run lint` (frontend)
- [ ] All Tangible Outcomes from spec.md are met

## Step 6: Update Checklist & Roadmap

After all tests pass and verification is complete:

### 6a. Finalize checklist.md
1. Mark all remaining Phase 5 (Verification) items as `- [x]` in `checklist.md`
2. Confirm every item across all phases is `- [x]` — no unchecked items should remain
3. If any item was skipped (not applicable), change it to `- [x] N/A — {reason}`

### 6b. Update roadmap.md
1. Find the spec row in **both** the Phase table and the Master Spec Index table
2. Change the Status column from `spec-written` (or `pending`) to `done` for this spec in **both** tables
3. Verify the edit — ensure no other rows were accidentally modified

Work through checklist.md phases in order. Do not skip "Tests First". Update checklist.md progressively as each phase completes — not all at once at the end. When done, report completion and confirm both checklist.md and roadmap.md were updated.
