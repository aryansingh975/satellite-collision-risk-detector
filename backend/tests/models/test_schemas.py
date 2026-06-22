"""Tests for S2.4 — All Pydantic schemas in backend/app/models/schemas.py."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.db.models import Satellite
from app.models.schemas import (
    ConjunctionOut,
    ErrorDetail,
    OrbitalRegionStats,
    PositionSample,
    PositionsResponse,
    RiskRankingItem,
    SatelliteDetail,
    SatelliteOut,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

EPOCH = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
TCA = datetime(2024, 6, 2, 8, 30, 0, tzinfo=timezone.utc)
NOW = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

ISS_LINE1 = "1 25544U 98067A   24153.50000000  .00007000  00000-0  12345-3 0  9990"
ISS_LINE2 = "2 25544  51.6400 123.4567 0001234  89.1234 270.9876 15.50000000123456"


def _make_satellite(**overrides) -> Satellite:
    """Construct a Satellite ORM instance without a DB session."""
    defaults = {
        "catalog_no": 25544,
        "name": "ISS (ZARYA)",
        "intl_designator": "98067A",
        "line1": ISS_LINE1,
        "line2": ISS_LINE2,
        "epoch": EPOCH,
        "a_km": 6778.0,
        "ecc": 0.0001234,
        "inc_deg": 51.64,
        "mean_motion": 15.5,
        "regime": "LEO",
        "group_name": "active",
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Satellite(**defaults)


# ---------------------------------------------------------------------------
# FR-1: SatelliteOut
# ---------------------------------------------------------------------------


def test_satellite_out_from_orm():
    sat = _make_satellite()
    out = SatelliteOut.model_validate(sat)
    assert out.catalog_no == 25544
    assert out.name == "ISS (ZARYA)"
    assert out.intl_designator == "98067A"
    assert out.epoch == EPOCH
    assert out.regime == "LEO"
    assert out.group_name == "active"
    assert out.updated_at == NOW


def test_satellite_out_missing_optional():
    """Optional fields default to None without raising ValidationError."""
    sat = _make_satellite(intl_designator=None, regime=None, group_name=None)
    out = SatelliteOut.model_validate(sat)
    assert out.intl_designator is None
    assert out.regime is None
    assert out.group_name is None


# ---------------------------------------------------------------------------
# FR-2: SatelliteDetail
# ---------------------------------------------------------------------------


def test_satellite_detail_from_orm():
    sat = _make_satellite()
    detail = SatelliteDetail.model_validate(sat)
    assert detail.catalog_no == 25544
    assert detail.a_km == pytest.approx(6778.0)
    assert detail.ecc == pytest.approx(0.0001234)
    assert detail.inc_deg == pytest.approx(51.64)
    assert detail.mean_motion == pytest.approx(15.5)
    assert detail.line1 == ISS_LINE1
    assert detail.line2 == ISS_LINE2


def test_satellite_detail_optional_elements():
    """Nullable element columns must not cause ValidationError."""
    sat = _make_satellite(a_km=None, ecc=None, inc_deg=None, mean_motion=None)
    detail = SatelliteDetail.model_validate(sat)
    assert detail.a_km is None
    assert detail.ecc is None
    assert detail.inc_deg is None
    assert detail.mean_motion is None


# ---------------------------------------------------------------------------
# FR-3: PositionSample
# ---------------------------------------------------------------------------


def test_position_sample_fields():
    """alt_km is stored as kilometres — not converted to metres."""
    sample = PositionSample(time=EPOCH, lat=51.6, lon=-70.2, alt_km=408.3)
    assert sample.alt_km == pytest.approx(408.3)
    assert sample.lat == pytest.approx(51.6)
    assert sample.lon == pytest.approx(-70.2)
    assert sample.time == EPOCH


# ---------------------------------------------------------------------------
# FR-4: PositionsResponse
# ---------------------------------------------------------------------------


def test_positions_response_empty():
    """Empty positions list is valid (decayed sat or no window)."""
    resp = PositionsResponse(catalog_no=25544, name="ISS (ZARYA)", positions=[])
    assert resp.catalog_no == 25544
    assert resp.positions == []


def test_positions_response_with_samples():
    sample = PositionSample(time=EPOCH, lat=51.6, lon=-70.2, alt_km=408.3)
    resp = PositionsResponse(catalog_no=25544, name="ISS (ZARYA)", positions=[sample])
    assert len(resp.positions) == 1
    assert resp.positions[0].alt_km == pytest.approx(408.3)


# ---------------------------------------------------------------------------
# FR-5: ConjunctionOut
# ---------------------------------------------------------------------------


def test_conjunction_out_from_fixture():
    data = {
        "id": 1,
        "sat_a": 25544,
        "sat_b": 99001,
        "sat_a_name": "ISS (ZARYA)",
        "sat_b_name": "DEBRIS-99001",
        "tca": TCA,
        "miss_km": 3.7,
        "rel_vel_kms": 7.8,
        "window_start": NOW,
        "computed_at": NOW,
    }
    conj = ConjunctionOut(**data)
    assert conj.id == 1
    assert conj.sat_a == 25544
    assert conj.sat_b == 99001
    assert conj.sat_a_name == "ISS (ZARYA)"
    assert conj.sat_b_name == "DEBRIS-99001"
    assert conj.miss_km == pytest.approx(3.7)
    assert conj.rel_vel_kms == pytest.approx(7.8)
    assert conj.tca == TCA


# ---------------------------------------------------------------------------
# FR-6: OrbitalRegionStats
# ---------------------------------------------------------------------------


def test_orbital_region_stats_valid():
    stats = OrbitalRegionStats(leo=100, meo=20, geo=10, heo=5, total=135)
    assert stats.total == 135


def test_orbital_region_stats_total_mismatch():
    """total that does not equal leo+meo+geo+heo must raise ValidationError."""
    with pytest.raises(ValidationError):
        OrbitalRegionStats(leo=100, meo=20, geo=10, heo=5, total=999)


# ---------------------------------------------------------------------------
# FR-7: RiskRankingItem
# ---------------------------------------------------------------------------


def test_risk_ranking_item():
    item = RiskRankingItem(
        rank=1,
        sat_a=25544,
        sat_b=99001,
        sat_a_name="ISS (ZARYA)",
        sat_b_name="DEBRIS-99001",
        miss_km=1.2,
        rel_vel_kms=7.8,
        tca=TCA,
    )
    assert item.rank == 1
    assert item.miss_km == pytest.approx(1.2)


# ---------------------------------------------------------------------------
# FR-8: ErrorDetail
# ---------------------------------------------------------------------------


def test_error_detail():
    err = ErrorDetail(detail="not found")
    assert err.detail == "not found"
