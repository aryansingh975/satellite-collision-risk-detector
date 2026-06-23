"""Tests for S6.3 — GET /satellites/positions bulk positions endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db
from app.db.database import Base, get_db
from app.db.models import Satellite

# ---------------------------------------------------------------------------
# ISS TLE fixture — same canonical TLE used in test_positions.py
# ---------------------------------------------------------------------------

ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"

_START = datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
_STOP_1H = datetime(2024, 5, 2, 13, 0, 0, tzinfo=timezone.utc)
EPOCH = datetime(2024, 5, 2, 12, 11, 0, tzinfo=timezone.utc)
NOW = datetime(2024, 5, 2, 12, 0, 0, tzinfo=timezone.utc)

_FAKE_GEODETIC = [{"lat": 10.0, "lon": -90.0, "alt_km": 420.5}]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_satellite(catalog_no: int, name: str = "SAT") -> Satellite:
    return Satellite(
        catalog_no=catalog_no,
        name=name,
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


def _seed(engine, *satellites: Satellite) -> None:
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        for sat in satellites:
            db.add(sat)
        db.commit()
    finally:
        db.close()


def _fake_propagate_return(n_sats: int, n_times: int):
    """All-zero error codes → all satellites survive the error-code filter."""
    return (
        np.zeros((n_sats, n_times, 3)),
        np.zeros((n_sats, n_times, 3)),
        np.zeros((n_sats, n_times), dtype=np.uint8),
    )


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
    """TestClient wired to in-memory SQLite, no pre-seeded satellites."""
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
def client_two_sats(mem_engine, monkeypatch):
    """TestClient pre-seeded with two satellites (catalog 25544 and 33591)."""
    _seed(
        mem_engine,
        _make_satellite(25544, "ISS (ZARYA)"),
        _make_satellite(33591, "SAT-B"),
    )

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
# FR-1: Happy path — two satellites returned
# ---------------------------------------------------------------------------


def test_bulk_positions_returns_two_satellites(client_two_sats):
    """Outcome 1: two known IDs → satellites list with two entries, each has positions."""
    with patch("app.api.satellites.build_satrec_array") as mock_bsa, patch(
        "app.api.satellites.propagate_array"
    ) as mock_pa, patch(
        "app.api.satellites.teme_to_geodetic", return_value=_FAKE_GEODETIC
    ):
        mock_bsa.return_value = MagicMock()
        mock_pa.return_value = _fake_propagate_return(2, 1)

        resp = client_two_sats.get(
            "/satellites/positions",
            params={
                "ids": "25544,33591",
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
                "step": 60,
            },
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "satellites" in data
    sats = data["satellites"]
    assert len(sats) == 2
    for entry in sats:
        assert "catalog_no" in entry
        assert "name" in entry
        assert len(entry["positions"]) >= 1
        pt = entry["positions"][0]
        assert "time" in pt
        assert "lat" in pt
        assert "lon" in pt
        assert "alt_km" in pt


# ---------------------------------------------------------------------------
# FR-1: Unknown IDs silently skipped
# ---------------------------------------------------------------------------


def test_bulk_positions_unknown_id_skipped(client_two_sats):
    """Outcome 2: one known ID + one unknown → only the known satellite returned."""
    with patch("app.api.satellites.build_satrec_array") as mock_bsa, patch(
        "app.api.satellites.propagate_array"
    ) as mock_pa, patch(
        "app.api.satellites.teme_to_geodetic", return_value=_FAKE_GEODETIC
    ):
        mock_bsa.return_value = MagicMock()
        mock_pa.return_value = _fake_propagate_return(1, 1)

        resp = client_two_sats.get(
            "/satellites/positions",
            params={
                "ids": "25544,999999",
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
            },
        )

    assert resp.status_code == 200, resp.text
    sats = resp.json()["satellites"]
    assert len(sats) == 1
    assert sats[0]["catalog_no"] == 25544


def test_bulk_positions_all_unknown_returns_empty(client):
    """Outcome 2: all IDs unknown → satellites: [] (not 404)."""
    resp = client.get(
        "/satellites/positions",
        params={
            "ids": "999999,888888",
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data == {"satellites": []}


# ---------------------------------------------------------------------------
# FR-1: Validation — start >= stop → 422
# ---------------------------------------------------------------------------


def test_bulk_positions_start_gte_stop_422(client):
    """Outcome 3: start == stop → 422."""
    resp = client.get(
        "/satellites/positions",
        params={
            "ids": "25544",
            "start": _START.isoformat(),
            "stop": _START.isoformat(),
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# FR-1: Validation — missing ids param → 422
# ---------------------------------------------------------------------------


def test_bulk_positions_empty_ids_422(client):
    """Outcome 4: ids param absent → 422 (FastAPI required-query validation)."""
    resp = client.get(
        "/satellites/positions",
        params={
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# FR-1: Validation — ids > 500 → 422
# ---------------------------------------------------------------------------


def test_bulk_positions_too_many_ids_422(client):
    """Outcome 5: 501 IDs → 422."""
    too_many = ",".join(str(i) for i in range(501))
    resp = client.get(
        "/satellites/positions",
        params={
            "ids": too_many,
            "start": _START.isoformat(),
            "stop": _STOP_1H.isoformat(),
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# FR-1: Validation — window > 30 days → 422
# ---------------------------------------------------------------------------


def test_bulk_positions_window_too_large_422(client):
    """Outcome 3 (window): 31-day window → 422."""
    resp = client.get(
        "/satellites/positions",
        params={
            "ids": "25544",
            "start": _START.isoformat(),
            "stop": (_START + timedelta(days=31)).isoformat(),
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# FR-2: Vectorized propagation — propagate_array called exactly once
# ---------------------------------------------------------------------------


def test_bulk_positions_uses_propagate_array(client_two_sats):
    """Outcome 6: propagate_array is called exactly once for a 2-satellite request."""
    with patch("app.api.satellites.build_satrec_array") as mock_bsa, patch(
        "app.api.satellites.propagate_array"
    ) as mock_pa, patch(
        "app.api.satellites.teme_to_geodetic", return_value=_FAKE_GEODETIC
    ):
        mock_bsa.return_value = MagicMock()
        mock_pa.return_value = _fake_propagate_return(2, 1)

        client_two_sats.get(
            "/satellites/positions",
            params={
                "ids": "25544,33591",
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
                "step": 60,
            },
        )

    mock_pa.assert_called_once()


# ---------------------------------------------------------------------------
# FR-3: teme_to_geodetic failure → satellite excluded, others retained
# ---------------------------------------------------------------------------


def test_bulk_positions_error_satellite_excluded(client_two_sats):
    """Outcome: if teme_to_geodetic raises ValueError for one sat, it is excluded."""
    call_count = [0]

    def teme_side_effect(line1, line2, times):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("SGP4 decayed — simulated failure")
        return _FAKE_GEODETIC

    with patch("app.api.satellites.build_satrec_array") as mock_bsa, patch(
        "app.api.satellites.propagate_array"
    ) as mock_pa, patch(
        "app.api.satellites.teme_to_geodetic", side_effect=teme_side_effect
    ):
        mock_bsa.return_value = MagicMock()
        mock_pa.return_value = _fake_propagate_return(2, 1)

        resp = client_two_sats.get(
            "/satellites/positions",
            params={
                "ids": "25544,33591",
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
                "step": 60,
            },
        )

    assert resp.status_code == 200, resp.text
    sats = resp.json()["satellites"]
    assert len(sats) == 1


# ---------------------------------------------------------------------------
# FR-4: Response schema — BulkPositionsResponse parses correctly
# ---------------------------------------------------------------------------


def test_bulk_positions_response_schema(client_two_sats):
    """Outcome 7: response parses as BulkPositionsResponse; satellites key present."""
    from app.models.schemas import BulkPositionsResponse

    with patch("app.api.satellites.build_satrec_array") as mock_bsa, patch(
        "app.api.satellites.propagate_array"
    ) as mock_pa, patch(
        "app.api.satellites.teme_to_geodetic", return_value=_FAKE_GEODETIC
    ):
        mock_bsa.return_value = MagicMock()
        mock_pa.return_value = _fake_propagate_return(2, 1)

        resp = client_two_sats.get(
            "/satellites/positions",
            params={
                "ids": "25544,33591",
                "start": _START.isoformat(),
                "stop": _STOP_1H.isoformat(),
                "step": 60,
            },
        )

    assert resp.status_code == 200, resp.text
    model = BulkPositionsResponse.model_validate(resp.json())
    assert len(model.satellites) == 2
    assert model.satellites[0].catalog_no in {25544, 33591}
