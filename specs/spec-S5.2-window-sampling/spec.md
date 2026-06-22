# Spec S5.2 — Position Sampling Over Window

## Overview
The window-sampling step is the second stage of the conjunction engine, sitting between the
apogee/perigee sieve (S5.1) and the cKDTree spatial screen (S5.3). It takes the subset of
satellite pairs that survived the altitude sieve, extracts the unique satellites involved, builds
a uniform UTC time grid spanning `SCREEN_WINDOW_HOURS` at `SCREEN_STEP_SECONDS` resolution, and
vectorizes propagation of those satellites via `SatrecArray.sgp4` (S4.3). All positions are
returned in the TEME frame (km) — no geodetic conversion occurs here. The output is a compact
position tensor `(n_unique, n_times, 3)` plus the Julian date grid and an index map that lets
S5.3 look up each original satellite's position row without searching.

## Dependencies
- **S4.3** (`propagation.py`) — `build_satrec_array` + `propagate_array` for vectorized TEME
  propagation. The `propagate_array` return contract is `(positions, velocities, error_codes)`;
  S5.2 uses positions and error_codes only.
- **S5.1** (`conjunctions.py`) — `apogee_perigee_sieve` returns the surviving `(i, j)` index
  pairs that feed into this function. S5.2's inputs are undefined without S5.1 producing output.

## Target Location
`backend/app/services/conjunctions.py`

---

## Functional Requirements

### FR-1: Time grid construction
- **What**: Build a uniform grid of UTC times from `t_start` to `t_start + window_hours`, spaced
  `step_seconds` apart. Convert each time to a `(jd, fr)` Julian date pair for `SatrecArray.sgp4`.
- **Inputs**:
  - `t_start: datetime` — UTC start of the screening window (timezone-naive or timezone-aware UTC).
  - `window_hours: float` — total window length in hours (config: `SCREEN_WINDOW_HOURS`, 24–72).
  - `step_seconds: float` — sample spacing in seconds (config: `SCREEN_STEP_SECONDS`, 30–60).
- **Outputs**:
  - `jds: np.ndarray` — shape `(n_times,)` float64, Julian date integer parts.
  - `frs: np.ndarray` — shape `(n_times,)` float64, Julian date fractional parts.
  - `n_times = max(1, floor(window_hours * 3600 / step_seconds) + 1)` — inclusive of both
    endpoints; always at least one timestep even if `step_seconds > window_hours * 3600`.
- **Edge cases**:
  - `window_hours = 0` → single timestep at `t_start`.
  - `step_seconds` larger than the window → single timestep at `t_start`.
  - Fractional seconds in `t_start` are preserved in the Julian date calculation.

### FR-2: Unique satellite extraction
- **What**: From the survivor pairs, collect the sorted deduplicated set of satellite indices that
  need to be propagated, and produce a compact mapping so downstream code can translate from
  original index to local (row) index in the position tensor.
- **Inputs**:
  - `survivors: list[tuple[int, int]]` — output of `apogee_perigee_sieve`.
- **Outputs**:
  - `unique_indices: list[int]` — sorted list of unique original satellite indices appearing in
    any pair. Length `n_unique`.
  - Implicit mapping: position row `k` corresponds to original satellite `unique_indices[k]`.
- **Edge cases**:
  - Empty `survivors` → `unique_indices = []`; positions shape `(0, n_times, 3)`.
  - A satellite index may appear in many pairs; it must appear exactly once in `unique_indices`.

### FR-3: Vectorized bulk propagation
- **What**: Build a `SatrecArray` from the unique satellite `Satrec` objects and call
  `propagate_array(satrec_arr, jds, frs)` (S4.3) to obtain TEME positions for all unique
  satellites across the full time grid in one vectorized call.
- **Inputs**:
  - `satrecs: list[Satrec]` — one `Satrec` per satellite in the full catalog, indexed the same
    way as the sieve input. Only the subset at `unique_indices` is assembled into `SatrecArray`.
  - `jds, frs` — from FR-1.
- **Outputs**:
  - Raw positions `(n_unique, n_times, 3)` float64 TEME km.
  - `error_codes (n_unique, n_times)` from `propagate_array` for error handling (FR-4).
- **Edge cases**:
  - `unique_indices = []` → skip `SatrecArray` construction; return shape `(0, n_times, 3)`.
  - Single satellite pair → `SatrecArray` with one element; `propagate_array` still works.

### FR-4: SGP4 error handling
- **What**: Satellites with any non-zero SGP4 error code (e.g., error 6 = decayed orbit) must
  not silently produce garbage positions. Their positions are set to `NaN` for all timesteps
  where `error_codes[k, t] != 0`, and a `WARNING` log is emitted with the satellite's original
  index. The function does NOT raise an exception — resilience is required for a live catalog
  that may contain a handful of decayed objects.
- **Inputs**: `error_codes (n_unique, n_times)` from `propagate_array`.
- **Outputs**: modified `positions` tensor with `NaN` where errors occurred.
- **Edge cases**:
  - All timesteps for a satellite have errors → entire row is NaN; downstream S5.3 skips those
    pairs naturally (NaN distances are never ≤ threshold).
  - Zero error codes → no logging, no NaN injection; fast path.

### FR-5: Return contract
- **What**: `sample_window` returns a 4-tuple `(positions, jds, frs, unique_indices)` that
  fully describes the sampled window for S5.3 consumption.
- **Outputs**:
  - `positions: np.ndarray` — shape `(n_unique, n_times, 3)` float64 TEME km, NaN where SGP4
    errors occurred.
  - `jds: np.ndarray` — shape `(n_times,)` float64.
  - `frs: np.ndarray` — shape `(n_times,)` float64.
  - `unique_indices: list[int]` — length `n_unique`; `positions[k]` belongs to
    original satellite `unique_indices[k]`.
