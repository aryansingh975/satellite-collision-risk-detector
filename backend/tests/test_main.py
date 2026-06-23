"""Tests for S1.4 — FastAPI app factory (backend/app/main.py)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db


@pytest.fixture(autouse=True)
def patch_db_engine(monkeypatch):
    """Replace the real SQLite engine with an in-memory one for every test.

    StaticPool is required so that init_db() and get_db() share the same
    connection — without it each call to engine.connect() creates an
    independent in-memory database and the tables are invisible to sessions.
    """
    mem_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    mem_session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(_db, "engine", mem_engine)
    monkeypatch.setattr(_db, "SessionLocal", mem_session)
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


# ---------------------------------------------------------------------------
# S10.2 — CORS allows Vite dev-server origin
# ---------------------------------------------------------------------------


def test_cors_allow_origin():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin in ("http://localhost:5173", "*"), (
        f"Expected CORS allow-origin for http://localhost:5173, got: {allow_origin!r}"
    )


def test_cors_preflight():
    from app.main import app

    with TestClient(app) as client:
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
