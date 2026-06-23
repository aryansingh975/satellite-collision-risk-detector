# Checklist — Spec S5.6: Brute-Force Correctness Oracle

## Phase 1: Setup & Dependencies
- [x] Verify S5.3 is `done` (cKDTree Spatial Screen)
- [x] Locate target file: `backend/tests/services/test_conjunctions.py` (already exists — will add oracle tests)
- [x] No new imports or dependencies needed beyond NumPy (already in pyproject.toml)

## Phase 2: Tests First (TDD)
- [x] Write `test_oracle_single_timestep_exact_match` — 6 satellites, 1 timestep, all pairs as survivors; assert found_pairs == brute-force pairs
- [x] Write `test_oracle_multi_timestep_per_step_agreement` — 4 satellites, 4 timesteps with varying separations; validate each timestep independently
- [x] Write `test_oracle_survivor_filter_respected` — 3 satellites, pair (0,2) spatially close but excluded from survivors; assert (0,2) not in output
- [x] Write `test_oracle_boundary_at_radius_excluded` — verifies inclusive ≤ r semantics: pair at exactly r IS flagged; pair at r+0.001 is not
- [x] Write `test_oracle_large_grid_no_false_negatives_or_positives` — 20-satellite 3D grid, all pairs as survivors; assert full set equality
- [x] Run tests — initial run revealed FR-4 spec error (strict < r vs ≤ r); corrected spec + test; all 18 pass (Green immediately after fix)

## Phase 3: Implementation
- [x] Add oracle tests to `backend/tests/services/test_conjunctions.py` under a clearly labelled section
- [x] Implement `_brute_force_pairs(positions, t, radius)` helper that returns `set[tuple[int,int]]` for a given timestep (O(n²), used only in tests)
- [x] Run tests — all five oracle tests pass (Green); 18/18 total in the file
- [x] Refactor helper if duplication exists between tests — single `_brute_force_pairs` shared by all oracle tests

## Phase 4: Integration
- [x] No app wiring needed — this spec is test-only
- [x] Run lint: ruff check backend/tests/services/test_conjunctions.py — all checks passed
- [x] Run full backend test suite: 239/239 passed, 0 regressions

## Phase 5: Verification
- [x] All 5 tangible outcomes checked off
- [x] No hardcoded secrets or tokens
- [x] Tests are purely synthetic (no CelesTrak HTTP, no DB, no SGP4)
- [x] Each test includes a docstring stating the expected brute-force result for traceability
- [x] Update roadmap.md status: `spec-written` → `done`
