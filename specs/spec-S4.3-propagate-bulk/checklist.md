# Checklist — Spec S4.3: Vectorized Bulk Propagation

## Phase 1: Setup & Dependencies
- [x] Verify S4.1 (`build_satrec_array`) is `done` and its tests pass
- [x] Confirm `SatrecArray` is already imported in `backend/app/services/propagation.py`
- [x] No new dependencies required — `sgp4`, `numpy`, `loguru` already in `pyproject.toml`

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_propagation_bulk.py`
- [x] Write `test_propagate_array_shape` — 3 sats × 5 timesteps, assert (3,5,3) shape
- [x] Write `test_propagate_array_matches_single` — compare bulk[0,0] vs propagate()[0][0] ≤ 1e-6 km
- [x] Write `test_propagate_array_decayed_satellite` — nonzero error_codes, no exception
- [x] Write `test_propagate_array_empty_times` — shape (n_sats,0,3) with empty jds/frs
- [x] Write `test_propagate_array_dtype` — float64 dtype for positions and velocities
- [x] Write `test_propagate_array_single_sat_single_time` — shape (1,1,3) edge case
- [x] Run tests — expect failures (Red) ✓ ImportError: propagate_array not found

## Phase 3: Implementation
- [x] Add `propagate_array(satrec_array, jds, frs)` to `backend/app/services/propagation.py`
- [x] Handle empty `jds` case early-return with correct zero-length shapes
- [x] N/A — SatrecArray.sgp4 accepts 1D jds/frs directly; tiling is not needed
- [x] Capture `(e, r, v)` from `SatrecArray.sgp4`; cast positions/velocities to float64
- [x] Log a WARNING summary if `np.any(e != 0)` (number of affected sats/timesteps)
- [x] Return `(positions, velocities, error_codes)` — do NOT raise on SGP4 errors
- [x] Run tests — expect pass (Green) ✓ 6/6 passed
- [x] Refactor if needed (no premature abstractions)

## Phase 4: Integration
- [x] Verify `propagate_array` is importable from `backend/app/services/propagation.py`
- [x] Confirm S5.2 (position sampling) will be able to call it — no wiring needed yet
- [x] Run lint: ruff check + format — All checks passed
- [x] Run full test suite: 134/134 passed, 0 failures

## Phase 5: Verification
- [x] All 6 tangible outcomes checked against test output
- [x] No hardcoded secrets or tokens
- [x] Loguru WARNING includes count of error sats/timesteps (not just a flag)
- [x] Conjunction math stays in TEME — no geodetic conversion here
- [x] Update roadmap.md status: `spec-written` → `done`
