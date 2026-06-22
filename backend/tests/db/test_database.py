"""Tests for S2.1 — SQLAlchemy engine + session (backend/app/db/database.py)."""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

import app.db.database as _db
from app.core.config import settings


# ---------------------------------------------------------------------------
# FR-1: engine URL matches settings
# ---------------------------------------------------------------------------


def test_engine_url_matches_settings():
    assert str(_db.engine.url) == settings.DATABASE_URL


# ---------------------------------------------------------------------------
# FR-3: SessionLocal is configured correctly
# ---------------------------------------------------------------------------


def test_session_local_is_configured():
    assert _db.SessionLocal.kw["autocommit"] is False
    assert _db.SessionLocal.kw["autoflush"] is False


# ---------------------------------------------------------------------------
# FR-5: init_db() creates tables in an in-memory database
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(monkeypatch):
    mem_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    monkeypatch.setattr(_db, "engine", mem_engine)

    # Import models so Base.metadata is populated
    import app.db.models  # noqa: F401

    _db.init_db()

    inspector = inspect(mem_engine)
    table_names = inspector.get_table_names()
    assert "satellites" in table_names
    assert "conjunctions" in table_names


def test_init_db_is_idempotent(monkeypatch):
    mem_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    monkeypatch.setattr(_db, "engine", mem_engine)

    import app.db.models  # noqa: F401

    _db.init_db()
    _db.init_db()  # second call must not raise

    inspector = inspect(mem_engine)
    assert "satellites" in inspector.get_table_names()


# ---------------------------------------------------------------------------
# FR-4: get_db() yields a Session and closes it
# ---------------------------------------------------------------------------


def test_get_db_yields_session():
    from unittest.mock import patch

    gen = _db.get_db()
    db = next(gen)
    assert isinstance(db, Session)
    with patch.object(db, "close") as mock_close:
        try:
            next(gen)
        except StopIteration:
            pass
        mock_close.assert_called_once()


def test_get_db_closes_on_exception():
    """Session must close even when the consumer raises mid-request."""
    from unittest.mock import patch

    gen = _db.get_db()
    db = next(gen)
    assert isinstance(db, Session)
    with patch.object(db, "close") as mock_close:
        try:
            gen.throw(RuntimeError("simulated endpoint error"))
        except RuntimeError:
            pass
        mock_close.assert_called_once()
