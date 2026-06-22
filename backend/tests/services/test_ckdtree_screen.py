"""Tests for S5.3 — cKDTree Spatial Screen."""

import numpy as np

from app.services.conjunctions import ckdtree_screen

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RADIUS = 20.0  # coarse radius (km) used in most tests


def _far_positions(n_unique: int, n_times: int, sep_km: float = 1_000.0) -> np.ndarray:
    """Return (n_unique, n_times, 3) tensor with sats spread 1000 km apart on X axis."""
    pos = np.zeros((n_unique, n_times, 3), dtype=np.float64)
    for k in range(n_unique):
        pos[k, :, 0] = k * sep_km
    return pos


def _place_close(pos: np.ndarray, k0: int, k1: int, t: int, dist_km: float = 5.0) -> None:
    """Move satellite k1 to dist_km from k0 along Y at timestep t (in-place)."""
    pos[k1, t, :] = pos[k0, t, :].copy()
    pos[k1, t, 1] += dist_km


# ---------------------------------------------------------------------------
# FR-1 edge cases — empty inputs
# ---------------------------------------------------------------------------


def test_empty_survivors_returns_empty():
    """Empty survivors → no pairs possible → []."""
    pos = _far_positions(0, 5)
    result = ckdtree_screen(pos, [], [], _RADIUS)
    assert result == []


def test_zero_unique_sats_returns_empty():
    """n_unique = 0 → no valid rows at any timestep → []."""
    pos = np.empty((0, 10, 3), dtype=np.float64)
    result = ckdtree_screen(pos, [], [], _RADIUS)
    assert result == []


def test_single_satellite_no_pairs():
    """Only 1 satellite → fewer than 2 valid rows → []."""
    pos = _far_positions(1, 5)
    result = ckdtree_screen(pos, [], [42], _RADIUS)
    assert result == []


# ---------------------------------------------------------------------------
# FR-1: spatial threshold behaviour
# ---------------------------------------------------------------------------


def test_pair_beyond_radius_not_flagged():
    """Two satellites 25 km apart at all timesteps; radius 20 km → no hits."""
    pos = _far_positions(2, 8, sep_km=25.0)
    survivors = [(0, 1)]
    result = ckdtree_screen(pos, survivors, [0, 1], _RADIUS)
    assert result == []


def test_pair_within_radius_flagged_at_correct_timestep():
    """Satellites default 25 km apart but 5 km apart at t=7 → single hit at t_idx=7."""
    pos = _far_positions(2, 10, sep_km=25.0)
    _place_close(pos, 0, 1, t=7, dist_km=5.0)
    survivors = [(0, 1)]
    result = ckdtree_screen(pos, survivors, [0, 1], _RADIUS)
    assert result == [((0, 1), 7)]


def test_pair_flagged_multiple_timesteps():
    """Satellites close at t=2 and t=3 → two entries in output."""
    pos = _far_positions(2, 6, sep_km=25.0)
    _place_close(pos, 0, 1, t=2, dist_km=5.0)
    _place_close(pos, 0, 1, t=3, dist_km=5.0)
    survivors = [(0, 1)]
    result = ckdtree_screen(pos, survivors, [0, 1], _RADIUS)
    assert ((0, 1), 2) in result
    assert ((0, 1), 3) in result
    assert len(result) == 2


# ---------------------------------------------------------------------------
# FR-1: NaN handling
# ---------------------------------------------------------------------------


def test_all_nan_positions_returns_empty():
    """Entire positions tensor is NaN → no valid rows at any timestep → []."""
    pos = np.full((2, 5, 3), np.nan, dtype=np.float64)
    survivors = [(0, 1)]
    result = ckdtree_screen(pos, survivors, [0, 1], _RADIUS)
    assert result == []


