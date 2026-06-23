"""Tests for S6.2 — GET /satellites/{id}/positions endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db
from app.db.database import Base, get_db
from app.db.models import Satellite
from app.models.schemas import PositionsResponse

# ---------------------------------------------------------------------------
# ISS TLE fixture — same canonical TLE used in test_propagation_geodetic.py.
# Epoch ≈ 2024-05-02 12:11 UTC (day 123.50765046 of 2024).
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

# Propagation window near TLE epoch so skyfield results are accurate.
_START = datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
_STOP_1H = datetime(2024, 5, 2, 13, 0, 0, tzinfo=timezone.utc)

EPOCH = datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc)
NOW = datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iss(**overrides) -> Satellite:
    defaults = dict(
        catalog_no=25544,
        name="ISS (ZARYA)",
        intl_designator="98067A",
        line1=ISS_LINE1,
        line2=ISS_LINE2,
        epoch=EPOCH,
        a_km=6796.4,
        ecc=0.0001486,
        inc_deg=51.64,
        mean_motion=15.49311820,
        regime="LEO",
        group_name="active",
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Satellite(**defaults)


def _seed(engine, *satellites: Satellite) -> None:
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


@pytest.fixture()
def client_with_iss(mem_engine, monkeypatch):
    """TestClient pre-seeded with the ISS satellite."""
    _seed(mem_engine, _make_iss())

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
# FR-1 / FR-2 / FR-3: basic happy path
# ---------------------------------------------------------------------------


def test_positions_iss_basic(client_with_iss):
    """Outcome 1: ISS over 1h with step=60 → 200, correct catalog_no, ≥1 positions."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
            "step": 60,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["catalog_no"] == 25544
    assert data["name"] == "ISS (ZARYA)"
    positions = data["positions"]
    assert len(positions) >= 1
    for pt in positions:
        assert "lat" in pt
        assert "lon" in pt
        assert "alt_km" in pt
        assert isinstance(pt["lat"], float)
        assert isinstance(pt["lon"], float)
        assert isinstance(pt["alt_km"], float)
        # ISS is in LEO ~400 km altitude
        assert 300.0 < pt["alt_km"] < 500.0, f"ISS alt_km={pt['alt_km']:.1f} outside LEO range"


def test_positions_step_respected(client_with_iss):
    """FR-2: step=300 over 1h window → ≤13 samples (12 intervals + 1 inclusive endpoint)."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
            "step": 300,
        },
    )
    assert resp.status_code == 200, resp.text
    positions = resp.json()["positions"]
    assert len(positions) >= 1
    assert len(positions) <= 13


def test_positions_response_schema(client_with_iss):
    """Outcome 6: response parses cleanly as PositionsResponse Pydantic model."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
            "step": 60,
        },
    )
    assert resp.status_code == 200, resp.text
    # Validate against the schema — raises ValidationError if fields are wrong
    model = PositionsResponse.model_validate(resp.json())
    assert model.catalog_no == 25544
    assert len(model.positions) >= 1


# ---------------------------------------------------------------------------
# FR-1: 404 for unknown satellite
# ---------------------------------------------------------------------------


def test_positions_unknown_satellite(client):
    """Outcome 2: unknown sat_id → 404."""
    resp = client.get(
        "/satellites/99999/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
        },
    )
    assert resp.status_code == 404
    assert "99999" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# FR-1: validation — start must be before stop
# ---------------------------------------------------------------------------


def test_positions_start_not_before_stop_equal(client_with_iss):
    """Outcome 3: start == stop → 422 with 'start must be before stop'."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _START.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert "start must be before stop" in resp.json()["detail"]


def test_positions_start_after_stop(client_with_iss):
    """FR-1: start > stop → 422 with 'start must be before stop'."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _STOP_1H.isoformat(),
            "stop": _START.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert "start must be before stop" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# FR-1: validation — window too large
# ---------------------------------------------------------------------------


def test_positions_window_too_large(client_with_iss):
    """Outcome 4: 31-day window → 422."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": (_START + timedelta(days=31)).isoformat(),
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "30" in detail or "window" in detail.lower()


# ---------------------------------------------------------------------------
# FR-1: validation — step out of FastAPI Query range
# ---------------------------------------------------------------------------


def test_positions_step_zero(client_with_iss):
    """FR-1: step=0 → 422 (FastAPI Query ge=1 constraint)."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
            "step": 0,
        },
    )
    assert resp.status_code == 422


def test_positions_step_too_large(client_with_iss):
    """FR-1: step=7200 → 422 (FastAPI Query le=3600 constraint)."""
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
            "step": 7200,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# FR-3: decayed satellite — teme_to_geodetic returns [] → positions: []
# ---------------------------------------------------------------------------


def test_positions_decayed_satellite(client_with_iss):
    """Outcome 5: mock teme_to_geodetic → [] → HTTP 200 with empty positions list."""
    with patch("app.api.satellites.teme_to_geodetic", return_value=[]):
        resp = client_with_iss.get(
            "/satellites/25544/positions",
            params={
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
                "step": 60,
            },
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["positions"] == []
    assert data["catalog_no"] == 25544


# ---------------------------------------------------------------------------
# FR-2: step larger than window → single sample at start
# ---------------------------------------------------------------------------


def test_positions_step_larger_than_window(client_with_iss):
    """FR-2: step bigger than window → at least one sample emitted (start point)."""
    short_stop = _START + timedelta(seconds=30)
    resp = client_with_iss.get(
        "/satellites/25544/positions",
        params={
            "start": _START.isoformat(),
            "stop": short_stop.isoformat(),
            "step": 60,  # 60s step over a 30s window
        },
    )
    assert resp.status_code == 200, resp.text
    positions = resp.json()["positions"]
    assert len(positions) >= 1
