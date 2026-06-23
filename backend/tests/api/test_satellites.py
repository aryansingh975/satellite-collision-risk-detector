"""Tests for S6.1 — Satellites list + detail API endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db
from app.db.database import Base, get_db
from app.db.models import Satellite

# ---------------------------------------------------------------------------
# Constants — ISS TLE (catalog 25544, well-known fixture)
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"
EPOCH = datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc)
NOW = datetime(2021, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_satellite(**overrides) -> Satellite:
    defaults = dict(
        catalog_no=25544,
        name="ISS (ZARYA)",
        intl_designator="98067A",
        line1=ISS_LINE1,
        line2=ISS_LINE2,
        epoch=EPOCH,
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6461,
        mean_motion=15.48917104,
        regime="LEO",
        group_name="active",
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Satellite(**defaults)


def _seed(engine, *satellites: Satellite) -> None:
    """Insert satellites into engine, commit, and close."""
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        for sat in satellites:
            db.add(sat)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_engine():
    """In-memory SQLite with StaticPool so all sessions share one connection."""
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
    """TestClient wired to mem_engine via dependency override."""
    from app.main import app

    Session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    # Patch _db.engine so lifespan init_db() targets mem_engine
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
# FR-1: GET /satellites — paginated list with optional filters
# ---------------------------------------------------------------------------


def test_list_satellites_empty(client):
    resp = client.get("/satellites")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_satellites_returns_all(client, mem_engine):
    _seed(
        mem_engine,
        _make_satellite(catalog_no=10001, name="SAT-A"),
        _make_satellite(catalog_no=10002, name="SAT-B"),
        _make_satellite(catalog_no=10003, name="SAT-C"),
    )
    resp = client.get("/satellites")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert [d["catalog_no"] for d in data] == [10001, 10002, 10003]


def test_list_filter_by_regime(client, mem_engine):
    _seed(
        mem_engine,
        _make_satellite(catalog_no=25544, name="ISS (ZARYA)", regime="LEO"),
        _make_satellite(catalog_no=99001, name="GEO-SAT", regime="GEO"),
    )
    resp = client.get("/satellites?regime=LEO")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["catalog_no"] == 25544
    assert data[0]["regime"] == "LEO"


def test_list_filter_by_regime_case_insensitive(client, mem_engine):
    _seed(mem_engine, _make_satellite(catalog_no=25544, regime="LEO"))
    resp = client.get("/satellites?regime=leo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["catalog_no"] == 25544


def test_list_filter_by_group(client, mem_engine):
    _seed(
        mem_engine,
        _make_satellite(catalog_no=25544, name="ISS (ZARYA)", group_name="active"),
        _make_satellite(catalog_no=99001, name="STATION-X", group_name="stations"),
    )
    resp = client.get("/satellites?group=active")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["catalog_no"] == 25544


def test_list_pagination(client, mem_engine):
    sats = [_make_satellite(catalog_no=20000 + i, name=f"SAT-{i}") for i in range(1, 6)]
    _seed(mem_engine, *sats)
    resp = client.get("/satellites?limit=2&offset=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["catalog_no"] == 20003
    assert data[1]["catalog_no"] == 20004


def test_list_unknown_regime(client):
    resp = client.get("/satellites?regime=UNKNOWN")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# FR-2: GET /satellites/{id} — single satellite detail
# ---------------------------------------------------------------------------


def test_detail_known(client, mem_engine):
    _seed(mem_engine, _make_satellite())
    resp = client.get("/satellites/25544")
    assert resp.status_code == 200
    data = resp.json()
    assert data["catalog_no"] == 25544
    assert data["name"] == "ISS (ZARYA)"
    assert data["line1"] == ISS_LINE1
    assert data["line2"] == ISS_LINE2


def test_detail_not_found(client):
    resp = client.get("/satellites/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Satellite 999999 not found"


def test_detail_schema(client, mem_engine):
    """Response contains all required SatelliteDetail fields."""
    _seed(mem_engine, _make_satellite())
    resp = client.get("/satellites/25544")
    assert resp.status_code == 200
    data = resp.json()
    required_fields = {"catalog_no", "name", "epoch", "updated_at", "line1", "line2"}
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    assert data["a_km"] == pytest.approx(6796.4, rel=1e-4)
    assert data["ecc"] == pytest.approx(0.0003836, rel=1e-4)


def test_detail_nullable_elements(client, mem_engine):
    """Satellite with no orbital elements returns 200 with null fields."""
    _seed(
        mem_engine,
        _make_satellite(
            catalog_no=99002,
            a_km=None,
            ecc=None,
            inc_deg=None,
            mean_motion=None,
            regime=None,
        ),
    )
    resp = client.get("/satellites/99002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["a_km"] is None
    assert data["ecc"] is None
    assert data["inc_deg"] is None
    assert data["mean_motion"] is None
    assert data["regime"] is None
