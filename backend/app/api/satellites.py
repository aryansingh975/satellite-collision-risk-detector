"""Satellites API router — S6.1 (list + detail) / S6.2 (positions) / S6.3 (bulk)."""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sgp4.api import jday as sgp4_jday
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Satellite
from app.models.schemas import (
    BulkPositionsResponse,
    PositionSample,
    PositionsResponse,
    SatelliteDetail,
    SatelliteOut,
)
from app.services.propagation import build_satrec_array, propagate_array, teme_to_geodetic

router = APIRouter()


@router.get("", response_model=list[SatelliteOut])
def list_satellites(
    group: Optional[str] = Query(None, description="Filter by group name (case-insensitive)"),
    regime: Optional[str] = Query(None, description="Orbital regime filter: LEO, MEO, GEO, HEO"),
    limit: int = Query(100, ge=1, le=1000, description="Page size (max 1000)"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    db: Session = Depends(get_db),
) -> list[SatelliteOut]:
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        logger.debug(
            "list_satellites group={} regime={} limit={} offset={}", group, regime, limit, offset
        )
        q = db.query(Satellite)
        if group is not None:
            q = q.filter(func.lower(Satellite.group_name) == group.lower())
        if regime is not None:
            q = q.filter(func.lower(Satellite.regime) == regime.lower())
        rows = q.order_by(Satellite.catalog_no).offset(offset).limit(limit).all()
        return [SatelliteOut.model_validate(r) for r in rows]


_MAX_WINDOW_DAYS = 30
_MAX_BULK_IDS = 500


def _jd_fr(dt: datetime) -> tuple[float, float]:
    """Convert a UTC datetime to (jd, fr) Julian date pair for sgp4."""
    sec = dt.second + dt.microsecond / 1_000_000.0
    return sgp4_jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, sec)


# S6.3 — registered before /{sat_id} so Starlette matches the static segment first
@router.get("/positions", response_model=BulkPositionsResponse)
def get_bulk_positions(
    ids: str = Query(..., description="Comma-separated NORAD catalog numbers (1–500)"),
    start: datetime = Query(..., description="Propagation window start (ISO-8601 UTC)"),
    stop: datetime = Query(..., description="Propagation window end (ISO-8601 UTC)"),
    step: int = Query(60, ge=1, le=3600, description="Step size in seconds (1–3600)"),
    db: Session = Depends(get_db),
) -> BulkPositionsResponse:
    request_id = str(uuid.uuid4())
    t0_wall = time.perf_counter()
    with logger.contextualize(request_id=request_id):
        # Parse and validate IDs
        try:
            id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="ids must be comma-separated integers")

        if not id_list:
            raise HTTPException(status_code=422, detail="ids must not be empty")
        if len(id_list) > _MAX_BULK_IDS:
            raise HTTPException(
                status_code=422,
                detail=f"ids must contain at most {_MAX_BULK_IDS} entries",
            )

        # Timezone normalization
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if stop.tzinfo is None:
            stop = stop.replace(tzinfo=timezone.utc)

        if start >= stop:
            raise HTTPException(status_code=422, detail="start must be before stop")
        if (stop - start) > timedelta(days=_MAX_WINDOW_DAYS):
            raise HTTPException(
                status_code=422,
                detail=f"window too large; maximum is {_MAX_WINDOW_DAYS} days",
            )

        # Fetch from DB — unknown IDs are silently absent
        sats = (
            db.query(Satellite)
            .filter(Satellite.catalog_no.in_(id_list))
            .order_by(Satellite.catalog_no)
            .all()
        )
        logger.debug(
            "get_bulk_positions: requested={} found={} start={} stop={} step={}",
            len(id_list),
            len(sats),
            start,
            stop,
            step,
        )

        if not sats:
            return BulkPositionsResponse(satellites=[])

        # Build time grid
        times: list[datetime] = []
        t = start
        while t <= stop:
            times.append(t)
            t += timedelta(seconds=step)
        if not times:
            times = [start]

        # Vectorized propagation via S4.3 — one SatrecArray call for all satellites
        jds = np.array([_jd_fr(t)[0] for t in times])
        frs = np.array([_jd_fr(t)[1] for t in times])

        try:
            satrec_array = build_satrec_array([(s.line1, s.line2) for s in sats])
        except ValueError as exc:
            logger.warning("get_bulk_positions: build_satrec_array failed: {}", exc)
            return BulkPositionsResponse(satellites=[])

        _, _, error_codes = propagate_array(satrec_array, jds, frs)

        # Geodetic conversion (S4.4) for each satellite with zero SGP4 error codes
        results: list[PositionsResponse] = []
        for i, sat in enumerate(sats):
            if i >= error_codes.shape[0] or not np.all(error_codes[i] == 0):
                logger.warning(
                    "get_bulk_positions: sat {} excluded — non-zero SGP4 error codes",
                    sat.catalog_no,
                )
                continue
            try:
                geodetic_pts = teme_to_geodetic(sat.line1, sat.line2, times)
            except ValueError as exc:
                logger.warning(
                    "get_bulk_positions: sat {} excluded — teme_to_geodetic failed: {}",
                    sat.catalog_no,
                    exc,
                )
                continue
            results.append(
                PositionsResponse(
                    catalog_no=sat.catalog_no,
                    name=sat.name,
                    positions=[
                        PositionSample(
                            time=t, lat=pt["lat"], lon=pt["lon"], alt_km=pt["alt_km"]
                        )
                        for t, pt in zip(times, geodetic_pts)
                    ],
                )
            )

        elapsed = time.perf_counter() - t0_wall
        logger.debug(
            "get_bulk_positions: returned={}/{} sats in {:.3f}s",
            len(results),
            len(sats),
            elapsed,
        )
        return BulkPositionsResponse(satellites=results)


