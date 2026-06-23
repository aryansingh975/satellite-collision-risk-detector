"""Tests for S5.1 — Apogee/Perigee Sieve and S5.6 — Brute-Force Correctness Oracle."""

import itertools
from types import SimpleNamespace

import numpy as np

from app.services.conjunctions import apogee_perigee_sieve, ckdtree_screen


def _sat(perigee_km: float, apogee_km: float) -> SimpleNamespace:
    return SimpleNamespace(perigee_km=perigee_km, apogee_km=apogee_km)


# ---------------------------------------------------------------------------
# FR-1: edge cases — empty / single
# ---------------------------------------------------------------------------


def test_empty_list_returns_empty():
    assert apogee_perigee_sieve([]) == []


def test_single_satellite_returns_empty():
    assert apogee_perigee_sieve([_sat(400, 420)]) == []


# ---------------------------------------------------------------------------
# FR-2: rejection rule
# ---------------------------------------------------------------------------


def test_geo_leo_pair_rejected():
    """GEO–LEO altitude gap (~35 000 km) far exceeds default pad of 30 km."""
    geo = _sat(perigee_km=35_786, apogee_km=35_786)
    leo = _sat(perigee_km=400, apogee_km=420)
    result = apogee_perigee_sieve([geo, leo], pad_km=30.0)
    assert result == []


def test_leo_leo_overlap_survives():
    """Two LEO sats with overlapping altitude shells survive."""
    leo_a = _sat(perigee_km=400, apogee_km=420)
    leo_b = _sat(perigee_km=410, apogee_km=430)
    result = apogee_perigee_sieve([leo_a, leo_b], pad_km=30.0)
    assert (0, 1) in result


def test_heo_leo_survives():
    """HEO perigee dips into LEO shell — pair should survive."""
    heo = _sat(perigee_km=300, apogee_km=20_000)
    leo = _sat(perigee_km=400, apogee_km=420)
    result = apogee_perigee_sieve([heo, leo], pad_km=30.0)
    assert len(result) == 1
    assert (0, 1) in result


def test_second_rejection_branch():
    """Explicitly exercises perigee_B − apogee_A > pad (B is higher than A)."""
    leo = _sat(perigee_km=400, apogee_km=420)  # index 0
    geo = _sat(perigee_km=35_786, apogee_km=35_786)  # index 1
    # perigee_B(35786) - apogee_A(420) = 35366 >> 30 → rejected via second branch
    result = apogee_perigee_sieve([leo, geo], pad_km=30.0)
    assert result == []


# ---------------------------------------------------------------------------
# FR-2: pad boundary conditions
# ---------------------------------------------------------------------------


def test_pad_boundary_exactly_touching():
    """apogee_A == perigee_B with pad=0 → shells touch exactly → survives."""
    sat_a = _sat(perigee_km=400, apogee_km=500)
    sat_b = _sat(perigee_km=500, apogee_km=600)
    # perigee_B - apogee_A = 500 - 500 = 0 ≤ 0 → survives
    result = apogee_perigee_sieve([sat_a, sat_b], pad_km=0.0)
    assert (0, 1) in result


def test_pad_boundary_just_over():
    """perigee_A − apogee_B = pad + 0.001 → rejected."""
    pad = 10.0
    sat_a = _sat(perigee_km=520.001, apogee_km=530.0)
    sat_b = _sat(perigee_km=400.0, apogee_km=510.0)
    # perigee_A - apogee_B = 520.001 - 510 = 10.001 > 10.0 → rejected
    result = apogee_perigee_sieve([sat_a, sat_b], pad_km=pad)
    assert result == []


def test_pad_boundary_just_under():
    """perigee_A − apogee_B = pad − 0.001 → survives."""
    pad = 10.0
    sat_a = _sat(perigee_km=519.999, apogee_km=530.0)
    sat_b = _sat(perigee_km=400.0, apogee_km=510.0)
    # perigee_A - apogee_B = 519.999 - 510 = 9.999 ≤ 10.0 → survives
    result = apogee_perigee_sieve([sat_a, sat_b], pad_km=pad)
    assert (0, 1) in result


# ---------------------------------------------------------------------------
# FR-1 / FR-4: multi-satellite catalog
# ---------------------------------------------------------------------------


def test_three_sats_one_survivor():
    """3 sats: GEO(0), LEO-A(1), LEO-B(2). Only (1,2) survives."""
    geo = _sat(perigee_km=35_786, apogee_km=35_786)
    leo_a = _sat(perigee_km=400, apogee_km=420)
    leo_b = _sat(perigee_km=410, apogee_km=430)
    result = apogee_perigee_sieve([geo, leo_a, leo_b], pad_km=30.0)
    assert result == [(1, 2)]


