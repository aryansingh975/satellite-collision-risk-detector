# Spec S5.1 — Apogee/Perigee Sieve

## Overview
The apogee/perigee sieve is the first and cheapest filter in the conjunction engine. Before any propagation
occurs, it eliminates satellite pairs whose orbits cannot physically intersect within a small altitude pad.
The rejection rule is: if the perigee of satellite A is higher than the apogee of satellite B by more than
the pad (or vice versa), the two orbits cannot come within `pad` km of each other and the pair is discarded.
This O(n) per-object filter runs on the full catalog and removes the vast majority of pairs (e.g., every
GEO–LEO combination), making the downstream vectorized propagation and cKDTree screen tractable.

## Dependencies
- **S4.5** (`classification.py`) — provides `apogee_km` and `perigee_km` derived from semi-major axis and
  eccentricity: `apogee = a*(1+e)`, `perigee = a*(1−e)`.
- **S4.6** (`classification.py`) — regime classification is available (though not directly required by the
  sieve logic, it is a prerequisite of the conjunction pipeline that S5.1 starts).

## Target Location
`backend/app/services/conjunctions.py`

---

## Functional Requirements

### FR-1: Sieve function signature and contract
- **What**: Expose a function `apogee_perigee_sieve(satellites, pad_km=30.0)` that accepts a sequence of
  satellite records (each having `apogee_km` and `perigee_km` attributes or dict keys) and returns the
  list of (index_a, index_b) pairs that *survive* (cannot be rejected by the altitude test).
- **Inputs**:
  - `satellites`: list/sequence of objects with `.apogee_km` and `.perigee_km` (float, km). May be ORM
    `Satellite` instances or lightweight dataclass/namedtuple wrappers.
  - `pad_km`: float, default `30.0` km. Configurable so tests and production can adjust sensitivity.
- **Outputs**: list of `(int, int)` index pairs `(i, j)` where `i < j`, containing only pairs that pass
  the sieve. Order within the output list is unspecified.
- **Complexity**: O(n²) pairs tested but each test is O(1); acceptable for catalogs up to ~25 000 sats.
  The sieve is CPU-bound but runs on floats — NumPy vectorization is encouraged for large catalogs.
- **Edge cases**:
  - Empty satellite list → return `[]`.
  - Single satellite → return `[]` (no pairs).
  - Two co-orbital satellites (identical apogee/perigee) → pair survives (distance = 0 ≤ pad).
  - `pad_km = 0` → only pairs where orbit shells exactly touch survive.
  - Satellite with `apogee_km < perigee_km` (malformed data) → treat as-is; sieve uses the values
    provided; caller is responsible for data quality.

### FR-2: Rejection rule
- **What**: A pair `(A, B)` is **rejected** (excluded from output) if either of the following holds:
  - `perigee_A − apogee_B > pad_km`  (A's lowest point is above B's highest point by more than pad)
  - `perigee_B − apogee_A > pad_km`  (B's lowest point is above A's highest point by more than pad)
- **Equivalently**, the pair **survives** if and only if the altitude shells overlap within pad:
  - `perigee_A − apogee_B ≤ pad_km` AND `perigee_B − apogee_A ≤ pad_km`
- **Why the pad**: The coarse sieve uses a generous buffer so that fast-moving objects crossing the
  boundary between timesteps are not missed. Default 30 km is wider than the 5 km risk threshold and
  the 10–20 km `COARSE_RADIUS_KM` to leave headroom.
- **Edge cases**:
  - Highly eccentric orbit (HEO, `e ≥ 0.25`) with wide apogee/perigee spread — its perigee may dip
    into LEO while its apogee reaches GEO altitude; it will survive against most other regimes, which is
    correct behaviour.
  - GEO satellite (`n < 1.2`) paired with LEO satellite (`n ≥ 11.25`) — the altitude gap is tens of
    thousands of km, far exceeding pad, so they are correctly rejected.

### FR-3: NumPy-vectorized implementation (optional but preferred)
- **What**: For catalogs with thousands of satellites, build apogee and perigee arrays and compute the
  sieve using broadcasting (`np.subtract.outer`) to generate all-pairs difference matrices, then extract
  surviving index pairs with `np.argwhere`.
- **Inputs**: same as FR-1.
- **Outputs**: same as FR-1 (list of tuples).
- **Edge cases**: Single satellite or empty list handled before entering NumPy path (no 0-row array edge
  case leaks into the vectorized code).

