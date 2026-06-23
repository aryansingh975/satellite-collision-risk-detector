"""Conjunctions API router — S6.4."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Conjunction
from app.models.schemas import ConjunctionOut

router = APIRouter()

_MAX_LIMIT = 500


def _to_schema(row: Conjunction) -> ConjunctionOut:
    """Convert a Conjunction ORM row (with loaded relationships) to ConjunctionOut."""
    return ConjunctionOut(
        id=row.id,
        sat_a=row.sat_a,
        sat_b=row.sat_b,
        sat_a_name=row.satellite_a.name,
        sat_b_name=row.satellite_b.name,
        tca=row.tca,
        miss_km=row.miss_km,
        rel_vel_kms=row.rel_vel_kms,
        window_start=row.window_start,
        computed_at=row.computed_at,
    )


@router.get("", response_model=list[ConjunctionOut])
def list_conjunctions(
    threshold: float = Query(
        default=None,
        description="Max miss distance in km (default: RISK_THRESHOLD_KM setting)",
    ),
    window: float = Query(
        default=None,
        description="Look-ahead hours; 0 disables filter (default: SCREEN_WINDOW_HOURS setting)",
    ),
    limit: int = Query(100, ge=1, description="Max results to return (capped at 500)"),
    db: Session = Depends(get_db),
) -> list[ConjunctionOut]:
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        # Apply defaults from settings
        if threshold is None:
            threshold = settings.RISK_THRESHOLD_KM
        if window is None:
            window = float(settings.SCREEN_WINDOW_HOURS)

        # Clamp limit
        limit = min(limit, _MAX_LIMIT)

        logger.debug("list_conjunctions threshold={} window={} limit={}", threshold, window, limit)

        # Exclude co-orbiting objects (miss_km < 0.01 are physically attached, e.g. ISS modules)
        q = db.query(Conjunction).filter(
            Conjunction.miss_km <= threshold,
            Conjunction.miss_km >= 0.01,
        )

        if window > 0:
            cutoff = datetime.utcnow() + timedelta(hours=window)
            q = q.filter(Conjunction.tca <= cutoff)

        rows = q.order_by(Conjunction.miss_km).limit(limit).all()
        return [_to_schema(r) for r in rows]


@router.get("/{pair_id}", response_model=ConjunctionOut)
def get_conjunction(pair_id: int, db: Session = Depends(get_db)) -> ConjunctionOut:
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        logger.debug("get_conjunction pair_id={}", pair_id)
        row = db.query(Conjunction).filter(Conjunction.id == pair_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Conjunction not found")
        return _to_schema(row)
