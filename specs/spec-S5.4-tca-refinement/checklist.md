# Checklist — Spec S5.4: TCA Refinement & Miss Distance

## Phase 1: Setup & Dependencies
- [x] Verify S5.3 (cKDTree spatial screen) is `done`
- [x] Locate `backend/app/services/conjunctions.py` — confirm cKDTree screen output contract
      (flagged pairs as `(sat_a_idx, sat_b_idx, coarse_t_idx)` tuples)
- [x] No new `pyproject.toml` dependencies needed (`sgp4`, `numpy` already declared in S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_tca_refinement.py`
- [x] Write `test_refine_tca_known_geometry` (Red)
- [x] Write `test_refine_tca_no_zero_crossing` (Red)
- [x] Write `test_refine_tca_sgp4_error` (Red)
- [x] Write `test_refine_tca_empty_pairs` (Red)
- [x] Write `test_refine_tca_rel_vel` (Red)
- [x] Write `test_refine_tca_multiple_zero_crossings` (Red)
- [x] Run `.venv/Scripts/python.exe -m pytest backend/tests/services/test_tca_refinement.py -v` — confirmed all failures (ImportError on missing symbols)

## Phase 3: Implementation
- [x] Define `TCARefinement` frozen dataclass in `conjunctions.py`:
      `(sat_a_idx, sat_b_idx, tca: datetime, miss_km: float, rel_vel_kms: float)`
- [x] Add `_J2000_JD` / `_J2000_EPOCH` constants + `_jd_to_utc` helper
- [x] Implement `_build_dense_bracket(jds, frs, coarse_t_idx, screen_step_s)`:
  - [x] Build dense bracket `jd`/`fr` arrays (±`screen_step_s` at 1 s resolution)
  - [x] Clamp bracket when `coarse_t_idx` is at array boundary
- [x] Implement `_find_tca_in_bracket(pos_a, vel_a, pos_b, vel_b, dense_jds, dense_frs)`:
  - [x] Compute `r_rel = pos_a - pos_b`, `v_rel = vel_a - vel_b` at each dense step
  - [x] Compute range-rate `ṙ = dot(r_rel, v_rel) / max(|r_rel|, 1e-6)`
  - [x] Detect sign changes (negative→positive); handle multiple crossings (pick global min dist)
  - [x] Fallback to argmin `|r_rel|` when no sign change detected
  - [x] Linearly interpolate TCA between the two bounding timesteps
  - [x] Extract `miss_km = |r_rel|` and `rel_vel_kms = |v_rel|` at TCA step
- [x] Implement `refine_tca(flagged_pairs, satrec_list, jds, frs, screen_step_s)`:
  - [x] Return `[]` for empty input
  - [x] Check init-time SGP4 errors (`sat.error != 0`) before propagating → `None`
  - [x] Use `SatrecArray([sat_a, sat_b]).sgp4(dense_jds, dense_frs)` for vectorized propagation
  - [x] Check runtime SGP4 error codes → `None` with Loguru warning
  - [x] Return `TCARefinement` or `None` per pair
- [x] Add Loguru warning log on SGP4 skip (includes pair indices and error code)
- [x] Run tests — all 9 pass (Green)
- [x] Refactor: extracted `_build_dense_bracket` and `_find_tca_in_bracket` as testable helpers

## Phase 4: Integration
- [x] `refine_tca` is defined in `conjunctions.py` immediately after `ckdtree_screen`
- [x] Module docstring updated with S5.4 description and pipeline order comment
- [x] Output `TCARefinement` list matches what S5.5 (risk scoring) expects as input
      (fields: sat_a_idx, sat_b_idx, tca, miss_km, rel_vel_kms)
- [x] Run `ruff check + format` — clean
- [x] Run full backend test suite: 225 passed, 0 failed

## Phase 5: Verification
- [x] Outcome 1: identical TLEs → miss_km < 0.1 km ✓ (`test_refine_tca_known_geometry`)
- [x] Outcome 2: no zero crossing → fallback, no exception ✓ (`test_refine_tca_no_zero_crossing`)
- [x] Outcome 3: SGP4 init error → None returned ✓ (`test_refine_tca_sgp4_error`)
- [x] Outcome 4: identical TLEs → rel_vel_kms < 0.001 km/s ✓ (`test_refine_tca_rel_vel`)
- [x] Outcome 5: empty input → [] ✓ (`test_refine_tca_empty_pairs`)
- [x] No hardcoded secrets or tokens
- [x] Loguru warning logged when a pair is skipped due to SGP4 error
- [x] All conjunction math remains in TEME throughout (no geodetic conversion)
- [x] Update roadmap.md status: `spec-written` → `done`
