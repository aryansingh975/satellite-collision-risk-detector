# Checklist — Spec S5.3: cKDTree Spatial Screen

## Phase 1: Setup & Dependencies
- [x] Verify S5.2 (`sample_window`) is `done` and its tests pass
- [x] Confirm `scipy` is in `pyproject.toml` (added in S5.1/S5.2; `scipy.spatial.cKDTree`)
- [x] Locate `backend/app/services/conjunctions.py` (target file — `ckdtree_screen` goes here)

## Phase 2: Tests First (TDD)
- [x] Identify or create test file: `backend/tests/services/test_ckdtree_screen.py` (new file)
- [x] Write `test_empty_survivors_returns_empty`
- [x] Write `test_zero_unique_sats_returns_empty`
- [x] Write `test_pair_beyond_radius_not_flagged`
- [x] Write `test_pair_within_radius_flagged_at_correct_timestep`
- [x] Write `test_pair_flagged_multiple_timesteps`
- [x] Write `test_nan_row_excluded_valid_pairs_survive`
- [x] Write `test_all_nan_positions_returns_empty`
- [x] Write `test_non_survivor_pair_filtered`
- [x] Write `test_original_indices_preserved`
- [x] Write `test_output_pairs_normalized_i_less_j`
- [x] Write `test_output_ordered_by_timestep`
- [x] Write `test_single_satellite_no_pairs`
- [x] Write `test_brute_force_matches_ckdtree`
- [x] Run tests — expect failures (Red) ✓ ImportError: ckdtree_screen not yet defined

## Phase 3: Implementation
- [x] Add `ckdtree_screen` function signature to `conjunctions.py`
- [x] FR-1: Per-timestep loop; `valid_mask` from `np.isfinite`; skip if < 2 valid rows;
      build `cKDTree(P_t[valid_rows])`; call `.query_pairs(r=coarse_radius_km)`
- [x] FR-2: Map local pairs → `unique_indices` via `valid_rows`; normalize to `(min, max)`;
      filter against `survivor_set = set(survivors)`
- [x] FR-3: Append `(pair, t)` to hit list per timestep; return flat list
- [x] Run tests — expect pass (Green) ✓ 16/16 passed
- [x] Refactor if needed (no functional changes; keep conjunction math in TEME)

## Phase 4: Integration
- [x] Confirm `ckdtree_screen` is importable from `backend.app.services.conjunctions`
      (S5.4 will import it next)
- [x] Run lint: `make local-lint` (ruff check + format, line length 100) ✓ All checks passed
- [x] Run full test suite: `cd backend && python -m pytest tests/ -v --tb=short` ✓ 216/216
- [x] All tests green (no regressions in S5.1/S5.2 tests)

## Phase 5: Verification
- [x] Outcome 1: empty survivors → `[]` ✓ test_empty_survivors_returns_empty
- [x] Outcome 2: pair beyond radius → `[]` ✓ test_pair_beyond_radius_not_flagged
- [x] Outcome 3: pair within radius at t=7 → hit at t_idx=7 ✓ test_pair_within_radius_flagged_at_correct_timestep
- [x] Outcome 4: pair close at t=2 and t=3 → two entries ✓ test_pair_flagged_multiple_timesteps
- [x] Outcome 5: NaN satellite excluded; valid pairs still flagged ✓ test_nan_row_excluded_valid_pairs_survive
- [x] Outcome 6: non-survivor pair filtered out despite spatial proximity ✓ test_non_survivor_pair_filtered
- [x] Outcome 7: all output pairs have i < j ✓ test_output_pairs_normalized_i_less_j
- [x] Outcome 8: output ordered by ascending t_idx ✓ test_output_ordered_by_timestep
- [x] No hardcoded secrets/tokens
- [x] All conjunction math stays in TEME; no geodetic conversion
- [x] Update roadmap.md status: `spec-written` → `done` (after implement + verify pass)
