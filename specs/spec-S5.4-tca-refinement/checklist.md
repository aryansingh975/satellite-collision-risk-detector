# Checklist — Spec S5.4: TCA Refinement & Miss Distance

## Phase 1: Setup & Dependencies
- [ ] Verify S5.3 (cKDTree spatial screen) is `done`
- [ ] Locate `backend/app/services/conjunctions.py` — confirm cKDTree screen output contract
      (flagged pairs as `(sat_a_idx, sat_b_idx, coarse_t_idx)` tuples)
- [ ] No new `pyproject.toml` dependencies needed (`sgp4`, `numpy` already declared in S1.1)

## Phase 2: Tests First (TDD)
- [ ] Write test file: `backend/tests/services/test_tca_refinement.py`
- [ ] Write `test_refine_tca_known_geometry` (Red)
- [ ] Write `test_refine_tca_no_zero_crossing` (Red)
- [ ] Write `test_refine_tca_sgp4_error` (Red)
- [ ] Write `test_refine_tca_empty_pairs` (Red)
- [ ] Write `test_refine_tca_rel_vel` (Red)
- [ ] Write `test_refine_tca_multiple_zero_crossings` (Red)
- [ ] Run `python -m pytest backend/tests/services/test_tca_refinement.py -v` — expect all failures

## Phase 3: Implementation
- [ ] Define `TCARefinement` named-tuple/dataclass in `conjunctions.py`:
      `(sat_a_idx, sat_b_idx, tca: datetime, miss_km: float, rel_vel_kms: float)`
- [ ] Implement `refine_tca(flagged_pairs, satrec_array, jds, frs, screen_step_s)`:
  - [ ] Build dense bracket `jd`/`fr` arrays (±`screen_step_s` at 1 s resolution)
  - [ ] Clamp bracket when `coarse_t_idx` is at array boundary
  - [ ] Propagate both satellites over bracket; catch SGP4 nonzero error codes → return `None`
  - [ ] Compute `r_rel = pos_a - pos_b`, `v_rel = vel_a - vel_b` at each dense step
  - [ ] Compute range-rate `ṙ = dot(r_rel, v_rel) / max(|r_rel|, 1e-6)`
  - [ ] Detect sign changes (negative→positive); handle multiple crossings (pick global min dist)
  - [ ] Fallback to argmin `|r_rel|` when no sign change detected
  - [ ] Linearly interpolate TCA between the two bounding timesteps
  - [ ] Extract `miss_km = |r_rel|` and `rel_vel_kms = |v_rel|` at TCA step
  - [ ] Return `TCARefinement` or `None` per pair; return `[]` for empty input
- [ ] Add Loguru warning log on SGP4 skip (include pair indices and error code; no request_id
      needed — background computation)
- [ ] Run tests — expect all pass (Green)
- [ ] Refactor: extract `_build_dense_bracket`, `_find_tca_in_bracket` helpers if it improves
      readability without changing behaviour

## Phase 4: Integration
- [ ] Confirm `refine_tca` is called from the conjunction pipeline in `conjunctions.py` after
      S5.3's `screen_with_ckdtree` step
- [ ] Verify output `TCARefinement` list matches what S5.5 (risk scoring) expects as input
- [ ] Run `make local-lint` (ruff check + format, line length 100)
- [ ] Run full backend test suite:
      `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [ ] All 5 tangible outcomes from spec.md verified
- [ ] No hardcoded secrets or tokens
- [ ] Loguru warning logged when a pair is skipped due to SGP4 error
- [ ] All conjunction math remains in TEME throughout this function (no geodetic conversion)
- [ ] Update roadmap.md status: `spec-written` → `done` (only after implement + verify pass)
