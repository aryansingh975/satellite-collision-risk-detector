# Checklist — Spec S4.4: TEME to Geodetic Conversion

## Phase 1: Setup & Dependencies
- [x] Verify S4.2 (single-sat propagation) is `done`
- [x] Locate `backend/app/services/propagation.py` — `teme_to_geodetic` will be added here
- [x] Confirm `skyfield` is already in `pyproject.toml` (it is — no new deps needed)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_propagation_geodetic.py`
- [x] Add ISS TLE fixture to `conftest.py` (or inline in the test file) — inlined in test file
- [x] Write `test_teme_to_geodetic_iss_known_epoch` — expect lat/lon/alt within tolerance
- [x] Write `test_teme_to_geodetic_multiple_times` — 3 timestamps → list length 3
- [x] Write `test_teme_to_geodetic_empty_times` — `[]` → `[]`
- [x] Write `test_teme_to_geodetic_malformed_tle` — garbage TLE → `ValueError`
- [x] Write `test_teme_to_geodetic_decayed_sat` — mocked error → skip timestep, log warning
- [x] Write `test_teme_to_geodetic_negative_alt_logged` — sub-zero alt → included + debug log
- [x] Run tests — expect failures (Red) ✓ confirmed ImportError before implementation

## Phase 3: Implementation
- [x] Add `teme_to_geodetic(line1, line2, times)` to `propagation.py`
- [x] Build `EarthSatellite` from `line1`/`line2`; raise `ValueError` on malformed TLE
- [x] Create skyfield `Time` objects from input datetimes using `_TS.utc()`
- [x] Call `sat.at(ts_t)` then `wgs84.subpoint(geocentric)` to get lat/lon/alt
- [x] Handle SGP4 error codes: skip errored timesteps (NaN position), log warning via Loguru
- [x] Handle negative altitude: include point, emit debug/warning log
- [x] Handle empty `times` list → return `[]` early
- [x] Run tests — expect pass (Green) ✓ 7/7 passed
- [x] Refactor if needed (no behavior change)

## Phase 4: Integration
- [x] Confirm `teme_to_geodetic` is NOT imported in `backend/app/services/conjunctions.py` (file does not exist yet — frame boundary clean)
- [x] Confirm `teme_to_geodetic` is ready to be called from S6.2 positions endpoint
- [x] Run lint: `ruff check propagation.py test_propagation_geodetic.py` — all checks passed
- [x] Run full backend test suite: 141/141 passed

## Phase 5: Verification
- [x] All 5 tangible outcomes checked manually
- [x] No hardcoded secrets or tokens
- [x] Loguru warnings logged for NaN positions; debug log for negative altitudes
- [x] TEME frame not used in display path; geodetic only returned from `teme_to_geodetic`
- [x] Conjunction math boundary confirmed: `conjunctions.py` does not import `teme_to_geodetic`
- [x] Update `roadmap.md` status: `spec-written` → `done`
