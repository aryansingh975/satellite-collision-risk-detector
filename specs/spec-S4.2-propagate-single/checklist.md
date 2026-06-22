# Checklist — Spec S4.2: Single-Sat Propagation

## Phase 1: Setup & Dependencies
- [x] Verify S4.1 (Satrec builder) is `done`
- [x] Locate `backend/app/services/propagation.py` — add `propagate()` and `PropagationError` alongside existing S4.1 code
- [x] Confirm `sgp4` and `numpy` are already in `pyproject.toml` (they should be from S1.1/S4.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_propagation.py` (extended existing)
- [x] N/A — ISS TLE fixture already in test file from S4.1
- [x] Write `test_propagate_iss_position_accuracy` — fails (Red)
- [x] Write `test_propagate_returns_correct_shape` — fails (Red)
- [x] Write `test_propagate_dtype_float64` — fails (Red)
- [x] Write `test_propagate_error_code_raises` — fails (Red)
- [x] Write `test_propagate_empty_times` — fails (Red)
- [x] Write `test_propagate_single_timestamp` — fails (Red)
- [x] Write `test_propagate_partial_error_raises` — fails (Red)
- [x] Run tests — confirmed failures (Red: ImportError on PropagationError/propagate)

## Phase 3: Implementation
- [x] Define `PropagationError(Exception)` in `propagation.py`
- [x] Implement Julian date conversion helper `_datetime_to_jd` (datetime → jd + fr via `sgp4.api.jday`)
- [x] Implement `propagate(sat, times)`:
  - Handle empty `times` → return empty arrays
  - Loop over times: call `sat.sgp4(jd, fr)`, collect `(e, r, v)`
  - If any `e != 0`, raise `PropagationError` with sat catalog number + error code
  - Stack results → `np.array(positions, dtype=float64)`, `np.array(velocities, dtype=float64)`
- [x] Run tests — 15/15 passed (Green)
- [x] N/A — no refactor needed; code is minimal and clear

## Phase 4: Integration
- [x] `propagate` and `PropagationError` importable from `backend/app/services/propagation` (consumed by S4.4, S6.2)
- [x] Run lint: `ruff check app/services/propagation.py tests/services/test_propagation.py` — all checks passed
- [x] Run full test suite: 128/128 passed

## Phase 5: Verification
- [x] All 4 tangible outcomes confirmed by test results
- [x] No hardcoded secrets or tokens
- [x] No silent return of zero/NaN on SGP4 error — confirmed by `test_propagate_error_code_raises`
- [x] Output is TEME km / km·s⁻¹ — no geodetic conversion here (display conversion belongs in S4.4)
- [x] WGS-72 constants used (inherited from S4.1 Satrec builder — no override needed)
- [x] Update roadmap.md status: `spec-written` → `done`
