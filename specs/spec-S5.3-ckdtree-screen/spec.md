# Spec S5.3 — cKDTree Spatial Screen

## Overview
The cKDTree spatial screen is the third stage of the conjunction engine, consuming the sampled
position tensor produced by the window-sampling step (S5.2). For each timestep in the screening
window it builds a `scipy.spatial.cKDTree` from the finite satellite positions and calls
`query_pairs(r=COARSE_RADIUS_KM)` to find all satellite pairs within the coarse-radius threshold.
The coarse radius is deliberately generous (10–20 km) to ensure that fast-crossing pairs whose
true minimum distance falls between sample points are not missed. Each hit is recorded as
`((i, j), t_idx)` where `i < j` are original satellite catalog indices and `t_idx` is the
timestep index. At each timestep, only rows with fully finite positions participate in the
cKDTree — satellites with NaN positions (from SGP4 errors, set by S5.2) are excluded at that
timestep without skipping valid pairs. Pairs not present in the `survivors` list from the
apogee/perigee sieve (S5.1) are filtered out of the output regardless of their spatial
proximity. The resulting hit list feeds directly into S5.4 for dense TCA refinement around
each flagged timestep.

## Dependencies
- **S5.2** (`conjunctions.py`) — `sample_window` returns `(positions, jds, frs, unique_indices)`.
  The positions tensor `(n_unique, n_times, 3)` is the primary input; `unique_indices` provides
  the mapping from local row index to original catalog satellite index.

## Target Location
`backend/app/services/conjunctions.py`

---

## Functional Requirements

### FR-1: Per-timestep cKDTree query with valid-row filtering
- **What**: For each timestep `t` in `range(n_times)`, extract the rows with fully finite
  positions, build a `cKDTree`, and call `query_pairs(r=coarse_radius_km)` to find all pairs
  within the coarse threshold.
- **Inputs**:
  - `positions: np.ndarray` — shape `(n_unique, n_times, 3)` float64 TEME km.
  - `coarse_radius_km: float` — threshold in km (`COARSE_RADIUS_KM`, typically 10–20 km).
- **Procedure**:
  1. At each timestep `t`, extract `P_t = positions[:, t, :]` — shape `(n_unique, 3)`.
  2. Identify valid rows: `valid_mask = np.all(np.isfinite(P_t), axis=1)`.
  3. If fewer than 2 valid rows, skip this timestep (no pairs possible).
  4. Let `valid_rows = np.where(valid_mask)[0]` — indices into `unique_indices`.
  5. Build `cKDTree(P_t[valid_rows])` and call `.query_pairs(r=coarse_radius_km)`.
  6. The returned local pair indices `(a, b)` index into `valid_rows`, not into `unique_indices` directly.
- **Edge cases**:
  - `n_unique == 0` → no satellites; skip all timesteps; return `[]`.
  - Entire timestep is NaN → fewer than 2 valid rows → skip.
  - Single valid row at a timestep → skip (no pairs).
  - `n_times == 0` → loop body never executes; return `[]`.

### FR-2: Index remapping and survivor filtering
- **What**: Map local cKDTree pair indices back to original catalog indices via `unique_indices`
  and `valid_rows`, then discard any pairs not in the `survivors` set.
- **Inputs**:
  - `unique_indices: list[int]` — from `sample_window`; `positions[k]` belongs to the satellite
    at original index `unique_indices[k]`.
  - `survivors: list[tuple[int, int]]` — sieve output from S5.1; only these pairs are eligible
    for TCA refinement.
  - `valid_rows: np.ndarray` — per-timestep indices of finite rows (from FR-1).
- **Procedure**:
  For each pair `(a, b)` from `query_pairs` (indices into `valid_rows` at timestep `t`):
  1. `orig_a = unique_indices[valid_rows[a]]`
  2. `orig_b = unique_indices[valid_rows[b]]`
  3. Normalize: `pair = (min(orig_a, orig_b), max(orig_a, orig_b))`.
  4. Keep only if `pair` is in the pre-built `survivor_set = set(survivors)`.
  5. Emit `(pair, t)`.
- **Edge cases**:
  - Two satellites close in space but `pair` not in `survivors` → filtered out.
  - `survivors = []` → `survivor_set` is empty → all pairs filtered → return `[]`.

### FR-3: Output contract
- **What**: Return a flat list of all `((i, j), t_idx)` hits across all timesteps, ordered by
  ascending `t_idx` (within a timestep, order is arbitrary).
- **Outputs**:
  - `hits: list[tuple[tuple[int, int], int]]` — each entry is `((i, j), t_idx)` where `i < j`
    are original satellite indices and `t_idx` is the 0-based timestep index.
  - A pair may appear multiple times — once per timestep where the satellites were within
    `coarse_radius_km`. S5.4 groups by pair to find the minimum-distance bracket.
- **Edge cases**:
  - Empty survivors or all-NaN positions → `[]`.
  - A pair crossing within radius at consecutive timesteps → multiple entries (expected and correct).
  - `query_pairs` uses strict inequality (`dist < r`, not `≤ r`) — pairs at exactly
    `coarse_radius_km` may not appear (document this; S5.4 dense re-propagation covers the gap).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `ckdtree_screen` with empty `survivors` and empty `unique_indices` returns `[]`.
