# Checklist — Spec S3.2: TLE Cache (2-Hour Cadence)

## Phase 1: Setup & Dependencies
- [x] Verify S3.1 is `done` (CelesTrak GP client + `fetch_group` implemented and tests passing)
- [x] Locate `backend/app/services/ingestion.py` — `get_cached_group` is added here alongside `fetch_group`
- [x] Confirm `TLE_CACHE_DIR` and `TLE_MAX_AGE_HOURS` exist in `backend/app/core/config.py` (present from S1.3)

## Phase 2: Tests First (TDD)
- [x] Create `backend/tests/services/test_ingestion_cache.py`
- [x] Write `test_cache_hit_returns_cached_content`
- [x] Write `test_cache_miss_stale_triggers_fetch`
- [x] Write `test_cache_miss_no_file_triggers_fetch`
- [x] Write `test_cache_dir_created_if_missing`
- [x] Write `test_403_fallback_with_cache`
- [x] Write `test_403_no_cache_reraises`
- [x] Write `test_cache_path_includes_group_and_fmt`
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Implement FR-1 — `_cache_path(group, fmt)` helper; `mkdir(parents=True, exist_ok=True)`
- [x] Implement FR-2 — freshness check via `time.time()` vs `st_mtime`; zero-byte = stale
- [x] Implement FR-3 — read cache file on hit; fall through to fetch on OSError
- [x] Implement FR-4 — call `fetch_group`, write result to cache file on miss
- [x] Implement FR-5 — catch `HTTPStatusError` with `status_code == 403`; return cache or re-raise
- [x] Implement FR-6 — Loguru INFO on hit/miss, WARNING on 403 fallback
- [x] Run tests — expect pass (Green) — 7/7 passed
- [x] Refactor if needed (no behaviour change)

## Phase 4: Integration
- [x] `get_cached_group` is importable from `app.services.ingestion`
- [x] N/A — no existing callers of `fetch_group` to migrate yet (pipeline not wired until later specs)
- [x] Run lint: ruff check + format — all clean (line length 100)
- [x] Run full test suite: 75 passed, 10 pre-existing failures (missing `apscheduler` in env, unrelated to S3.2)

## Phase 5: Verification
- [x] All 6 tangible outcomes confirmed by 7 passing tests
- [x] No hardcoded paths or secrets — `TLE_CACHE_DIR` always sourced from `settings`
- [x] Loguru INFO on hit (path + age in minutes), INFO on miss (reason), WARNING on 403 fallback
- [x] `get_cached_group` is async; filesystem ops are synchronous (fine for small cache files)
- [x] Update roadmap.md status: `spec-written` → `done`
