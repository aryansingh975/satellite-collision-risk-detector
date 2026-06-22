# Spec S4.6 — Regime Classification

## Overview
Classifies each satellite into one of four orbital regimes (LEO, MEO, GEO, HEO) based on its
mean motion `n` (rev/day) and eccentricity `e`, as derived by S4.5. The eccentricity test takes
priority: any orbit with `e ≥ 0.25` is Highly Elliptical (HEO) regardless of altitude. For
near-circular orbits, mean motion thresholds split the remaining three shells: LEO (low Earth,
fast), MEO (medium, GPS/Galileo band), and GEO (geostationary / geosynchronous, slow). These
regime labels drive the conjunction apogee/perigee sieve (S5.1), the stats endpoint (S6.5), and
the frontend colour-coding of satellite entities (S7.3).

## Dependencies
- S4.5 — Orbital element derivation (provides `a_km`, `ecc`, `mean_motion`, `apogee_km`, `perigee_km`)

## Target Location
`backend/app/services/classification.py`

---

## Functional Requirements

### FR-1: Regime classification function
- **What**: `classify_regime(n: float, e: float) -> str` returns one of `"HEO"`, `"LEO"`, `"MEO"`, `"GEO"`.
- **Inputs**:
  - `n` — mean motion in rev/day (float, from TLE field or S4.5)
  - `e` — eccentricity (float, dimensionless, 0 ≤ e < 1)
- **Outputs**: A regime string, one of `{"LEO", "MEO", "GEO", "HEO"}`.
- **Decision tree** (in priority order):
  1. `e ≥ 0.25` → `"HEO"` (Molniya-type; eccentricity dominates)
  2. else `n ≥ 11.25` → `"LEO"` (period ≤ ~128 min; ~2000 km ceiling)
  3. else `1.2 ≤ n < 11.25` → `"MEO"` (GPS / Galileo / radiation belts)
  4. else `n < 1.2` → `"GEO"` (near-synchronous; ~35 786 km)
- **Edge cases**:
  - `e` exactly `0.25` → HEO (boundary is inclusive)
  - `n` exactly `11.25` → LEO (boundary is inclusive)
  - `n` exactly `1.2` → MEO (lower boundary inclusive)
  - `n < 0` or `e < 0` — treat as invalid; raise `ValueError`
  - `e ≥ 1` (hyperbolic) — raise `ValueError`; SGP4 does not support these

### FR-2: Threshold rationale (documented in this spec)
The chosen thresholds match the CLAUDE.md table and are grounded in standard orbital mechanics:

| Boundary | Value | Physical meaning |
|----------|-------|-----------------|
| HEO eccentricity | `e ≥ 0.25` | Significant apogee/perigee asymmetry; orbit sweeps multiple shells |
| LEO lower bound | `n ≥ 11.25` rev/day | Period ≤ 128 min; ~2000 km altitude ceiling |
| MEO lower bound | `1.2 ≤ n < 11.25` rev/day | ~2 000–35 000 km; GPS (n≈2.0), Galileo (n≈1.9) |
| GEO | `n < 1.2` rev/day | Period ≥ 1200 min; geostationary ring (~35 786 km) |

These thresholds match the CelesTrak SOCRATES regime definitions and the codebase constant
table in CLAUDE.md. They must NOT be changed without creating a new spec.

### FR-3: Integration into satellite classification pipeline
- **What**: `classify_regime` is called from the satellite ingestion/classification pipeline
  (the function that populates the `regime` column in the `Satellite` ORM model via S2.2).
- **Inputs**: `n` and `e` values already parsed from the TLE (S3.3) and stored in `Satellite`.
- **Outputs**: The `regime` string is written to `Satellite.regime` during upsert.
- **Edge cases**: If SGP4 reports a decayed orbit (error code ≠ 0), regime classification should
  still proceed from the TLE orbital elements — decayed means the propagation failed, not that
  the orbital elements are unavailable.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `classify_regime(n=15.0, e=0.001)` returns `"LEO"`.
- [ ] **Outcome 2**: `classify_regime(n=2.0, e=0.01)` returns `"MEO"` (GPS-like orbit).
- [ ] **Outcome 3**: `classify_regime(n=1.0, e=0.0)` returns `"GEO"`.
- [ ] **Outcome 4**: `classify_regime(n=2.5, e=0.72)` returns `"HEO"` (Molniya).
- [ ] **Outcome 5**: `classify_regime(n=11.25, e=0.0)` returns `"LEO"` (exact boundary).
- [ ] **Outcome 6**: `classify_regime(n=1.2, e=0.0)` returns `"MEO"` (exact lower boundary).
- [ ] **Outcome 7**: `classify_regime(n=0.9, e=0.24)` returns `"GEO"` (e just below HEO threshold).
- [ ] **Outcome 8**: `classify_regime(n=0.9, e=0.25)` returns `"HEO"` (e at exact HEO boundary).
- [ ] **Outcome 9**: Calling with `e=-0.1` or `e=1.0` raises `ValueError`.
- [ ] **Outcome 10**: `Satellite.regime` column is populated after the ingestion pipeline runs.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_classify_leo**: `n=15.0, e=0.001` → `"LEO"` (typical ISS-like orbit)
2. **test_classify_meo**: `n=2.0, e=0.01` → `"MEO"` (GPS-band)
3. **test_classify_geo**: `n=1.0, e=0.0` → `"GEO"` (geostationary)
4. **test_classify_heo**: `n=2.5, e=0.72` → `"HEO"` (Molniya)
5. **test_classify_heo_overrides_meo_n**: `n=2.0, e=0.30` → `"HEO"` (HEO check runs before MEO)
6. **test_classify_boundary_leo**: `n=11.25, e=0.0` → `"LEO"` (inclusive lower boundary)
7. **test_classify_boundary_meo_lower**: `n=1.2, e=0.0` → `"MEO"` (inclusive MEO lower bound)
8. **test_classify_boundary_heo**: `n=0.9, e=0.25` → `"HEO"` (inclusive HEO boundary)
9. **test_classify_just_below_heo**: `n=0.9, e=0.249` → `"GEO"` (just below HEO threshold)
10. **test_classify_invalid_negative_e**: raises `ValueError`
11. **test_classify_invalid_hyperbolic**: `e=1.0` raises `ValueError`
12. **test_classify_invalid_negative_n**: raises `ValueError`

### Mocking Strategy
- No external I/O needed — pure function; test with direct calls only.
- DB integration test: use in-memory SQLite fixture from `conftest.py`; verify that the
  ingestion pipeline sets `Satellite.regime` correctly for a known TLE fixture.

### Coverage Expectation
- All four regime branches covered; all boundary conditions tested; invalid-input paths tested.

---

## References
- roadmap.md S4.6 row (Notes column), CLAUDE.md (Orbital Mechanics constants table, Regime split)
- S4.5 spec (orbital element derivation — provides `n` and `e`)
- S2.2 spec (Satellite ORM model — `regime` column)
