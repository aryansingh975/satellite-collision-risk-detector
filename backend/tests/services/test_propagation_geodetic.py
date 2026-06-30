"""Tests for S4.4 — TEME→geodetic conversion via skyfield (teme_to_geodetic)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from loguru import logger

from app.services.propagation import teme_to_geodetic

# ISS (ZARYA) — catalog 25544; same canonical fixture used across propagation tests.
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

# Subterrestrial orbit — sgp4 sets a non-zero error on twoline2rv.
BAD_LINE1 = "1 00001U 00001A   00001.00000000  .00000000  00000-0  00000-0 0  9991"
BAD_LINE2 = "2 00001   0.0000   0.0000 9000001   0.0000   0.0000  0.99999990000012"

# UTC time near the ISS TLE epoch (2024-05-02 12:11 UTC)
_T0 = datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc)


@pytest.fixture
def captured_warnings():
    """Capture loguru WARNING-level records during a test."""
    records: list[dict] = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="WARNING")
    yield records
    logger.remove(sink_id)


@pytest.fixture
def captured_debug():
    """Capture all loguru records at DEBUG level and above during a test."""
    records: list[dict] = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


# ---------------------------------------------------------------------------
# FR-1: normal propagation path
# ---------------------------------------------------------------------------


def test_teme_to_geodetic_iss_known_epoch():
    """Outcome 1: ISS at a known epoch → numeric lat/lon/alt_km within tolerances."""
    result = teme_to_geodetic(ISS_LINE1, ISS_LINE2, [_T0])

    assert len(result) == 1
    pt = result[0]
    assert set(pt.keys()) == {"lat", "lon", "alt_km"}
    assert isinstance(pt["lat"], float)
    assert isinstance(pt["lon"], float)
    assert isinstance(pt["alt_km"], float)
    # ISS is in LEO ~400 km altitude
    assert 300.0 < pt["alt_km"] < 500.0, f"alt_km={pt['alt_km']:.1f} not in expected LEO range"
    # Latitude bounded by ISS inclination (~51.64°)
    assert -52.0 < pt["lat"] < 52.0, f"lat={pt['lat']:.2f} outside ISS inclination ±51.64°"
    # Longitude in valid range
    assert -180.0 <= pt["lon"] <= 180.0


def test_teme_to_geodetic_multiple_times():
    """FR-1: 3 timestamps → list length 3, each entry has the required keys."""
    times = [
        datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc),
        datetime(2024, 5, 2, 12, 21, 0, tzinfo=timezone.utc),
        datetime(2024, 5, 2, 12, 31, 0, tzinfo=timezone.utc),
    ]
    result = teme_to_geodetic(ISS_LINE1, ISS_LINE2, times)

    assert len(result) == 3
    for pt in result:
        assert set(pt.keys()) == {"lat", "lon", "alt_km"}
        assert isinstance(pt["lat"], float)
        assert isinstance(pt["lon"], float)
        assert isinstance(pt["alt_km"], float)


# ---------------------------------------------------------------------------
# FR-1 edge case: empty input
# ---------------------------------------------------------------------------


def test_teme_to_geodetic_empty_times():
    """Outcome 2: empty times list → []."""
    result = teme_to_geodetic(ISS_LINE1, ISS_LINE2, [])
    assert result == []


# ---------------------------------------------------------------------------
# FR-1 / FR-3 edge case: malformed TLE raises ValueError
# ---------------------------------------------------------------------------


def test_teme_to_geodetic_malformed_tle():
    """Outcome 3: subterrestrial TLE (sgp4 init error) → ValueError."""
    with pytest.raises(ValueError):
        teme_to_geodetic(BAD_LINE1, BAD_LINE2, [_T0])


def test_teme_to_geodetic_garbage_strings():
    """FR-3: completely garbage TLE strings → ValueError."""
    with pytest.raises(ValueError):
        teme_to_geodetic("not a tle line 1", "not a tle line 2", [_T0])


# ---------------------------------------------------------------------------
# FR-1 edge case: decayed satellite (NaN positions) — mocked
# ---------------------------------------------------------------------------


def test_teme_to_geodetic_decayed_sat(captured_warnings):
    """Outcome 4: NaN position on 2nd of 2 timesteps → 1 result + WARNING logged."""
    times = [
        datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc),
        datetime(2024, 5, 2, 12, 21, 0, tzinfo=timezone.utc),
    ]

    # sat.at() is called ONCE with a vectorized time array; return shape (3, 2)
    # where the 2nd column is NaN (simulating a decayed-satellite timestep).
    mock_geo = MagicMock()
    mock_geo.position.km = np.array([
        [7000.0, np.nan],
        [0.0,    np.nan],
        [0.0,    np.nan],
    ])

    # wgs84.subpoint returns arrays of length 2; 2nd values are never used (NaN row skipped).
    mock_subpoint = MagicMock()
    mock_subpoint.latitude.degrees = np.array([51.6, 0.0])
    mock_subpoint.longitude.degrees = np.array([-10.0, 0.0])
    mock_subpoint.elevation.km = np.array([420.0, 0.0])

    with (
        patch("app.services.propagation.EarthSatellite") as MockESat,
        patch("app.services.propagation.wgs84") as mock_wgs84,
    ):
        mock_sat = MagicMock()
        mock_sat.model.error = 0
        mock_sat.model.satnum = 25544
        mock_sat.at.return_value = mock_geo
        MockESat.return_value = mock_sat
        mock_wgs84.subpoint.return_value = mock_subpoint

        result = teme_to_geodetic(ISS_LINE1, ISS_LINE2, times)

    assert len(result) == 1, f"expected 1 result (decayed step skipped), got {len(result)}"
    assert len(captured_warnings) >= 1
    all_msgs = " ".join(str(r["message"]) for r in captured_warnings).lower()
    assert "skip" in all_msgs or "nan" in all_msgs or "error" in all_msgs


# ---------------------------------------------------------------------------
# FR-2 edge case: negative altitude — mocked
# ---------------------------------------------------------------------------


def test_teme_to_geodetic_negative_alt_logged(captured_debug):
    """FR-2: sub-zero altitude → point included in output + debug log emitted."""
    mock_subpoint = MagicMock()
    mock_subpoint.latitude.degrees = 51.6
    mock_subpoint.longitude.degrees = -10.0
    mock_subpoint.elevation.km = -5.0

    mock_geo = MagicMock()
    mock_geo.position.km = np.array([6000.0, 0.0, 0.0])

    with (
        patch("app.services.propagation.EarthSatellite") as MockESat,
        patch("app.services.propagation.wgs84") as mock_wgs84,
    ):
        mock_sat = MagicMock()
        mock_sat.model.error = 0
        mock_sat.model.satnum = 25544
        mock_sat.at.return_value = mock_geo
        MockESat.return_value = mock_sat
        mock_wgs84.subpoint.return_value = mock_subpoint

        result = teme_to_geodetic(ISS_LINE1, ISS_LINE2, [_T0])

    assert len(result) == 1, "negative altitude point must NOT be dropped"
    assert result[0]["alt_km"] == pytest.approx(-5.0)
    all_msgs = " ".join(str(r["message"]) for r in captured_debug).lower()
    assert (
        "negative" in all_msgs or "alt" in all_msgs or "-5" in all_msgs
    ), "expected a debug log about negative altitude"