def test_nan_row_excluded_valid_pairs_survive():
    """Sat 0 has NaN at t=0; sats 1 and 2 are 5 km apart at t=0.

    Expected: (1,2) hit at t=0; no hit for pairs involving sat 0.
    """
    pos = _far_positions(3, 3, sep_km=1_000.0)
    # Place sats 1 and 2 close at t=0
    _place_close(pos, 1, 2, t=0, dist_km=5.0)
    # Inject NaN for sat 0 at t=0
    pos[0, 0, :] = np.nan

    unique_indices = [0, 1, 2]
    survivors = [(0, 1), (0, 2), (1, 2)]
    result = ckdtree_screen(pos, survivors, unique_indices, _RADIUS)

    # (1,2) should appear at t=0
    assert ((1, 2), 0) in result
    # No pair involving original index 0 at t=0
    for pair, t in result:
        if t == 0:
            assert 0 not in pair, f"Pair {pair} at t=0 should not involve NaN satellite 0"


def test_nan_at_one_timestep_other_timesteps_unaffected():
    """NaN only at t=1; same pair close at t=0 and t=2 → hits at t=0 and t=2 only."""
    pos = _far_positions(2, 4, sep_km=25.0)
    _place_close(pos, 0, 1, t=0, dist_km=5.0)
    pos[1, 1, :] = np.nan  # sat 1 NaN at t=1
    _place_close(pos, 0, 1, t=2, dist_km=5.0)

    survivors = [(0, 1)]
    result = ckdtree_screen(pos, survivors, [0, 1], _RADIUS)
    t_indices = [t for _, t in result]
    assert 0 in t_indices
    assert 1 not in t_indices
    assert 2 in t_indices


# ---------------------------------------------------------------------------
# FR-2: index remapping and survivor filtering
# ---------------------------------------------------------------------------


def test_original_indices_preserved():
    """unique_indices=[3, 7]; close pair at t=0 → output pair is (3, 7)."""
    pos = _far_positions(2, 3, sep_km=25.0)
    _place_close(pos, 0, 1, t=0, dist_km=5.0)
    survivors = [(3, 7)]
    result = ckdtree_screen(pos, survivors, [3, 7], _RADIUS)
    assert result == [((3, 7), 0)]


def test_output_pairs_normalized_i_less_j():
    """unique_indices=[7, 3] (large first); output pair is (3, 7) — always i < j."""
    pos = _far_positions(2, 3, sep_km=25.0)
    _place_close(pos, 0, 1, t=0, dist_km=5.0)
    # Note: unique_indices[0]=7, unique_indices[1]=3 — inverted order
    survivors = [(3, 7)]
    result = ckdtree_screen(pos, survivors, [7, 3], _RADIUS)
    assert len(result) == 1
    pair, t = result[0]
    assert pair == (3, 7), f"Expected (3, 7) but got {pair}"
    assert pair[0] < pair[1]


def test_non_survivor_pair_filtered():
    """Pair (orig 10, orig 30) is spatially close but not in survivors → not in output."""
    # 3 satellites: orig indices 10, 20, 30
    pos = _far_positions(3, 3, sep_km=1_000.0)
    # Place sats at index 0 (orig 10) and index 2 (orig 30) close at t=1
    _place_close(pos, 0, 2, t=1, dist_km=2.0)
    # survivors only include (10, 20) — not (10, 30)
    survivors = [(10, 20)]
    result = ckdtree_screen(pos, survivors, [10, 20, 30], _RADIUS)
    # (10, 30) pair should not appear; (10, 20) is far apart — so empty
    for pair, _ in result:
        assert pair != (10, 30), "Non-survivor pair (10, 30) must not appear in output"


def test_survivor_pair_appears_non_survivor_does_not():
    """When one pair is in survivors and another isn't, only the survivor appears."""
    # 3 satellites, orig indices 0, 1, 2
    pos = _far_positions(3, 3, sep_km=1_000.0)
    # Sats 0 and 2 close at t=0 (not in survivors)
    _place_close(pos, 0, 2, t=0, dist_km=3.0)
    # Sats 0 and 1 close at t=1 (in survivors)
    _place_close(pos, 0, 1, t=1, dist_km=3.0)

    survivors = [(0, 1)]  # (0,2) deliberately excluded
    result = ckdtree_screen(pos, survivors, [0, 1, 2], _RADIUS)

    pairs_in_output = {pair for pair, _ in result}
    assert (0, 2) not in pairs_in_output
    assert (0, 1) in pairs_in_output