- **Edge cases**:
  - If `survivors = []` → `positions.shape == (0, n_times, 3)`, `unique_indices == []`.
    `jds` and `frs` still span the full requested window (S5.3 skips gracefully with no pairs).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `sample_window([], satrecs, t_start, 48, 60)` returns positions with shape
  `(0, n_times, 3)` and `unique_indices == []`.
- [ ] **Outcome 2**: With survivors `[(0, 1), (1, 2)]` and 3 satrecs, `unique_indices == [0, 1, 2]`
  and `positions.shape == (3, n_times, 3)`.
- [ ] **Outcome 3**: For a 24 h window / 60 s step, `n_times == 1441` (inclusive endpoints).
- [ ] **Outcome 4**: `jds[0]` and `frs[0]` correspond to `t_start`; `jds[-1] + frs[-1]` ≈
  `jds[0] + frs[0] + 1.0` (24 h = 1 Julian day).
- [ ] **Outcome 5**: Positions of the ISS (catalog 25544) at `t_start` have magnitude in the
  range 6500–7000 km (LEO orbit radius).
- [ ] **Outcome 6**: A satellite whose `Satrec.sgp4` returns error code 6 (decayed) has its
  position rows set to `NaN`, and a WARNING is emitted via Loguru.
- [ ] **Outcome 7**: All returned positions are in TEME km — no lat/lon/alt values appear.
- [ ] **Outcome 8**: `unique_indices` is always sorted in ascending order.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_empty_survivors_returns_zero_sats**: `sample_window([], satrecs, t_start, 24, 60)` →
   `positions.shape[0] == 0`, `unique_indices == []`, `len(jds) > 0`.
2. **test_time_grid_inclusive_endpoints**: 24 h window / 60 s step → `len(jds) == 1441`.
3. **test_time_grid_start_matches_t_start**: `jds[0]` + `frs[0]` round-trips back to `t_start`
   within 1 ms tolerance.
4. **test_time_grid_step_spacing**: difference between consecutive `jds + frs` values ≈
   `step_seconds / 86400.0` (Julian days).
5. **test_step_larger_than_window_gives_one_timestep**: `window_hours=1`, `step_seconds=7200` →
   `len(jds) >= 1`.
6. **test_unique_indices_deduplicated**: survivors `[(0,1),(1,2),(0,2)]` → `unique_indices == [0,1,2]`.
7. **test_unique_indices_sorted**: survivors `[(2,3),(0,1)]` → `unique_indices == [0,1,2,3]`.
8. **test_positions_shape**: 2 unique sats from survivors, 24 h / 60 s → `positions.shape == (2, 1441, 3)`.
9. **test_iss_position_magnitude_in_leo_range**: ISS TLE (catalog 25544) propagated at a known
   epoch → `np.linalg.norm(positions[0, 0, :])` in range 6500–7000 km.
10. **test_decayed_satellite_positions_are_nan**: construct a Satrec whose propagation always
    returns error code 6 (mock `sgp4` call); `positions[k]` is all NaN and a WARNING is logged.
11. **test_no_nan_for_valid_sats**: valid ISS TLE over 1 h window → no NaN in positions.
12. **test_positions_frame_is_teme_not_geodetic**: position magnitudes ~6000–8000 km, not latitude
    values (|lat| ≤ 90).
13. **test_single_pair_two_unique**: survivors `[(0, 1)]` with 2 satrecs → `unique_indices == [0, 1]`,
    `positions.shape[0] == 2`.
14. **test_empty_satrecs_empty_survivors**: both satrecs=[] and survivors=[] → no crash, shape
    `(0, n_times, 3)`.

### Mocking Strategy
- **CelesTrak HTTP**: not touched by S5.2 — no mocking needed.
- **SGP4 errors**: mock `SatrecArray.sgp4` (via `unittest.mock.patch` or `monkeypatch`) to
  return non-zero error codes for specific satellites to test FR-4.
- **Satrec fixtures**: use the ISS TLE (catalog 25544) and a second known LEO TLE as fixtures
  in `conftest.py`; build Satrec objects with `Satrec.twoline2rv(l1, l2)`.
- **DB**: not required — S5.2 is a pure propagation function; no DB access.
- **Time**: pass an explicit `t_start` (e.g., `datetime(2024, 1, 1, 0, 0, 0)`) in all tests —
  no calls to `datetime.utcnow()`.

### Coverage Expectation
- All public functions (`sample_window`) have tests.
- Empty survivors, single pair, multi-pair cases all covered.
- Time grid length, start value, and step spacing all asserted.
- SGP4 error → NaN path exercised with a mock.
- At least one integration-level test uses real ISS TLE propagation.

---

## References
- `roadmap.md` — Phase 5 table, S5.2 row; Notes (vectorized propagation, SCREEN_WINDOW_HOURS,
  SCREEN_STEP_SECONDS).
- `CLAUDE.md` — SCREEN_WINDOW_HOURS (24–72), SCREEN_STEP_SECONDS (30–60), COARSE_RADIUS_KM
  (10–20), conjunction math stays in TEME, WGS-72 constants, propagation accuracy note.
- S4.3 spec + `propagation.py` — `build_satrec_array`, `propagate_array(satrec_arr, jds, frs)`
  returning `(positions (n,t,3), velocities (n,t,3), error_codes (n,t))`.
- S5.1 spec + `conjunctions.py` — `apogee_perigee_sieve` output contract: `list[tuple[int,int]]`.
- S5.3 spec (pending) — consumes `(positions, jds, frs, unique_indices)` for per-timestep
  cKDTree queries.
