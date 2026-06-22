# Checklist — Spec S5.2: Position Sampling Over Window

## Phase 1: Setup & Dependencies
- [x] Verify S4.3 is `done` — `build_satrec_array` and `propagate_array` available in
  `backend/app/services/propagation.py`
- [x] Verify S5.1 is `done` — `apogee_perigee_sieve` available in
  `backend/app/services/conjunctions.py`
- [x] Confirm `sgp4`, `numpy`, `loguru` are already declared in `pyproject.toml` (no new deps needed)
- [x] N/A — no shared conftest.py; ISS TLE fixture defined inline per test file (established pattern)

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/services/test_window_sampling.py`
- [x] Write `test_empty_survivors_returns_zero_sats`
- [x] Write `test_time_grid_inclusive_endpoints`
- [x] Write `test_time_grid_start_matches_t_start`
- [x] Write `test_time_grid_step_spacing`
- [x] Write `test_step_larger_than_window_gives_one_timestep`
- [x] Write `test_unique_indices_deduplicated`
- [x] Write `test_unique_indices_sorted`
- [x] Write `test_positions_shape`
- [x] Write `test_iss_position_magnitude_in_leo_range`
- [x] Write `test_decayed_satellite_positions_are_nan` (mock SGP4 error code 6)
- [x] Write `test_no_nan_for_valid_sats`
- [x] Write `test_positions_frame_is_teme_not_geodetic`
- [x] Write `test_single_pair_two_unique`
- [x] Write `test_empty_satrecs_empty_survivors`
- [x] Run tests — expect failures (Red): confirmed ImportError (sample_window not yet defined)

## Phase 3: Implementation
- [x] Add `sample_window` function to `backend/app/services/conjunctions.py`
- [x] Implement FR-1: `_build_time_grid` helper — inclusive endpoints, min 1 timestep
- [x] Implement FR-2: extract sorted `unique_indices` from `survivors` via set comprehension
- [x] Implement FR-3: build `SatrecArray(subset)` directly from Satrec objects, call
  `propagate_array(satrec_arr, jds, frs)`; short-circuit on empty `unique_indices`
- [x] Implement FR-4: set `positions[k, bad, :] = NaN` where `error_codes[k] != 0`; emit
  `logger.warning(...)` for each affected satellite
- [x] Implement FR-5: return `(positions, jds, frs, unique_indices)`
- [x] Run tests — 15/15 pass (Green)
- [x] Refactor: tolerance note added to `test_time_grid_step_spacing` (catastrophic cancellation
  at JD ≈ 2.46e6 requires atol rather than rtol)

## Phase 4: Integration
- [x] Confirm `sample_window` is importable from `backend/app/services/conjunctions.py`
- [x] Confirm the function is ready to receive S5.1 output directly (no adapter needed)
- [x] Run lint: `ruff check + format` — all clean (100 char line limit)
- [x] Run full test suite: 200/200 pass, 0 regressions
- [x] Confirm no existing S5.1 tests are broken (13/13 still pass)

## Phase 5: Verification
- [x] All 8 tangible outcomes checked — covered by 15 passing tests
- [x] No hardcoded `SCREEN_WINDOW_HOURS` / `SCREEN_STEP_SECONDS` values — params passed in by caller
- [x] Loguru WARNING emitted for decayed satellites (error code ≠ 0), includes original sat index
  and timestep count; captured and asserted in `test_decayed_satellite_positions_are_nan`
- [x] Positions returned in TEME km — no geodetic conversion anywhere in `sample_window`
- [x] `unique_indices` is always sorted ascending — verified by `test_unique_indices_sorted`
- [x] Empty-survivors path returns shape `(0, n_times, 3)` without touching `SatrecArray`
- [x] Update `roadmap.md` status: `spec-written` → `done`
