"""One-shot DB seed script: fetch TLEs → parse → persist → screen conjunctions.

Run via:  make seed   (or .venv/Scripts/python backend/scripts/seed.py)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# When invoked as a script (make seed), only backend/scripts/ is on sys.path.
# Insert backend/ so that app.* imports resolve.
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from loguru import logger  # noqa: E402

import app.db.models  # noqa: E402, F401 — registers ORM models on Base.metadata

from app.core.config import settings  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.services.conjunctions import run_conjunction_screen  # noqa: E402
from app.services.ingestion import ingest_tle_group  # noqa: E402


def _run_seed(db) -> tuple[int, int]:
    """Ingest TLEs then run conjunction screen. Returns (sat_count, conj_count)."""
    sat_count: int = asyncio.run(ingest_tle_group(db, settings))
    logger.info("seed: ingested satellites={}", sat_count)

    conj_count: int = run_conjunction_screen(db, settings)
    logger.info("seed: persisted conjunctions={}", conj_count)

    return sat_count, conj_count


def main() -> None:
    with logger.contextualize(request_id="seed"):
        logger.info("seed: initialising database")
        try:
            init_db()
        except Exception:
            logger.exception("seed: database initialisation failed")
            sys.exit(1)

        db = SessionLocal()
        try:
            sat_count, conj_count = _run_seed(db)
            logger.info(
                "seed: complete satellites={} conjunctions={}", sat_count, conj_count
            )
        except Exception:
            logger.exception("seed: pipeline failed")
            sys.exit(1)
        finally:
            db.close()


if __name__ == "__main__":
    main()
