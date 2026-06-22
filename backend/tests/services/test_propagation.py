"""Tests for S4.1 — Satrec builder and S4.2 — single-sat propagation."""

from datetime import datetime, timezone

import numpy as np
import pytest
from loguru import logger
from sgp4.api import Satrec, SatrecArray, jday as sgp4_jday

from app.services.propagation import PropagationError, build_satrec, build_satrec_array, propagate

# ISS (ZARYA) — catalog 25544, canonical valid TLE fixture.
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

# Invalid TLE — subterrestrial orbit triggers sgp4 error=6 during initialization.
BAD_LINE1 = "1 00001U 00001A   00001.00000000  .00000000  00000-0  00000-0 0  9991"
BAD_LINE2 = "2 00001   0.0000   0.0000 9000001   0.0000   0.0000  0.99999990000012"

# WGS-72 gravity constants (must match these, NOT WGS-84 values).
_WGS72_RADIUS_KM = 6378.135
_WGS72_MU = 398600.8


@pytest.fixture
def captured_warnings():
    """Capture loguru WARNING-level records during a test."""
    records: list[dict] = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="WARNING")
    yield records
    logger.remove(sink_id)


# ---------------------------------------------------------------------------
# FR-1 / FR-3: build_satrec — single TLE pair
# ---------------------------------------------------------------------------


def test_build_satrec_returns_satrec():
    """Outcome 1: valid ISS TLE returns a Satrec with no initialization error."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    assert isinstance(sat, Satrec)
    assert sat.error == 0


def test_build_satrec_wgs72_constant():
    """Outcome 1 / FR-3: WGS-72 gravity constants used (radiusearthkm, mu)."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    assert sat.radiusearthkm == pytest.approx(_WGS72_RADIUS_KM)
    assert sat.mu == pytest.approx(_WGS72_MU)


def test_build_satrec_malformed_line_raises():
    """Outcome 3: physically invalid TLE (subterrestrial orbit) raises ValueError."""
    with pytest.raises(ValueError):
        build_satrec(BAD_LINE1, BAD_LINE2)


