# Spec S3.2 — TLE Cache (2-Hour Cadence)

## Overview
Implements the mandatory local cache layer around `fetch_group()` that enforces CelesTrak's
one-download-per-update policy. The public entry point `get_cached_group(group, fmt)` checks
whether a cache file for the requested group+format exists and is younger than `TLE_MAX_AGE_HOURS`
(2 h). If fresh, it returns the cached text immediately. If stale or absent, it calls
`fetch_group()`, writes the new content to disk, and returns it. If the live fetch raises
`httpx.HTTPStatusError` with status 403 (CelesTrak's firewall response for abusive IPs), it logs a
warning and falls back to whatever cached copy exists — only re-raising if no cache is available.
This ensures the app never hammers CelesTrak and survives transient 403s gracefully.

## Dependencies
- S3.1 — CelesTrak GP client (`fetch_group` function)
- S1.3 — pydantic-settings config (`TLE_CACHE_DIR`, `TLE_MAX_AGE_HOURS`)

## Target Location
`backend/app/services/ingestion.py`

---

## Functional Requirements

### FR-1: Cache file path derivation
- **What**: Derive a deterministic file path for each `(group, fmt)` pair inside `TLE_CACHE_DIR`.
- **Inputs**: `group: str`, `fmt: str`, `settings.TLE_CACHE_DIR: Path`.
- **Outputs**: `Path` object, e.g. `TLE_CACHE_DIR / f"{group}_{fmt}.cache"`.
- **Edge cases**: `TLE_CACHE_DIR` must be created if it does not exist (`mkdir(parents=True, exist_ok=True)`).

### FR-2: Cache freshness check
- **What**: A cache hit occurs when the file exists **and** its modification time is less than
  `TLE_MAX_AGE_HOURS` hours ago relative to `datetime.utcnow()`.
- **Inputs**: Cache file path, `settings.TLE_MAX_AGE_HOURS`.
- **Outputs**: `True` (fresh) / `False` (stale or missing).
- **Edge cases**: Non-existent file → not fresh; zero-byte file → treat as stale.

### FR-3: Cache read on hit
- **What**: Return the cache file contents as a string when the cache is fresh.
- **Inputs**: Cache file path.
- **Outputs**: Raw text string (same type as `fetch_group` returns).
- **Edge cases**: Read error (e.g. permission denied) → treat as a cache miss and attempt live fetch.

### FR-4: Fetch, write, and return on miss
- **What**: When the cache is stale or absent, call `await fetch_group(group, fmt)`, write the
  returned text to the cache file (overwrite), and return the text.
- **Inputs**: `group`, `fmt`.
- **Outputs**: Raw text string.
- **Edge cases**: Non-403 fetch failures propagate to the caller unchanged.

### FR-5: HTTP 403 fallback
- **What**: If `fetch_group` raises `httpx.HTTPStatusError` with `response.status_code == 403`,
  log a warning and return the existing cache file contents instead of re-raising.
- **Inputs**: `httpx.HTTPStatusError` from `fetch_group`.
- **Outputs**: Cached text string when cache exists.
- **Edge cases**: If 403 is raised **and** no cache file exists (or it is empty), re-raise the
  original `HTTPStatusError` so the caller knows there is no data at all.

### FR-6: Logging
- **What**: Log at INFO level for cache hits (path + age in minutes) and cache misses (reason).
  Log at WARNING level for 403 fallback events. Use Loguru (`from loguru import logger`).
- **Inputs**: Cache state, error details.
- **Outputs**: Log records only; no change to return value.
- **Edge cases**: Log cache age in minutes for human readability.

---

## Tangible Outcomes

- [ ] **Outcome 1**: With a fresh cache file (<2 h old), `get_cached_group()` returns the cached
  content without making any HTTP call — verified by asserting `fetch_group` was never called.
- [ ] **Outcome 2**: With a stale cache (mtime >2 h ago), `get_cached_group()` calls `fetch_group`
  once, overwrites the cache file, and returns the new content.
- [ ] **Outcome 3**: With no cache file present, `get_cached_group()` calls `fetch_group`, writes
  the file to disk, and returns the fetched content.
- [ ] **Outcome 4**: When `fetch_group` raises HTTP 403 and a non-empty cached file exists,
  `get_cached_group` returns the cached content without re-raising.
- [ ] **Outcome 5**: When `fetch_group` raises HTTP 403 and **no** cached file exists,
  `get_cached_group` re-raises the `HTTPStatusError`.
- [ ] **Outcome 6**: `TLE_CACHE_DIR` is created automatically if it does not exist before the
  first write.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_cache_hit_returns_cached_content**: Write a fresh cache file; call `get_cached_group`;
   assert `fetch_group` not called and result matches file content.
2. **test_cache_miss_stale_triggers_fetch**: Write a cache file with mtime set >2 h ago via
   `os.utime`; assert `fetch_group` called once and cache file content updated.
3. **test_cache_miss_no_file_triggers_fetch**: Start with no cache file; assert `fetch_group`
   called and a new file is written.
4. **test_cache_dir_created_if_missing**: Point `TLE_CACHE_DIR` at a non-existent path; call
   `get_cached_group`; assert the directory exists afterwards.
5. **test_403_fallback_with_cache**: Cache file exists; mock `fetch_group` to raise HTTP 403;
   assert cached content returned and no exception raised.
6. **test_403_no_cache_reraises**: No cache file; mock `fetch_group` to raise HTTP 403; assert
   `httpx.HTTPStatusError` propagates.
7. **test_cache_path_includes_group_and_fmt**: Verify the derived cache path string contains both
   the group name and the format string.

### Mocking Strategy
- Patch `app.services.ingestion.fetch_group` with an `AsyncMock` — never invoke the real coroutine.
- Use `tmp_path` pytest fixture for `TLE_CACHE_DIR` (set via `monkeypatch.setattr(settings, ...)`).
- Manipulate file mtime with `os.utime(path, (ts, ts))` to simulate a stale cache.
- Use `pytest-asyncio` for async test functions.

### Coverage Expectation
- All 6 FRs covered; both 403 branches (cache present / absent) tested; directory-creation tested.

---

## References
- roadmap.md S3.2 row (Phase 3 table + Master Spec Index)
- CLAUDE.md: "RESPECT CelesTrak limits: data updates every 2 hours; one-download-per-update.
  Cache locally; never re-fetch fresh data; on HTTP 403 fall back to the cached copy."
- S3.1 spec.md FR-4 note: "HTTP 403 … cache fallback for 403 is handled in S3.2, not here."
