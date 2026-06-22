# Checklist — Spec S5.1: Apogee/Perigee Sieve

## Phase 1: Setup & Dependencies
- [x] Verify S4.5 (orbital element derivation) is `done` — provides `apogee_km` / `perigee_km`
- [x] Verify S4.6 (regime classification) is `done`
- [x] Create or locate `backend/app/services/conjunctions.py` (created as new file)
- [x] No new package dependencies needed — NumPy already declared in `pyproject.toml`

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_conjunctions.py`
- [x] Write `test_empty_list_returns_empty`
- [x] Write `test_single_satellite_returns_empty`
- [x] Write `test_geo_leo_pair_rejected`
- [x] Write `test_leo_leo_overlap_survives`
- [x] Write `test_heo_leo_survives`
- [x] Write `test_pad_boundary_exactly_touching`
- [x] Write `test_pad_boundary_just_over`
- [x] Write `test_pad_boundary_just_under`
- [x] Write `test_three_sats_one_survivor`
- [x] Write `test_output_pairs_ordered`
- [x] Write `test_symmetric_rejection`
- [x] Write `test_large_catalog_no_crash`
- [x] Run tests — expect failures (Red): confirmed ImportError (module not yet created)

## Phase 3: Implementation
- [x] Implement `apogee_perigee_sieve(satellites, pad_km=30.0)` in `conjunctions.py`
- [x] Handle edge cases: empty list, single satellite
- [x] Implement rejection rule: reject if `perigee_A − apogee_B > pad_km` OR `perigee_B − apogee_A > pad_km`
- [x] Ensure output pairs satisfy `i < j`
- [x] Add NumPy-vectorized path for large catalogs (via `np.subtract.outer` + `np.triu_indices`)
- [x] Run tests — expect pass (Green): 13/13 passed
- [x] Refactor if needed — clean, no further changes required

## Phase 4: Integration
- [x] Confirm function signature is compatible with S5.2 (window sampling) — returns `list[tuple[int,int]]`
- [x] Run lint: ruff check + format — all checks passed (removed unused pytest import)
- [x] Run full test suite: 147 of 157 collected pass; 10 failures are pre-existing (apscheduler/sgp4 not in system env, unrelated to S5.1)

## Phase 5: Verification
- [x] All 7 tangible outcomes verified (see spec.md) — covered by test suite
- [x] Both rejection branches tested (perigee_A > apogee_B+pad: test_geo_leo_pair_rejected; perigee_B > apogee_A+pad: test_second_rejection_branch)
- [x] Boundary conditions covered (exactly at pad: test_pad_boundary_exactly_touching; just inside: test_pad_boundary_just_under; just outside: test_pad_boundary_just_over)
- [x] No hardcoded secrets or tokens
- [x] No external HTTP calls in this module
- [x] No geodetic conversion needed here (sieve operates on orbital elements, not positions)
- [x] Update `roadmap.md` status: `spec-written` → `done`
