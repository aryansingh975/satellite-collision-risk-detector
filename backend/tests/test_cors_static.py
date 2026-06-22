"""Tests for S1.5 — CORS + static serving (backend/app/main.py)."""

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db.database as _db


@pytest.fixture()
def patch_db_engine(monkeypatch):
    """Use in-memory SQLite so the lifespan DB init doesn't create a real file."""
    mem_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    monkeypatch.setattr(_db, "engine", mem_engine)
    yield mem_engine


def _make_settings(**kwargs):
    from app.core.config import Settings

    return Settings(_env_file=None, **kwargs)


def _make_static_app(static_dir: str) -> FastAPI:
    """Minimal app that only mounts StaticFiles — isolates static-serving behaviour."""
    mini = FastAPI()
    mini.mount("/static", StaticFiles(directory=static_dir), name="static")
    return mini


# ---------------------------------------------------------------------------
# FR-1: CORS middleware
# ---------------------------------------------------------------------------


def test_cors_allowed_origin(patch_db_engine):
    """Whitelisted origin receives Access-Control-Allow-Origin header."""
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight(patch_db_engine):
    """OPTIONS pre-flight for a whitelisted origin returns 200 + required CORS headers."""
    from app.main import app

    with TestClient(app) as client:
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
    assert resp.status_code == 200
    assert "access-control-allow-methods" in resp.headers
    assert "access-control-allow-headers" in resp.headers


def test_cors_disallowed_origin(patch_db_engine):
    """Unknown origin does NOT receive Access-Control-Allow-Origin header."""
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in resp.headers


# ---------------------------------------------------------------------------
# FR-2: Static file mount
# ---------------------------------------------------------------------------


def test_static_mount_serves_file(tmp_path):
    """GET /static/index.html returns 200 and the file body."""
    index = tmp_path / "index.html"
    index.write_text("<html>Cesium</html>")
    test_app = _make_static_app(str(tmp_path))
    with TestClient(test_app) as client:
        resp = client.get("/static/index.html")
    assert resp.status_code == 200
    assert "Cesium" in resp.text


def test_static_missing_file(tmp_path):
    """GET /static/nonexistent.txt returns 404 for a file that doesn't exist."""
    test_app = _make_static_app(str(tmp_path))
    with TestClient(test_app) as client:
        resp = client.get("/static/nonexistent.txt")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FR-3: Settings fields
# ---------------------------------------------------------------------------


def test_settings_cors_defaults(monkeypatch):
    """CORS_ORIGINS and STATIC_DIR have the documented defaults."""
    for key in ["CORS_ORIGINS", "STATIC_DIR"]:
        monkeypatch.delenv(key, raising=False)
    s = _make_settings()
    assert s.CORS_ORIGINS == ["http://localhost:5173"]
    assert s.STATIC_DIR == "frontend"


def test_settings_cors_override(monkeypatch):
    """CORS_ORIGINS is overridable from an environment variable."""
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:4000"]')
    s = _make_settings()
    assert s.CORS_ORIGINS == ["http://localhost:4000"]
