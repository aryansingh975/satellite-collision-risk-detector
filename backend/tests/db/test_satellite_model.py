"""Tests for S2.2 — Satellite ORM model (backend/app/db/models.py)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Satellite

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"

EXPECTED_COLUMNS = {
    "catalog_no",
    "name",
    "intl_designator",
    "line1",
    "line2",
    "epoch",
    "a_km",
    "ecc",
    "inc_deg",
    "mean_motion",
    "regime",
    "group_name",
    "updated_at",
}


@pytest.fixture()
def mem_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session(mem_engine):
    Session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    db = Session()
    yield db
    db.close()


def _make_satellite(**overrides):
    defaults = dict(
        catalog_no=25544,
        name="ISS (ZARYA)",
        intl_designator="98067A",
        line1=ISS_LINE1,
        line2=ISS_LINE2,
        epoch=datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc),
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6461,
        mean_motion=15.48917104,
        regime="LEO",
        group_name="stations",
    )
    defaults.update(overrides)
    return Satellite(**defaults)


# ---------------------------------------------------------------------------
# FR-1 / FR-4: table creation
# ---------------------------------------------------------------------------


def test_satellite_table_created(mem_engine):
    inspector = inspect(mem_engine)
    col_names = {c["name"] for c in inspector.get_columns("satellites")}
    assert EXPECTED_COLUMNS == col_names, f"Missing: {EXPECTED_COLUMNS - col_names}"


# ---------------------------------------------------------------------------
# FR-1 / FR-3: insert and query (round-trip)
# ---------------------------------------------------------------------------


def test_satellite_insert_and_query(session):
    sat = _make_satellite()
    session.add(sat)
    session.commit()

    fetched = session.get(Satellite, 25544)
    assert fetched is not None
    assert fetched.catalog_no == 25544
    assert fetched.name == "ISS (ZARYA)"
    assert fetched.intl_designator == "98067A"
    assert fetched.line1 == ISS_LINE1
    assert fetched.line2 == ISS_LINE2
    assert fetched.a_km == pytest.approx(6796.4)
    assert fetched.ecc == pytest.approx(0.0003836)
    assert fetched.inc_deg == pytest.approx(51.6461)
    assert fetched.mean_motion == pytest.approx(15.48917104)
    assert fetched.regime == "LEO"
    assert fetched.group_name == "stations"


# ---------------------------------------------------------------------------
# FR-2: primary key uniqueness
# ---------------------------------------------------------------------------


def test_satellite_pk_uniqueness(session):
    sat1 = _make_satellite(catalog_no=25544, name="ISS (ZARYA)")
    sat2 = _make_satellite(catalog_no=25544, name="ISS (ZARYA) DUPLICATE")
    session.add(sat1)
    session.commit()

    session.add(sat2)
    with pytest.raises(IntegrityError):
        session.commit()


# ---------------------------------------------------------------------------
# FR-3: TLE lines stored verbatim
# ---------------------------------------------------------------------------


def test_tle_lines_stored_verbatim(session):
    sat = _make_satellite(catalog_no=25544, line1=ISS_LINE1, line2=ISS_LINE2)
    session.add(sat)
    session.commit()

    fetched = session.get(Satellite, 25544)
    assert fetched.line1 == ISS_LINE1
    assert fetched.line2 == ISS_LINE2


# ---------------------------------------------------------------------------
# FR-1: updated_at defaults automatically
# ---------------------------------------------------------------------------


def test_updated_at_defaults_to_now(session):
    sat = _make_satellite(catalog_no=99001)
    # Do not set updated_at — rely on server default
    session.add(sat)
    session.commit()

    session.expire(sat)
    fetched = session.get(Satellite, 99001)
    assert fetched.updated_at is not None
    now = datetime.utcnow()
    delta = abs((fetched.updated_at.replace(tzinfo=None) - now).total_seconds())
    assert delta < 5, f"updated_at too stale: {delta}s"


# ---------------------------------------------------------------------------
# FR-1: nullable derived fields accept None
# ---------------------------------------------------------------------------


def test_nullable_derived_fields(session):
    sat = _make_satellite(
        catalog_no=99002,
        a_km=None,
        ecc=None,
        inc_deg=None,
        mean_motion=None,
        regime=None,
        group_name=None,
        intl_designator=None,
    )
    session.add(sat)
    session.commit()

    fetched = session.get(Satellite, 99002)
    assert fetched.a_km is None
    assert fetched.ecc is None
    assert fetched.inc_deg is None
    assert fetched.mean_motion is None
    assert fetched.regime is None
    assert fetched.group_name is None
    assert fetched.intl_designator is None
