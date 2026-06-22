"""Tests for S2.3 — Conjunction ORM model (backend/app/db/models.py)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Conjunction, Satellite

# ---------------------------------------------------------------------------
# TLE fixtures
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"

HST_LINE1 = "1 20580U 90037B   21275.52502778  .00002182  00000-0  44580-4 0  9991"
HST_LINE2 = "2 20580  28.4697 151.7849 0002859 303.6697  56.3940 15.09330078294876"

EPOCH = datetime(2021, 10, 2, 12, 36, 2, tzinfo=timezone.utc)

EXPECTED_COLUMNS = {
    "id",
    "sat_a",
    "sat_b",
    "tca",
    "miss_km",
    "rel_vel_kms",
    "window_start",
    "computed_at",
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
def fk_engine():
    """In-memory SQLite engine with foreign-key enforcement enabled."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_fk_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


@pytest.fixture()
def fk_session(fk_engine):
    Session = sessionmaker(bind=fk_engine, autocommit=False, autoflush=False)
    db = Session()
    yield db
    db.close()


def _make_satellite(catalog_no, name, line1, line2):
    return Satellite(
        catalog_no=catalog_no,
        name=name,
        intl_designator="98067A",
        line1=line1,
        line2=line2,
        epoch=EPOCH,
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6461,
        mean_motion=15.48917104,
        regime="LEO",
        group_name="active",
    )


def _make_conjunction(sat_a_no, sat_b_no, **overrides):
    defaults = dict(
        sat_a=sat_a_no,
        sat_b=sat_b_no,
        tca=datetime(2021, 10, 3, 6, 0, 0),
        miss_km=3.5,
        rel_vel_kms=7.2,
        window_start=datetime(2021, 10, 2, 12, 0, 0),
    )
    defaults.update(overrides)
    return Conjunction(**defaults)


# ---------------------------------------------------------------------------
# FR-1: table creation
# ---------------------------------------------------------------------------


def test_conjunction_table_created(mem_engine):
    table_names = inspect(mem_engine).get_table_names()
    assert "conjunctions" in table_names


def test_conjunction_columns(mem_engine):
    col_names = {c["name"] for c in inspect(mem_engine).get_columns("conjunctions")}
    assert EXPECTED_COLUMNS == col_names, f"Missing: {EXPECTED_COLUMNS - col_names}"


# ---------------------------------------------------------------------------
# FR-2: miss_km index
# ---------------------------------------------------------------------------


def test_conjunction_miss_km_index(mem_engine):
    indexes = inspect(mem_engine).get_indexes("conjunctions")
    index_names = {idx["name"] for idx in indexes}
    assert "ix_conjunctions_miss_km" in index_names


# ---------------------------------------------------------------------------
# FR-1: valid insert
# ---------------------------------------------------------------------------


def test_insert_conjunction_valid(session):
    iss = _make_satellite(25544, "ISS (ZARYA)", ISS_LINE1, ISS_LINE2)
    hst = _make_satellite(20580, "HST", HST_LINE1, HST_LINE2)
    session.add_all([iss, hst])
    session.commit()

    conj = _make_conjunction(25544, 20580)
    session.add(conj)
    session.commit()

    assert session.query(Conjunction).count() == 1


# ---------------------------------------------------------------------------
# FR-1: FK constraint enforced
# ---------------------------------------------------------------------------


def test_conjunction_fk_enforced(fk_session):
    conj = _make_conjunction(99999, 88888)  # no satellites with these IDs
    fk_session.add(conj)
    with pytest.raises(IntegrityError):
        fk_session.commit()


# ---------------------------------------------------------------------------
# FR-3: relationship back-references
# ---------------------------------------------------------------------------


def test_conjunction_relationship(session):
    iss = _make_satellite(25544, "ISS (ZARYA)", ISS_LINE1, ISS_LINE2)
    hst = _make_satellite(20580, "HST", HST_LINE1, HST_LINE2)
    session.add_all([iss, hst])
    session.commit()

    conj = _make_conjunction(25544, 20580)
    session.add(conj)
    session.commit()

    session.expire_all()
    fetched = session.query(Conjunction).first()
    assert fetched.satellite_a.name == "ISS (ZARYA)"
    assert fetched.satellite_b.name == "HST"


# ---------------------------------------------------------------------------
# FR-1: computed_at default
# ---------------------------------------------------------------------------


def test_computed_at_default(session):
    iss = _make_satellite(25544, "ISS (ZARYA)", ISS_LINE1, ISS_LINE2)
    hst = _make_satellite(20580, "HST", HST_LINE1, HST_LINE2)
    session.add_all([iss, hst])
    session.commit()

    conj = _make_conjunction(25544, 20580)  # no computed_at supplied
    session.add(conj)
    session.commit()

    session.expire_all()
    fetched = session.query(Conjunction).first()
    assert fetched.computed_at is not None
    now = datetime.utcnow()
    delta = abs((fetched.computed_at.replace(tzinfo=None) - now).total_seconds())
    assert delta < 5, f"computed_at too stale: {delta}s"
