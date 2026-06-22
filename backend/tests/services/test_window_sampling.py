"""Tests for S5.2 — Position Sampling Over Window."""

from datetime import datetime

import numpy as np
from loguru import logger
from sgp4.api import Satrec
from sgp4.api import jday as sgp4_jday

from app.services.conjunctions import sample_window

# ISS (ZARYA) — catalog 25544; same TLE used across propagation test files.
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

# Fixed start time — no datetime.utcnow() in tests.
T_START = datetime(2024, 1, 1, 0, 0, 0)


def _iss() -> Satrec:
    return Satrec.twoline2rv(ISS_LINE1, ISS_LINE2)


# ---------------------------------------------------------------------------
# FR-5 / FR-2: empty survivors
# ---------------------------------------------------------------------------


def test_empty_survivors_returns_zero_sats():
    """Outcome 1: no survivors → positions.shape[0]==0, unique_indices==[], jds non-empty."""
    satrecs = [_iss(), _iss()]
    positions, jds, frs, unique_indices = sample_window([], satrecs, T_START, 24, 60)
    assert positions.shape[0] == 0
    assert positions.shape[2] == 3
    assert unique_indices == []
    assert len(jds) > 0
    assert len(frs) > 0


def test_empty_satrecs_empty_survivors():
    """Empty satrecs AND empty survivors → no crash, shape (0, n_times, 3)."""
    positions, jds, frs, unique_indices = sample_window([], [], T_START, 1, 60)
    assert positions.shape[0] == 0
    assert positions.ndim == 3
    assert unique_indices == []


# ---------------------------------------------------------------------------
# FR-1: time grid
# ---------------------------------------------------------------------------


def test_time_grid_inclusive_endpoints():
    """Outcome 3: 24 h / 60 s → n_times == 1441 (floor(86400/60)+1)."""
    _, jds, frs, _ = sample_window([], [], T_START, 24, 60)
    assert len(jds) == 1441
    assert len(frs) == 1441


def test_time_grid_start_matches_t_start():
    """jds[0]+frs[0] matches the Julian date of T_START to within 1e-9 JD (~0.1 ms)."""
    _, jds, frs, _ = sample_window([], [], T_START, 1, 60)
    jd0, fr0 = sgp4_jday(
        T_START.year, T_START.month, T_START.day, T_START.hour, T_START.minute, 0.0
    )
    assert abs((jds[0] + frs[0]) - (jd0 + fr0)) < 1e-9


def test_time_grid_step_spacing():
    """Consecutive JD values differ by step_seconds/86400.

    Uses absolute tolerance because jds+frs ≈ 2.46e6; subtracting consecutive values causes
    ~7 digits of cancellation, so relative tolerance must be relaxed to ~1e-6.
    atol=1e-9 JD ≈ 86 µs, which is far tighter than any operational need.
    """
    step_seconds = 60.0
    _, jds, frs, _ = sample_window([], [], T_START, 1, step_seconds)
    expected_step_jd = step_seconds / 86400.0
    actual_steps = np.diff(jds + frs)
    np.testing.assert_allclose(actual_steps, expected_step_jd, atol=1e-9)


def test_step_larger_than_window_gives_one_timestep():
    """step_seconds > window → at least 1 timestep (never empty)."""
    _, jds, frs, _ = sample_window([], [], T_START, window_hours=1, step_seconds=7200)
    assert len(jds) >= 1


def test_time_grid_24h_endpoint():
    """Outcome 4: last JD ≈ first JD + 1.0 for a 24 h window."""
    _, jds, frs, _ = sample_window([], [], T_START, 24, 60)
    first_full = jds[0] + frs[0]
    last_full = jds[-1] + frs[-1]
    # 24 h = 1 Julian day; last timestep is at exactly 24 h (1440 steps × 60 s)
    np.testing.assert_allclose(last_full - first_full, 1.0, rtol=1e-9)


# ---------------------------------------------------------------------------
# FR-2: unique index extraction
# ---------------------------------------------------------------------------


def test_unique_indices_deduplicated():
    """Outcome 8: [(0,1),(1,2),(0,2)] → unique_indices == [0,1,2]."""
    satrecs = [_iss(), _iss(), _iss()]
    _, _, _, unique_indices = sample_window([(0, 1), (1, 2), (0, 2)], satrecs, T_START, 1, 60)
    assert unique_indices == [0, 1, 2]


