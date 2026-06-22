"""Tests for S4.5 — orbital element derivation, and S4.6 — regime classification."""

import math
import pytest

from app.services.classification import (
    OrbitalElements,
    apogee_km,
    classify_regime,
    derive_orbital_elements,
    orbital_period,
    perigee_km,
    semi_major_axis,
)

# ISS representative parameters (NORAD 25544, typical epoch)
ISS_N = 15.49  # rev/day
ISS_E = 0.0006

# Molniya-like HEO analytic values
HEO_N = 2.0  # rev/day
HEO_E = 0.74
# a derived from n: n_rad = 2.0 * 2π / 86400 ≈ 1.4544e-4 rad/s
# a = (398600.4418 / n_rad²)^(1/3)
_heo_n_rad = HEO_N * 2 * math.pi / 86400
HEO_A = (398600.4418 / _heo_n_rad**2) ** (1 / 3)
HEO_APOGEE = HEO_A * (1 + HEO_E)
HEO_PERIGEE = HEO_A * (1 - HEO_E)


# ---------------------------------------------------------------------------
# FR-1: semi_major_axis
# ---------------------------------------------------------------------------


def test_semi_major_axis_iss():
    a = semi_major_axis(ISS_N)
    assert 6700 <= a <= 6850, f"Expected ISS semi-major axis in [6700, 6850] km, got {a:.1f}"


def test_semi_major_axis_zero_raises():
    with pytest.raises(ValueError, match="mean_motion must be positive"):
        semi_major_axis(0)


def test_semi_major_axis_negative_raises():
    with pytest.raises(ValueError, match="mean_motion must be positive"):
        semi_major_axis(-5)


# ---------------------------------------------------------------------------
# FR-2: orbital_period
# ---------------------------------------------------------------------------


def test_orbital_period_iss():
    period = orbital_period(ISS_N)
    expected = 1440 / ISS_N  # ≈ 92.97 min
    assert abs(period - expected) < 0.1, f"Expected ≈{expected:.2f} min, got {period:.2f}"


def test_orbital_period_zero_raises():
    with pytest.raises(ValueError, match="mean_motion must be positive"):
        orbital_period(0)


def test_orbital_period_negative_raises():
    with pytest.raises(ValueError, match="mean_motion must be positive"):
        orbital_period(-1.0)


# ---------------------------------------------------------------------------
# FR-3: apogee_km
# ---------------------------------------------------------------------------


def test_apogee_perigee_circular():
    a = 7000.0  # km, arbitrary circular orbit
    assert apogee_km(a, 0.0) == pytest.approx(a)
    assert perigee_km(a, 0.0) == pytest.approx(a)


def test_apogee_heo():
    result = apogee_km(HEO_A, HEO_E)
    assert abs(result - HEO_APOGEE) < 5.0, (
        f"HEO apogee: expected ≈{HEO_APOGEE:.1f}, got {result:.1f}"
    )


def test_apogee_eccentricity_negative_raises():
    with pytest.raises(ValueError, match="eccentricity must be in"):
        apogee_km(6780.0, -0.01)


def test_apogee_eccentricity_one_raises():
    with pytest.raises(ValueError, match="eccentricity must be in"):
        apogee_km(6780.0, 1.0)


# ---------------------------------------------------------------------------
# FR-4: perigee_km
# ---------------------------------------------------------------------------


def test_perigee_heo():
    result = perigee_km(HEO_A, HEO_E)
    assert abs(result - HEO_PERIGEE) < 5.0, (
        f"HEO perigee: expected ≈{HEO_PERIGEE:.1f}, got {result:.1f}"
    )


def test_perigee_eccentricity_negative_raises():
    with pytest.raises(ValueError, match="eccentricity must be in"):
        perigee_km(6780.0, -0.01)


def test_perigee_eccentricity_one_raises():
    with pytest.raises(ValueError, match="eccentricity must be in"):
        perigee_km(6780.0, 1.0)


# ---------------------------------------------------------------------------
# FR-5: derive_orbital_elements
# ---------------------------------------------------------------------------


def test_derive_orbital_elements_returns_namedtuple():
    result = derive_orbital_elements(ISS_N, ISS_E)
    assert isinstance(result, OrbitalElements)
    assert hasattr(result, "a_km")
    assert hasattr(result, "period_min")
    assert hasattr(result, "apogee_km")
    assert hasattr(result, "perigee_km")


def test_derive_orbital_elements_iss():
    result = derive_orbital_elements(ISS_N, ISS_E)
    assert 6700 <= result.a_km <= 6850
    assert abs(result.period_min - 1440 / ISS_N) < 0.1
    assert result.apogee_km >= result.a_km  # apogee ≥ a
    assert result.perigee_km <= result.a_km  # perigee ≤ a


def test_derive_orbital_elements_heo_apogee_dominates():
    result = derive_orbital_elements(HEO_N, HEO_E)
    assert result.apogee_km > 4 * result.perigee_km, "HEO apogee should be > 4× perigee"


def test_derive_invalid_motion_raises():
    with pytest.raises(ValueError, match="mean_motion must be positive"):
        derive_orbital_elements(0, 0.001)


def test_derive_invalid_eccentricity_raises():
    with pytest.raises(ValueError, match="eccentricity must be in"):
        derive_orbital_elements(15.49, -0.01)


# ---------------------------------------------------------------------------
# S4.6: classify_regime
# ---------------------------------------------------------------------------


def test_classify_leo():
    assert classify_regime(15.0, 0.001) == "LEO"


def test_classify_meo():
    assert classify_regime(2.0, 0.01) == "MEO"


def test_classify_geo():
    assert classify_regime(1.0, 0.0) == "GEO"


def test_classify_heo():
    assert classify_regime(2.5, 0.72) == "HEO"


def test_classify_heo_overrides_meo_n():
    # e=0.30 satisfies HEO threshold; n would otherwise suggest MEO
    assert classify_regime(2.0, 0.30) == "HEO"


def test_classify_boundary_leo():
    # n=11.25 is the inclusive lower bound for LEO
    assert classify_regime(11.25, 0.0) == "LEO"


def test_classify_boundary_meo_lower():
    # n=1.2 is the inclusive lower bound for MEO
    assert classify_regime(1.2, 0.0) == "MEO"


def test_classify_boundary_heo():
    # e=0.25 is the inclusive HEO threshold
    assert classify_regime(0.9, 0.25) == "HEO"


def test_classify_just_below_heo():
    # e=0.249 is just below HEO; GEO because n<1.2
    assert classify_regime(0.9, 0.249) == "GEO"


def test_classify_invalid_negative_e():
    with pytest.raises(ValueError):
        classify_regime(15.0, -0.1)


def test_classify_invalid_hyperbolic():
    with pytest.raises(ValueError):
        classify_regime(15.0, 1.0)


def test_classify_invalid_negative_n():
    with pytest.raises(ValueError):
        classify_regime(-1.0, 0.001)