def test_output_pairs_ordered():
    """All returned pairs satisfy i < j."""
    sats = [_sat(400 + i * 2, 420 + i * 2) for i in range(5)]
    result = apogee_perigee_sieve(sats, pad_km=30.0)
    for i, j in result:
        assert i < j, f"Pair ({i},{j}) violates i < j"


def test_symmetric_rejection():
    """Rejection does not depend on order — (A,B) and (B,A) give the same outcome."""
    geo = _sat(perigee_km=35_786, apogee_km=35_786)
    leo = _sat(perigee_km=400, apogee_km=420)
    result_ab = apogee_perigee_sieve([geo, leo], pad_km=30.0)
    result_ba = apogee_perigee_sieve([leo, geo], pad_km=30.0)
    assert result_ab == []
    assert result_ba == []


# ---------------------------------------------------------------------------
# FR-3: large catalog performance / no crash
# ---------------------------------------------------------------------------


def test_large_catalog_no_crash():
    """100 LEO sats all survive → 100*99/2 = 4950 pairs, no crash."""
    sats = [_sat(perigee_km=400 + i * 0.1, apogee_km=420 + i * 0.1) for i in range(100)]
    result = apogee_perigee_sieve(sats, pad_km=30.0)
    assert len(result) == 4950
    for i, j in result:
        assert i < j


# ---------------------------------------------------------------------------
# S5.6 — Brute-Force Correctness Oracle
#
# Constructs synthetic position tensors with fully-known Euclidean geometry
# and asserts that ckdtree_screen returns exactly the same close pairs as an
# O(n²) all-pairs brute-force enumeration.  Trust anchor for the conjunction
# engine: if these pass, the spatial-screen step is provably correct.
# ---------------------------------------------------------------------------


def _brute_force_pairs(
    positions: np.ndarray,
    t: int,
    radius: float,
) -> set[tuple[int, int]]:
    """All (i, j) pairs with i < j where Euclidean distance at timestep t is < radius."""
    n = positions.shape[0]
    result: set[tuple[int, int]] = set()
    for i, j in itertools.combinations(range(n), 2):
        dist = float(np.linalg.norm(positions[i, t] - positions[j, t]))
        if dist < radius:
            result.add((i, j))
    return result


def test_oracle_single_timestep_exact_match():
    """6 satellites on the X-axis; ckdtree_screen set == brute-force set (1 timestep).

    Positions (km on X-axis): 0, 10, 20, 30, 100, 200.
    Radius 15 km → adjacent pairs (dist=10) survive; non-adjacent (dist≥20) do not.
    Expected: {(0,1), (1,2), (2,3)}.
    """
    xs = [0.0, 10.0, 20.0, 30.0, 100.0, 200.0]
    n = len(xs)
    pos = np.zeros((n, 1, 3), dtype=np.float64)
    for k, x in enumerate(xs):
        pos[k, 0, 0] = x

    radius = 15.0
    unique_indices = list(range(n))
    survivors = [(i, j) for i in range(n) for j in range(i + 1, n)]

    result = ckdtree_screen(pos, survivors, unique_indices, radius)
    found_pairs = {pair for pair, _ in result}

    expected_pairs = _brute_force_pairs(pos, 0, radius)
    assert expected_pairs == {(0, 1), (1, 2), (2, 3)}, "Fixture sanity check failed"
    assert found_pairs == expected_pairs, (
        f"cKDTree result {found_pairs!r} != brute-force {expected_pairs!r}"
    )


def test_oracle_multi_timestep_per_step_agreement():
    """4 satellites, 4 timesteps; close pair differs per timestep (radius=15 km).

    t=0: all 1000 km apart → no close pairs
    t=1: sats 0 and 1 are 5 km apart → {(0,1)}
    t=2: sats 2 and 3 are 5 km apart → {(2,3)}
    t=3: both (0,1) and (2,3) close at 5 km → {(0,1), (2,3)}
    """
    n, T = 4, 4
    radius = 15.0
    pos = np.zeros((n, T, 3), dtype=np.float64)

    # t=0: all satellites far apart
    for k in range(n):
        pos[k, 0, 0] = k * 1_000.0

    # t=1: sats 0 and 1 close; sats 2 and 3 far
    pos[0, 1, 0] = 0.0
    pos[1, 1, 0] = 5.0
    pos[2, 1, 0] = 1_000.0
    pos[3, 1, 0] = 2_000.0

    # t=2: sats 0 and 1 far; sats 2 and 3 close
    pos[0, 2, 0] = 0.0
    pos[1, 2, 0] = 1_000.0
    pos[2, 2, 0] = 5_000.0
    pos[3, 2, 0] = 5_005.0

    # t=3: both pairs close
    pos[0, 3, 0] = 0.0
    pos[1, 3, 0] = 5.0
    pos[2, 3, 0] = 500.0
    pos[3, 3, 0] = 505.0

    unique_indices = list(range(n))
    survivors = [(i, j) for i in range(n) for j in range(i + 1, n)]

    result = ckdtree_screen(pos, survivors, unique_indices, radius)

    hits_by_t: dict[int, set[tuple[int, int]]] = {t: set() for t in range(T)}
    for pair, t_idx in result:
        hits_by_t[t_idx].add(pair)

    for t in range(T):
        expected = _brute_force_pairs(pos, t, radius)
        assert hits_by_t[t] == expected, (
            f"Timestep {t}: cKDTree {hits_by_t[t]!r} != brute-force {expected!r}"
        )


