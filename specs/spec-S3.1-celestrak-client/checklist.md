# Checklist — Spec S3.1: CelesTrak GP Client

## Phase 1: Setup & Dependencies
- [x] Verify S1.3 (pydantic-settings) is `done` in roadmap.md
- [x] Locate / create `backend/app/services/ingestion.py`
- [x] Confirm `httpx`, `tenacity`, `loguru` are listed in `pyproject.toml` (they should be from S1.1)
- [x] Confirm `respx` and `pytest-asyncio` (or `anyio`) are in dev extras in `pyproject.toml` — anyio 4.14.0 available via anyio pytest plugin; respx>=0.21 in dev extras

## Phase 2: Tests First (TDD)
- [x] Create test file: `backend/tests/services/test_ingestion.py`
- [x] Write `test_fetch_group_returns_body` — mock 200, assert return value
- [x] Write `test_fetch_group_url_contains_group_and_format` — inspect captured URL params
- [x] Write `test_fetch_group_default_group_is_active` — no group arg, assert URL uses `active`
- [x] Write `test_fetch_group_retries_on_5xx` — mock 503 ×3, assert `HTTPStatusError` + call count
- [x] Write `test_fetch_group_raises_on_403` — mock 403, assert `HTTPStatusError`
- [x] Write `test_fetch_group_empty_group_raises_value_error` — assert `ValueError`
- [x] Run tests — expect failures (Red): confirmed 6 ImportErrors before implementation

## Phase 3: Implementation
- [x] Implement FR-1 — `fetch_group(group, fmt)` async function skeleton with default args
- [x] Implement FR-2 — URL construction from `settings.CELESTRAK_BASE_URL` (strips trailing slash; base URL already contains `/GPS/gp.php` so query params appended directly)
- [x] Implement FR-3 — `httpx.AsyncClient` GET + `response.raise_for_status()`
- [x] Implement FR-4 — `@tenacity.retry` decorator (3 attempts, exponential backoff, `HTTPError`); `fetch_group.retry` is `AsyncRetrying` — patched via `fetch_group.retry.wait` in tests
- [x] Implement FR-5 — Loguru DEBUG log on request, INFO log on response, DEBUG on each retry via `before_sleep`
- [x] Run tests — expect pass (Green): 6/6 passed
- [x] Refactor if needed — N/A; implementation is clean

## Phase 4: Integration
- [x] Import `fetch_group` in `ingestion.py` public surface (will be called by S3.2 cache wrapper)
- [x] Run lint: `ruff check` — all checks passed
- [x] Run full backend test suite: 78/78 passed

## Phase 5: Verification
- [x] All 5 tangible outcomes in spec.md are confirmed
- [x] No hardcoded CelesTrak URLs (use `settings.CELESTRAK_BASE_URL`)
- [x] No live HTTP calls in any test (all mocked via respx 0.23.1)
- [x] Loguru logger used (not `print` or stdlib `logging`)
- [x] Update roadmap.md status: `spec-written` → `done` for S3.1 in both tables
