"""Tests for S3.1 — CelesTrak GP client (backend/app/services/ingestion.py)."""

import httpx
import pytest
import respx
import tenacity

from app.services.ingestion import fetch_group


@pytest.fixture(autouse=True)
def no_retry_wait():
    """Disable tenacity exponential backoff so retry tests finish instantly."""
    original_wait = fetch_group.retry.wait
    fetch_group.retry.wait = tenacity.wait_none()
    yield
    fetch_group.retry.wait = original_wait


# ---------------------------------------------------------------------------
# FR-1: return value
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_group_returns_body():
    """Outcome 1: mocked 200 response body is returned verbatim."""
    mock_body = "OBJECT_NAME,OBJECT_ID,EPOCH\nISS (ZARYA),1998-067A,2024-01-01"
    with respx.mock:
        respx.get("https://celestrak.org/NORAD/elements/gp.php").mock(
            return_value=httpx.Response(200, text=mock_body)
        )
        result = await fetch_group("active", "csv")
    assert result == mock_body


# ---------------------------------------------------------------------------
# FR-2: URL construction
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_group_url_contains_group_and_format():
    """Outcome 2: outgoing URL carries correct GROUP and FORMAT query params."""
    with respx.mock:
        route = respx.get("https://celestrak.org/NORAD/elements/gp.php").mock(
            return_value=httpx.Response(200, text="data")
        )
        await fetch_group("stations", "json")

        request_url = str(route.calls[0].request.url)
        assert "GROUP=stations" in request_url
        assert "FORMAT=json" in request_url


@pytest.mark.anyio
async def test_fetch_group_default_group_is_active():
    """FR-1 default: omitting group arg results in GROUP=active in the URL."""
    with respx.mock:
        route = respx.get("https://celestrak.org/NORAD/elements/gp.php").mock(
            return_value=httpx.Response(200, text="data")
        )
        await fetch_group(fmt="csv")

        request_url = str(route.calls[0].request.url)
        assert "GROUP=active" in request_url


# ---------------------------------------------------------------------------
# FR-3 / FR-4: httpx + tenacity retries
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_group_retries_on_5xx():
    """Outcome 3: 503 triggers all 3 attempts, then raises HTTPStatusError."""
    with respx.mock:
        route = respx.get("https://celestrak.org/NORAD/elements/gp.php").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_group("active", "csv")

        assert route.call_count == 3


@pytest.mark.anyio
async def test_fetch_group_raises_on_403():
    """Outcome 4: 403 is not silently swallowed — HTTPStatusError raised after retries."""
    with respx.mock:
        respx.get("https://celestrak.org/NORAD/elements/gp.php").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_group("active", "csv")


# ---------------------------------------------------------------------------
# FR-1 edge case: empty group
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_group_empty_group_raises_value_error():
    """Outcome 5: empty group string raises ValueError before any HTTP call."""
    with pytest.raises(ValueError, match="group must not be empty"):
        await fetch_group("")