# ---------------------------------------------------------------------------
# FR-3: output ordering
# ---------------------------------------------------------------------------


def test_output_ordered_by_timestep():
    """Two separate pairs: pair A hit at t=5, pair B hit at t=0 → t=0 comes first."""
    # 4 satellites: orig 0,1,2,3
    pos = _far_positions(4, 8, sep_km=1_000.0)
    # Pair (2,3) close at t=5
    _place_close(pos, 2, 3, t=5, dist_km=5.0)
    # Pair (0,1) close at t=0
    _place_close(pos, 0, 1, t=0, dist_km=5.0)

    survivors = [(0, 1), (2, 3)]
    result = ckdtree_screen(pos, survivors, [0, 1, 2, 3], _RADIUS)

    t_vals = [t for _, t in result]
    assert t_vals == sorted(t_vals), f"Output not ordered by timestep: {t_vals}"


# ---------------------------------------------------------------------------
# Oracle: brute-force cross-validation (paves way for S5.6)
# ---------------------------------------------------------------------------


def test_brute_force_matches_ckdtree():
    """4 satellites at known positions; ckdtree_screen matches brute-force all-pairs distance.

    Satellite positions (single timestep, TEME-like km):
        sat 0: (0, 0, 0)
        sat 1: (5, 0, 0)   → dist(0,1) = 5 km
        sat 2: (50, 0, 0)  → dist(0,2) = 50, dist(1,2) = 45 km
        sat 3: (6, 0, 0)   → dist(0,3) = 6, dist(1,3) = 1, dist(2,3) = 44 km

    With radius=15 km, pairs within radius: (0,1), (0,3), (1,3).
    survivors excludes (0,2), (1,2), (2,3) — so those must not appear.
    """
    sat_pos = np.array(
        [[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [50.0, 0.0, 0.0], [6.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    # shape: (4, 1, 3) — single timestep
    pos = sat_pos[:, np.newaxis, :]  # (4, 1, 3)

    radius = 15.0
    unique_indices = [0, 1, 2, 3]
    survivors = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

    result = ckdtree_screen(pos, survivors, unique_indices, radius)
    found_pairs = {pair for pair, _ in result}

    # Brute-force: check every pair
    expected_pairs: set[tuple[int, int]] = set()
    for i in range(4):
        for j in range(i + 1, 4):
            dist = float(np.linalg.norm(sat_pos[i] - sat_pos[j]))
            if dist < radius:
                expected_pairs.add((i, j))

    assert found_pairs == expected_pairs, (
        f"cKDTree result {found_pairs} != brute-force {expected_pairs}"
    )


def test_brute_force_with_filtered_survivors():
    """Same positions as brute-force test but survivors only includes (0,1) and (1,3).

    Output must match brute-force filtered to only those pairs.
    """
    sat_pos = np.array(
        [[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [50.0, 0.0, 0.0], [6.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    pos = sat_pos[:, np.newaxis, :]
    radius = 15.0
    unique_indices = [0, 1, 2, 3]
    survivors = [(0, 1), (1, 3)]  # only two pairs eligible

    result = ckdtree_screen(pos, survivors, unique_indices, radius)
    found_pairs = {pair for pair, _ in result}

    # Brute-force filtered to survivors
    survivor_set = set(survivors)
    expected_pairs: set[tuple[int, int]] = set()
    for i in range(4):
        for j in range(i + 1, 4):
            dist = float(np.linalg.norm(sat_pos[i] - sat_pos[j]))
            if dist < radius and (i, j) in survivor_set:
                expected_pairs.add((i, j))

    assert found_pairs == expected_pairs
