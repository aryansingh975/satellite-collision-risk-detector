"""Tests for S3.5 — persist_satellites (backend/app/services/ingestion.py)."""

import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Satellite
from app.services.classification import classify_regime
from app.services.ingestion import persist_satellites

# ISS (ZARYA) fixture — catalog 25544, same TLE used in S3.3 tests
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

ISS_EPOCH = datetime(2024, 5, 2, 12, 11, 1, tzinfo=timezone.utc)


def _make_record(
    catalog_no: int,
    name: str = "SAT",
    line1: str = ISS_LINE1,
    line2: str = ISS_LINE2,
) -> dict:
    return {
        "catalog_no": catalog_no,
        "name": name,
        "intl_designator": "98067A",
        "line1": line1,
        "line2": line2,
        "epoch": ISS_EPOCH,
        "mean_motion": 15.49311820,
        "ecc": 0.0001486,
        "inc_deg": 51.6400,
        "a_km": None,
        "regime": None,
        "group_name": "stations",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db(mem_engine):
    Session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_persist_satellites_inserts_new_rows(db):
    """Outcome 1: 3 records into empty DB → (3, 0), 3 rows in table."""
    records = [
        _make_record(25544, "ISS (ZARYA)"),
        _make_record(25545, "SAT-B"),
        _make_record(25546, "SAT-C"),
    ]
    inserted, updated = persist_satellites(db, records)

    assert inserted == 3
    assert updated == 0
    assert db.query(Satellite).count() == 3
    catalog_nos = {s.catalog_no for s in db.query(Satellite).all()}
    assert catalog_nos == {25544, 25545, 25546}


def test_persist_satellites_upserts_on_conflict(db):
    """Outcome 2: same 3 records twice → no duplicates; second call returns (0, 3)."""
    records = [
        _make_record(25544, "ISS (ZARYA)"),
        _make_record(25545, "SAT-B"),
        _make_record(25546, "SAT-C"),
    ]
    persist_satellites(db, records)
    inserted, updated = persist_satellites(db, records)

    assert inserted == 0
    assert updated == 3
    assert db.query(Satellite).count() == 3


def test_persist_satellites_line_bytes_preserved(db):
    """Outcome 3: stored line1/line2 are byte-for-byte identical to the input strings."""
    persist_satellites(db, [_make_record(25544, "ISS (ZARYA)", ISS_LINE1, ISS_LINE2)])

    sat = db.get(Satellite, 25544)
    assert sat is not None
    assert sat.line1 == ISS_LINE1
    assert sat.line2 == ISS_LINE2


def test_persist_satellites_empty_list(db):
    """Outcome 4: empty list → (0, 0), no rows written."""
    inserted, updated = persist_satellites(db, [])

    assert inserted == 0
    assert updated == 0
    assert db.query(Satellite).count() == 0


def test_persist_satellites_updated_at_refreshed(db):
    """Outcome 5: second upsert of same record sets updated_at >= first updated_at."""
    record = _make_record(25544, "ISS (ZARYA)")
    persist_satellites(db, [record])

    first_updated_at = db.get(Satellite, 25544).updated_at

    time.sleep(0.01)  # ensure system clock advances before second upsert
    persist_satellites(db, [record])
    db.expire_all()
    second_updated_at = db.get(Satellite, 25544).updated_at

    assert second_updated_at >= first_updated_at


def test_persist_satellites_dedupes_within_batch(db):
    """FR-3: same catalog_no twice in one batch → only 1 row; last record wins."""
    original = _make_record(25544, "ISS (ZARYA)")
    duplicate = _make_record(25544, "ISS DUPLICATE")

    inserted, updated = persist_satellites(db, [original, duplicate])

    assert db.query(Satellite).count() == 1
    assert inserted == 1
    assert updated == 0
    sat = db.get(Satellite, 25544)
    assert sat.name == "ISS DUPLICATE"


# ---------------------------------------------------------------------------
# S4.6 integration: classify_regime populates Satellite.regime in DB
# ---------------------------------------------------------------------------


def test_regime_populated_via_classify_regime(db):
    """FR-3 (S4.6): calling classify_regime before persist stores the correct regime."""
    record = _make_record(25544, "ISS (ZARYA)")
    # ISS: n≈15.49 rev/day, e≈0.0001 → LEO
    record["regime"] = classify_regime(record["mean_motion"], record["ecc"])

    persist_satellites(db, [record])

    sat = db.get(Satellite, 25544)
    assert sat is not None
    assert sat.regime == "LEO"
