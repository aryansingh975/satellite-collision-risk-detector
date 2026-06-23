"""Periodic TLE refresh + conjunction screen job (S6.6)."""

import asyncio
import uuid
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.services.conjunctions import run_conjunction_screen
from app.services.ingestion import ingest_tle_group


def _refresh_job(settings, session_factory: Callable) -> None:
    """Periodic job body: re-ingest TLEs then re-run conjunction screen.

    All exceptions are caught, logged at ERROR, and swallowed so the scheduler
    continues firing on schedule regardless of transient network or DB failures.
    """
    job_id = uuid.uuid4().hex[:8]
    logger.info("scheduler: job start job_id={}", job_id)
    db = session_factory()
    try:
        sat_count = asyncio.run(ingest_tle_group(db, settings))
        conj_count = run_conjunction_screen(db, settings)
        logger.info(
            "scheduler: job complete job_id={} satellites={} conjunctions={}",
            job_id,
            sat_count,
            conj_count,
        )
    except Exception:
        logger.exception("scheduler: job failed job_id={}", job_id)
    finally:
        db.close()


def start_scheduler(settings, session_factory: Callable) -> BackgroundScheduler:
    """Create, configure, and start a BackgroundScheduler with the 2-hour refresh job.

    Returns the running scheduler instance. The caller stores it on app.state and
    calls scheduler.shutdown(wait=False) during lifespan teardown.
    """
    sched = BackgroundScheduler()
    sched.add_job(
        _refresh_job,
        trigger=IntervalTrigger(hours=2),
        args=[settings, session_factory],
        id="tle_refresh",
        replace_existing=True,
    )
    sched.start()
    return sched
