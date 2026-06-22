"""Application settings loaded from environment variables / .env file."""

from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CelesTrak
    CELESTRAK_BASE_URL: str = "https://celestrak.org/GPS/gp.php"
    DEFAULT_GROUP: str = "active"

    # Cache
    TLE_CACHE_DIR: Path = Path("data/tle_cache")
    TLE_MAX_AGE_HOURS: int = 2

    # Database
    DATABASE_URL: str = "sqlite:///./satellite_tracking.db"

    # Conjunction screening
    SCREEN_WINDOW_HOURS: int = 72
    SCREEN_STEP_SECONDS: int = 60
    COARSE_RADIUS_KM: float = 15.0
    RISK_THRESHOLD_KM: float = 5.0

    # Optional frontend token — never commit a real value
    CESIUM_ION_TOKEN: Optional[str] = None

    # CORS + static serving
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    STATIC_DIR: str = "frontend"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("TLE_MAX_AGE_HOURS")
    @classmethod
    def _tle_max_age_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("TLE_MAX_AGE_HOURS must be ≥ 1")
        return v

    @field_validator("SCREEN_WINDOW_HOURS")
    @classmethod
    def _screen_window_range(cls, v: int) -> int:
        if not (1 <= v <= 336):
            raise ValueError("SCREEN_WINDOW_HOURS must be in [1, 336]")
        return v

    @field_validator("SCREEN_STEP_SECONDS")
    @classmethod
    def _screen_step_range(cls, v: int) -> int:
        if not (10 <= v <= 3600):
            raise ValueError("SCREEN_STEP_SECONDS must be in [10, 3600]")
        return v

    @field_validator("COARSE_RADIUS_KM")
    @classmethod
    def _coarse_radius_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("COARSE_RADIUS_KM must be > 0")
        return v

    @field_validator("RISK_THRESHOLD_KM")
    @classmethod
    def _risk_threshold_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("RISK_THRESHOLD_KM must be > 0")
        return v


settings = Settings()
