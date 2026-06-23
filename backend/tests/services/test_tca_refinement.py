"""Tests for S5.4 — TCA Refinement & Miss Distance.

Integration tests exercise refine_tca() with real Satrec objects.
Unit tests exercise _find_tca_in_bracket() with known position/velocity arrays
to cover edge cases (no zero crossing, multiple zero crossings) without needing
real orbital geometries that are hard to construct deterministically.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pytest
from sgp4.api import Satrec
from sgp4.api import jday as sgp4_jday

from app.services.conjunctions import TCARefinement, _find_tca_in_bracket, refine_tca

# ---------------------------------------------------------------------------
# TLE fixtures (same as other test files in this suite)
# ---------------------------------------------------------------------------

# ISS (ZARYA) — catalog 25544, canonical valid TLE fixture.
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

# Invalid TLE — subterrestrial orbit triggers sgp4 error=6 during initialization.
BAD_LINE1 = "1 00001U 00001A   00001.00000000  .00000000  00000-0  00000-0 0  9991"
BAD_LINE2 = "2 00001   0.0000   0.0000 9000001   0.0000   0.0000  0.99999990000012"

# Fixed reference Julian date: 2024-05-02 12:00:00 UTC
_T_JD, _T_FR = sgp4_jday(2024, 5, 2, 12, 0, 0)


def _coarse_grid(n_steps: int = 5, step_s: float = 30.0) -> tuple[np.ndarray, np.ndarray]:
    """Return (jds, frs) coarse time grid starting at _T_JD/_T_FR."""
    step_jd = step_s / 86400.0
    jds = np.full(n_steps, _T_JD, dtype=np.float64)
    frs = _T_FR + np.arange(n_steps, dtype=np.float64) * step_jd
    return jds, frs


def _dense_jd_grid(n_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (jds, frs) dense grid at 1 s resolution, n_steps long."""
    t_start = _T_JD + _T_FR
    jd_base = math.floor(t_start)
    fr_start = t_start - jd_base
    dense_jds = np.full(n_steps, jd_base, dtype=np.float64)
    dense_frs = fr_start + np.arange(n_steps, dtype=np.float64) / 86400.0
    return dense_jds, dense_frs


# ---------------------------------------------------------------------------
# refine_tca — FR-3: empty input
# ---------------------------------------------------------------------------


def test_refine_tca_empty_pairs():
    """Outcome 5: empty flagged-pair list → [] immediately, no error."""
    jds, frs = _coarse_grid()
    result = refine_tca([], [], jds, frs, 30.0)
    assert result == []


# ---------------------------------------------------------------------------
# refine_tca — Outcome 1: known geometry (identical TLEs → miss_km ≈ 0)
# ---------------------------------------------------------------------------


def test_refine_tca_known_geometry():
    """Outcome 1: two Satrecs from the same TLE produce miss_km < 0.1 km.

    Ground truth: identical orbital elements → positions always coincide → miss_km = 0.
    TCA must fall within the dense bracket around coarse_t_idx=2 (±30 s of 12:01:00 UTC).
    """
    sat_a = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)
    sat_b = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)  # same TLE → same trajectory

    jds, frs = _coarse_grid(n_steps=5, step_s=30.0)
    results = refine_tca([(0, 1, 2)], [sat_a, sat_b], jds, frs, 30.0)

    assert len(results) == 1
    r = results[0]
    assert r is not None
    assert isinstance(r, TCARefinement)
    assert r.sat_a_idx == 0
    assert r.sat_b_idx == 1
    # Ground truth miss_km = 0 km; allow floating-point floor tolerance
    assert r.miss_km < 0.1

    # TCA must be a UTC-aware datetime within the bracket window
    assert isinstance(r.tca, datetime)
    assert r.tca.tzinfo is not None
    bracket_lo = datetime(2024, 5, 2, 12, 0, 29, tzinfo=timezone.utc)  # 1 s before t_lo
    bracket_hi = datetime(2024, 5, 2, 12, 1, 31, tzinfo=timezone.utc)  # 1 s after t_hi
    assert bracket_lo <= r.tca <= bracket_hi


