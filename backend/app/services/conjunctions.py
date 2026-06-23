"""Conjunction engine.

S5.1 — Apogee/Perigee Sieve: eliminates pairs whose orbital shells cannot intersect.
S5.2 — Window Sampling: propagates survivor-pair satellites over the screening window.
S5.3 — cKDTree Spatial Screen: per-timestep cKDTree query to flag candidate close pairs.
S5.4 — TCA Refinement: dense re-propagation to find exact Time of Closest Approach,
       miss distance (km), and relative velocity (km/s) for each flagged pair.
S5.5 — Risk Scoring + Persist: filter by RISK_THRESHOLD_KM, rank, idempotently persist
       to the Conjunction table keyed on window_start.

Pipeline order: apogee_perigee_sieve → sample_window → ckdtree_screen → refine_tca
               → score_and_persist
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

import numpy as np
from loguru import logger
from scipy.spatial import cKDTree
from sgp4.api import Satrec, SatrecArray
from sgp4.api import jday as _jday

from sqlalchemy.orm import Session

from app.db.models import Conjunction, Satellite
from app.services.classification import derive_orbital_elements
from app.services.propagation import build_satrec, propagate_array

# J2000 epoch constants for Julian-date → UTC conversion
_J2000_JD = 2451545.0
_J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class TCARefinement:
    """Result of TCA refinement for one satellite pair (S5.4 output)."""

    sat_a_idx: int
    sat_b_idx: int
    tca: datetime  # UTC-aware datetime of closest approach
    miss_km: float  # separation (km) at TCA
    rel_vel_kms: float  # relative speed (km/s) at TCA


def _jd_to_utc(jd: float) -> datetime:
    """Convert a Julian date scalar to a UTC-aware datetime."""
    return _J2000_EPOCH + timedelta(days=jd - _J2000_JD)


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

    # Process in row-chunks to avoid allocating an n×n matrix (n=15k → 2 GB).
    # Only iterate upper triangle: col_start >= row_start.
    # Accumulate pairs as numpy int32 chunks (10× less RAM than Python tuples).
    _CHUNK = 512
    chunks: list[np.ndarray] = []
    for row_start in range(0, n - 1, _CHUNK):
        row_end = min(row_start + _CHUNK, n)
        peri_a = perigees[row_start:row_end, np.newaxis]  # (chunk_r, 1)
        apo_a = apogees[row_start:row_end, np.newaxis]    # (chunk_r, 1)

        for col_start in range(row_start, n, _CHUNK):
            col_end = min(col_start + _CHUNK, n)
            peri_b = perigees[np.newaxis, col_start:col_end]  # (1, chunk_c)
            apo_b = apogees[np.newaxis, col_start:col_end]    # (1, chunk_c)

            surviving = ~((peri_a - apo_b > pad_km) | (peri_b - apo_a > pad_km))

            local_ii, local_jj = np.where(surviving)
            abs_i = (local_ii + row_start).astype(np.int32)
            abs_j = (local_jj + col_start).astype(np.int32)
            mask = abs_i < abs_j
            if mask.any():
                chunks.append(np.column_stack([abs_i[mask], abs_j[mask]]))

    if not chunks:
        return []
    pairs_arr = np.concatenate(chunks, axis=0)  # (N_pairs, 2) int32
    return list(zip(pairs_arr[:, 0].tolist(), pairs_arr[:, 1].tolist()))


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


# ---------------------------------------------------------------------------
# S5.4 — TCA Refinement & Miss Distance
# ---------------------------------------------------------------------------


def _build_dense_bracket(
    jds: np.ndarray,
    frs: np.ndarray,
    coarse_t_idx: int,
    screen_step_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a ±screen_step_s dense bracket around coarse_t_idx at 1-second resolution.

    Clamps the bracket start/end to the valid coarse grid bounds when coarse_t_idx
    is at an array boundary, preventing the bracket from reaching outside the
    propagation window.

    Returns (dense_jds, dense_frs) both shaped (n_steps,).
    """
    step_s = float(screen_step_s)
    t_centre = jds[coarse_t_idx] + frs[coarse_t_idx]
    t_grid_start = jds[0] + frs[0]
    t_grid_end = jds[-1] + frs[-1]

    t_lo = max(t_centre - step_s / 86400.0, t_grid_start)
    t_hi = min(t_centre + step_s / 86400.0, t_grid_end)

    n_steps = max(1, int(round((t_hi - t_lo) * 86400.0)) + 1)

    jd_base = math.floor(t_lo)
    fr_start = t_lo - jd_base

    dense_jds = np.full(n_steps, float(jd_base), dtype=np.float64)
    dense_frs = fr_start + np.arange(n_steps, dtype=np.float64) / 86400.0

    return dense_jds, dense_frs


