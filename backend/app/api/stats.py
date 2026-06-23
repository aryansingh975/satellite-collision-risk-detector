"""Stats router — S6.5.

GET /stats/orbital-regions  → OrbitalRegionStats (counts per regime)
GET /stats/risk-ranking     → list[RiskRankingItem] (top-N by miss distance)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.db.database import get_db
from app.db.models import Conjunction, Satellite
from app.models.schemas import OrbitalRegionStats, RiskRankingItem

router = APIRouter()

_KNOWN_REGIMES = {"LEO", "MEO", "GEO", "HEO"}


@router.get("/orbital-regions", response_model=OrbitalRegionStats)
def orbital_regions(db: Session = Depends(get_db)) -> OrbitalRegionStats:
    rows = (
        db.query(Satellite.regime, func.count(Satellite.catalog_no))
        .filter(Satellite.regime.isnot(None))
        .group_by(Satellite.regime)
        .all()
    )
    counts: dict[str, int] = {regime: count for regime, count in rows if regime in _KNOWN_REGIMES}
    leo = counts.get("LEO", 0)
    meo = counts.get("MEO", 0)
    geo = counts.get("GEO", 0)
    heo = counts.get("HEO", 0)
    return OrbitalRegionStats(leo=leo, meo=meo, geo=geo, heo=heo, total=leo + meo + geo + heo)


@router.get("/risk-ranking", response_model=list[RiskRankingItem])
def risk_ranking(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[RiskRankingItem]:
    SatA = aliased(Satellite)
    SatB = aliased(Satellite)

    rows = (
        db.query(Conjunction, SatA.name, SatB.name)
        .join(SatA, Conjunction.sat_a == SatA.catalog_no)
        .join(SatB, Conjunction.sat_b == SatB.catalog_no)
        .filter(Conjunction.miss_km >= 0.01)  # exclude co-orbiting objects (ISS modules etc.)
        .order_by(Conjunction.miss_km.asc(), Conjunction.rel_vel_kms.desc())
        .limit(limit)
        .all()
    )

    return [
        RiskRankingItem(
            rank=idx + 1,
            sat_a=conj.sat_a,
            sat_b=conj.sat_b,
            sat_a_name=name_a,
            sat_b_name=name_b,
            miss_km=conj.miss_km,
            rel_vel_kms=conj.rel_vel_kms,
            tca=conj.tca,
        )
        for idx, (conj, name_a, name_b) in enumerate(rows)
    ]
