"""Orbital element derivation (S4.5) and regime classification (S4.6)."""

import math
from typing import NamedTuple

# WGS-72 gravitational parameter (km³/s²) — matches TLE generation standard
GM_EARTH = 398600.4418


class OrbitalElements(NamedTuple):
    a_km: float
    period_min: float
    apogee_km: float
    perigee_km: float


def semi_major_axis(mean_motion_rev_day: float) -> float:
    """Return semi-major axis in km for the given mean motion (rev/day)."""
    if mean_motion_rev_day <= 0:
        raise ValueError("mean_motion must be positive")
    n_rad = mean_motion_rev_day * 2 * math.pi / 86400  # rad/s
    return (GM_EARTH / n_rad**2) ** (1 / 3)


def orbital_period(mean_motion_rev_day: float) -> float:
    """Return orbital period in minutes for the given mean motion (rev/day)."""
    if mean_motion_rev_day <= 0:
        raise ValueError("mean_motion must be positive")
    return 1440.0 / mean_motion_rev_day


def _validate_ecc(ecc: float) -> None:
    if ecc < 0 or ecc >= 1:
        raise ValueError("eccentricity must be in [0, 1)")


def apogee_km(a_km: float, ecc: float) -> float:
    """Return apogee radius in km."""
    _validate_ecc(ecc)
    return a_km * (1 + ecc)


def perigee_km(a_km: float, ecc: float) -> float:
    """Return perigee radius in km."""
    _validate_ecc(ecc)
    return a_km * (1 - ecc)


def derive_orbital_elements(mean_motion: float, ecc: float) -> OrbitalElements:
    """Derive all four orbital elements from TLE mean motion (rev/day) and eccentricity."""
    a = semi_major_axis(mean_motion)
    return OrbitalElements(
        a_km=a,
        period_min=orbital_period(mean_motion),
        apogee_km=apogee_km(a, ecc),
        perigee_km=perigee_km(a, ecc),
    )


# ---------------------------------------------------------------------------
# S4.6 — Regime classification
# Thresholds from CLAUDE.md / CelesTrak SOCRATES definitions:
#   e ≥ 0.25            → HEO  (Molniya-type; eccentricity dominates over altitude)
#   n ≥ 11.25 rev/day   → LEO  (period ≤ 128 min; altitude ≲ 2 000 km)
#   1.2 ≤ n < 11.25     → MEO  (GPS/Galileo band; 2 000–35 000 km)
#   n < 1.2             → GEO  (near-synchronous ring; ≈ 35 786 km)
# ---------------------------------------------------------------------------


def classify_regime(n: float, e: float) -> str:
    """Classify an orbit into LEO, MEO, GEO, or HEO.

    Parameters
    ----------
    n : mean motion in rev/day
    e : eccentricity (dimensionless, must be in [0, 1))

    Returns one of ``"LEO"``, ``"MEO"``, ``"GEO"``, or ``"HEO"``.
    Raises ValueError for out-of-range inputs.
    """
    if e < 0 or e >= 1:
        raise ValueError(f"eccentricity must be in [0, 1), got {e}")
    if n < 0:
        raise ValueError(f"mean_motion must be non-negative, got {n}")
    if e >= 0.25:
        return "HEO"
    if n >= 11.25:
        return "LEO"
    if n >= 1.2:
        return "MEO"
    return "GEO"
