# Spec S1.5 — CORS + Static Serving

## Overview
Adds `CORSMiddleware` to the FastAPI application so that the Cesium frontend (running on a
different port during development) can call the API without browser cross-origin blocks.
Also mounts the `frontend/` directory at `/static` so that FastAPI can serve the Cesium
app in dev mode from a single process. The allowed origins and the static directory path
are both driven by pydantic-settings (`.env`), never hardcoded.

## Dependencies
- S1.4 (FastAPI app factory — the `app` instance this spec extends)

## Target Location
`backend/app/main.py`

---

## Functional Requirements

### FR-1: CORS middleware registration
- **What**: `CORSMiddleware` must be added to the FastAPI `app` instance so that browsers
  receive the correct `Access-Control-Allow-Origin` response headers.
- **Inputs**: `CORS_ORIGINS` setting (list of strings, e.g. `["http://localhost:5173"]`),
  loaded from `.env` via `config.py`.
- **Outputs**: Pre-flight `OPTIONS` requests return HTTP 200 with `Access-Control-Allow-Origin`,
  `Access-Control-Allow-Methods`, and `Access-Control-Allow-Headers` headers. Actual
  cross-origin requests carry `Access-Control-Allow-Origin` in the response.
- **Constraints**:
  - Allowed methods: at minimum `GET`, `POST`, `OPTIONS`.
  - Allowed headers: at minimum `Content-Type`, `Authorization`.
  - `allow_credentials` may be `False` for this prototype (no cookies/auth).
  - Origin list must come from config — never a bare `"*"` hardcoded in source.
- **Edge cases**: Empty `CORS_ORIGINS` list → middleware still registered but no origin is
  whitelisted (safe default); unrecognised origin → no CORS headers emitted (browser blocks).

### FR-2: Static file mount
- **What**: Mount a `StaticFiles` instance so `GET /static/{path}` serves files from the
  `frontend/` directory (or a config-overridable path `STATIC_DIR`).
- **Inputs**: `STATIC_DIR` setting (default: `frontend/` relative to project root, resolved
  to an absolute path). Mounted at path `/static`.
- **Outputs**: `GET /static/index.html` returns the Cesium shell page; assets (JS, CSS,
  images) are served with appropriate content-type headers.
- **Edge cases**:
  - If `STATIC_DIR` does not exist on disk, the mount must fail loudly at startup (not
    silently swallow the error).
  - Requests for non-existent files return HTTP 404.

### FR-3: Config additions
- **What**: Add `CORS_ORIGINS` (list[str], default `["http://localhost:5173"]`) and
  `STATIC_DIR` (str, default `"frontend"`) to `backend/app/core/config.py`.
- **Inputs**: `.env` values.
- **Outputs**: Settings object exposes `cors_origins` and `static_dir` attributes.
- **Edge cases**: `.env` omits these keys → defaults apply silently.

---

## Tangible Outcomes

- [ ] **Outcome 1**: A `GET /health` request sent with `Origin: http://localhost:5173` returns
  `Access-Control-Allow-Origin: http://localhost:5173` in the response headers.
- [ ] **Outcome 2**: An `OPTIONS /health` pre-flight request returns HTTP 200 with the three
  required CORS headers.
- [ ] **Outcome 3**: `GET /static/index.html` returns HTTP 200 (when `frontend/index.html`
  exists) or HTTP 404 (when `STATIC_DIR` points to a non-existent path is handled at mount
  time, but a missing file inside a valid dir returns 404).
- [ ] **Outcome 4**: `CORS_ORIGINS` and `STATIC_DIR` are present in `Settings` with the
  documented defaults and override correctly from environment variables.
- [ ] **Outcome 5**: An origin NOT in `CORS_ORIGINS` does not receive `Access-Control-Allow-Origin`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_cors_allowed_origin** — request `GET /health` with `Origin: http://localhost:5173`;
   assert response header `Access-Control-Allow-Origin == "http://localhost:5173"`.
2. **test_cors_preflight** — request `OPTIONS /health` with standard pre-flight headers;
   assert HTTP 200 and presence of `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`.
3. **test_cors_disallowed_origin** — request with `Origin: http://evil.example.com`; assert
   `Access-Control-Allow-Origin` is absent from response headers.
4. **test_static_mount_serves_file** — write a temp `index.html` to a tmp dir, override
   `STATIC_DIR`, start the test app, assert `GET /static/index.html` → HTTP 200 with HTML body.
5. **test_static_missing_file** — assert `GET /static/nonexistent.txt` → HTTP 404.
6. **test_settings_cors_defaults** — instantiate `Settings` with no env overrides; assert
   `cors_origins == ["http://localhost:5173"]` and `static_dir == "frontend"`.
7. **test_settings_cors_override** — set `CORS_ORIGINS='["http://localhost:4000"]'` in env;
   assert `settings.cors_origins == ["http://localhost:4000"]`.

### Mocking Strategy
- Use `fastapi.testclient.TestClient` (synchronous) for CORS and static-file tests — no
  external HTTP calls involved.
- For static-file tests: use `tmp_path` (pytest fixture) to create a temporary directory with
  a real `index.html`; override `settings.static_dir` via `app.dependency_overrides` or
  monkeypatching before the `StaticFiles` mount (mount happens at import time, so tests that
  need a custom `STATIC_DIR` must rebuild the app or patch via `monkeypatch.setenv` +
  reimport).
- No CelesTrak mocking required — this spec has no external HTTP.

### Coverage Expectation
- All public-facing behaviour (CORS headers, static mount, config defaults) has at least one
  test; the disallowed-origin case is explicitly covered.

---

## References
- roadmap.md S1.5 row (Phase 1 table + Master Spec Index)
- CLAUDE.md — "NEVER hardcode secrets/tokens … All via `.env` → `config.py`"
- FastAPI docs: `CORSMiddleware`, `StaticFiles`
