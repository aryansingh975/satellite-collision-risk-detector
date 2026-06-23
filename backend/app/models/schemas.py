"""Pydantic request/response schemas — S2.4.

All API endpoints return instances of these schemas; no raw ORM objects
are exposed to callers.  Schemas that wrap ORM rows carry
``model_config = ConfigDict(from_attributes=True)`` so that
``Schema.model_validate(orm_row)`` works without an explicit dict conversion.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Satellite schemas
# ---------------------------------------------------------------------------


class SatelliteOut(BaseModel):
    """Lightweight satellite representation used in list responses."""

    model_config = ConfigDict(from_attributes=True)

    catalog_no: int
    name: str
    intl_designator: Optional[str] = None
    epoch: datetime
    regime: Optional[str] = None
    group_name: Optional[str] = None
    updated_at: datetime


class SatelliteDetail(SatelliteOut):
    """Full satellite detail including orbital elements and raw TLE lines."""

    # Orbital elements — nullable until classification has run
    a_km: Optional[float] = None
    ecc: Optional[float] = None
    inc_deg: Optional[float] = None
    mean_motion: Optional[float] = None

    # Raw TLE lines stored byte-for-byte for deterministic re-propagation
    line1: str
    line2: str


# ---------------------------------------------------------------------------
# Position schemas
# ---------------------------------------------------------------------------


class PositionSample(BaseModel):
    """Single geodetic position snapshot for one satellite at one instant.

    ``alt_km`` is in **kilometres** — the Cesium frontend converts to metres
    (multiply by 1000) before passing to ``Cartesian3.fromDegrees``.
    """

    time: datetime
    lat: float
    lon: float
    alt_km: float  # kilometres above WGS-84 ellipsoid


class PositionsResponse(BaseModel):
    """Sampled position track for one satellite (``GET /satellites/{id}/positions``)."""

    catalog_no: int
    name: str
    positions: list[PositionSample]


class BulkPositionsResponse(BaseModel):
    """Sampled position tracks for multiple satellites (``GET /satellites/positions``).

    Each entry in ``satellites`` is one ``PositionsResponse``; the list is empty when none of
    the requested catalog numbers exist in the DB — that is not an error condition.
    """

    satellites: list[PositionsResponse]


# ---------------------------------------------------------------------------
# Conjunction schemas
# ---------------------------------------------------------------------------


class ConjunctionOut(BaseModel):
    """Conjunction event returned by ``GET /conjunctions`` endpoints."""

    id: int
    sat_a: int
    sat_b: int
    sat_a_name: str
    sat_b_name: str
    tca: datetime
    miss_km: float
    rel_vel_kms: float
    window_start: datetime
    computed_at: datetime


# ---------------------------------------------------------------------------
# Stats schemas
# ---------------------------------------------------------------------------


class OrbitalRegionStats(BaseModel):
    """Satellite counts per orbital regime (``GET /stats/orbital-regions``).

    Satellites with a null regime are excluded from counts; ``total`` must
    equal ``leo + meo + geo + heo``.
    """

    leo: int
    meo: int
    geo: int
    heo: int
    total: int

    @model_validator(mode="after")
    def _check_total(self) -> "OrbitalRegionStats":
        expected = self.leo + self.meo + self.geo + self.heo
        if self.total != expected:
            raise ValueError(f"total ({self.total}) must equal leo+meo+geo+heo ({expected})")
        return self


class RiskRankingItem(BaseModel):
    """One row of the risk ranking table (``GET /stats/risk-ranking``).

    ``rank`` is 1-based and computed server-side — it is not stored in the DB.
    """

    rank: int
    sat_a: int
    sat_b: int
    sat_a_name: str
    sat_b_name: str
    miss_km: float
    rel_vel_kms: float
    tca: datetime


# ---------------------------------------------------------------------------
# Error schema
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Consistent error envelope matching FastAPI's default HTTPException shape."""

    detail: str
