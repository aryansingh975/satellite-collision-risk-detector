"""Shared pytest fixtures for the satellite collision risk detector backend.

Provides: in-memory SQLite engine + session, FastAPI TestClient with DB
override, ISS TLE constants, a pre-built Satellite fixture, and a respx
mock for CelesTrak. Individual test files may shadow any fixture locally.
"""

from __future__ import annotations

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
# ISS TLE constants (NORAD 25544) — the canonical test fixture per CLAUDE.md
# ---------------------------------------------------------------------------

ISS_CATALOG_NO = 25544
ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"
ISS_EPOCH = datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# anyio backend — required for @pytest.mark.anyio tests (ingestion, cache)
# ---------------------------------------------------------------------------


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ---------------------------------------------------------------------------
# In-memory SQLite engine — shared across all DB-touching tests
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
def db_session(mem_engine):
    """SQLAlchemy session bound to mem_engine; closed on teardown."""
    Session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    db = Session()
    yield db
    db.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient wired to the in-memory engine
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(mem_engine, monkeypatch):
    """TestClient with get_db overridden to use the in-memory SQLite engine."""
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
# TLE fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def iss_tle() -> dict:
    """Raw ISS TLE fields as a dict (catalog_no, line1, line2, epoch)."""
    return {
        "catalog_no": ISS_CATALOG_NO,
        "name": "ISS (ZARYA)",
        "intl_designator": "98067A",
        "line1": ISS_LINE1,
        "line2": ISS_LINE2,
        "epoch": ISS_EPOCH,
    }


@pytest.fixture()
def iss_satellite(iss_tle) -> Satellite:
    """Pre-built ISS Satellite ORM object — not yet committed to any session."""
    return Satellite(
        catalog_no=iss_tle["catalog_no"],
        name=iss_tle["name"],
        intl_designator=iss_tle["intl_designator"],
        line1=iss_tle["line1"],
        line2=iss_tle["line2"],
        epoch=iss_tle["epoch"],
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6461,
        mean_motion=15.48917104,
        regime="LEO",
        group_name="active",
        updated_at=ISS_EPOCH,
    )


# ---------------------------------------------------------------------------
# CelesTrak mock — prevents any live HTTP calls in tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_celestrak_csv() -> str:
    """Minimal CSV payload that mirrors the CelesTrak GP CSV format."""
    return (
        "OBJECT_NAME,OBJECT_ID,EPOCH,MEAN_MOTION,ECCENTRICITY,INCLINATION,"
        "RA_OF_ASC_NODE,ARG_OF_PERICENTER,MEAN_ANOMALY,EPHEMERIS_TYPE,"
        "CLASSIFICATION_TYPE,NORAD_CAT_ID,ELEMENT_SET_NO,REV_AT_EPOCH,"
        "BSTAR,MEAN_MOTION_DOT,MEAN_MOTION_DDOT\n"
        "ISS (ZARYA),1998-067A,2021-10-02T12:36:02.240832,15.48917104,"
        "0.0003836,51.6461,121.1237,206.2024,303.1972,0,U,25544,999,30552,"
        "0.000044580,0.00002182,0\n"
    )
