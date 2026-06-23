"""Tests for S6.5 — Stats endpoints (/stats/orbital-regions, /stats/risk-ranking)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db
from app.db.database import Base, get_db
from app.db.models import Conjunction, Satellite

# ---------------------------------------------------------------------------
# Shared TLE lines (content not used for computation in these tests)
# ---------------------------------------------------------------------------

_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"
_EPOCH = datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc)
_NOW = datetime(2021, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_satellite(catalog_no: int, name: str, regime: str | None = "LEO") -> Satellite:
    return Satellite(
        catalog_no=catalog_no,
        name=name,
        intl_designator="98067A",
        line1=_LINE1,
        line2=_LINE2,
        epoch=_EPOCH,
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6,
        mean_motion=15.49,
        regime=regime,
        group_name="active",
        updated_at=_NOW,
    )


def _make_conjunction(
    sat_a: int,
    sat_b: int,
    miss_km: float = 2.0,
    rel_vel_kms: float = 7.5,
    tca: datetime | None = None,
) -> Conjunction:
    if tca is None:
        tca = _NOW + timedelta(hours=1)
    return Conjunction(
        sat_a=sat_a,
        sat_b=sat_b,
        tca=tca,
        miss_km=miss_km,
        rel_vel_kms=rel_vel_kms,
        window_start=_NOW,
        computed_at=_NOW,
    )


def _seed(engine, *objects) -> None:
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        for obj in objects:
            db.add(obj)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(mem_engine, monkeypatch):
    from app.main import app

    Session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(_db, "engine", mem_engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# FR-1: GET /stats/orbital-regions
# ---------------------------------------------------------------------------


def test_orbital_regions_empty_db(client):
    """Empty DB returns all-zero counts."""
    resp = client.get("/stats/orbital-regions")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"leo": 0, "meo": 0, "geo": 0, "heo": 0, "total": 0}


def test_orbital_regions_counts(client, mem_engine):
    """Known regime mix returns correct per-bucket counts and total."""
    _seed(
        mem_engine,
        _make_satellite(1, "LEO-1", regime="LEO"),
        _make_satellite(2, "LEO-2", regime="LEO"),
        _make_satellite(3, "MEO-1", regime="MEO"),
        _make_satellite(4, "GEO-1", regime="GEO"),
        _make_satellite(5, "HEO-1", regime="HEO"),
        _make_satellite(6, "HEO-2", regime="HEO"),
    )
    resp = client.get("/stats/orbital-regions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["leo"] == 2
    assert data["meo"] == 1
    assert data["geo"] == 1
    assert data["heo"] == 2
    assert data["total"] == 6


def test_orbital_regions_null_regime_excluded(client, mem_engine):
    """Satellites with regime=None are excluded from all counts."""
    _seed(
        mem_engine,
        _make_satellite(10, "SAT-NULL-1", regime=None),
        _make_satellite(11, "SAT-NULL-2", regime=None),
        _make_satellite(12, "LEO-1", regime="LEO"),
    )
    resp = client.get("/stats/orbital-regions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["leo"] == 1
    assert data["meo"] == 0
    assert data["geo"] == 0
    assert data["heo"] == 0
    assert data["total"] == 1


def test_orbital_regions_unknown_regime_excluded(client, mem_engine):
    """Satellites with an unrecognised regime string are excluded silently."""
    _seed(
        mem_engine,
        _make_satellite(20, "WEIRD", regime="UNKNOWN"),
        _make_satellite(21, "LEO-X", regime="LEO"),
    )
    resp = client.get("/stats/orbital-regions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["leo"] == 1
    assert data["total"] == 1


# ---------------------------------------------------------------------------
# FR-2: GET /stats/risk-ranking
# ---------------------------------------------------------------------------


def test_risk_ranking_empty(client):
    """No conjunctions → 200 with empty list."""
    resp = client.get("/stats/risk-ranking")
    assert resp.status_code == 200
    assert resp.json() == []


def test_risk_ranking_order(client, mem_engine):
    """Three conjunctions returned ordered by miss_km ascending with correct 1-based ranks."""
    sat_a = _make_satellite(100, "SAT-A")
    sat_b = _make_satellite(101, "SAT-B")
    sat_c = _make_satellite(102, "SAT-C")
    _seed(mem_engine, sat_a, sat_b, sat_c)
    _seed(
        mem_engine,
        _make_conjunction(100, 102, miss_km=4.5),
        _make_conjunction(100, 101, miss_km=1.2),
        _make_conjunction(101, 102, miss_km=3.0),
    )

    resp = client.get("/stats/risk-ranking")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["miss_km"] == pytest.approx(1.2)
    assert data[0]["rank"] == 1
    assert data[1]["miss_km"] == pytest.approx(3.0)
    assert data[1]["rank"] == 2
    assert data[2]["miss_km"] == pytest.approx(4.5)
    assert data[2]["rank"] == 3


def test_risk_ranking_tie_break(client, mem_engine):
    """Tied miss_km: higher rel_vel_kms comes first."""
    sat_a = _make_satellite(200, "SAT-A")
    sat_b = _make_satellite(201, "SAT-B")
    sat_c = _make_satellite(202, "SAT-C")
    _seed(mem_engine, sat_a, sat_b, sat_c)
    _seed(
        mem_engine,
        _make_conjunction(200, 201, miss_km=2.0, rel_vel_kms=5.0),
        _make_conjunction(200, 202, miss_km=2.0, rel_vel_kms=10.0),
    )

    resp = client.get("/stats/risk-ranking")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["rel_vel_kms"] == pytest.approx(10.0)
    assert data[1]["rel_vel_kms"] == pytest.approx(5.0)


def test_risk_ranking_limit(client, mem_engine):
    """?limit=2 returns exactly 2 items from 5 seeded conjunctions."""
    sat_a = _make_satellite(300, "SAT-A")
    sat_b = _make_satellite(301, "SAT-B")
    _seed(mem_engine, sat_a, sat_b)
    _seed(mem_engine, *[_make_conjunction(300, 301, miss_km=float(i)) for i in range(1, 6)])

    resp = client.get("/stats/risk-ranking?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_risk_ranking_limit_exceeds_count(client, mem_engine):
    """?limit=20 with only 3 conjunctions returns all 3."""
    sat_a = _make_satellite(400, "SAT-A")
    sat_b = _make_satellite(401, "SAT-B")
    _seed(mem_engine, sat_a, sat_b)
    _seed(
        mem_engine,
        _make_conjunction(400, 401, miss_km=1.0),
        _make_conjunction(400, 401, miss_km=2.0),
        _make_conjunction(400, 401, miss_km=3.0),
    )

    resp = client.get("/stats/risk-ranking?limit=20")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_risk_ranking_limit_invalid_zero(client):
    """`?limit=0` is below minimum → HTTP 422."""
    resp = client.get("/stats/risk-ranking?limit=0")
    assert resp.status_code == 422


def test_risk_ranking_limit_invalid_over_max(client):
    """`?limit=101` exceeds maximum → HTTP 422."""
    resp = client.get("/stats/risk-ranking?limit=101")
    assert resp.status_code == 422


def test_risk_ranking_names(client, mem_engine):
    """Response items include sat_a_name and sat_b_name from the Satellite join."""
    sat_a = _make_satellite(500, "ISS (ZARYA)")
    sat_b = _make_satellite(501, "DEBRIS-99")
    _seed(mem_engine, sat_a, sat_b)
    _seed(mem_engine, _make_conjunction(500, 501, miss_km=1.5))

    resp = client.get("/stats/risk-ranking")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sat_a_name"] == "ISS (ZARYA)"
    assert data[0]["sat_b_name"] == "DEBRIS-99"
    assert data[0]["sat_a"] == 500
    assert data[0]["sat_b"] == 501
