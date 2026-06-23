"""Tests for S6.4 — Conjunctions endpoints."""

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
# Constants — two well-known satellites for seeding
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"
EPOCH = datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc)
NOW = datetime(2021, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_satellite(catalog_no: int, name: str) -> Satellite:
    return Satellite(
        catalog_no=catalog_no,
        name=name,
        intl_designator="98067A",
        line1=ISS_LINE1,
        line2=ISS_LINE2,
        epoch=EPOCH,
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6,
        mean_motion=15.49,
        regime="LEO",
        group_name="active",
        updated_at=NOW,
    )


def _make_conjunction(
    sat_a: int,
    sat_b: int,
    miss_km: float = 2.0,
    tca: datetime | None = None,
    window_start: datetime | None = None,
) -> Conjunction:
    if tca is None:
        tca = datetime.utcnow() + timedelta(hours=1)
    if window_start is None:
        window_start = datetime.utcnow()
    return Conjunction(
        sat_a=sat_a,
        sat_b=sat_b,
        tca=tca,
        miss_km=miss_km,
        rel_vel_kms=7.5,
        window_start=window_start,
        computed_at=datetime.utcnow(),
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
# FR-1: GET /conjunctions — list with filters
# ---------------------------------------------------------------------------


def test_list_conjunctions_empty(client):
    """Empty DB returns 200 with empty list."""
    resp = client.get("/conjunctions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_conjunctions_returns_rows(client, mem_engine):
    """Seeded conjunction is returned with sat names populated."""
    sat_a = _make_satellite(25544, "ISS (ZARYA)")
    sat_b = _make_satellite(40000, "DEBRIS-1")
    conj = _make_conjunction(25544, 40000, miss_km=2.0)
    _seed(mem_engine, sat_a, sat_b, conj)

    resp = client.get("/conjunctions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert item["sat_a"] == 25544
    assert item["sat_b"] == 40000
    assert item["sat_a_name"] == "ISS (ZARYA)"
    assert item["sat_b_name"] == "DEBRIS-1"
    assert item["miss_km"] == pytest.approx(2.0)
    assert item["rel_vel_kms"] == pytest.approx(7.5)
    assert "tca" in item
    assert "window_start" in item
    assert "computed_at" in item


def test_list_conjunctions_ordered_by_miss_km(client, mem_engine):
    """Results are ordered by miss_km ascending."""
    sat_a = _make_satellite(25544, "ISS (ZARYA)")
    sat_b = _make_satellite(40000, "DEBRIS-1")
    sat_c = _make_satellite(40001, "DEBRIS-2")
    conj1 = _make_conjunction(25544, 40001, miss_km=4.5)
    conj2 = _make_conjunction(25544, 40000, miss_km=1.2)
    _seed(mem_engine, sat_a, sat_b, sat_c, conj1, conj2)

    resp = client.get("/conjunctions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["miss_km"] == pytest.approx(1.2)
    assert data[1]["miss_km"] == pytest.approx(4.5)


def test_list_conjunctions_threshold_filter(client, mem_engine):
    """?threshold=5 returns only events with miss_km <= 5."""
    sat_a = _make_satellite(25544, "ISS (ZARYA)")
    sat_b = _make_satellite(40000, "DEBRIS-1")
    sat_c = _make_satellite(40001, "DEBRIS-2")
    conj_inside = _make_conjunction(25544, 40000, miss_km=2.0)
    conj_outside = _make_conjunction(25544, 40001, miss_km=8.0)
    _seed(mem_engine, sat_a, sat_b, sat_c, conj_inside, conj_outside)

    resp = client.get("/conjunctions?threshold=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["miss_km"] == pytest.approx(2.0)


def test_list_conjunctions_window_filter(client, mem_engine):
    """?window=1 excludes conjunctions with tca > now+1h; ?window=0 disables filter."""
    sat_a = _make_satellite(25544, "ISS (ZARYA)")
    sat_b = _make_satellite(40000, "DEBRIS-1")
    far_tca = datetime.utcnow() + timedelta(hours=48)
    conj = _make_conjunction(25544, 40000, miss_km=1.0, tca=far_tca)
    _seed(mem_engine, sat_a, sat_b, conj)

    # window=1 → far-future TCA excluded
    resp = client.get("/conjunctions?window=1")
    assert resp.status_code == 200
    assert resp.json() == []

    # window=0 → filter disabled, row returned
    resp = client.get("/conjunctions?window=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


def test_list_conjunctions_limit(client, mem_engine):
    """?limit=3 returns at most 3 items."""
    sat_a = _make_satellite(10000, "SAT-A")
    sat_b = _make_satellite(10001, "SAT-B")
    _seed(mem_engine, sat_a, sat_b)
    conjunctions = [_make_conjunction(10000, 10001, miss_km=float(i)) for i in range(1, 11)]
    _seed(mem_engine, *conjunctions)

    resp = client.get("/conjunctions?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_conjunctions_limit_clamped(client, mem_engine):
    """limit > 500 is silently clamped to 500."""
    sat_a = _make_satellite(10000, "SAT-A")
    sat_b = _make_satellite(10001, "SAT-B")
    _seed(mem_engine, sat_a, sat_b)
    # Seed just 2 rows — clamping doesn't fail even with fewer rows
    conj = _make_conjunction(10000, 10001, miss_km=1.0)
    _seed(mem_engine, conj)

    resp = client.get("/conjunctions?limit=9999")
    assert resp.status_code == 200
    assert len(resp.json()) == 1  # only 1 row exists


# ---------------------------------------------------------------------------
# FR-2: GET /conjunctions/{pair_id} — single event by id
# ---------------------------------------------------------------------------


def test_get_conjunction_by_id(client, mem_engine):
    """Valid id returns correct event with sat names."""
    sat_a = _make_satellite(25544, "ISS (ZARYA)")
    sat_b = _make_satellite(40000, "DEBRIS-1")
    conj = _make_conjunction(25544, 40000, miss_km=3.1)
    _seed(mem_engine, sat_a, sat_b, conj)

    # Retrieve id from list first
    list_resp = client.get("/conjunctions")
    conj_id = list_resp.json()[0]["id"]

    resp = client.get(f"/conjunctions/{conj_id}")
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == conj_id
    assert item["sat_a"] == 25544
    assert item["sat_b"] == 40000
    assert item["sat_a_name"] == "ISS (ZARYA)"
    assert item["sat_b_name"] == "DEBRIS-1"
    assert item["miss_km"] == pytest.approx(3.1)


def test_get_conjunction_not_found(client):
    """Unknown id returns 404 with detail message."""
    resp = client.get("/conjunctions/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conjunction not found"