@router.get("/{sat_id}", response_model=SatelliteDetail)
def get_satellite(
    sat_id: int,
    db: Session = Depends(get_db),
) -> SatelliteDetail:
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        logger.debug("get_satellite sat_id={}", sat_id)
        sat = db.get(Satellite, sat_id)
        if sat is None:
            raise HTTPException(status_code=404, detail=f"Satellite {sat_id} not found")
        return SatelliteDetail.model_validate(sat)


@router.get("/{sat_id}/positions", response_model=PositionsResponse)
def get_satellite_positions(
    sat_id: int,
    start: datetime = Query(..., description="Propagation window start (ISO-8601 UTC)"),
    stop: datetime = Query(..., description="Propagation window end (ISO-8601 UTC)"),
    step: int = Query(60, ge=1, le=3600, description="Step size in seconds (1–3600)"),
    db: Session = Depends(get_db),
) -> PositionsResponse:
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        logger.debug(
            "get_satellite_positions sat_id={} start={} stop={} step={}",
            sat_id,
            start,
            stop,
            step,
        )

        sat = db.get(Satellite, sat_id)
        if sat is None:
            raise HTTPException(status_code=404, detail=f"Satellite {sat_id} not found")

        # Ensure start/stop are timezone-aware (treat naive datetimes as UTC)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if stop.tzinfo is None:
            stop = stop.replace(tzinfo=timezone.utc)

        if start >= stop:
            raise HTTPException(status_code=422, detail="start must be before stop")

        if (stop - start) > timedelta(days=_MAX_WINDOW_DAYS):
            raise HTTPException(
                status_code=422,
                detail=f"window too large; maximum is {_MAX_WINDOW_DAYS} days",
            )

        # Build inclusive time grid: [start, start+step, ..., stop] (stop capped if not exact)
        times: list[datetime] = []
        t = start
        while t <= stop:
            times.append(t)
            t += timedelta(seconds=step)
        # Always include at least the start point
        if not times:
            times = [start]

        try:
            geodetic_points = teme_to_geodetic(sat.line1, sat.line2, times)
        except ValueError as exc:
            logger.error(
                "get_satellite_positions: teme_to_geodetic failed for sat {}: {}", sat_id, exc
            )
            raise HTTPException(status_code=500, detail="Propagation failed for this satellite")

        positions = [
            PositionSample(
                time=t,
                lat=pt["lat"],
                lon=pt["lon"],
                alt_km=pt["alt_km"],
            )
            for t, pt in zip(times, geodetic_points)
        ]

        return PositionsResponse(
            catalog_no=sat.catalog_no,
            name=sat.name,
            positions=positions,
        )
