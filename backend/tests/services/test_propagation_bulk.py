"""Tests for S4.3 — vectorized bulk propagation (propagate_array)."""

from datetime import datetime, timezone

import numpy as np
import pytest
from sgp4.api import jday as sgp4_jday

from app.services.propagation import build_satrec, build_satrec_array, propagate, propagate_array

# ISS (ZARYA) — catalog 25544; same fixture as test_propagation.py
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

_T0 = datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc)


def _jd_fr(dt: datetime) -> tuple[float, float]:
    return sgp4_jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, float(dt.second))


# ---------------------------------------------------------------------------
# S4.3 — propagate_array()
# ---------------------------------------------------------------------------


def test_propagate_array_shape():
    """Outcome 1: 3 sats × 5 timesteps → shapes (3,5,3), (3,5,3), (3,5)."""
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)] * 3)
    times = [datetime(2024, 5, 2, 12, i * 10, 0, tzinfo=timezone.utc) for i in range(5)]
    jds = np.array([_jd_fr(t)[0] for t in times])
    frs = np.array([_jd_fr(t)[1] for t in times])

    positions, velocities, error_codes = propagate_array(arr, jds, frs)

    assert positions.shape == (3, 5, 3)
    assert velocities.shape == (3, 5, 3)
    assert error_codes.shape == (3, 5)


def test_propagate_array_matches_single():
    """Outcome 2: bulk[0,0] matches propagate()[0] to within 1e-6 km (same SGP4 kernel)."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)])

    jd, fr = _jd_fr(_T0)
    positions, _, error_codes = propagate_array(arr, np.array([jd]), np.array([fr]))
    pos_single, _ = propagate(sat, [_T0])

    assert error_codes[0, 0] == 0
    np.testing.assert_allclose(positions[0, 0], pos_single[0], atol=1e-6)


def test_propagate_array_decayed_satellite():
    """Outcome 3: far-future propagation yields nonzero error_codes; no exception raised.

    SGP4 secular perturbations drive eccentricity out of range (error 1) after ~50 years,
    simulating what callers will see for decayed or long-expired satellites.
    """
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)])
    jd, fr = _jd_fr(datetime(2074, 5, 2, 12, 0, 0, tzinfo=timezone.utc))

    # Must not raise — error codes are returned so the caller decides what to do
    positions, velocities, error_codes = propagate_array(arr, np.array([jd]), np.array([fr]))

    assert np.any(error_codes != 0), "expected nonzero error code for far-future propagation"
    assert positions.shape == (1, 1, 3), "shape invariant holds even for errored timesteps"


def test_propagate_array_empty_times():
    """Outcome 4: empty jds/frs → shapes (n_sats,0,3) and (n_sats,0), no exception."""
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)] * 2)
    jds = np.array([], dtype=np.float64)
    frs = np.array([], dtype=np.float64)

    positions, velocities, error_codes = propagate_array(arr, jds, frs)

    assert positions.shape == (2, 0, 3)
    assert velocities.shape == (2, 0, 3)
    assert error_codes.shape == (2, 0)


def test_propagate_array_dtype():
    """Outcome 5: positions and velocities are always float64."""
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)])
    jd, fr = _jd_fr(_T0)

    positions, velocities, _ = propagate_array(arr, np.array([jd]), np.array([fr]))

    assert positions.dtype == np.float64
    assert velocities.dtype == np.float64


def test_propagate_array_single_sat_single_time():
    """FR-3: degenerate case n_sats=1, n_times=1 → shapes (1,1,3) and (1,1)."""
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)])
    jd, fr = _jd_fr(_T0)

    positions, velocities, error_codes = propagate_array(arr, np.array([jd]), np.array([fr]))

    assert positions.shape == (1, 1, 3)
    assert velocities.shape == (1, 1, 3)
    assert error_codes.shape == (1, 1)