def test_build_satrec_preserves_catalog_number():
    """build_satrec preserves the satellite catalog number from the TLE."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    assert sat.satnum == 25544


# ---------------------------------------------------------------------------
# FR-2: build_satrec_array — batch assembly
# ---------------------------------------------------------------------------


def test_build_satrec_array_valid_batch():
    """Outcome 2: 3 valid TLE pairs → SatrecArray of length 3."""
    pairs = [(ISS_LINE1, ISS_LINE2)] * 3
    arr = build_satrec_array(pairs)
    assert isinstance(arr, SatrecArray)
    assert len(arr) == 3


def test_build_satrec_array_skips_bad_record(captured_warnings):
    """Outcome 4: batch with 1 bad pair → length 2, warning logged for the skip."""
    pairs = [
        (ISS_LINE1, ISS_LINE2),
        (BAD_LINE1, BAD_LINE2),  # bad — should be skipped
        (ISS_LINE1, ISS_LINE2),
    ]
    arr = build_satrec_array(pairs)
    assert len(arr) == 2
    assert len(captured_warnings) >= 1
    messages = " ".join(r["message"].lower() for r in captured_warnings)
    assert "skip" in messages or "invalid" in messages or "error" in messages


def test_build_satrec_array_single_element():
    """Outcome 2: single-element list returns a SatrecArray of length 1."""
    arr = build_satrec_array([(ISS_LINE1, ISS_LINE2)])
    assert isinstance(arr, SatrecArray)
    assert len(arr) == 1


def test_build_satrec_array_empty_list_raises():
    """Outcome 5: empty list raises ValueError."""
    with pytest.raises(ValueError):
        build_satrec_array([])


# ---------------------------------------------------------------------------
# S4.2 helpers — duck-typed Satrec stand-ins for error-path tests
# ---------------------------------------------------------------------------


class _AlwaysErrorSat:
    """Always returns a given SGP4 error code from sgp4()."""

    def __init__(self, error_code: int = 6):
        self.satnum = 99999
        self._code = error_code

    def sgp4(self, jd, fr):  # noqa: ARG002
        return (self._code, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])


class _PartialErrorSat:
    """Succeeds on first call, returns error code 1 on second call."""

    def __init__(self):
        self.satnum = 99998
        self._calls = 0

    def sgp4(self, jd, fr):  # noqa: ARG002
        self._calls += 1
        if self._calls == 2:
            return (1, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        return (0, [7000.0, 0.0, 0.0], [0.0, 7.5, 0.0])


# ---------------------------------------------------------------------------
# S4.2 tests — propagate()
# ---------------------------------------------------------------------------

# UTC time near the ISS TLE epoch (2024-123.50765046 ≈ 2024-05-02T12:11 UTC)
_T0 = datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc)


def test_propagate_iss_position_accuracy():
    """Outcome 1: propagate() wraps sgp4 correctly; ISS position in LEO range."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    pos, vel = propagate(sat, [_T0])

    # Cross-check against a direct sgp4 call with the same time
    jd, fr = sgp4_jday(_T0.year, _T0.month, _T0.day, _T0.hour, _T0.minute, float(_T0.second))
    e, r_exp, v_exp = sat.sgp4(jd, fr)
    assert e == 0, "Direct sgp4 call should succeed for ISS near epoch"
    np.testing.assert_allclose(pos[0], r_exp, atol=1e-9)
    np.testing.assert_allclose(vel[0], v_exp, atol=1e-9)

    # Physical sanity: ISS ~400 km altitude → |r| ≈ 6778 km
    r_mag = float(np.linalg.norm(pos[0]))
    assert 6500.0 < r_mag < 7100.0, f"|r| = {r_mag:.1f} km not in expected LEO range"
    v_mag = float(np.linalg.norm(vel[0]))
    assert 7.0 < v_mag < 8.5, f"|v| = {v_mag:.3f} km/s not in expected orbital range"


def test_propagate_returns_correct_shape():
    """Outcome 3: N=5 timestamps → shapes (5, 3)."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    times = [datetime(2024, 5, 2, 12, i, 0, tzinfo=timezone.utc) for i in range(5)]
    pos, vel = propagate(sat, times)
    assert pos.shape == (5, 3)
    assert vel.shape == (5, 3)


def test_propagate_dtype_float64():
    """Outcome 3: output arrays are dtype float64."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    pos, vel = propagate(sat, [_T0])
    assert pos.dtype == np.float64
    assert vel.dtype == np.float64


def test_propagate_error_code_raises():
    """Outcome 2: nonzero SGP4 error code raises PropagationError with code + satnum."""
    fake_sat = _AlwaysErrorSat(error_code=6)
    with pytest.raises(PropagationError) as exc_info:
        propagate(fake_sat, [_T0])
    msg = str(exc_info.value)
    assert "6" in msg
    assert "99999" in msg


def test_propagate_empty_times():
    """Outcome 4: empty times list returns empty (0, 3) arrays without error."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    pos, vel = propagate(sat, [])
    assert pos.shape == (0, 3)
    assert vel.shape == (0, 3)
    assert pos.dtype == np.float64
    assert vel.dtype == np.float64


def test_propagate_single_timestamp():
    """Outcome 3: single timestamp → shapes (1, 3)."""
    sat = build_satrec(ISS_LINE1, ISS_LINE2)
    pos, vel = propagate(sat, [_T0])
    assert pos.shape == (1, 3)
    assert vel.shape == (1, 3)


def test_propagate_partial_error_raises():
    """FR-2: if any timestep errors, the whole call raises (no silent drop)."""
    fake_sat = _PartialErrorSat()
    times = [
        datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 5, 2, 12, 1, 0, tzinfo=timezone.utc),
    ]
    with pytest.raises(PropagationError):
        propagate(fake_sat, times)
