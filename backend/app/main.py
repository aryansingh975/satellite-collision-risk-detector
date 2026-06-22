"""FastAPI application entry point — S1.4 / S1.5."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

import app.db.database as _db
import app.db.models  # noqa: F401 — registers ORM classes with Base before create_all
from app.api import conjunctions, satellites, stats
from app.core.config import settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup: initializing database tables")
    _db.init_db()

    logger.info("startup: starting APScheduler")
    scheduler = BackgroundScheduler()
    scheduler.start()
    application.state.scheduler = scheduler
    logger.info("startup: ready")

    yield

    logger.info("shutdown: stopping scheduler")
    scheduler.shutdown(wait=False)
    logger.info("shutdown: complete")


app = FastAPI(
    title="Satellite Collision Risk Detector",
    version="0.1.0",
    description="Tracks satellites and predicts close approaches.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

_static_dir = Path(settings.STATIC_DIR)
if not _static_dir.is_absolute():
    _static_dir = Path(__file__).parent.parent.parent / settings.STATIC_DIR
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(satellites.router, prefix="/satellites", tags=["satellites"])
app.include_router(conjunctions.router, prefix="/conjunctions", tags=["conjunctions"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
