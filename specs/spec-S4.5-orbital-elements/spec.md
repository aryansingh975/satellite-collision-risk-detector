# Spec S4.5 — Orbital Element Derivation

## Overview
Derives the four key orbital elements from TLE-parsed fields (mean motion `n` in rev/day and eccentricity `e`): semi-major axis `a`, orbital period, apogee radius, and perigee radius. These values feed the regime classifier (S4.6) and the apogee/perigee sieve (S5.1). All arithmetic uses WGS-72 GM constant μ = 398600.4418 km³/s² and stays in km throughout; no frame conversion is needed.

## Dependencies
- **S3.3** — TLE field parser (provides `mean_motion` in rev/day and `ecc` dimensionless from the parsed TLE)

## Target Location
`backend/app/services/classification.py`

---

## Functional Requirements

### FR-1: Semi-major axis
- **What**: Compute the semi-major axis `a` in km from mean motion.
- **Formula**: Convert mean motion to rad/s: `n_rad = n * 2π / 86400`; then `a = (μ / n_rad²)^(1/3)` with μ = 398600.4418 km³/s².
- **Inputs**: `mean_motion_rev_day` (float, rev/day, > 0)
- **Outputs**: `a_km` (float, km)
- **Edge cases**: `mean_motion_rev_day ≤ 0` → raise `ValueError("mean_motion must be positive")`

### FR-2: Orbital period
- **What**: Compute orbital period in minutes.
- **Formula**: `period_min = 1440 / n` where n is in rev/day.
- **Inputs**: `mean_motion_rev_day` (float, rev/day, > 0)
- **Outputs**: `period_min` (float, minutes)
- **Edge cases**: `mean_motion_rev_day ≤ 0` → raise `ValueError("mean_motion must be positive")`

### FR-3: Apogee radius
- **What**: Compute apogee radius (highest point of orbit above Earth centre) in km.
- **Formula**: `apogee_km = a * (1 + e)`
- **Inputs**: `a_km` (float, km), `ecc` (float, 0 ≤ e < 1)
- **Outputs**: `apogee_km` (float, km)
- **Edge cases**: `ecc < 0` or `ecc ≥ 1` → raise `ValueError("eccentricity must be in [0, 1)")`

### FR-4: Perigee radius
- **What**: Compute perigee radius (lowest point of orbit above Earth centre) in km.
- **Formula**: `perigee_km = a * (1 - e)`
- **Inputs**: `a_km` (float, km), `ecc` (float, 0 ≤ e < 1)
- **Outputs**: `perigee_km` (float, km)
- **Edge cases**: Same as FR-3

### FR-5: Composite derive function
- **What**: Single entry point that returns all four elements from raw TLE fields.
- **Signature**: `derive_orbital_elements(mean_motion: float, ecc: float) -> OrbitalElements` where `OrbitalElements` is a `NamedTuple` with fields `a_km`, `period_min`, `apogee_km`, `perigee_km` (all floats in km or min).
- **Inputs**: `mean_motion` (rev/day), `ecc` (dimensionless)
- **Outputs**: `OrbitalElements` namedtuple
- **Edge cases**: Delegates to FR-1 through FR-4; propagates their `ValueError`s.

---

## Tangible Outcomes

- [ ] **Outcome 1**: For ISS (NORAD 25544, n ≈ 15.49 rev/day, e ≈ 0.0006), `semi_major_axis` returns a value within ±50 km of 6780 km.
- [ ] **Outcome 2**: For ISS, `orbital_period` returns a value within ±0.1 min of `1440 / 15.49 ≈ 92.9` min.
- [ ] **Outcome 3**: For a perfectly circular orbit (e = 0), apogee_km == perigee_km == a_km.
- [ ] **Outcome 4**: For a Molniya-like HEO (e = 0.74, n ≈ 2.0), apogee_km is roughly 4× perigee_km.
- [ ] **Outcome 5**: `derive_orbital_elements(0, 0.1)` raises `ValueError`.
- [ ] **Outcome 6**: `derive_orbital_elements(-1, 0.1)` raises `ValueError`.
- [ ] **Outcome 7**: `derive_orbital_elements(15.49, -0.01)` raises `ValueError`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_semi_major_axis_iss** — `semi_major_axis(15.49)` returns value in range [6700, 6850] km
2. **test_orbital_period_iss** — `orbital_period(15.49)` ≈ 92.97 min (abs tolerance 0.1)
3. **test_apogee_perigee_circular** — with e=0, apogee == perigee == a for any a
4. **test_apogee_heo** — with e=0.74, a=26560 km (Molniya-like): apogee ≈ 46213 km, perigee ≈ 6906 km (abs tolerance 5 km)
5. **test_derive_orbital_elements_returns_namedtuple** — result has attributes a_km, period_min, apogee_km, perigee_km
6. **test_derive_orbital_elements_iss** — all four fields plausible for ISS parameters
7. **test_semi_major_axis_zero_raises** — `semi_major_axis(0)` raises `ValueError`
8. **test_semi_major_axis_negative_raises** — `semi_major_axis(-5)` raises `ValueError`
9. **test_eccentricity_negative_raises** — `apogee_km(6780, -0.01)` raises `ValueError`
10. **test_eccentricity_one_raises** — `apogee_km(6780, 1.0)` raises `ValueError`
11. **test_derive_invalid_motion_raises** — `derive_orbital_elements(0, 0.001)` raises `ValueError`

### Mocking Strategy
- No external I/O — pure math functions, no mocking required.
- Use fixed numeric fixtures (ISS parameters from CLAUDE.md, Molniya analytic values).
- Run from project root: `source .venv/bin/activate && cd backend && python -m pytest tests/services/test_classification.py -v --tb=short`

### Coverage Expectation
- All five public callables covered; happy path + both error branches per function.

---

## References
- `roadmap.md` row S4.5, Phase 4 table Notes column
- `CLAUDE.md`: μ = 398600.4418 km³/s², WGS-72 note, regime split thresholds (context for S4.6)
