"""Tests for S3.2 — TLE cache layer (backend/app/services/ingestion.py)."""

import os
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.ingestion import _cache_path, get_cached_group


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    """Redirect TLE_CACHE_DIR to an isolated temp directory."""
    from app.core import config

    d = tmp_path / "tle_cache"
    d.mkdir()
    monkeypatch.setattr(config.settings, "TLE_CACHE_DIR", d)
    return d


def _make_403_error() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://celestrak.org/GPS/gp.php")
    response = httpx.Response(403, request=request)
    return httpx.HTTPStatusError("403 Forbidden", request=request, response=response)


# ---------------------------------------------------------------------------
# FR-1: Cache path derivation
# ---------------------------------------------------------------------------


def test_cache_path_includes_group_and_fmt(cache_dir):
    """FR-1: derived cache path contains both the group name and format string."""
    path = _cache_path("stations", "json")
    assert "stations" in str(path)
    assert "json" in str(path)


# ---------------------------------------------------------------------------
# FR-2 / FR-3: Cache hit (fresh file)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cache_hit_returns_cached_content(cache_dir):
    """Outcome 1: fresh cache → no HTTP call, cached content returned verbatim."""
    (cache_dir / "active_csv.cache").write_text("cached payload")

    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        result = await get_cached_group("active", "csv")

    mock_fetch.assert_not_called()
    assert result == "cached payload"


# ---------------------------------------------------------------------------
# FR-4: Cache miss — stale file
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cache_miss_stale_triggers_fetch(cache_dir):
    """Outcome 2: stale cache (>2 h) → fetch called once, file overwritten with new data."""
    cache_file = cache_dir / "active_csv.cache"
    cache_file.write_text("old data")
    stale_ts = time.time() - 3 * 3600
    os.utime(cache_file, (stale_ts, stale_ts))

    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "new data"
        result = await get_cached_group("active", "csv")

    mock_fetch.assert_called_once_with("active", "csv")
    assert result == "new data"
    assert cache_file.read_text() == "new data"


# ---------------------------------------------------------------------------
# FR-4: Cache miss — no file at all
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cache_miss_no_file_triggers_fetch(cache_dir):
    """Outcome 3: absent cache → fetch called, new file written to disk."""
    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "fresh data"
        result = await get_cached_group("active", "csv")

    mock_fetch.assert_called_once_with("active", "csv")
    assert result == "fresh data"
    assert (cache_dir / "active_csv.cache").read_text() == "fresh data"


# ---------------------------------------------------------------------------
# FR-1 edge case: TLE_CACHE_DIR auto-creation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cache_dir_created_if_missing(tmp_path, monkeypatch):
    """Outcome 6: TLE_CACHE_DIR is created automatically when it does not exist."""
    from app.core import config

    missing_dir = tmp_path / "does_not_exist" / "tle_cache"
    monkeypatch.setattr(config.settings, "TLE_CACHE_DIR", missing_dir)

    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "data"
        await get_cached_group("active", "csv")

    assert missing_dir.exists()


# ---------------------------------------------------------------------------
# FR-5: HTTP 403 fallback — cache exists
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_403_fallback_with_cache(cache_dir):
    """Outcome 4: 403 + stale-but-existing cache → return cached content, no exception."""
    cache_file = cache_dir / "active_csv.cache"
    cache_file.write_text("stale but usable data")
    stale_ts = time.time() - 3 * 3600
    os.utime(cache_file, (stale_ts, stale_ts))

    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = _make_403_error()
        result = await get_cached_group("active", "csv")

    assert result == "stale but usable data"


# ---------------------------------------------------------------------------
# FR-5: HTTP 403 fallback — no cache
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_403_no_cache_reraises(cache_dir):
    """Outcome 5: 403 + no cache → HTTPStatusError propagates to caller."""
    with patch("app.services.ingestion.fetch_group", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = _make_403_error()
        with pytest.raises(httpx.HTTPStatusError):
            await get_cached_group("active", "csv")