# ---------------------------------------------------------------------------
# refine_tca — Outcome 4: rel_vel_kms = |v_A − v_B| at TCA
# ---------------------------------------------------------------------------


def test_refine_tca_rel_vel():
    """Outcome 4: two Satrecs from the same TLE → rel_vel_kms < 0.001 km/s.

    Ground truth: identical orbital elements → velocity vectors always equal → |v_A−v_B| = 0.
    """
    sat_a = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)
    sat_b = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)

    jds, frs = _coarse_grid()
    results = refine_tca([(0, 1, 2)], [sat_a, sat_b], jds, frs, 30.0)

    assert results[0] is not None
    # Ground truth: same orbit → |v_A − v_B| = 0; allow floating-point noise
    assert results[0].rel_vel_kms < 0.001


# ---------------------------------------------------------------------------
# refine_tca — Outcome 3: SGP4 error → None, no exception
# ---------------------------------------------------------------------------


def test_refine_tca_sgp4_error():
    """Outcome 3: satellite with SGP4 init error → pair entry is None, no exception propagates."""
    sat_good = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)
    # BAD_LINE triggers error=6 at twoline2rv (subterrestrial orbit)
    sat_bad = Satrec.twoline2rv(BAD_LINE1, BAD_LINE2)

    jds, frs = _coarse_grid()
    results = refine_tca([(0, 1, 2)], [sat_good, sat_bad], jds, frs, 30.0)

    assert len(results) == 1
    assert results[0] is None


# ---------------------------------------------------------------------------
# refine_tca — multiple pairs: mix of None and valid
# ---------------------------------------------------------------------------


def test_refine_tca_mixed_pairs():
    """One good pair and one SGP4-error pair → list length 2, first valid, second None."""
    sat_a = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)
    sat_b = Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)
    sat_bad = Satrec.twoline2rv(BAD_LINE1, BAD_LINE2)

    jds, frs = _coarse_grid()
    results = refine_tca(
        [(0, 1, 2), (0, 2, 2)],
        [sat_a, sat_b, sat_bad],
        jds,
        frs,
        30.0,
    )

    assert len(results) == 2
    assert results[0] is not None  # (sat_a, sat_b) → valid
    assert results[1] is None  # (sat_a, sat_bad) → error


# ---------------------------------------------------------------------------
# _find_tca_in_bracket — Outcome 2: no zero crossing → fallback to argmin
# ---------------------------------------------------------------------------


def test_refine_tca_no_zero_crossing():
    """Outcome 2: monotonically increasing separation → fallback to argmin, no exception.

    sat_a is stationary at origin; sat_b starts at origin and moves away at constant
    velocity.  The range-rate is 0 at t=0 then positive everywhere → no neg→pos crossing.
    Fallback: argmin returns t=0 with miss_km = 0.
    """
    N = 61  # ±30 s at 1 s resolution
    dense_jds, dense_frs = _dense_jd_grid(N)

    pos_a = np.zeros((N, 3), dtype=np.float64)
    vel_a = np.zeros((N, 3), dtype=np.float64)

    # sat_b starts at origin, moves in +x at 0.1 km/s
    t = np.arange(N, dtype=np.float64)
    pos_b = np.zeros((N, 3), dtype=np.float64)
    pos_b[:, 0] = t * 0.1  # x = 0, 0.1, 0.2, ... km
    vel_b = np.zeros((N, 3), dtype=np.float64)
    vel_b[:, 0] = 0.1  # constant velocity away

    tca_jd, miss_km, rel_vel_kms = _find_tca_in_bracket(
        pos_a, vel_a, pos_b, vel_b, dense_jds, dense_frs
    )

    # Minimum separation is at t=0 (both at origin) → miss_km = 0
    assert miss_km == pytest.approx(0.0, abs=1e-9)
    # rel_vel_kms = |v_b - v_a| at TCA index (t=0) → 0.1 km/s
    assert rel_vel_kms == pytest.approx(0.1, abs=1e-9)
    # No exception should have been raised


# ---------------------------------------------------------------------------
# _find_tca_in_bracket — FR-2: multiple zero crossings → global minimum wins
# ---------------------------------------------------------------------------


