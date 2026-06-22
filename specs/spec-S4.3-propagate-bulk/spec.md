# Spec S4.3 — Vectorized Bulk Propagation

## Overview
Implements `propagate_array`, which uses `sgp4`'s vectorized `SatrecArray.sgp4` to propagate
all surviving candidate satellites over a grid of Julian dates in a single NumPy call.
The function returns a `(n_sats, n_times, 3)` TEME position array (km) plus a matching velocity
array and per-element error codes. This is the performance-critical path that feeds the
conjunction screening window (S5.2): single-sat accuracy from S4.2 is verified there; here the
goal is throughput across thousands of satellites and dozens of timesteps without looping in Python.

## Dependencies
- S4.1 — `build_satrec_array` (produces the `SatrecArray` consumed here)

## Target Location
`backend/app/services/propagation.py`

---

## Functional Requirements

### FR-1: Core vectorized propagation
- **What**: `propagate_array(satrec_array, jds, frs)` calls `SatrecArray.sgp4` once and returns
  positions, velocities, and error codes without a Python loop over satellites or timesteps.
- **Inputs**:
  - `satrec_array: SatrecArray` — built by `build_satrec_array` (S4.1)
  - `jds: np.ndarray` — shape `(n_times,)`, integer part of Julian date (float64)
  - `frs: np.ndarray` — shape `(n_times,)`, fractional-day part (float64)
- **Outputs**: `tuple[np.ndarray, np.ndarray, np.ndarray]`
  - `positions` — shape `(n_sats, n_times, 3)`, TEME km, float64
  - `velocities` — shape `(n_sats, n_times, 3)`, TEME km·s⁻¹, float64
  - `error_codes` — shape `(n_sats, n_times)`, int, zero means success
- **Implementation note**: `SatrecArray.sgp4` requires the JD/FR arrays to be 2-D of shape
  `(n_sats, n_times)`. Tile the 1-D time inputs with `np.tile(jds, (n_sats, 1))` before the call.
- **Edge cases**: empty `jds`/`frs` (length 0) → return zero-length arrays with correct shapes.

### FR-2: Error-code transparency
- **What**: Do NOT raise on individual SGP4 errors (unlike `propagate`). Instead, surface the raw
  `error_codes` array so callers (S5.2) can decide whether to exclude a satellite or timestep.
  Log a summary warning if any satellite has nonzero error codes across the entire window.
- **Inputs**: `error_codes` produced by `SatrecArray.sgp4`
- **Outputs**: `error_codes` passed through as the third return value
- **Rationale**: In a bulk screen of 10 000+ satellites a few decayed objects are expected; hard
  failure here would abort the whole conjunction screen.

### FR-3: Output dtype and shape guarantee
- **What**: Positions and velocities are always `np.float64`. Shapes must match
  `(len(satrec_array), len(jds), 3)` exactly, even when some error codes are nonzero.
  Callers rely on this invariant for NumPy indexing.
- **Edge cases**: single satellite (`n_sats=1`), single timestep (`n_times=1`), both simultaneously.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `propagate_array` returns positions of shape `(n_sats, n_times, 3)` when called
  with a 3-sat array and a 5-timestep grid (3×5×3).
- [ ] **Outcome 2**: For a single ISS-like satellite propagated at one known time, the position from
  `propagate_array[0, 0]` matches `propagate` (S4.2) to within 1e-6 km (pure floating-point
  round-trip — same underlying SGP4 kernel).
- [ ] **Outcome 3**: A TLE for a known-decayed satellite produces a nonzero value in `error_codes`,
  and the corresponding position in the returned array is not silently treated as valid.
- [ ] **Outcome 4**: Empty timestep input (`jds = np.array([])`) returns arrays of shape
  `(n_sats, 0, 3)` and `(n_sats, 0)` without raising.
- [ ] **Outcome 5**: `ruff check` passes with no warnings on the updated file.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_propagate_array_shape**: Build a 3-element `SatrecArray` from three ISS-like TLE pairs;
   call with a 5-timestep JD/FR grid; assert `positions.shape == (3, 5, 3)`,
   `velocities.shape == (3, 5, 3)`, `error_codes.shape == (3, 5)`.
2. **test_propagate_array_matches_single**: Build a 1-element array from ISS TLE; propagate at one
   time; compare `positions[0, 0]` with the result of `propagate(sat, [t])[0][0]`; assert
   `np.allclose` with `atol=1e-6`.
3. **test_propagate_array_decayed_satellite**: Use a TLE with `mean_motion=0` (or a known-bad TLE)
   that triggers SGP4 error 6; assert the matching `error_codes` entry is nonzero and no exception
   is raised.
4. **test_propagate_array_empty_times**: Call with `jds=np.array([])`, `frs=np.array([])`; assert
   positions shape is `(n_sats, 0, 3)`, error_codes shape is `(n_sats, 0)`.
5. **test_propagate_array_dtype**: Assert `positions.dtype == np.float64` and
   `velocities.dtype == np.float64`.
6. **test_propagate_array_single_sat_single_time**: Shape `(1, 1, 3)` for positions when n_sats=1,
   n_times=1; exercises the degenerate edge case.

### Mocking Strategy
- No external I/O — pure NumPy/sgp4. Use fixed ISS TLE fixture (catalog 25544, from `conftest.py`).
- For the decayed-satellite test, construct a minimal `Satrec` object with a known error or a TLE
  that decays at epoch; do not hit CelesTrak.

### Coverage Expectation
- `propagate_array` and all branches (empty input, error-code logging, normal path) covered.

---

## References
- roadmap.md S4.3 row + Notes
- CLAUDE.md: WGS-72 constants, TEME frame, propagation accuracy window, `SatrecArray` for bulk
- sgp4 library: `SatrecArray.sgp4(jd_2d, fr_2d)` → `(e, r, v)` each shape `(n_sats, n_times, 3)`
