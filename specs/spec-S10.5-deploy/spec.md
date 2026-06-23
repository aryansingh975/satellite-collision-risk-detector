# Spec S10.5 — Deployment

## Overview
Deploy the containerized satellite collision risk detector to a public cloud host (Render, Fly.io, or EC2 t3.micro free tier). The deployment runs the seed script on first start, exposes the FastAPI backend and Cesium frontend under a single public URL, and records that URL in the README. This is an optional but recommended step for the graded prototype demo.

## Dependencies
- S10.4 (Containerization) — multi-stage Dockerfile + docker-compose.yml must exist and build cleanly
- S10.1 (Seed script) — `make seed` / `python backend/scripts/seed.py` must be idempotent

## Target Location
Cloud host: Render / Fly.io / EC2 (student choice)
Config files: deployment manifests, `.env` on the host, `README.md` (public URL recorded)

---

## Functional Requirements

### FR-1: Container deploys and stays healthy
- **What**: The Docker image built in S10.4 must start successfully on the target host and pass a health check at `GET /health → {"status":"ok"}`.
- **Inputs**: Docker image pushed to a container registry (Docker Hub, Render's registry, or GHCR); environment variables set on the host (DATABASE_URL, TLE_CACHE_DIR, CELESTRAK_BASE_URL, CESIUM_ION_TOKEN optional).
- **Outputs**: Running container; `/health` returns 200 within 60 s of startup.
- **Edge cases**: Missing env vars must cause a clear startup error (pydantic-settings validation), not a silent misconfiguration. Container must not crash on clean startup with an empty SQLite database.

### FR-2: Seed runs on first deploy
- **What**: After the container starts for the first time (empty DB), `python backend/scripts/seed.py` is run (either as a Docker CMD one-shot, a compose `command:` override, a Render "pre-deploy command", or a Fly.io release command) to fetch TLEs, parse, persist, and screen conjunctions.
- **Inputs**: Live CelesTrak GP endpoint (or a cached copy in the volume).
- **Outputs**: SQLite DB populated with ≥1 satellite and ≥0 conjunctions; `/satellites` returns non-empty JSON.
- **Edge cases**: Seed is idempotent — running it twice must not duplicate records. If CelesTrak is unreachable, seed falls back to cached TLE file (S3.2 behaviour).

### FR-3: Frontend is accessible at the public URL
- **What**: The Cesium globe loads at the public root URL (e.g. `https://your-app.onrender.com/`). The frontend makes API calls to the same origin (no CORS errors in the browser console).
- **Inputs**: Static files served by FastAPI's `StaticFiles` mount (S1.5) or the Nginx/Caddy layer in the compose stack.
- **Outputs**: Cesium viewport renders without errors; satellites appear on the globe within the animation window.
- **Edge cases**: No Cesium ion token is required (offline Natural Earth imagery, S7.1). The page must not 404 on hard refresh (SPA fallback if needed).

### FR-4: Public URL recorded for the README
- **What**: Once the deployment is live, the public URL is captured and added to `README.md` under a "Live Demo" heading (fulfilled by S11.1, but the URL must be available here).
- **Inputs**: Successful FR-1 + FR-3 verification.
- **Outputs**: `README.md` contains the live URL; it is accessible from a browser with no VPN.
- **Edge cases**: Free-tier hosts may sleep after inactivity — acceptable for a student prototype; note in the README that a cold start may take 30–60 s.

### FR-5: Secrets managed via host environment variables
- **What**: No secrets (tokens, DB paths, API keys) are hardcoded in the image or checked into git. All configuration is injected through the host's environment variable UI (Render dashboard / Fly.io secrets / EC2 SSM or `.env` on instance).
- **Inputs**: `.env.example` (S1.3) documents every variable.
- **Outputs**: `docker inspect` / `fly secrets list` shows variables set; image layers contain no plaintext secrets.
- **Edge cases**: CESIUM_ION_TOKEN is optional — the app must start correctly if it is absent.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET https://<public-host>/health` returns `{"status":"ok"}` with HTTP 200 from a browser or `curl`.
- [ ] **Outcome 2**: `GET https://<public-host>/satellites` returns a non-empty JSON array (seed was run).
- [ ] **Outcome 3**: Cesium globe loads at `https://<public-host>/` with no JavaScript console errors related to CORS, 404, or missing token.
- [ ] **Outcome 4**: `README.md` contains the live URL under a "Live Demo" section.
- [ ] **Outcome 5**: No secrets appear in `git log`, Dockerfile, or docker-compose.yml — all sensitive values are host-side env vars.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

Because this is an infrastructure/deployment spec rather than a pure code spec, the tests are smoke-checks and configuration validators rather than unit tests.

1. **test_docker_image_health**: Build the image locally (`docker build .`), start a container with a minimal `.env`, and assert `GET /health` returns 200. Run via `backend/tests/test_docker_config.py` using `subprocess` + `requests` (or `httpx`). Skip if Docker daemon unavailable.
2. **test_seed_idempotency_on_empty_db**: Start the container, run seed twice in sequence, assert satellite count does not double. (Reuses the existing seed idempotency test from S10.1; verify it passes against the Docker image.)
3. **test_env_var_validation**: Launch the container with a deliberately missing required env var (e.g., `DATABASE_URL`); assert the container exits with a non-zero code and a pydantic-settings validation message in stderr.
4. **test_no_secrets_in_image**: Inspect the built image layers (via `docker history --no-trunc` or `docker save | tar -t`) and assert none of the known secret patterns (`CESIUM_ION_TOKEN=`, password strings) appear in the image filesystem.

### Mocking Strategy
- CelesTrak HTTP: continue using `respx` mocks in unit tests. The Docker smoke-test (test 1) may use a real network call for CelesTrak in a controlled CI environment, or mock it via an env-var override pointing to a local fixture server.
- DB: the Docker container uses a volume-mounted SQLite file; tests use a tmpfs or named volume cleaned between runs.
- Host platform API (Render/Fly): not tested in automated tests — deployment steps are manual (run `fly deploy` or push to Render via GitHub).

### Coverage Expectation
- Docker build + health smoke-test covered
- Seed idempotency on the containerized app covered
- Env-var validation covered
- Manual checklist covers the live public URL and no-secrets audit

---

## References
- [roadmap.md](../../roadmap.md) — S10.5 row: Depends On S10.4, S10.1; Location: Host (Render / Fly.io / EC2)
- [CLAUDE.md](../../.claude/CLAUDE.md) — no hardcoded secrets rule; CelesTrak 2-hour cadence; WGS-72; Docker build context = repo root
- [specs/spec-S10.4-docker/](../spec-S10.4-docker/) — Dockerfile + docker-compose.yml that this spec deploys
- [specs/spec-S10.1-seed-script/](../spec-S10.1-seed-script/) — seed.py idempotency guarantee