def test_refine_tca_multiple_zero_crossings():
    """FR-2 edge case: two neg→pos zero crossings → TCA at the one with smaller miss_km.

    Constructed scenario (N=71 dense steps, 1 s each):
      f(t) = 3.0 + (t−20)²/500  for t ≤ 40  → local min at t=20, f=3.0 km
      f(t) = 1.0 + (t−60)²/500  for t > 40  → global min at t=60, f=1.0 km

    pos_b = [f(t), 0, 0],  vel_b = [f'(t), 0, 0]
    range_rate = f'(t):  neg→pos at t≈20 (miss≈3 km) and t≈60 (miss≈1 km).
    Expected: TCA selected at crossing t≈60 with miss_km ≈ 1.0 km.
    """
    N = 71
    dense_jds, dense_frs = _dense_jd_grid(N)

    t = np.arange(N, dtype=np.float64)

    # Piecewise distance profile with two minima
    f = np.where(t <= 40, 3.0 + (t - 20.0) ** 2 / 500.0, 1.0 + (t - 60.0) ** 2 / 500.0)
    # Derivative f'(t) = range-rate
    fp = np.where(t <= 40, (t - 20.0) / 250.0, (t - 60.0) / 250.0)

    pos_a = np.zeros((N, 3), dtype=np.float64)
    vel_a = np.zeros((N, 3), dtype=np.float64)

    pos_b = np.zeros((N, 3), dtype=np.float64)
    pos_b[:, 0] = f

    vel_b = np.zeros((N, 3), dtype=np.float64)
    vel_b[:, 0] = fp

    tca_jd, miss_km, rel_vel_kms = _find_tca_in_bracket(
        pos_a, vel_a, pos_b, vel_b, dense_jds, dense_frs
    )

    # Global minimum is at t=60 (miss≈1.0 km), not t=20 (miss≈3.0 km)
    assert miss_km == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# _find_tca_in_bracket — near-zero separation floor (no div/0)
# ---------------------------------------------------------------------------


def test_find_tca_near_zero_separation_no_exception():
    """r_rel ≈ 0 (identical positions) → floor prevents div/0; miss_km returned truthfully."""
    N = 11
    dense_jds, dense_frs = _dense_jd_grid(N)

    pos_a = np.zeros((N, 3), dtype=np.float64)
    vel_a = np.zeros((N, 3), dtype=np.float64)
    pos_b = np.zeros((N, 3), dtype=np.float64)
    vel_b = np.zeros((N, 3), dtype=np.float64)

    tca_jd, miss_km, rel_vel_kms = _find_tca_in_bracket(
        pos_a, vel_a, pos_b, vel_b, dense_jds, dense_frs
    )

    assert miss_km == pytest.approx(0.0, abs=1e-9)
    assert rel_vel_kms == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# _build_dense_bracket — boundary clamping
# ---------------------------------------------------------------------------


def test_build_dense_bracket_boundary_clamping():
    """coarse_t_idx=0 → bracket start clamped to grid start (no negative-time bracket)."""
    from app.services.conjunctions import _build_dense_bracket

    jds, frs = _coarse_grid(n_steps=3, step_s=30.0)
    dense_jds, dense_frs = _build_dense_bracket(jds, frs, coarse_t_idx=0, screen_step_s=30.0)

    t_bracket_start = dense_jds[0] + dense_frs[0]
    t_grid_start = jds[0] + frs[0]

    # Bracket must not start before the coarse grid start
    assert t_bracket_start >= t_grid_start - 1e-9  # allow floating-point tolerance
    # Bracket must contain at least one step
    assert len(dense_jds) >= 1
    # Steps are at 1 s spacing
    if len(dense_jds) > 1:
        dt_s = (dense_jds[1] + dense_frs[1] - dense_jds[0] - dense_frs[0]) * 86400.0
        # 1 s spacing; allow 0.1 ms float rounding (1/86400 * 86400 ≠ exactly 1.0)
        assert dt_s == pytest.approx(1.0, abs=1e-4)
