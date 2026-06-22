"""S4.1 — Satrec builder: construct SGP4 satellite records from raw TLE line pairs.
S4.2 — Single-sat propagation: propagate(sat, times) → TEME pos/vel arrays.
S4.4 — TEME→geodetic conversion: teme_to_geodetic(line1, line2, times) → lat/lon/alt
       for display only. Conjunction math stays in TEME.

WGS-72 gravity constants are used throughout (matches TLE generation conventions).
Do NOT switch to WGS-84.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import numpy as np
from loguru import logger
from sgp4.api import SGP4_ERRORS, Satrec, SatrecArray, jday
from skyfield.api import EarthSatellite
from skyfield.api import load as _skyfield_load
from skyfield.api import wgs84

# Module-level Timescale — builtin=True avoids network I/O for IERS data.
_TS = _skyfield_load.timescale(builtin=True)


class PropagationError(Exception):
    """Raised when SGP4 returns a non-zero error code during propagation."""


def _datetime_to_jd(dt: datetime) -> tuple[float, float]:
    """Convert a UTC datetime to (jd, fr) Julian date pair for sgp4."""
    sec = dt.second + dt.microsecond / 1_000_000.0
    return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, sec)


def propagate(sat: Satrec, times: list[datetime]) -> tuple[np.ndarray, np.ndarray]:
    """Propagate a single satellite over a list of UTC datetimes.

    Returns (positions, velocities) as float64 arrays of shape (N, 3) in TEME km / km·s⁻¹.
    Raises PropagationError if SGP4 returns a non-zero error code for any timestep.
    """
    if not times:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.float64)

    positions: list = []
    velocities: list = []
    for t in times:
        jd_val, fr = _datetime_to_jd(t)
        e, r, v = sat.sgp4(jd_val, fr)
        if e != 0:
            detail = SGP4_ERRORS.get(e, "unknown error")
            raise PropagationError(f"SGP4 error {e} ({detail}) for sat {sat.satnum} at {t}")
        positions.append(r)
        velocities.append(v)

    return np.array(positions, dtype=np.float64), np.array(velocities, dtype=np.float64)


def build_satrec(line1: str, line2: str) -> Satrec:
    """Return an SGP4 Satrec initialised from a raw TLE line pair.

    Uses the sgp4 library default (WGS-72 gravity constants).  Raises ValueError
    if the library reports a non-zero error code after initialisation.
    """
    sat = Satrec.twoline2rv(line1, line2)
    if sat.error != 0:
        detail = SGP4_ERRORS.get(sat.error, "unknown error")
        raise ValueError(
            f"SGP4 initialisation error {sat.error} for satellite '{line1[2:7].strip()}': {detail}"
        )
    return sat


def propagate_array(
    satrec_array: SatrecArray,
    jds: np.ndarray,
    frs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Propagate all satellites over a time grid using SatrecArray.sgp4 (vectorized).

    Unlike propagate(), does NOT raise on SGP4 errors — returns error codes so the
    caller (conjunction screen, S5.2) can decide which satellites to exclude.

    Returns:
        positions:   (n_sats, n_times, 3) TEME km, float64
        velocities:  (n_sats, n_times, 3) TEME km·s⁻¹, float64
        error_codes: (n_sats, n_times) uint8, zero means success
    """
    n_sats = len(satrec_array)
    n_times = len(jds)

    if n_times == 0:
        return (
            np.empty((n_sats, 0, 3), dtype=np.float64),
            np.empty((n_sats, 0, 3), dtype=np.float64),
            np.empty((n_sats, 0), dtype=np.uint8),
        )

    e, r, v = satrec_array.sgp4(jds, frs)

    positions = np.asarray(r, dtype=np.float64)
    velocities = np.asarray(v, dtype=np.float64)
    error_codes = np.asarray(e)

    if np.any(error_codes != 0):
        n_error_sats = int(np.any(error_codes != 0, axis=1).sum())
        n_error_steps = int((error_codes != 0).sum())
        logger.warning(
            "propagate_array: {} of {} satellite(s) have SGP4 errors ({} total error timestep(s))",
            n_error_sats,
            n_sats,
            n_error_steps,
        )

    return positions, velocities, error_codes


def build_satrec_array(tle_pairs: list[tuple[str, str]]) -> SatrecArray:
    """Return a SatrecArray built from a list of (line1, line2) TLE pairs.

    Bad pairs (non-zero SGP4 error) are skipped with a WARNING log; the rest
    are assembled into the array.  Raises ValueError if tle_pairs is empty or
    if every pair is invalid.
    """
    if not tle_pairs:
        raise ValueError("tle_pairs must not be empty")

    valid: list[Satrec] = []
    for line1, line2 in tle_pairs:
        try:
            valid.append(build_satrec(line1, line2))
        except ValueError as exc:
            logger.warning("Skipping invalid TLE pair: {}", exc)

    if not valid:
        raise ValueError("No valid TLE pairs found in the supplied batch")

    return SatrecArray(valid)


def teme_to_geodetic(
    line1: str,
    line2: str,
    times: Sequence[datetime],
) -> list[dict[str, float | None]]:
    """Convert a satellite's TLE track to geodetic lat/lon/alt for display.

    Uses skyfield EarthSatellite + wgs84.subpoint — the display-only boundary.
    Conjunction math must stay in TEME; never call this from the conjunction pipeline.

    Returns one dict per valid timestep with keys 'lat', 'lon', 'alt_km'.
    Timesteps where SGP4 signals an error (NaN position vector) are skipped with
    a WARNING log.  Negative altitudes are included with a DEBUG log.
    Raises ValueError for malformed or physically invalid TLE lines.
    """
    if not times:
        return []

    catalog = line1[2:7].strip() if len(line1) >= 7 else "unknown"
    try:
        sat = EarthSatellite(line1, line2, ts=_TS)
    except Exception as exc:
        raise ValueError(f"Cannot build EarthSatellite for sat {catalog}: {exc}") from exc

    if sat.model.error != 0:
        detail = SGP4_ERRORS.get(sat.model.error, "unknown error")
        raise ValueError(f"SGP4 init error {sat.model.error} ({detail}) for sat {catalog}")

    results: list[dict[str, float | None]] = []
    for t in times:
        ts_t = _TS.utc(
            t.year,
            t.month,
            t.day,
            t.hour,
            t.minute,
            t.second + t.microsecond / 1_000_000.0,
        )
        geocentric = sat.at(ts_t)
        pos_km = geocentric.position.km
        if np.any(np.isnan(pos_km)):
            logger.warning(
                "teme_to_geodetic: NaN position for sat {} at {} — timestep skipped",
                sat.model.satnum,
                t,
            )
            continue
        subpoint = wgs84.subpoint(geocentric)
        alt = float(subpoint.elevation.km)
        if alt < 0.0:
            logger.debug(
                "teme_to_geodetic: negative altitude {:.2f} km for sat {} at {} — included",
                alt,
                sat.model.satnum,
                t,
            )
        results.append(
            {
                "lat": float(subpoint.latitude.degrees),
                "lon": float(subpoint.longitude.degrees),
                "alt_km": alt,
            }
        )

    return results
