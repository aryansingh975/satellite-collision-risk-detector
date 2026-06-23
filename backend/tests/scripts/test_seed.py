"""Tests for S10.1 — Seed Script (backend/scripts/seed.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 — registers ORM models on Base.metadata
from app.db.database import Base
from scripts.seed import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_engine():
    """In-memory SQLite with a single shared connection (StaticPool)."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seed_creates_tables():
    """main() creates satellites and conjunctions tables via init_db()."""
    eng = _make_test_engine()
    Session = sessionmaker(bind=eng)
    db_instance = Session()

    def _fake_init_db():
        Base.metadata.create_all(bind=eng)

    with (
        patch("scripts.seed.init_db", side_effect=_fake_init_db),
        patch("scripts.seed.SessionLocal", return_value=db_instance),
        patch("scripts.seed.ingest_tle_group", new_callable=AsyncMock, return_value=0),
        patch("scripts.seed.run_conjunction_screen", return_value=0),
    ):
        main()

    table_names = inspect(eng).get_table_names()
    assert "satellites" in table_names
    assert "conjunctions" in table_names


def test_seed_calls_ingest_and_screen():
    """main() calls ingest_tle_group and run_conjunction_screen exactly once each."""
    mock_ingest = AsyncMock(return_value=5)
    mock_screen = MagicMock(return_value=1)

    with (
        patch("scripts.seed.init_db"),
        patch("scripts.seed.SessionLocal", return_value=MagicMock()),
        patch("scripts.seed.ingest_tle_group", mock_ingest),
        patch("scripts.seed.run_conjunction_screen", mock_screen),
    ):
        main()

    assert mock_ingest.call_count == 1
    assert mock_screen.call_count == 1


def test_seed_idempotent():
    """Running main() twice must not raise and pipeline functions are called each time."""
    mock_ingest = AsyncMock(return_value=10)
    mock_screen = MagicMock(return_value=2)
    eng = _make_test_engine()
    Session = sessionmaker(bind=eng)

    def _fake_init_db():
        Base.metadata.create_all(bind=eng)

    with (
        patch("scripts.seed.init_db", side_effect=_fake_init_db),
        patch("scripts.seed.SessionLocal", side_effect=lambda: Session()),
        patch("scripts.seed.ingest_tle_group", mock_ingest),
        patch("scripts.seed.run_conjunction_screen", mock_screen),
    ):
        main()
        main()

    assert mock_ingest.call_count == 2
    assert mock_screen.call_count == 2


def test_seed_exits_nonzero_on_ingest_failure():
    """main() exits with code 1 when ingest_tle_group raises."""

    async def _failing_ingest(db, cfg):
        raise RuntimeError("simulated ingest failure")

    with (
        patch("scripts.seed.init_db"),
        patch("scripts.seed.SessionLocal", return_value=MagicMock()),
        patch("scripts.seed.ingest_tle_group", _failing_ingest),
        patch("scripts.seed.run_conjunction_screen"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_seed_exits_nonzero_on_screen_failure():
    """main() exits with code 1 when run_conjunction_screen raises."""
    with (
        patch("scripts.seed.init_db"),
        patch("scripts.seed.SessionLocal", return_value=MagicMock()),
        patch("scripts.seed.ingest_tle_group", new_callable=AsyncMock, return_value=10),
        patch(
            "scripts.seed.run_conjunction_screen",
            side_effect=RuntimeError("screen fail"),
        ),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_seed_logs_counts():
    """main() logs satellite and conjunction counts at INFO level."""
    captured: list[str] = []
    sink_id = logger.add(captured.append, format="{message}", colorize=False)

    try:
        with (
            patch("scripts.seed.init_db"),
            patch("scripts.seed.SessionLocal", return_value=MagicMock()),
            patch("scripts.seed.ingest_tle_group", new_callable=AsyncMock, return_value=42),
            patch("scripts.seed.run_conjunction_screen", return_value=7),
        ):
            main()
    finally:
        logger.remove(sink_id)

    all_logs = "\n".join(captured)
    assert "42" in all_logs
    assert "7" in all_logs
