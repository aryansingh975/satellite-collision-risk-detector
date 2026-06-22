"""Tests for S1.3 — Settings via pydantic-settings (backend/app/core/config.py)."""

from pathlib import Path

import pytest
from pydantic import ValidationError


def _make_settings(**kwargs):
    """Instantiate Settings with env_file disabled so tests are isolation-safe."""
    from app.core.config import Settings

    return Settings(_env_file=None, **kwargs)


# ---------------------------------------------------------------------------
# FR-1 / FR-2: defaults
# ---------------------------------------------------------------------------


def test_defaults(monkeypatch):
    """All fields have the documented defaults when no env vars are set."""
    # Clear any env vars that might bleed in from the CI environment
    for key in [
        "CELESTRAK_BASE_URL",
        "DEFAULT_GROUP",
        "TLE_CACHE_DIR",
        "TLE_MAX_AGE_HOURS",
        "DATABASE_URL",
        "SCREEN_WINDOW_HOURS",
        "SCREEN_STEP_SECONDS",
        "COARSE_RADIUS_KM",
        "RISK_THRESHOLD_KM",
        "CESIUM_ION_TOKEN",
    ]:
        monkeypatch.delenv(key, raising=False)

    s = _make_settings()

    assert "celestrak.org" in s.CELESTRAK_BASE_URL
    assert s.DEFAULT_GROUP == "active"
    assert isinstance(s.TLE_CACHE_DIR, Path)
    assert s.TLE_MAX_AGE_HOURS == 2
    assert "sqlite" in s.DATABASE_URL
    assert 24 <= s.SCREEN_WINDOW_HOURS <= 72
    assert 30 <= s.SCREEN_STEP_SECONDS <= 60
    assert 10.0 <= s.COARSE_RADIUS_KM <= 20.0
    assert s.RISK_THRESHOLD_KM == 5.0
    assert s.CESIUM_ION_TOKEN is None


# ---------------------------------------------------------------------------
# FR-2: env-var override
# ---------------------------------------------------------------------------


def test_env_override(monkeypatch):
    """An env var overrides the default value."""
    monkeypatch.setenv("RISK_THRESHOLD_KM", "3.0")
    s = _make_settings()
    assert s.RISK_THRESHOLD_KM == pytest.approx(3.0)


def test_env_override_str_field(monkeypatch):
    """String fields are also overridable."""
    monkeypatch.setenv("DEFAULT_GROUP", "stations")
    s = _make_settings()
    assert s.DEFAULT_GROUP == "stations"


# ---------------------------------------------------------------------------
# FR-1: optional token
# ---------------------------------------------------------------------------


def test_optional_token_absent(monkeypatch):
    """CESIUM_ION_TOKEN is None when not set — no error raised."""
    monkeypatch.delenv("CESIUM_ION_TOKEN", raising=False)
    s = _make_settings()
    assert s.CESIUM_ION_TOKEN is None


def test_optional_token_present(monkeypatch):
    """CESIUM_ION_TOKEN is populated when the env var is set."""
    monkeypatch.setenv("CESIUM_ION_TOKEN", "tok123")
    s = _make_settings()
    assert s.CESIUM_ION_TOKEN == "tok123"


# ---------------------------------------------------------------------------
# FR-3: validators — out-of-range values raise ValidationError
# ---------------------------------------------------------------------------


def test_invalid_risk_threshold(monkeypatch):
    """RISK_THRESHOLD_KM ≤ 0 raises ValidationError."""
    monkeypatch.setenv("RISK_THRESHOLD_KM", "-1")
    with pytest.raises(ValidationError):
        _make_settings()


def test_invalid_tle_max_age(monkeypatch):
    """TLE_MAX_AGE_HOURS < 1 raises ValidationError."""
    monkeypatch.setenv("TLE_MAX_AGE_HOURS", "0")
    with pytest.raises(ValidationError):
        _make_settings()


def test_invalid_screen_window_too_large(monkeypatch):
    """SCREEN_WINDOW_HOURS > 336 raises ValidationError."""
    monkeypatch.setenv("SCREEN_WINDOW_HOURS", "337")
    with pytest.raises(ValidationError):
        _make_settings()


def test_invalid_coarse_radius(monkeypatch):
    """COARSE_RADIUS_KM ≤ 0 raises ValidationError."""
    monkeypatch.setenv("COARSE_RADIUS_KM", "0")
    with pytest.raises(ValidationError):
        _make_settings()


# ---------------------------------------------------------------------------
# FR-1 / FR-2: correct Python types (not raw strings)
# ---------------------------------------------------------------------------


def test_types(monkeypatch):
    """Numeric fields are the correct Python types after parsing."""
    for key in ["TLE_MAX_AGE_HOURS", "COARSE_RADIUS_KM", "RISK_THRESHOLD_KM"]:
        monkeypatch.delenv(key, raising=False)

    s = _make_settings()
    assert isinstance(s.TLE_MAX_AGE_HOURS, int)
    assert isinstance(s.COARSE_RADIUS_KM, float)
    assert isinstance(s.RISK_THRESHOLD_KM, float)
    assert isinstance(s.SCREEN_WINDOW_HOURS, int)
    assert isinstance(s.SCREEN_STEP_SECONDS, int)


# ---------------------------------------------------------------------------
# FR-4: module-level singleton
# ---------------------------------------------------------------------------


def test_singleton():
    """The module-level `settings` object is the same instance on every import."""
    from app.core.config import settings as s1
    from app.core.config import settings as s2

    assert s1 is s2
