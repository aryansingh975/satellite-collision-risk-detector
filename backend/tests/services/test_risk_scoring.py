"""Tests for S5.5 — Risk Scoring + Persist (backend/app/services/conjunctions.py)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Conjunction, Satellite
from app.services.conjunctions import TCARefinement, score_and_persist

# ---------------------------------------------------------------------------
# TLE text fixtures (same as other test files in this suite)
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   21275.52502778  .00002182  00000-0  44580-4 0  9990"
ISS_LINE2 = "2 25544  51.6461 121.1237 0003836 206.2024 303.1972 15.48917104305523"

HST_LINE1 = "1 20580U 90037B   21275.52502778  .00002182  00000-0  44580-4 0  9991"
HST_LINE2 = "2 20580  28.4697 151.7849 0002859 303.6697  56.3940 15.09330078294876"

_EPOCH = datetime(2021, 10, 2, 12, 36, 2)
_WINDOW_START = datetime(2021, 10, 2, 12, 0, 0)
_TCA_NAIVE = datetime(2021, 10, 3, 6, 0, 0)

# Two-element catalog list: index 0 → ISS (25544), index 1 → HST (20580)
# Canonical ordering: sat_a = min(25544, 20580) = 20580, sat_b = 25544.
CATALOG_NOS = [25544, 20580]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    """Session with ISS and HST satellite rows pre-inserted (satisfy FK constraints)."""
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    iss = Satellite(
        catalog_no=25544,
        name="ISS (ZARYA)",
        intl_designator="98067A",
        line1=ISS_LINE1,
        line2=ISS_LINE2,
        epoch=_EPOCH,
        a_km=6796.4,
        ecc=0.0003836,
        inc_deg=51.6461,
        mean_motion=15.48917104,
        regime="LEO",
        group_name="active",
    )
    hst = Satellite(
        catalog_no=20580,
        name="HST",
        intl_designator="90037B",
        line1=HST_LINE1,
        line2=HST_LINE2,
        epoch=_EPOCH,
        a_km=6919.2,
        ecc=0.0002859,
        inc_deg=28.4697,
        mean_motion=15.09330078,
        regime="LEO",
        group_name="active",
    )
    session.add_all([iss, hst])
    session.commit()
    yield session
    session.close()


def _ref(
    sat_a_idx: int,
    sat_b_idx: int,
    miss_km: float,
    rel_vel_kms: float = 7.5,
    tca: datetime = _TCA_NAIVE,
) -> TCARefinement:
    """Build a TCARefinement with the given miss_km / rel_vel_kms."""
    return TCARefinement(
        sat_a_idx=sat_a_idx,
        sat_b_idx=sat_b_idx,
        tca=tca,
        miss_km=miss_km,
        rel_vel_kms=rel_vel_kms,
    )


# ---------------------------------------------------------------------------
# FR-1: filter by risk threshold
# ---------------------------------------------------------------------------


def test_filter_by_threshold(db):
    """miss_km [1.0, 4.9, 5.0, 5.1] with threshold 5.0 → 3 events survive (≤ 5.0)."""
    refinements = [
        _ref(0, 1, 1.0),
        _ref(0, 1, 4.9),
        _ref(0, 1, 5.0),  # boundary: exactly at threshold → included
        _ref(0, 1, 5.1),  # exceeds threshold → excluded
    ]
    result = score_and_persist(refinements, CATALOG_NOS, _WINDOW_START, 5.0, db)
    assert len(result) == 3
    assert all(c.miss_km <= 5.0 for c in result)


def test_filter_all_none(db):
    """All-None refinements → empty result, Conjunction table stays empty."""
    result = score_and_persist([None, None], CATALOG_NOS, _WINDOW_START, 5.0, db)
    assert result == []
    assert db.query(Conjunction).count() == 0


def test_filter_zero_threshold(db):
    """risk_threshold_km=0.0 → no event passes (miss_km is always > 0 in practice)."""
    result = score_and_persist([_ref(0, 1, 0.001)], CATALOG_NOS, _WINDOW_START, 0.0, db)
    assert result == []


# ---------------------------------------------------------------------------
# FR-2: ranking — ascending miss_km, descending rel_vel_kms tie-break
# ---------------------------------------------------------------------------


def test_rank_by_miss_then_vel(db):
    """miss_km [3.0, 1.5, 3.0], rel_vel [7.0, 5.0, 9.0] → [1.5/5.0, 3.0/9.0, 3.0/7.0]."""
    refinements = [
        _ref(0, 1, miss_km=3.0, rel_vel_kms=7.0),
        _ref(0, 1, miss_km=1.5, rel_vel_kms=5.0),
        _ref(0, 1, miss_km=3.0, rel_vel_kms=9.0),
    ]
    result = score_and_persist(refinements, CATALOG_NOS, _WINDOW_START, 5.0, db)
    assert len(result) == 3
    assert result[0].miss_km == pytest.approx(1.5)
    assert result[0].rel_vel_kms == pytest.approx(5.0)
    assert result[1].miss_km == pytest.approx(3.0)
    assert result[1].rel_vel_kms == pytest.approx(9.0)  # higher vel → ranks before 7.0
    assert result[2].miss_km == pytest.approx(3.0)
    assert result[2].rel_vel_kms == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# FR-4: idempotency
# ---------------------------------------------------------------------------


def test_persist_idempotent(db):
    """Same window_start called twice → count equals one call's output, not doubled."""
    refinements = [_ref(0, 1, 2.5), _ref(0, 1, 4.0)]
    score_and_persist(refinements, CATALOG_NOS, _WINDOW_START, 5.0, db)
    db.commit()
    score_and_persist(refinements, CATALOG_NOS, _WINDOW_START, 5.0, db)
    db.commit()
    count = db.query(Conjunction).filter(Conjunction.window_start == _WINDOW_START).count()
    assert count == 2


