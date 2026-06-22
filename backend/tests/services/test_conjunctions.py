"""Tests for S5.1 — Apogee/Perigee Sieve."""

from types import SimpleNamespace

from app.services.conjunctions import apogee_perigee_sieve


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