def _find_tca_in_bracket(
    pos_a: np.ndarray,
    vel_a: np.ndarray,
    pos_b: np.ndarray,
    vel_b: np.ndarray,
    dense_jds: np.ndarray,
    dense_frs: np.ndarray,
) -> tuple[float, float, float]:
    """Find TCA from dense TEME position/velocity arrays (km, km/s).

    Detects the Time of Closest Approach via the range-rate sign change
    (negative → positive) and linearly interpolates for sub-second precision.
    Falls back to argmin(|r_rel|) when no sign change is found.

    When multiple zero crossings exist, picks the one whose surrounding miss
    distance is globally smallest.

    Returns:
        tca_jd:      Julian date of TCA (float, sub-second precision).
        miss_km:     Separation (km) at TCA timestep.
        rel_vel_kms: Relative speed (km/s) at TCA timestep.
    """
    r_rel = pos_a - pos_b  # (N, 3) TEME km
    v_rel = vel_a - vel_b  # (N, 3) TEME km/s

    r_norm = np.linalg.norm(r_rel, axis=1)  # (N,)
    r_safe = np.maximum(r_norm, 1e-6)  # floor avoids div/0

    # Range-rate: ṙ = (r_rel · v_rel) / |r_rel|
    range_rate = np.einsum("ij,ij->i", r_rel, v_rel) / r_safe  # (N,)

    # All negative→positive zero crossings (approaching → receding = TCA)
    crossings = np.where((range_rate[:-1] < 0) & (range_rate[1:] >= 0))[0]

    if crossings.size == 0:
        # No sign change → fall back to global minimum distance
        tca_idx = int(np.argmin(r_norm))
        tca_jd = float(dense_jds[tca_idx] + dense_frs[tca_idx])
    else:
        # Multiple crossings → pick the one with the smallest neighbouring miss_km
        r_at_crossings = np.minimum(r_norm[crossings], r_norm[crossings + 1])
        best_i = int(crossings[int(np.argmin(r_at_crossings))])

        # Linear interpolation for sub-second TCA precision
        rr0 = float(range_rate[best_i])
        rr1 = float(range_rate[best_i + 1])
        denom = rr1 - rr0
        frac = (-rr0 / denom) if denom != 0.0 else 0.5
        frac = max(0.0, min(1.0, frac))

        jd0 = float(dense_jds[best_i] + dense_frs[best_i])
        jd1 = float(dense_jds[best_i + 1] + dense_frs[best_i + 1])
        tca_jd = jd0 + frac * (jd1 - jd0)
        tca_idx = best_i

    miss_km = float(r_norm[tca_idx])
    rel_vel_kms = float(np.linalg.norm(v_rel[tca_idx]))

    return tca_jd, miss_km, rel_vel_kms


