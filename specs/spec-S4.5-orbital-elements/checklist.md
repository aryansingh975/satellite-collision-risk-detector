# Checklist — Spec S4.5: Orbital Element Derivation

## Phase 1: Setup & Dependencies
- [x] Verify S3.3 (TLE field parser) is `done`
- [x] Create or locate `backend/app/services/classification.py`
- [x] No new dependencies needed — only Python stdlib `math` and `typing`

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_classification.py`
- [x] Write failing test: `test_semi_major_axis_iss`
- [x] Write failing test: `test_orbital_period_iss`
- [x] Write failing test: `test_apogee_perigee_circular`
- [x] Write failing test: `test_apogee_heo`
- [x] Write failing test: `test_derive_orbital_elements_returns_namedtuple`
- [x] Write failing test: `test_derive_orbital_elements_iss`
- [x] Write failing test: `test_semi_major_axis_zero_raises`
- [x] Write failing test: `test_semi_major_axis_negative_raises`
- [x] Write failing test: `test_eccentricity_negative_raises`
- [x] Write failing test: `test_eccentricity_one_raises`
- [x] Write failing test: `test_derive_invalid_motion_raises`
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Define `OrbitalElements` NamedTuple (a_km, period_min, apogee_km, perigee_km)
- [x] Implement FR-1: `semi_major_axis(mean_motion_rev_day: float) -> float`
- [x] Implement FR-2: `orbital_period(mean_motion_rev_day: float) -> float`
- [x] Implement FR-3: `apogee_km(a_km: float, ecc: float) -> float`
- [x] Implement FR-4: `perigee_km(a_km: float, ecc: float) -> float`
- [x] Implement FR-5: `derive_orbital_elements(mean_motion: float, ecc: float) -> OrbitalElements`
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (no behaviour change)

## Phase 4: Integration
- [x] Confirm `derive_orbital_elements` is importable from `backend.app.services.classification`
- [x] Verify S4.6 (regime classification) can import and call `derive_orbital_elements` (no circular imports)
- [x] Run lint: `ruff check + ruff format --check` — clean
- [x] Run full test suite: 159 passed, 0 failures

## Phase 5: Verification
- [x] Outcome 1: ISS semi-major axis in [6700, 6850] km ✓
- [x] Outcome 2: ISS period within ±0.1 min of 92.9 min ✓
- [x] Outcome 3: Circular orbit apogee == perigee == a ✓
- [x] Outcome 4: HEO apogee ≈ 46213 km, perigee ≈ 6906 km (tol 5 km) ✓
- [x] Outcome 5–7: All ValueError edge cases raise ✓
- [x] No hardcoded secrets/tokens
- [x] No external I/O — pure math, no logging needed
- [x] Update roadmap.md status: `spec-written` → `done` (after implementation + verify pass)
