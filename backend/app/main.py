"""FastAPI application entry point — S1.4 / S1.5."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

import app.db.database as _db
import app.db.models  # noqa: F401 — registers ORM classes with Base before create_all
from app.api import conjunctions, satellites, stats
from app.core.config import settings
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup: initializing database tables")
    _db.init_db()

    logger.info("startup: starting APScheduler")
    sched = start_scheduler(settings, _db.SessionLocal)
    application.state.scheduler = sched
    logger.info("startup: ready")

    yield

    logger.info("shutdown: stopping scheduler")
    application.state.scheduler.shutdown(wait=False)
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

# API routes first — must be registered before any static mounts
app.include_router(satellites.router, prefix="/satellites", tags=["satellites"])
app.include_router(conjunctions.router, prefix="/conjunctions", tags=["conjunctions"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Static file serving — registered last so API routes always take priority.
# Mount specific subdirectories rather than "/" to avoid intercepting API paths.
_static_dir = Path(settings.STATIC_DIR)
if not _static_dir.is_absolute():
    _static_dir = Path(__file__).parent.parent.parent / settings.STATIC_DIR
if _static_dir.exists():
    for _subdir in ["assets", "cesium", "Workers"]:
        _subpath = _static_dir / _subdir
        if _subpath.exists():
            app.mount(f"/{_subdir}", StaticFiles(directory=str(_subpath)), name=_subdir)

    @app.get("/")
    async def _serve_index() -> FileResponse:
        return FileResponse(str(_static_dir / "index.html"))
