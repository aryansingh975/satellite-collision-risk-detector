"""Tests for S1.4 — FastAPI app factory (backend/app/main.py)."""

import pytest
from sqlalchemy import create_engine
from fastapi.testclient import TestClient

import app.db.database as _db


@pytest.fixture(autouse=True)
def patch_db_engine(monkeypatch):
    """Replace the real SQLite engine with an in-memory one for every test."""
    mem_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    monkeypatch.setattr(_db, "engine", mem_engine)
    yield mem_engine


# ---------------------------------------------------------------------------
# FR-5: Health endpoint
# ---------------------------------------------------------------------------


def test_health_ok():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# FR-2: DB tables created on startup
# ---------------------------------------------------------------------------


def test_db_tables_created_on_startup(patch_db_engine):
    from app.main import app

    with TestClient(app):
        table_names = list(_db.Base.metadata.tables.keys())
    assert "satellites" in table_names
    assert "conjunctions" in table_names


# ---------------------------------------------------------------------------
# FR-3: APScheduler lifecycle
# ---------------------------------------------------------------------------


def test_scheduler_starts_on_startup():
    from app.main import app

    with TestClient(app) as client:
        assert client.app.state.scheduler.running is True


def test_scheduler_stops_on_shutdown():
    from app.main import app

    with TestClient(app) as client:
        scheduler = client.app.state.scheduler
    assert scheduler.running is False


# ---------------------------------------------------------------------------
# FR-4: Router mounting (all three routers must not 404)
# ---------------------------------------------------------------------------


def test_satellites_router_mounted():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/satellites")
    assert resp.status_code != 404


def test_conjunctions_router_mounted():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/conjunctions")
    assert resp.status_code != 404


def test_stats_router_mounted():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/stats/orbital-regions")
    assert resp.status_code != 404
