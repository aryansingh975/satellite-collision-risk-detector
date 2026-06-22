# Spec S5.4 — TCA Refinement & Miss Distance

## Overview
After the coarse cKDTree spatial screen (S5.3) flags candidate pairs with a close approach within
COARSE_RADIUS_KM, this spec refines each flagged pair to find its precise Time of Closest Approach
(TCA). Dense re-propagation at ~1-second steps is performed in a narrow bracket around the coarse
minimum; the range-rate sign change (`r_rel · v_rel = 0`) pinpoints the TCA. Outputs are TCA
timestamp, miss_km (separation at TCA), and rel_vel_kms (relative speed at TCA) — the three values
consumed by S5.5's risk scorer and ultimately exposed through the REST API.

## Dependencies
- S5.3 (cKDTree spatial screen) — must be `done`

## Target Location
`backend/app/services/conjunctions.py`

---

## Functional Requirements

### FR-1: Dense bracket propagation
- **What**: For each flagged `(sat_a_idx, sat_b_idx, coarse_t_idx)` from S5.3, propagate both
  satellites over a dense time bracket — from `t[coarse_t_idx] - SCREEN_STEP_SECONDS` to
  `t[coarse_t_idx] + SCREEN_STEP_SECONDS` — at 1-second resolution.
- **Inputs**: Pair tuple `(sat_a_idx, sat_b_idx, coarse_t_idx)`, the `SatrecArray` (or Satrec
  list), the coarse time grid (`jds`, `frs` arrays), and `SCREEN_STEP_SECONDS` config value.
- **Outputs**: Dense NumPy arrays of TEME positions (km) and velocities (km/s) for both satellites
  over the bracket window; shape `(n_dense_steps, 3)` per satellite.
- **Edge cases**:
  - SGP4 nonzero error code during dense propagation → skip pair and log a warning with the error
    code; return `None` for this pair.
  - `coarse_t_idx` at array boundary (first or last step) → clamp bracket start/end to valid grid
    bounds rather than indexing out of range.

### FR-2: Range-rate zero-crossing detection (TCA)
- **What**: Compute the range-rate scalar at each dense timestep as
  `ṙ = dot(r_rel, v_rel) / |r_rel|`
  where `r_rel = pos_a - pos_b` and `v_rel = vel_a - vel_b` (all in TEME, km and km/s).
  Detect where the sign changes from negative (approaching) to positive (receding) — that crossing
  is the TCA. Linearly interpolate the two bounding timesteps to sub-second precision.
- **Inputs**: Dense TEME position and velocity arrays from FR-1; dense time values (Julian dates).
- **Outputs**: `tca` as a UTC `datetime`, `miss_km` (float, separation at TCA), `rel_vel_kms`
  (float, `|v_rel|` at TCA timestep).
- **Edge cases**:
  - No sign change within bracket (monotonically increasing separation after coarse flag) → fall
    back to the dense timestep with minimum `|r_rel|` as TCA.
  - Multiple sign changes in bracket → take the zero-crossing whose neighbouring minimum `|r_rel|`
    is smallest (global minimum within bracket).
  - `|r_rel| ≈ 0` (near-physical collision) → apply a small floor (e.g. 1e-6 km) to avoid
    division-by-zero in the range-rate formula; still return the miss_km truthfully.

### FR-3: Output contract
- **What**: `refine_tca(flagged_pairs, satrec_array, jds, frs, screen_step_s)` returns a list of
  `TCARefinement` named-tuple/dataclass instances with fields
  `(sat_a_idx, sat_b_idx, tca: datetime, miss_km: float, rel_vel_kms: float)`. Returns `None`
  for pairs that fail propagation or are otherwise unresolvable; callers filter out `None`.
- **Inputs**: Iterable of `(sat_a_idx, sat_b_idx, coarse_t_idx)` tuples from S5.3.
- **Outputs**: List of `TCARefinement` (one per successfully refined pair; `None` entries for
  failures).
- **Edge cases**:
  - Empty input list → return empty list immediately.
  - `miss_km > COARSE_RADIUS_KM` (false positive from the coarse screen) → still return the
    result; S5.5 will filter by `RISK_THRESHOLD_KM`.

---

## Tangible Outcomes

- [ ] **Outcome 1**: Given two synthetic satellites with a known closest approach at a specific UTC
  time, `refine_tca` returns a TCA within ±2 seconds and `miss_km` within ±0.1 km of ground truth.
- [ ] **Outcome 2**: When the dense bracket contains no range-rate sign change (monotonically
  increasing separation), the function returns the bracketed-minimum result without raising any
  exception.
- [ ] **Outcome 3**: When SGP4 returns a nonzero error code during dense propagation, the pair
  entry is `None` — no exception propagates to the caller.
- [ ] **Outcome 4**: `rel_vel_kms` equals `|v_a - v_b|` evaluated at the returned TCA timestep
  (verified against the same synthetic geometry used in Outcome 1).
- [ ] **Outcome 5**: Calling `refine_tca` with an empty flagged-pair list returns `[]` without
  error.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_refine_tca_known_geometry**: Build two `Satrec` objects from synthetic TLEs whose closest
   approach is at a known UTC second; call `refine_tca`; assert TCA within ±2 s and miss_km within
   ±0.1 km of ground truth.
2. **test_refine_tca_no_zero_crossing**: Supply positions where separation is monotonically
   increasing over the bracket; assert function returns a non-`None` result (fallback to minimum)
   without raising.
3. **test_refine_tca_sgp4_error**: Inject a decayed satellite (SGP4 error code 6) as one of the
   pair; assert the returned entry is `None` and no exception propagates.
4. **test_refine_tca_empty_pairs**: Call with an empty list; assert the return value is `[]`.
5. **test_refine_tca_rel_vel**: Using the same synthetic geometry as test 1, assert `rel_vel_kms`
   equals `|v_a - v_b|` at the returned TCA timestep to within floating-point precision.
6. **test_refine_tca_multiple_zero_crossings**: Construct or mock a dense time series with two
   range-rate sign changes; assert the returned TCA corresponds to the timestep with the smallest
   `|r_rel|` (global minimum).

### Mocking Strategy
- No external HTTP — all propagation uses real `sgp4` / `SatrecArray` on known TLE fixtures.
- Use ISS TLE (catalog 25544) and one other active LEO TLE as a realistic close-pass fixture.
- SGP4 verification vectors (Vallado et al.) confirm propagation correctness before testing TCA
  logic; do not re-test propagation itself here (covered by S4.2/S4.3).
- Pure-computation spec: no DB writes, no CelesTrak calls, no mocking of HTTP needed.

### Coverage Expectation
- All public functions (`refine_tca`, any private helpers) have at least one test.
- Every edge case in FR-1 and FR-2 is covered by a dedicated test.

---

## References
- roadmap.md (S5.4 row + Notes), CLAUDE.md (TEME frame rule, WGS-72 constants, risk threshold)
- Vallado et al., "Fundamentals of Astrodynamics and Applications" — SGP4 verification vectors
- Range-rate formula: `ṙ = (r_rel · v_rel) / |r_rel|`; TCA when `ṙ` changes sign negative→positive