- [ ] **Outcome 2**: Two satellites 25 km apart at all timesteps with `coarse_radius_km=20.0` → `[]`.
- [ ] **Outcome 3**: Two satellites 10 km apart at timestep 5 with `coarse_radius_km=20.0` → output contains `((i, j), 5)`.
- [ ] **Outcome 4**: Two satellites within radius at both t=3 and t=4 → two separate entries in output.
- [ ] **Outcome 5**: Satellite A has NaN position at t=0; satellites B and C are valid and within radius at t=0 → `(B, C)` pair is still flagged at t=0; pairs involving A are absent at t=0.
- [ ] **Outcome 6**: Two satellites spatially close but their pair is NOT in `survivors` → not in output.
- [ ] **Outcome 7**: All output pairs have `i < j` (first element smaller than second).
- [ ] **Outcome 8**: Output entries are ordered by ascending `t_idx`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_empty_survivors_returns_empty**: call with `survivors=[]`, `unique_indices=[]`,
   any positions → `[]`.
2. **test_zero_unique_sats_returns_empty**: `positions.shape == (0, 10, 3)` → `[]`.
3. **test_pair_beyond_radius_not_flagged**: two satellites 25 km apart at all timesteps,
   `coarse_radius_km=20.0` → `[]`.
4. **test_pair_within_radius_flagged_at_correct_timestep**: two satellites placed 5 km apart
   only at t=7 (beyond threshold at all other timesteps) → single hit at `t_idx=7`.
5. **test_pair_flagged_multiple_timesteps**: satellites within radius at t=2 and t=3 → two
   entries with `t_idx=2` and `t_idx=3`.
6. **test_nan_row_excluded_valid_pairs_survive**: three satellites; satellite 0 has NaN at t=0;
   satellites 1 and 2 are 5 km apart at t=0 → `(orig_1, orig_2)` hit at t=0, no hit for pairs
   involving satellite 0.
7. **test_all_nan_positions_returns_empty**: positions tensor entirely NaN → `[]`.
8. **test_non_survivor_pair_filtered**: positions[0] and positions[2] are 2 km apart at t=1,
   but `(unique_indices[0], unique_indices[2])` is NOT in survivors → not in output.
9. **test_original_indices_preserved**: `unique_indices=[3, 7]`; cKDTree row pair `(0, 1)`
   maps to output pair `(3, 7)`.
10. **test_output_pairs_normalized_i_less_j**: regardless of which row index is smaller, output
    pair is always `(min_orig, max_orig)`.
11. **test_output_ordered_by_timestep**: hits from t=0 appear before hits from t=5 in the list.
12. **test_single_satellite_no_pairs**: `n_unique=1` → `[]` (fewer than 2 valid rows).
13. **test_brute_force_matches_ckdtree**: 4 satellites at known 3D positions in a single-timestep
    positions tensor; compare `ckdtree_screen` output against brute-force all-pairs distance
    check filtered by survivors — must match exactly.

### Mocking Strategy
- **No CelesTrak HTTP** — pure NumPy/SciPy function; no external calls.
- **No DB** — in-memory computation only.
- **Positions fixtures**: construct synthetic `np.ndarray` tensors directly. Place satellites
  at known 3D TEME-like coordinates (e.g., two points in the XY-plane separated by a known
  distance in km) so distance assertions are deterministic.
- **Survivor sets**: pass explicit `survivors` lists to control which pairs are eligible.
- **NaN injection**: set `positions[k, t, :] = np.nan` directly in the test array to simulate
  SGP4 error output from S5.2.

### Coverage Expectation
- All FRs have at least one test; all edge cases in FR-1 and FR-2 are covered.
- NaN handling: full-NaN tensor, partial-NaN single timestep, and NaN-free fast path.
- Non-survivor filtering explicitly tested with a pair that is spatially close.
- Brute-force consistency test (`test_brute_force_matches_ckdtree`) serves as the unit-level
  oracle, paving the way for the system-level S5.6.

---

## References
- `roadmap.md` — Phase 5 table, S5.3 row; Notes (`cKDTree(P).query_pairs(r=COARSE_RADIUS_KM)`,
  "coarse radius generous to bridge fast crossings", "output flagged (pair, t_idx)").
- `CLAUDE.md` — `COARSE_RADIUS_KM` (10–20 km), `SCREEN_STEP_SECONDS` (30–60 s),
  `RISK_THRESHOLD_KM` (5 km), conjunction math stays in TEME, WGS-72 constants.
- S5.2 spec — `sample_window` return contract: `(positions (n_unique, n_times, 3), jds, frs,
  unique_indices)`.
- S5.4 spec (pending) — consumes `list[tuple[tuple[int, int], int]]` from this function.
- S5.6 spec (pending) — brute-force correctness oracle that cross-validates S5.3 output.
- `scipy.spatial.cKDTree` docs — `query_pairs(r)` returns a set of `(i, j)` pairs with `i < j`,
  strict inequality on distance.
