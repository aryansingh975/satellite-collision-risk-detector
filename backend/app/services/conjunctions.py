"""Conjunction engine.

S5.1 — Apogee/Perigee Sieve: eliminates pairs whose orbital shells cannot intersect.
S5.2 — Window Sampling: propagates survivor-pair satellites over the screening window.
S5.3 — cKDTree Spatial Screen: per-timestep cKDTree query to flag candidate close pairs.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Sequence

import numpy as np
from loguru import logger
from scipy.spatial import cKDTree
from sgp4.api import Satrec, SatrecArray
from sgp4.api import jday as _jday

from app.services.propagation import propagate_array


def apogee_perigee_sieve(
    satellites: Sequence[Any],
    pad_km: float = 30.0,
) -> list[tuple[int, int]]:
    """Return index pairs (i, j) with i < j whose altitude shells overlap within pad_km.

    A pair is rejected when either satellite's perigee is more than pad_km above the
    other's apogee, meaning their orbital shells cannot come within pad_km of each other:

        reject if  perigee_A − apogee_B > pad_km
                OR perigee_B − apogee_A > pad_km

    Each satellite must expose .apogee_km and .perigee_km (float, km).
    """
    n = len(satellites)
    if n < 2:
        return []

    apogees = np.array([s.apogee_km for s in satellites], dtype=np.float64)
    perigees = np.array([s.perigee_km for s in satellites], dtype=np.float64)

    # peri_minus_apo[i, j] = perigee[i] − apogee[j]  (shape n×n via broadcasting)
    peri_minus_apo = np.subtract.outer(perigees, apogees)

    # Upper-triangle indices only (i < j — no self-pairs, no duplicates)
    ii, jj = np.triu_indices(n, k=1)

    rejected = (peri_minus_apo[ii, jj] > pad_km) | (peri_minus_apo[jj, ii] > pad_km)
    surviving = ~rejected

    return list(zip(ii[surviving].tolist(), jj[surviving].tolist()))


def _build_time_grid(
    t_start: datetime,
    window_hours: float,
    step_seconds: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a uniform JD time grid from t_start over window_hours at step_seconds spacing.

    Inclusive of both endpoints; always returns at least one timestep.
    Returns (jds, frs) where the full Julian date at index k is jds[k] + frs[k].
    """
    total_seconds = window_hours * 3600.0
    n_times = max(1, int(math.floor(total_seconds / step_seconds)) + 1)

    sec = t_start.second + t_start.microsecond / 1_000_000.0
    jd0, fr0 = _jday(t_start.year, t_start.month, t_start.day, t_start.hour, t_start.minute, sec)

    step_jd = step_seconds / 86400.0
    offsets = np.arange(n_times, dtype=np.float64) * step_jd

    jds = np.full(n_times, float(jd0), dtype=np.float64)
    frs = fr0 + offsets

    return jds, frs


def sample_window(
    survivors: list[tuple[int, int]],
    satrecs: list[Satrec],
    t_start: datetime,
    window_hours: float,
    step_seconds: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    """Propagate the unique satellites from survivor pairs over the screening window.

    Positions are in the TEME frame (km) — no geodetic conversion occurs here.
    Timesteps where SGP4 reports a non-zero error (e.g., decayed orbit) are set to NaN
    and a WARNING is logged; no exception is raised.

    Args:
        survivors:     Output of apogee_perigee_sieve — list of (i, j) index pairs.
        satrecs:       One Satrec per satellite in the full catalog, same indexing as sieve.
        t_start:       UTC start of the screening window.
        window_hours:  Total window length in hours (SCREEN_WINDOW_HOURS, typically 24–72).
        step_seconds:  Sample spacing in seconds (SCREEN_STEP_SECONDS, typically 30–60).

    Returns:
        positions:      (n_unique, n_times, 3) float64 TEME km; NaN where SGP4 errored.
        jds:            (n_times,) Julian date integer parts.
        frs:            (n_times,) Julian date fractional parts.
        unique_indices: Sorted list of original satellite indices; positions[k] belongs to
                        the satellite at unique_indices[k].
    """
    # FR-1: Build time grid
    jds, frs = _build_time_grid(t_start, window_hours, step_seconds)
    n_times = len(jds)

    # FR-2: Extract unique, sorted satellite indices from all surviving pairs
    unique_indices: list[int] = sorted({idx for pair in survivors for idx in pair})
    n_unique = len(unique_indices)

    # FR-3: Skip SatrecArray construction if no candidates survive the sieve
    if n_unique == 0:
        return np.empty((0, n_times, 3), dtype=np.float64), jds, frs, unique_indices

    subset = [satrecs[i] for i in unique_indices]
    satrec_arr = SatrecArray(subset)
    positions, _, error_codes = propagate_array(satrec_arr, jds, frs)
    positions = positions.copy()  # ensure array is writeable before NaN injection

    # FR-4: NaN out positions at errored timesteps; warn once per affected satellite
    if np.any(error_codes != 0):
        for k, orig_idx in enumerate(unique_indices):
            bad = error_codes[k] != 0
            if np.any(bad):
                logger.warning(
                    "sample_window: SGP4 errors for satellite index {} at {}/{} timestep(s)"
                    " — positions set to NaN",
                    orig_idx,
                    int(bad.sum()),
                    n_times,
                )
                positions[k, bad, :] = np.nan

    # FR-5: Return positions + time grid + index map
    return positions, jds, frs, unique_indices


def ckdtree_screen(
    positions: np.ndarray,
    survivors: list[tuple[int, int]],
    unique_indices: list[int],
    coarse_radius_km: float,
) -> list[tuple[tuple[int, int], int]]:
    """Screen surviving pairs with a per-timestep cKDTree spatial query.

    For each timestep, builds a cKDTree from satellites with fully finite positions
    and calls query_pairs(r=coarse_radius_km). Pairs not in survivors are filtered out.
    The coarse radius is generous to bridge fast-crossing pairs between sample points.

    Args:
        positions:        (n_unique, n_times, 3) float64 TEME km; NaN where SGP4 errored.
        survivors:        Sieve-surviving (i, j) pairs from apogee_perigee_sieve.
        unique_indices:   Original satellite indices; positions[k] → unique_indices[k].
        coarse_radius_km: Spatial threshold in km (COARSE_RADIUS_KM, typically 10–20 km).

    Returns:
        List of ((i, j), t_idx) where i < j are original satellite indices and t_idx is the
        0-based timestep. A pair may appear multiple times; S5.4 groups by pair to find the
        minimum-distance bracket. query_pairs uses strict inequality (dist < r).
    """
    if not survivors:
        return []

    survivor_set: set[tuple[int, int]] = set(survivors)
    n_times = positions.shape[1] if positions.ndim == 3 else 0
    hits: list[tuple[tuple[int, int], int]] = []

    for t in range(n_times):
        P_t = positions[:, t, :]  # (n_unique, 3)
        valid_mask = np.all(np.isfinite(P_t), axis=1)
        valid_rows = np.where(valid_mask)[0]

        if valid_rows.shape[0] < 2:
            continue

        local_pairs = cKDTree(P_t[valid_rows]).query_pairs(r=coarse_radius_km)

        for a, b in local_pairs:
            orig_a = unique_indices[valid_rows[a]]
            orig_b = unique_indices[valid_rows[b]]
            pair = (min(orig_a, orig_b), max(orig_a, orig_b))
            if pair in survivor_set:
                hits.append((pair, t))

    return hits