def test_oracle_survivor_filter_respected():
    """Pair (0,2) is within radius but absent from survivors → must not appear in output.

    Positions: sat 0 at (0,0,0), sat 1 at (5,0,0), sat 2 at (3,0,0).
    Radius 10 km → all three pairs within radius; brute-force = {(0,1), (0,2), (1,2)}.
    survivors = [(0,1), (1,2)] — (0,2) deliberately excluded.
    Expected output: {(0,1), (1,2)}.
    """
    pos = np.array(
        [[[0.0, 0.0, 0.0]], [[5.0, 0.0, 0.0]], [[3.0, 0.0, 0.0]]],
        dtype=np.float64,
    )  # shape (3, 1, 3)
    radius = 10.0
    unique_indices = [0, 1, 2]
    survivors = [(0, 1), (1, 2)]  # (0,2) excluded

    result = ckdtree_screen(pos, survivors, unique_indices, radius)
    found_pairs = {pair for pair, _ in result}

    # Sanity: brute force sees all three pairs within radius
    brute_all = _brute_force_pairs(pos, 0, radius)
    assert brute_all == {(0, 1), (0, 2), (1, 2)}, "Fixture sanity check failed"

    assert (0, 2) not in found_pairs, "Non-survivor pair (0,2) leaked into output"
    assert found_pairs == {(0, 1), (1, 2)}, f"Expected {{(0,1),(1,2)}}, got {found_pairs!r}"


def test_oracle_boundary_at_radius_excluded():
    """Verify query_pairs boundary behaviour: dist == r is INCLUDED (≤ r, not strict < r).

    scipy cKDTree.query_pairs returns pairs with distance at most r (inclusive).
    A pair at exactly coarse_radius_km IS flagged; a pair at radius + 0.001 km is not.
    """
    radius = 20.0

    # dist == radius exactly → must be flagged (inclusive ≤ r)
    pos_at = np.array(
        [[[0.0, 0.0, 0.0]], [[radius, 0.0, 0.0]]],
        dtype=np.float64,
    )
    result_at = ckdtree_screen(pos_at, [(0, 1)], [0, 1], radius)
    assert len(result_at) == 1, (
        f"Pair at exactly radius={radius} km should be included (≤ r); got {result_at!r}"
    )

    # dist > radius → must NOT be flagged
    pos_over = np.array(
        [[[0.0, 0.0, 0.0]], [[radius + 0.001, 0.0, 0.0]]],
        dtype=np.float64,
    )
    result_over = ckdtree_screen(pos_over, [(0, 1)], [0, 1], radius)
    assert result_over == [], f"Pair at radius+0.001 km should not appear; got {result_over!r}"


def test_oracle_large_grid_no_false_negatives_or_positives():
    """20 satellites on a 1-D line, spacing 10 km, radius 12 km.

    Only adjacent pairs (dist=10 km) are within radius.
    Next-nearest-neighbor pairs (dist=20 km) are not.
    Expected: {(0,1), (1,2), ..., (18,19)} — exactly 19 pairs.
    Zero false negatives and zero false positives vs. brute force.
    """
    n = 20
    spacing = 10.0
    radius = 12.0  # > 10 (adjacent) but < 20 (skip-one)

    pos = np.zeros((n, 1, 3), dtype=np.float64)
    for k in range(n):
        pos[k, 0, 0] = k * spacing

    unique_indices = list(range(n))
    survivors = [(i, j) for i in range(n) for j in range(i + 1, n)]

    result = ckdtree_screen(pos, survivors, unique_indices, radius)
    found_pairs = {pair for pair, _ in result}

    expected_pairs = _brute_force_pairs(pos, 0, radius)
    assert expected_pairs == {(k, k + 1) for k in range(n - 1)}, "Fixture sanity check failed"

    assert found_pairs == expected_pairs, (
        f"cKDTree result {found_pairs!r} != brute-force {expected_pairs!r}"
    )
