# Spec S5.6 — Brute-Force Correctness Oracle

## Overview
S5.6 adds a brute-force correctness oracle as a dedicated test module targeting `backend/tests/services/test_conjunctions.py`. The oracle constructs a small synthetic satellite set with fully-known TEME positions, computes all-pairs Euclidean distances directly (O(n²), intentional), and asserts that `ckdtree_screen` returns exactly the same close pairs. This test is the trust anchor for the entire conjunction engine: if the oracle passes, the spatial-screen step is provably correct for the input it validates.

## Dependencies
- S5.3 — cKDTree Spatial Screen (the function under test)

## Target Location
`backend/tests/services/test_conjunctions.py`

---

## Functional Requirements

### FR-1: All-pairs brute-force agreement — single timestep
- **What**: Build a positions tensor `(n, 1, 3)` with known Cartesian coordinates; call `ckdtree_screen`; independently compute all-pairs Euclidean distances; assert the set of found pairs equals the set of pairs with `dist < coarse_radius_km`.
- **Inputs**: `positions (n, 1, 3)`, `survivors` listing every possible `(i, j)` with `i < j`, `unique_indices = [0 … n-1]`, `coarse_radius_km`
- **Outputs**: `found_pairs == expected_pairs` (both `set[tuple[int,int]]`)
- **Edge cases**: Pair exactly at the radius (strict `<` boundary — should NOT appear); pair 1 m inside radius (should appear); all positions identical (every pair within radius)

### FR-2: All-pairs brute-force agreement — multiple timesteps
- **What**: Extend FR-1 to `T ≥ 3` timesteps; at each timestep `t`, compare the ckdtree hits for that timestep against the brute-force set for that timestep independently.
- **Inputs**: `positions (n, T, 3)` with varying separations across timesteps; `survivors` and `unique_indices` cover all pairs
- **Outputs**: For every `t`, `ckdtree_hits[t] == brute_force_hits[t]`; a pair close only at `t=2` should not appear at `t=0` or `t=1`

### FR-3: Survivor filter does not mask brute-force pairs
- **What**: With a restricted `survivors` list, the oracle verifies that ckdtree correctly returns only survivor pairs within the radius — and that the restriction is respected (i.e., a spatially-close non-survivor never leaks through).
- **Inputs**: Positions where pair `(0,2)` is within radius but is absent from `survivors`; `survivors = [(0,1), (1,2)]`
- **Outputs**: `(0,2)` does not appear in the output even though it would appear in the unconstrained brute-force result

### FR-4: Boundary condition — `query_pairs` uses inclusive `≤ r`
- **What**: Verify `scipy.cKDTree.query_pairs` semantics: a pair at distance exactly `r` IS returned (inclusive `≤ r`); a pair at `r + 0.001` is NOT returned.
- **Inputs**: Two position tensors `(2, 1, 3)` — one with `|p1 − p0| = radius` and one with `|p1 − p0| = radius + 0.001`; `survivors = [(0,1)]`
- **Outputs**: `dist == r` → 1 hit; `dist > r` → empty result

### FR-5: Larger synthetic catalog — no missed pairs, no false positives
- **What**: Generate `n = 20` satellites placed on a 3-D grid; use a radius that captures a known subset of pairs; compare full ckdtree output against full brute-force enumeration.
- **Inputs**: `n=20` positions on a regular grid with known inter-satellite spacing; `survivors` = all pairs; radius chosen so ~10–30 % of pairs are within it
- **Outputs**: `found_pairs == expected_pairs` (zero false negatives and zero false positives)

---

## Tangible Outcomes

- [x] **Outcome 1**: `test_oracle_single_timestep_exact_match` passes — ckdtree finds the same pairs as brute force for a 6-satellite single-timestep scenario.
- [x] **Outcome 2**: `test_oracle_multi_timestep_per_step_agreement` passes — per-timestep sets agree across T=4 timesteps.
- [x] **Outcome 3**: `test_oracle_survivor_filter_respected` passes — non-survivor spatially-close pair is absent from output.
- [x] **Outcome 4**: `test_oracle_boundary_at_radius_excluded` passes — verifies inclusive `≤ r` semantics: pair at exactly `r` is flagged; pair at `r + 0.001` is not.
- [x] **Outcome 5**: `test_oracle_large_grid_no_false_negatives_or_positives` passes — 20-sat grid with full pair enumeration.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_oracle_single_timestep_exact_match**: 6 satellites, 1 timestep, all survivors — ckdtree set == brute-force set.
2. **test_oracle_multi_timestep_per_step_agreement**: 4 satellites, 4 timesteps, separation varies per timestep — validate each timestep independently.
3. **test_oracle_survivor_filter_respected**: 3 satellites, pair `(0,2)` close but excluded from survivors — confirm it never appears.
4. **test_oracle_boundary_at_radius_excluded**: 2 satellites at exactly `coarse_radius_km` — empty result.
5. **test_oracle_large_grid_no_false_negatives_or_positives**: 20-satellite 3D grid, full pair coverage — set equality.

### Mocking Strategy
- No external I/O, no DB, no SGP4 calls — all inputs are synthetic NumPy arrays constructed in the test
- No `respx` / httpx mocking needed; this is a pure-numerics test
- `unique_indices` is always a plain Python list matching the first dimension of `positions`

### Coverage Expectation
- All five FRs covered by dedicated tests
- Boundary condition (FR-4) explicitly tested with floating-point positions to confirm strict `< r`

---

## References
- roadmap.md S5.6 row and Phase 5 notes; CLAUDE.md (TEME frame, cKDTree, WGS-72 note)
- S5.3 spec and `ckdtree_screen` implementation in `backend/app/services/conjunctions.py`