def refine_tca(
    flagged_pairs: list[tuple[int, int, int]],
    satrec_list: list[Satrec],
    jds: np.ndarray,
    frs: np.ndarray,
    screen_step_s: float,
) -> list[Optional[TCARefinement]]:
    """Refine each flagged pair to find its TCA, miss distance, and relative velocity.

    For each (sat_a_idx, sat_b_idx, coarse_t_idx) tuple:
      1. Build a ±screen_step_s dense bracket around coarse_t_idx at 1-second resolution.
      2. Propagate both satellites over the bracket using SatrecArray.
      3. Detect the range-rate sign change → TCA, miss_km, rel_vel_kms.

    Args:
        flagged_pairs:  Flat 3-tuples (sat_a_idx, sat_b_idx, coarse_t_idx) from S5.3.
                        Convert from ckdtree_screen's ((i,j), t_idx) format before calling.
        satrec_list:    Full Satrec catalog; pairs index into this list.
        jds:            Coarse time grid Julian date integer parts (n_coarse,).
        frs:            Coarse time grid Julian date fractional parts (n_coarse,).
        screen_step_s:  Coarse step size in seconds; used as bracket half-width.

    Returns:
        One entry per input pair: TCARefinement on success, None when SGP4 errors occur.
        Returns [] immediately for empty input.
    """
    if not flagged_pairs:
        return []

    results: list[Optional[TCARefinement]] = []

    for sat_a_idx, sat_b_idx, coarse_t_idx in flagged_pairs:
        sat_a = satrec_list[sat_a_idx]
        sat_b = satrec_list[sat_b_idx]

        # Catch init-time errors (e.g., subterrestrial TLEs from BAD_LINE)
        err_a = getattr(sat_a, "error", 0)
        err_b = getattr(sat_b, "error", 0)
        if err_a != 0 or err_b != 0:
            logger.warning(
                "refine_tca: SGP4 init error ({}/{}) for pair ({}, {}) — skipping",
                err_a,
                err_b,
                sat_a_idx,
                sat_b_idx,
            )
            results.append(None)
            continue

        dense_jds, dense_frs = _build_dense_bracket(jds, frs, coarse_t_idx, screen_step_s)

        # Vectorized propagation of the pair over the dense bracket
        pair_arr = SatrecArray([sat_a, sat_b])
        e_arr, r_arr, v_arr = pair_arr.sgp4(dense_jds, dense_frs)
        # e_arr: (2, N), r_arr: (2, N, 3), v_arr: (2, N, 3)

        e_arr = np.asarray(e_arr)
        r_arr = np.asarray(r_arr, dtype=np.float64)
        v_arr = np.asarray(v_arr, dtype=np.float64)

        # Catch runtime SGP4 errors (e.g., decayed orbit during propagation)
        if np.any(e_arr != 0):
            first_err = int(e_arr[e_arr != 0].flat[0])
            logger.warning(
                "refine_tca: SGP4 propagation error {} for pair ({}, {}) — skipping",
                first_err,
                sat_a_idx,
                sat_b_idx,
            )
            results.append(None)
            continue

        tca_jd, miss_km, rel_vel_kms = _find_tca_in_bracket(
            r_arr[0], v_arr[0], r_arr[1], v_arr[1], dense_jds, dense_frs
        )

        results.append(
            TCARefinement(
                sat_a_idx=sat_a_idx,
                sat_b_idx=sat_b_idx,
                tca=_jd_to_utc(tca_jd),
                miss_km=miss_km,
                rel_vel_kms=rel_vel_kms,
            )
        )

    return results


# ---------------------------------------------------------------------------
# S5.5 — Risk Scoring + Persist
# ---------------------------------------------------------------------------


def score_and_persist(
    refinements: list[Optional[TCARefinement]],
    catalog_nos: list[int],
    window_start_dt: datetime,
    risk_threshold_km: float,
    db: Session,
) -> list[Conjunction]:
    """Filter, rank, and idempotently persist conjunction events to the Conjunction table.

    Pipeline:
      FR-1: Discard None entries; keep only miss_km ≤ risk_threshold_km.
      FR-2: Sort ascending miss_km; tie-break descending rel_vel_kms.
      FR-3: Map sat_a_idx / sat_b_idx → NORAD catalog numbers; enforce sat_a < sat_b.
      FR-4: Delete all Conjunction rows for window_start_dt, bulk-insert ranked events,
            flush session. Caller controls commit.

    Args:
        refinements:       Output of refine_tca — list of TCARefinement or None.
        catalog_nos:       NORAD catalog number at each positional index (same ordering as
                           the satrec_list passed to refine_tca).
        window_start_dt:   UTC start of the screening window (idempotency key).
        risk_threshold_km: Maximum miss distance to keep (RISK_THRESHOLD_KM, default 5 km).
        db:                SQLAlchemy Session (caller commits after return).

    Returns:
        List of newly created Conjunction ORM instances in ranked order.

    Raises:
        IndexError: if sat_a_idx or sat_b_idx is out of range for catalog_nos.
    """
    # FR-1: drop propagation failures and events exceeding the risk threshold
    filtered: list[TCARefinement] = [
        r for r in refinements if r is not None and r.miss_km <= risk_threshold_km
    ]

    logger.info(
        "score_and_persist: {}/{} refinements pass threshold ({} km)",
        len(filtered),
        sum(1 for r in refinements if r is not None),
        risk_threshold_km,
    )

    # FR-2: rank ascending miss_km, tie-break descending rel_vel_kms
    ranked = sorted(filtered, key=lambda r: (r.miss_km, -r.rel_vel_kms))

    # Naive datetime for SQLite storage (DateTime column has no timezone)
    window_naive = (
        window_start_dt.replace(tzinfo=None) if window_start_dt.tzinfo else window_start_dt
    )

    # FR-4: delete prior records for this window (idempotency)
    db.query(Conjunction).filter(Conjunction.window_start == window_naive).delete()

    # FR-3 + FR-4: map indices → catalog numbers, insert
    inserted: list[Conjunction] = []
    for r in ranked:
        cat_a = catalog_nos[r.sat_a_idx]  # IndexError propagates on bad index
        cat_b = catalog_nos[r.sat_b_idx]
        canon_a = min(cat_a, cat_b)
        canon_b = max(cat_a, cat_b)

        tca_naive = r.tca.replace(tzinfo=None) if r.tca.tzinfo else r.tca

        conj = Conjunction(
            sat_a=canon_a,
            sat_b=canon_b,
            tca=tca_naive,
            miss_km=r.miss_km,
            rel_vel_kms=r.rel_vel_kms,
            window_start=window_naive,
            computed_at=datetime.utcnow(),
        )
        db.add(conj)
        inserted.append(conj)

    db.flush()

    logger.info("score_and_persist: {} events persisted for window {}", len(inserted), window_naive)

    return inserted