### FR-4: Integration touchpoint
- **What**: The sieve result (surviving pairs) feeds directly into S5.2 (window sampling). The function
  must return indices that map unambiguously back to the input `satellites` sequence so downstream code
  can look up the correct `Satrec` objects for propagation.
- **Inputs/Outputs**: as FR-1.
- **Edge cases**: If the sieve returns zero surviving pairs, S5.2 must receive an empty list and skip
  propagation gracefully (not raise an exception).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `apogee_perigee_sieve([], pad_km=30)` returns `[]`.
- [ ] **Outcome 2**: A LEO satellite (perigee ≈ 400 km, apogee ≈ 420 km) paired with a GEO satellite
  (perigee ≈ apogee ≈ 35 786 km) is **rejected** — the altitude gap (~35 000 km) far exceeds 30 km.
- [ ] **Outcome 3**: Two LEO satellites with overlapping altitude shells (e.g., perigees 400/410 km,
  apogees 420/430 km) **survive** the sieve.
- [ ] **Outcome 4**: A HEO satellite with perigee 300 km and apogee 20 000 km **survives** against a
  LEO satellite at 400–420 km (HEO perigee dips into LEO shell).
- [ ] **Outcome 5**: With `pad_km=0`, two satellites whose shells exactly touch (apogee_A == perigee_B)
  **survive** (boundary inclusive).
- [ ] **Outcome 6**: For a catalog of 3 satellites where only 1 pair survives, the function returns
  exactly that 1 pair.
- [ ] **Outcome 7**: Output pairs satisfy `i < j` (no duplicates, no self-pairs).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_empty_list_returns_empty**: call `apogee_perigee_sieve([])` → `[]`.
2. **test_single_satellite_returns_empty**: one satellite → `[]`.
3. **test_geo_leo_pair_rejected**: GEO (perigee=apogee=35786) + LEO (perigee=400, apogee=420),
   pad=30 → empty result.
4. **test_leo_leo_overlap_survives**: two LEO sats with overlapping shells → pair `(0, 1)` in result.
5. **test_heo_leo_survives**: HEO (perigee=300, apogee=20000) + LEO (400, 420) → pair survives.
6. **test_pad_boundary_exactly_touching**: apogee_A = perigee_B (e.g., 500 km each), pad=0 → survives.
7. **test_pad_boundary_just_over**: perigee_A − apogee_B = pad + 0.001 → rejected.
8. **test_pad_boundary_just_under**: perigee_A − apogee_B = pad − 0.001 → survives.
9. **test_three_sats_one_survivor**: 3 satellites (GEO + LEO-A + LEO-B); GEO–LEO pairs rejected,
   LEO-A–LEO-B survives → result contains exactly `(1, 2)` (or appropriate indices).
10. **test_output_pairs_ordered**: all returned pairs have `i < j`.
11. **test_symmetric_rejection**: rejection is symmetric — if (A,B) rejected then (B,A) is also rejected
    (i.e., not in output in either order).
12. **test_large_catalog_no_crash**: 100 satellites all in LEO (perigee ~400, apogee ~420) → all
    n*(n-1)/2 = 4950 pairs survive (no crash, correct count).

### Mocking Strategy
- No external I/O required — the sieve is a pure function over in-memory data.
- Use lightweight `SimpleNamespace` or a `@dataclass` fixture to represent satellites with
  `apogee_km` / `perigee_km` attributes, rather than full ORM objects.
- DB: not needed for unit tests of the sieve function itself.
- CelesTrak HTTP: not touched by this module.

### Coverage Expectation
- All public functions in the sieve module have at least one test.
- Both rejection branches (`perigee_A > apogee_B + pad` and `perigee_B > apogee_A + pad`) are covered.
- Boundary conditions (exactly at pad, just inside, just outside) each have a dedicated test.

---

## References
- `roadmap.md` — Phase 5 table, S5.1 row; Notes column (rejection formula, default pad, complexity note).
- `CLAUDE.md` — Risk threshold (5 km), COARSE_RADIUS_KM (10–20 km), conjunction math stays in TEME,
  WGS-72 constants, propagation accuracy note.
- S4.5 spec — `apogee = a*(1+e)`, `perigee = a*(1−e)`, μ = 398600.4418 km³/s².
- S4.6 spec — regime thresholds (e ≥ 0.25 → HEO; n ≥ 11.25 → LEO; 1.2 ≤ n < 11.25 → MEO; n < 1.2 → GEO).