def test_persist_empty_clears_old(db):
    """All-None input for an existing window deletes prior rows, leaves table empty."""
    for miss in (1.5, 3.0):
        db.add(
            Conjunction(
                sat_a=20580,
                sat_b=25544,
                tca=_TCA_NAIVE,
                miss_km=miss,
                rel_vel_kms=7.0,
                window_start=_WINDOW_START,
            )
        )
    db.commit()
    assert db.query(Conjunction).count() == 2

    score_and_persist([None, None], CATALOG_NOS, _WINDOW_START, 5.0, db)
    db.commit()
    assert db.query(Conjunction).filter(Conjunction.window_start == _WINDOW_START).count() == 0


# ---------------------------------------------------------------------------
# FR-4: TCA timezone stripping
# ---------------------------------------------------------------------------


def test_persist_tca_naive(db):
    """Timezone-aware TCA is stored as naive UTC in the DB (SQLite has no tz column)."""
    tca_aware = datetime(2021, 10, 3, 6, 0, 0, tzinfo=timezone.utc)
    r = TCARefinement(sat_a_idx=0, sat_b_idx=1, tca=tca_aware, miss_km=2.0, rel_vel_kms=7.0)
    score_and_persist([r], CATALOG_NOS, _WINDOW_START, 5.0, db)
    db.commit()
    db.expire_all()
    stored = db.query(Conjunction).first()
    assert stored.tca.tzinfo is None
    assert stored.tca == datetime(2021, 10, 3, 6, 0, 0)


# ---------------------------------------------------------------------------
# FR-3: canonical catalog ordering (sat_a < sat_b)
# ---------------------------------------------------------------------------


def test_persist_catalog_order(db):
    """sat_a_idx=5 (cat 25544), sat_b_idx=2 (cat 20580) → stored as sat_a=20580 < sat_b=25544."""
    # 6-element catalog map; only indices 2 and 5 are used in this test
    catalog_nos = [99999, 99998, 20580, 99997, 99996, 25544]
    r = TCARefinement(sat_a_idx=5, sat_b_idx=2, tca=_TCA_NAIVE, miss_km=2.0, rel_vel_kms=7.0)
    score_and_persist([r], catalog_nos, _WINDOW_START, 5.0, db)
    db.commit()
    db.expire_all()
    stored = db.query(Conjunction).first()
    assert stored.sat_a == 20580
    assert stored.sat_b == 25544


# ---------------------------------------------------------------------------
# Full pipeline: FR-1 + FR-2 + FR-3 + FR-4
# ---------------------------------------------------------------------------


def test_score_and_persist_full_pipeline(db):
    """2 valid refinements + 1 None, threshold 5 km → 2 persisted, correct order & catalog nos."""
    refinements = [
        _ref(0, 1, miss_km=4.5, rel_vel_kms=8.0),
        None,
        _ref(0, 1, miss_km=2.0, rel_vel_kms=6.0),
    ]
    result = score_and_persist(refinements, CATALOG_NOS, _WINDOW_START, 5.0, db)
    db.commit()

    assert len(result) == 2
    # Ordered ascending by miss_km
    assert result[0].miss_km == pytest.approx(2.0)
    assert result[1].miss_km == pytest.approx(4.5)
    # Canonical catalog ordering: 20580 < 25544
    for row in result:
        assert row.sat_a == 20580
        assert row.sat_b == 25544
    assert db.query(Conjunction).count() == 2
