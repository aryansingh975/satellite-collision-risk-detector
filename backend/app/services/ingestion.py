"""CelesTrak GP API client and TLE ingestion pipeline."""

import time
from datetime import datetime
from pathlib import Path

import httpx
import tenacity
from loguru import logger
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Satellite


@tenacity.retry(
    wait=tenacity.wait_exponential(min=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    retry=tenacity.retry_if_exception_type(httpx.HTTPError),
    reraise=True,
    before_sleep=lambda rs: logger.debug("CelesTrak fetch retry {}/{}", rs.attempt_number, 3),
)
async def fetch_group(group: str = settings.DEFAULT_GROUP, fmt: str = "csv") -> str:
    """Fetch raw GP data for a satellite group from the CelesTrak GP API.

    Returns the raw response body as a string (CSV, JSON, or TLE text).
    Raises ValueError for an empty group; raises httpx.HTTPStatusError on
    non-2xx responses after 3 retry attempts.
    """
    if not group:
        raise ValueError("group must not be empty")

    url = f"{settings.CELESTRAK_BASE_URL.rstrip('/')}?GROUP={group}&FORMAT={fmt}"
    logger.debug("CelesTrak request: {}", url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    logger.info(
        "CelesTrak response: status={} bytes={}", response.status_code, len(response.content)
    )
    return response.text


# ---------------------------------------------------------------------------
# S3.2 — TLE cache (2-hour cadence)
# ---------------------------------------------------------------------------


def _cache_path(group: str, fmt: str) -> Path:
    """Return the deterministic cache file path for a (group, fmt) pair."""
    return settings.TLE_CACHE_DIR / f"{group}_{fmt}.cache"


def _is_fresh(path: Path) -> bool:
    """Return True if path exists, is non-empty, and is younger than TLE_MAX_AGE_HOURS."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    return (time.time() - path.stat().st_mtime) < settings.TLE_MAX_AGE_HOURS * 3600


async def get_cached_group(group: str = settings.DEFAULT_GROUP, fmt: str = "csv") -> str:
    """Return GP data for a group, fetching from CelesTrak only if the cache is ≥2 h old.

    On HTTP 403 falls back to the cached copy; re-raises only when no cache exists.
    """
    cache_file = _cache_path(group, fmt)

    if _is_fresh(cache_file):
        age_min = (time.time() - cache_file.stat().st_mtime) / 60
        logger.info("TLE cache hit: {} (age {:.1f} min)", cache_file, age_min)
        try:
            return cache_file.read_text()
        except OSError as exc:
            logger.warning("TLE cache read error ({}), falling through to live fetch", exc)
    else:
        if not cache_file.exists():
            reason = "missing"
        elif cache_file.stat().st_size == 0:
            reason = "empty"
        else:
            reason = "stale"
        logger.info(
            "TLE cache {} for group={} fmt={} — fetching from CelesTrak", reason, group, fmt
        )

    try:
        data = await fetch_group(group, fmt)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            if cache_file.exists() and cache_file.stat().st_size > 0:
                logger.warning("CelesTrak HTTP 403 — serving stale cache: {}", cache_file)
                return cache_file.read_text()
            logger.error("CelesTrak HTTP 403 and no usable cache for group={} fmt={}", group, fmt)
            raise
        raise

    settings.TLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(data)
    logger.info("TLE cache updated: {}", cache_file)
    return data


# ---------------------------------------------------------------------------
# S3.5 — Persist satellites
# ---------------------------------------------------------------------------


def persist_satellites(db: Session, records: list[dict]) -> tuple[int, int]:
    """Upsert parsed satellite records into the Satellite table.

    De-duplicates within the batch (last record for a given catalog_no wins),
    then issues a single bulk INSERT … ON CONFLICT DO UPDATE. Returns
    (inserted, updated) counts derived from a pre-upsert existence check.
    DB write failures propagate to the caller; the caller is responsible for
    rollback.
    """
    if not records:
        return (0, 0)

    # De-dupe within batch — last record with a given catalog_no wins
    seen: dict[int, dict] = {}
    for r in records:
        seen[r["catalog_no"]] = r
    deduped = list(seen.values())

    catalog_nos = [r["catalog_no"] for r in deduped]

    # Count pre-existing rows to compute insert vs update split without
    # loading full ORM objects into Python memory
    existing_count: int = (
        db.query(func.count(Satellite.catalog_no))
        .filter(Satellite.catalog_no.in_(catalog_nos))
        .scalar()
    )

    now = datetime.utcnow()
    rows = [
        {
            "catalog_no": r["catalog_no"],
            "name": r.get("name", ""),
            "intl_designator": r.get("intl_designator"),
            "line1": r["line1"],
            "line2": r["line2"],
            "epoch": r["epoch"],
            "a_km": r.get("a_km"),
            "ecc": r.get("ecc"),
            "inc_deg": r.get("inc_deg"),
            "mean_motion": r.get("mean_motion"),
            "regime": r.get("regime"),
            "group_name": r.get("group_name"),
            "updated_at": now,
        }
        for r in deduped
    ]

    stmt = sqlite_insert(Satellite).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["catalog_no"],
        set_={
            "name": stmt.excluded.name,
            "intl_designator": stmt.excluded.intl_designator,
            "line1": stmt.excluded.line1,
            "line2": stmt.excluded.line2,
            "epoch": stmt.excluded.epoch,
            "a_km": stmt.excluded.a_km,
            "ecc": stmt.excluded.ecc,
            "inc_deg": stmt.excluded.inc_deg,
            "mean_motion": stmt.excluded.mean_motion,
            "regime": stmt.excluded.regime,
            "group_name": stmt.excluded.group_name,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    db.execute(stmt)
    db.commit()

    total = len(deduped)
    updated = existing_count
    inserted = total - updated

    logger.info("persist_satellites: inserted={} updated={}", inserted, updated)
    return (inserted, updated)
