"""Tests for S6.6 — Scheduled Refresh (backend/app/services/scheduler.py)."""

import io
from unittest.mock import patch

import httpx
import pytest
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa — registers ORM classes with Base
from app.db.database import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_session_factory():
    """Isolated in-memory SQLite session factory for job-unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def mock_settings():
    from app.core.config import settings

    return settings


@pytest.fixture()
def loguru_sink():
    """Capture Loguru output for this test only."""
    buf = io.StringIO()
    handler_id = logger.add(buf, format="{level} {message}", level="DEBUG")
    yield buf
    logger.remove(handler_id)


@pytest.fixture()
def patch_db_engine(monkeypatch):
    """Replace the real SQLite engine with in-memory for lifespan integration tests."""
    import app.db.database as _db

    mem_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    mem_session = sessionmaker(bind=mem_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(_db, "engine", mem_engine)
    monkeypatch.setattr(_db, "SessionLocal", mem_session)
    yield mem_session


# ---------------------------------------------------------------------------
# FR-2: job body calls ingest then screen in order
# ---------------------------------------------------------------------------


def test_scheduler_job_calls_ingest_then_screen(mock_settings, in_memory_session_factory):
    from app.services.scheduler import _refresh_job

    call_order = []

    async def fake_ingest(db, cfg):
        call_order.append("ingest")
        return 10

    def fake_screen(db, cfg):
        call_order.append("screen")
        return 3

    with patch("app.services.scheduler.ingest_tle_group", fake_ingest), patch(
        "app.services.scheduler.run_conjunction_screen", fake_screen
    ):
        _refresh_job(mock_settings, in_memory_session_factory)

    assert call_order == ["ingest", "screen"]


# ---------------------------------------------------------------------------
# FR-2: job body logs satellite + conjunction counts at INFO
# ---------------------------------------------------------------------------


def test_scheduler_job_logs_counts(loguru_sink, mock_settings, in_memory_session_factory):
    from app.services.scheduler import _refresh_job

    async def fake_ingest(db, cfg):
        return 42

    def fake_screen(db, cfg):
        return 7

    with patch("app.services.scheduler.ingest_tle_group", fake_ingest), patch(
        "app.services.scheduler.run_conjunction_screen", fake_screen
    ):
        _refresh_job(mock_settings, in_memory_session_factory)

    log = loguru_sink.getvalue()
    assert "satellites=42" in log
    assert "conjunctions=7" in log


# ---------------------------------------------------------------------------
# FR-3: ingest failure is isolated — no exception escapes, ERROR logged
# ---------------------------------------------------------------------------


def test_scheduler_job_ingest_failure_isolated(
    loguru_sink, mock_settings, in_memory_session_factory
):
    from app.services.scheduler import _refresh_job

    async def failing_ingest(db, cfg):
        raise httpx.TimeoutException("network timeout")

    with patch("app.services.scheduler.ingest_tle_group", failing_ingest):
        _refresh_job(mock_settings, in_memory_session_factory)  # must not raise

    assert "ERROR" in loguru_sink.getvalue()


# ---------------------------------------------------------------------------
# FR-3: screen failure is isolated — no exception escapes, ERROR logged
# ---------------------------------------------------------------------------


def test_scheduler_job_screen_failure_isolated(
    loguru_sink, mock_settings, in_memory_session_factory
):
    from app.services.scheduler import _refresh_job

    async def fake_ingest(db, cfg):
        return 5

    def failing_screen(db, cfg):
        raise RuntimeError("screening failed")

    with patch("app.services.scheduler.ingest_tle_group", fake_ingest), patch(
        "app.services.scheduler.run_conjunction_screen", failing_screen
    ):
        _refresh_job(mock_settings, in_memory_session_factory)  # must not raise

    assert "ERROR" in loguru_sink.getvalue()


# ---------------------------------------------------------------------------
# FR-1: start_scheduler registers exactly one job with a 2-hour interval
# ---------------------------------------------------------------------------


def test_start_scheduler_registers_job(mock_settings, in_memory_session_factory):
    from app.services.scheduler import start_scheduler

    sched = start_scheduler(mock_settings, in_memory_session_factory)
    try:
        jobs = sched.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "tle_refresh"
        assert jobs[0].trigger.interval.total_seconds() == 2 * 3600
    finally:
        sched.shutdown(wait=False)


# ---------------------------------------------------------------------------
# FR-4: lifespan wires start_scheduler on startup + shutdown on teardown
# ---------------------------------------------------------------------------


def test_lifespan_starts_and_stops_scheduler(patch_db_engine):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        sched = client.app.state.scheduler
        assert sched.running is True
    assert sched.running is False