def test_unique_indices_sorted():
    """Survivors [(2,3),(0,1)] → unique_indices sorted ascending == [0,1,2,3]."""
    satrecs = [_iss(), _iss(), _iss(), _iss()]
    _, _, _, unique_indices = sample_window([(2, 3), (0, 1)], satrecs, T_START, 1, 60)
    assert unique_indices == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# FR-3 + FR-5: positions shape and content
# ---------------------------------------------------------------------------


def test_single_pair_two_unique():
    """Outcome 2 (partial): survivors [(0,1)] → unique_indices==[0,1], positions.shape[0]==2."""
    satrecs = [_iss(), _iss()]
    positions, _, _, unique_indices = sample_window([(0, 1)], satrecs, T_START, 1, 60)
    assert unique_indices == [0, 1]
    assert positions.shape[0] == 2


def test_positions_shape():
    """Outcome 2: survivors [(0,1),(1,2)] with 3 satrecs → shape (3, 1441, 3) for 24h/60s."""
    satrecs = [_iss(), _iss(), _iss()]
    positions, _, _, _ = sample_window([(0, 1), (1, 2)], satrecs, T_START, 24, 60)
    assert positions.shape == (3, 1441, 3)


def test_iss_position_magnitude_in_leo_range():
    """Outcome 5: ISS TEME position at t_start has magnitude 6500–7000 km."""
    satrecs = [_iss()]
    positions, _, _, _ = sample_window([(0, 0)], satrecs, T_START, 0, 60)
    # window_hours=0 → single timestep; (0,0) is a degenerate self-pair but exercises the path
    mag = np.linalg.norm(positions[0, 0, :])
    assert 6500.0 < mag < 7000.0, f"ISS position magnitude {mag:.1f} km out of LEO range"


def test_no_nan_for_valid_sats():
    """Outcome 7 (partial): valid ISS propagation over 1 h → no NaN in positions."""
    satrecs = [_iss(), _iss()]
    positions, _, _, _ = sample_window([(0, 1)], satrecs, T_START, 1, 60)
    assert not np.any(np.isnan(positions))


def test_positions_frame_is_teme_not_geodetic():
    """Outcome 7: position magnitudes ~6000–8000 km; not lat/lon values (|lat| ≤ 90)."""
    satrecs = [_iss(), _iss()]
    positions, _, _, _ = sample_window([(0, 1)], satrecs, T_START, 0, 60)
    mags = np.linalg.norm(positions[:, 0, :], axis=1)
    for mag in mags:
        assert mag > 100.0, f"Position magnitude {mag:.1f} looks like degrees, not km"


# ---------------------------------------------------------------------------
# FR-4: SGP4 error handling (NaN injection + WARNING log)
# ---------------------------------------------------------------------------


def test_decayed_satellite_positions_are_nan(monkeypatch):
    """Outcome 6: error_code != 0 → positions set to NaN; Loguru WARNING emitted."""
    import app.services.conjunctions as conj_mod

    satrecs = [_iss(), _iss()]

    def mock_propagate_array(sarr, jds, frs):
        n_sats = len(sarr)
        n_times = len(jds)
        pos = np.ones((n_sats, n_times, 3), dtype=np.float64) * 7000.0
        vel = np.zeros((n_sats, n_times, 3), dtype=np.float64)
        err = np.zeros((n_sats, n_times), dtype=np.uint8)
        err[0, :] = 6  # first unique sat is decayed
        return pos, vel, err

    monkeypatch.setattr(conj_mod, "propagate_array", mock_propagate_array)

    warning_messages: list[str] = []
    handler_id = logger.add(warning_messages.append, level="WARNING")
    try:
        positions, _, _, unique_indices = sample_window(
            [(0, 1)], satrecs, T_START, window_hours=1, step_seconds=3600
        )
    finally:
        logger.remove(handler_id)

    # unique_indices[0] = 0 → positions row 0 must be all NaN
    assert np.all(np.isnan(positions[0])), "Decayed sat positions should all be NaN"
    # unique_indices[1] = 1 → positions row 1 untouched (ones * 7000)
    assert not np.any(np.isnan(positions[1])), "Valid sat should have no NaN"
    # A WARNING was emitted
    assert len(warning_messages) > 0, "Expected a Loguru WARNING for decayed satellite"