# ---------------------------------------------------------------------------
# S6.6 — Full conjunction screen pipeline (called by the scheduler)
# ---------------------------------------------------------------------------


def run_conjunction_screen(db: Session, cfg=None) -> int:
    """Run the full conjunction pipeline against current DB satellites and persist results.

    Pipeline: load DB → sieve → window sample → cKDTree → TCA refine → score & persist.
    Returns total conjunction events persisted.
    """
    from app.core.config import settings as _settings

    if cfg is None:
        cfg = _settings

    rows = (
        db.query(Satellite)
        .filter(
            Satellite.line1.isnot(None),
            Satellite.line2.isnot(None),
            Satellite.mean_motion.isnot(None),
            Satellite.ecc.isnot(None),
        )
        .all()
    )

    if len(rows) < 2:
        logger.info("run_conjunction_screen: fewer than 2 valid satellites, skip")
        return 0

    # Cap the satellite count so the sieve/screen stay within memory limits.
    max_sats = getattr(cfg, "SCREEN_MAX_SATS", 5000)
    if len(rows) > max_sats:
        logger.info(
            "run_conjunction_screen: capping {} satellites → {} (SCREEN_MAX_SATS)",
            len(rows),
            max_sats,
        )
        rows = rows[:max_sats]

    @dataclass
    class _SatProxy:
        apogee_km: float
        perigee_km: float

    proxies: list[_SatProxy] = []
    satrec_list: list[Satrec] = []
    catalog_nos: list[int] = []

    for row in rows:
        try:
            satrec = build_satrec(row.line1, row.line2)
            elems = derive_orbital_elements(row.mean_motion, row.ecc)
        except Exception:
            logger.debug(
                "run_conjunction_screen: skipping catalog_no={} — build error", row.catalog_no
            )
            continue
        proxies.append(_SatProxy(apogee_km=elems.apogee_km, perigee_km=elems.perigee_km))
        satrec_list.append(satrec)
        catalog_nos.append(row.catalog_no)

    if len(proxies) < 2:
        logger.info("run_conjunction_screen: fewer than 2 valid satrecs after build, skip")
        return 0

    t_start = datetime.now(timezone.utc)

    survivors = apogee_perigee_sieve(proxies, pad_km=30.0)
    logger.info(
        "run_conjunction_screen: {} survivor pairs from {} satellites",
        len(survivors),
        len(proxies),
    )

    if not survivors:
        score_and_persist([], catalog_nos, t_start, cfg.RISK_THRESHOLD_KM, db)
        db.commit()
        return 0

    positions, jds, frs, unique_indices = sample_window(
        survivors,
        satrec_list,
        t_start,
        float(cfg.SCREEN_WINDOW_HOURS),
        float(cfg.SCREEN_STEP_SECONDS),
    )

    hits = ckdtree_screen(positions, survivors, unique_indices, float(cfg.COARSE_RADIUS_KM))
    logger.info("run_conjunction_screen: {} cKDTree hits", len(hits))

    # Convert ((i, j), t_idx) format from ckdtree_screen → (i, j, t_idx) for refine_tca
    flagged = [(i, j, t) for (i, j), t in hits]
    refinements = refine_tca(flagged, satrec_list, jds, frs, float(cfg.SCREEN_STEP_SECONDS))

    conjunctions = score_and_persist(
        refinements, catalog_nos, t_start, cfg.RISK_THRESHOLD_KM, db
    )
    db.commit()

    logger.info("run_conjunction_screen: {} events persisted", len(conjunctions))
    return len(conjunctions)
