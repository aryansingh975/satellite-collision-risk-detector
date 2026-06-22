# Spec S4.2 — Single-Sat Propagation

## Overview
Implements `propagate(sat, times)` — a function that takes a single `Satrec` object (built by S4.1) and a sequence of datetime-like timestamps, propagates the satellite's state via SGP4, and returns TEME position (km) and velocity (km/s) arrays for each time. Critically, the function must surface nonzero SGP4 error codes (e.g. error code 6 = satellite has decayed) rather than silently returning garbage zeros or NaN values. This is the single-satellite propagation primitive consumed by the positions endpoint (S6.2) and the TEME→geodetic display pipeline (S4.4).

## Dependencies
- S4.1 — Satrec builder (provides `Satrec` / `SatrecArray` with WGS-72 constants)

## Target Location
`backend/app/services/propagation.py`

---

## Functional Requirements

### FR-1: Propagate single satellite over a time sequence
- **What**: `propagate(sat: Satrec, times: list[datetime]) -> tuple[np.ndarray, np.ndarray]` propagates `sat` at each UTC datetime in `times` and returns `(positions, velocities)` where `positions` has shape `(N, 3)` (km, TEME) and `velocities` has shape `(N, 3)` (km/s, TEME).
- **Inputs**: `sat` — a `sgp4.api.Satrec` object from `Satrec.twoline2rv`; `times` — non-empty sequence of `datetime` objects (UTC, timezone-aware or naive-UTC). Must use WGS-72 gravity constants (inherited from S4.1 builder).
- **Outputs**: Tuple `(pos_km, vel_kms)` — NumPy arrays shape `(N, 3)`, dtype float64, TEME frame. No NaN or zeros masking an SGP4 error.
- **Edge cases**: Empty `times` list → return `(np.empty((0,3)), np.empty((0,3)))`; single timestamp → shape `(1, 3)`.

### FR-2: Surface SGP4 error codes — never return garbage
- **What**: After each SGP4 call, inspect the returned error code. If any timestep returns a nonzero error code, raise a descriptive exception (e.g. `PropagationError`) rather than returning the zero/garbage position SGP4 writes on error. Include the satellite catalog number and error code in the message.
- **Inputs**: SGP4 integer error code from `sat.sgp4(jd, fr)` or the vectorized equivalent.
- **Outputs**: `PropagationError(f"SGP4 error {code} for sat {catalog_no} at {t}")` raised. Error code 6 specifically means the satellite has decayed below the Earth's surface.
- **Edge cases**: Error codes 1–6 all treated as fatal for that timestep. Partial success (some timesteps ok, one fails) still raises — do not silently drop the bad sample.

### FR-3: Julian date conversion
- **What**: Convert each `datetime` to Julian date (JD integer) + fraction (fr) required by `sat.sgp4(jd, fr)`, using `sgp4.api.jday` or equivalent. Preserve sub-second accuracy via the fractional day component.
- **Inputs**: `datetime` objects (UTC). Timezone-naive inputs are treated as UTC.
- **Outputs**: `jd` (int or float) + `fr` (float) pair suitable for `Satrec.sgp4()`.
- **Edge cases**: Datetimes far from TLE epoch (>14 days) are propagated without error at the function level — accuracy degradation is a caller concern, not surfaced as an exception here (CLAUDE.md: "propagate only a few days to ~2 weeks").

---

## Tangible Outcomes

- [ ] **Outcome 1**: `propagate(iss_sat, [t0])` returns positions and velocities that match the published SGP4 verification vectors for ISS (NORAD 25544) within ±1 km / ±0.001 km/s.
- [ ] **Outcome 2**: Calling `propagate` with a decayed satellite (or times far past decay) raises `PropagationError` with error code in the message — no silent garbage return.
- [ ] **Outcome 3**: Return shapes are exactly `(N, 3)` for N input times; dtype is float64; TEME frame (not geodetic).
- [ ] **Outcome 4**: Empty `times` list returns `(np.empty((0,3)), np.empty((0,3)))` without error.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_propagate_iss_position_accuracy**: Build ISS Satrec from known TLE fixture; propagate at the TLE epoch; assert position within ±1 km and velocity within ±0.001 km/s of published SGP4 verification vectors.
2. **test_propagate_returns_correct_shape**: Propagate over N=5 timestamps; assert `pos.shape == (5, 3)` and `vel.shape == (5, 3)`.
3. **test_propagate_dtype_float64**: Assert output arrays are dtype float64.
4. **test_propagate_error_code_raises**: Construct a Satrec from a synthetic TLE that will produce SGP4 error 6 (eccentricity out of range or decayed orbit); assert `PropagationError` is raised.
5. **test_propagate_empty_times**: Call `propagate(sat, [])` and assert returns `(np.empty((0,3)), np.empty((0,3)))` with no exception.
6. **test_propagate_single_timestamp**: Propagate at exactly one time; assert shapes `(1, 3)`.
7. **test_propagate_partial_error_raises**: If any timestep errors, the whole call raises rather than silently dropping the bad sample.

### Mocking Strategy
- CelesTrak HTTP: not applicable to this spec (no network calls).
- Propagation fixtures: use ISS TLE (NORAD 25544) from a pinned fixture in `conftest.py`; compare against published SGP4 test vectors (Vallado et al.).
- DB: not applicable to this spec.
- Do NOT hit the live CelesTrak API in any test.

### Coverage Expectation
- All public functions (`propagate`, `PropagationError`) have tests; all error-code paths covered; shape/dtype invariants verified.

---

## References
- roadmap.md Phase 4, S4.2 row
- CLAUDE.md: WGS-72 constants; TEME frame for conjunction math; propagate only 2 weeks from epoch
- sgp4 library docs: `Satrec.sgp4(jd, fr)` → `(e, r, v)` where `e` is error code, `r`/`v` are TEME km / km·s⁻¹
