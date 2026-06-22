# Spec S3.1 — CelesTrak GP Client

## Overview
Implements an async HTTP client function `fetch_group(group, fmt)` that retrieves satellite GP data
from the CelesTrak GP query API (`gp.php`). It constructs the URL from pydantic-settings config,
issues the request via `httpx.AsyncClient`, and returns the raw response text (or parsed JSON for
`fmt="json"`). Tenacity provides 3-attempt exponential-backoff retry on transient failures. This is
the single point of contact with the external API; all caching logic lives in S3.2.

## Dependencies
- S1.3 — pydantic-settings config (`CELESTRAK_BASE_URL`, `DEFAULT_GROUP`)

## Target Location
`backend/app/services/ingestion.py`

---

## Functional Requirements

### FR-1: fetch_group signature and defaults
- **What**: Async function `fetch_group(group: str = settings.DEFAULT_GROUP, fmt: str = "csv") -> str`
  that returns the raw response body as a string.
- **Inputs**: `group` — CelesTrak group name (e.g. `"active"`, `"stations"`); `fmt` — format
  string (`"csv"`, `"json"`, `"tle"`).
- **Outputs**: Raw response body string. For `fmt="json"` the caller may parse it; this function
  always returns `str`.
- **Edge cases**: Empty group string should raise `ValueError`; fmt values outside the accepted set
  are passed through (CelesTrak will return an error, not our concern here).

### FR-2: URL construction
- **What**: Build the request URL as `{CELESTRAK_BASE_URL}/gp.php?GROUP={group}&FORMAT={fmt}`.
- **Inputs**: `CELESTRAK_BASE_URL` from `settings` (pydantic-settings), `group`, `fmt`.
- **Outputs**: Well-formed URL string passed to httpx.
- **Edge cases**: `CELESTRAK_BASE_URL` must not have a trailing slash (strip it defensively).

### FR-3: httpx async request
- **What**: Use `httpx.AsyncClient` (not `requests` or the sync client) to issue a `GET`.
- **Inputs**: Constructed URL.
- **Outputs**: `response.text` on HTTP 200.
- **Edge cases**: Raise `httpx.HTTPStatusError` on non-2xx responses (call `response.raise_for_status()`).

### FR-4: Tenacity retry
- **What**: Wrap the HTTP call with `@tenacity.retry` — 3 total attempts, exponential backoff
  (wait_exponential: min=1s, max=10s), retrying on `httpx.HTTPError` (covers timeouts,
  connection errors, and 5xx after raise_for_status).
- **Inputs**: N/A (decorator applied to the fetch function or an inner helper).
- **Outputs**: After 3 failed attempts, the last exception propagates to the caller.
- **Edge cases**: HTTP 403 is an `HTTPStatusError` and will be retried then re-raised; the cache
  fallback for 403 is handled in S3.2, not here.

### FR-5: Logging
- **What**: Log the outgoing request URL at DEBUG level and the response status + byte length at
  INFO level using Loguru (`from loguru import logger`).
- **Inputs**: URL, response.
- **Outputs**: Log records (no return value side effect).
- **Edge cases**: Log on each retry attempt so the caller can trace backoff.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `fetch_group("active", "csv")` with a mocked 200 response returns the exact
  response body string — verified by asserting `result == mock_body`.
- [ ] **Outcome 2**: The outgoing request URL contains `GROUP=active&FORMAT=csv` — verified by
  inspecting the captured httpx request in the mock.
- [ ] **Outcome 3**: A mocked 503 triggers retries; after 3 attempts `httpx.HTTPStatusError` is
  raised — verified with `pytest.raises` and a retry counter.
- [ ] **Outcome 4**: A mocked 403 raises `httpx.HTTPStatusError` after retries (not silently
  swallowed) — verified with `pytest.raises`.
- [ ] **Outcome 5**: Passing `group=""` raises `ValueError` before any HTTP call is made.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_fetch_group_returns_body**: Mock httpx 200; assert return value equals mocked text.
2. **test_fetch_group_url_contains_group_and_format**: Mock httpx; inspect captured request URL for
   correct GROUP and FORMAT query params.
3. **test_fetch_group_default_group_is_active**: Call without `group` arg; assert URL uses
   `GROUP=active`.
4. **test_fetch_group_retries_on_5xx**: Mock httpx to return 503 three times; assert
   `HTTPStatusError` raised and the mock was called 3 times.
5. **test_fetch_group_raises_on_403**: Mock httpx 403; assert `HTTPStatusError` raised.
6. **test_fetch_group_empty_group_raises_value_error**: Call `fetch_group("")`; assert `ValueError`.

### Mocking Strategy
- Use `respx` (or `httpx.MockTransport`) to intercept all httpx calls — never hit the live
  CelesTrak API in tests.
- Patch `tenacity` wait to `wait_none()` in tests so retries don't add real delay.
- Use `pytest-asyncio` (or `anyio`) for async test functions.

### Coverage Expectation
- All public functions have at least one test; all FRs covered; retry and error paths tested.

---

## References
- roadmap.md S3.1 row (Phase 3 table + Master Spec Index)
- CLAUDE.md: "Async for I/O", "Tenacity (3 attempts, exponential backoff)", "RESPECT CelesTrak
  limits", "on HTTP 403 fall back to the cached copy" (cache fallback = S3.2 concern)
