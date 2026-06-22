# Roadmap — Satellite Collision Risk Detector 🚀

**Prototype target**: End-to-end CelesTrak TLEs → SGP4 propagation → conjunction screening → 3D globe with live risk highlighting + insights dashboard.
**Data source**: CelesTrak GP query API (free, no auth) as primary; Space-Track optional/out of scope.
**Propagation**: `sgp4` (vectorized `SatrecArray`) for the bulk screen, `skyfield` for geodetic display positions.
**Frontend**: CesiumJS (offline Natural Earth imagery — no ion token required).
**Out of scope for prototype**: covariance-based collision *probability* (needs CDMs), Space-Track CDM/SOCRATES ingestion, real-time streaming, 6-digit catalog-number (post-2026-07) handling.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Python 3.11 / FastAPI / uvicorn | Async, auto OpenAPI, fast iteration |
| Orbital mechanics | `sgp4` + `skyfield` | `SatrecArray` for fast bulk TEME propagation; skyfield for TEME→geodetic |
| Numerics | NumPy + SciPy (`scipy.spatial.cKDTree`) | Vectorized propagation + O(n log n) spatial neighbour search |
| TLE source | CelesTrak GP API (`gp.php`) | Free, no login, JSON/CSV/TLE, curated groups |
| Database | SQLite via SQLAlchemy | Zero-config, file-based, perfect for a student project |
| Scheduler | APScheduler | Periodic 2-hourly TLE refresh + re-screen |
| HTTP client | httpx | Fetch CelesTrak data (sync or async) |
| Config | pydantic-settings + .env | All thresholds/URLs/tokens via environment |
| Logging | Loguru | Structured logs with request_id |
| 3D globe | CesiumJS | Time-dynamic globe, SampledPositionProperty, clock animation |
| Charts | Chart.js | Regime distribution, approach counts, risk ranking |
| Testing (backend) | pytest + httpx TestClient | All external HTTP (CelesTrak) mocked |
| Testing (frontend) | Vitest (+ jsdom) + Playwright | Logic units + a few true end-to-end checks |
| Linting | Ruff (line length 100) + Prettier | Fast, opinionated formatting |

---

## Cost / Resources

| Resource | Tier | Est. Monthly Cost |
|----------|------|-------------------|
| CelesTrak GP API | Public, free (2-hour update cadence) | $0 |
| CesiumJS + offline Natural Earth imagery | Bundled with Cesium, no token | $0 |
| Cesium ion (optional, nicer imagery) | Free tier | $0 |
| SQLite | File-based, local | $0 |
| Local dev compute | Laptop | $0 |
| Optional hosting (Render / Fly.io / EC2 t3.micro) | Free tier | $0–5 |
| **Total (prototype demo volume)** | | **~$0** |

CelesTrak enforces a **one-download-per-update** policy (updates every 2 hours) and will return HTTP 403 / firewall abusive IPs — caching is mandatory, not optional (see S3.2).

---

## Spec Folder Convention

Each spec has a dedicated folder under `specs/`:

```
specs/
  spec-S1.1-dependency-declaration/
    spec.md        ← detailed specification (Phase 1 output)
    checklist.md   ← 4-phase lifecycle + TDD test tracker (Phases 2–4)
  spec-S1.2-developer-commands/
    spec.md
    checklist.md
  ...
```

### Spec Lifecycle (every spec passes through 4 phases)

Each spec's `checklist.md` tracks the four phases; a spec is only marked **done** when phase 4 passes.

```
Phase 1  CREATE SPEC      → writes spec.md (objective, interface, deps, acceptance criteria, test list)
Phase 2  VERIFY SPEC      → other student reviews; deps confirmed; acceptance criteria made testable → frozen
Phase 3  IMPLEMENT SPEC   → TDD: write failing tests (RED) → minimal code (GREEN) → refactor
Phase 4  VERIFY IMPLEMENT → full suite green in CI + acceptance met + integrates with dependents
```

**Status vocabulary** (the Status column below encodes the lifecycle):
`pending` → `spec` (spec.md written & verified) → `impl` (implementing, TDD in progress) → `done` (phase 4 passed, frozen)

**Completion rule:** a spec may not enter Phase 1 until every spec in its **Depends On** is `done`. A `done` spec is frozen — changes go to a new spec (e.g. `S4.2a`), never a reopen.

---

## Phases Overview

| Phase | Name | Owner | Specs | Key Output |
|-------|------|-------|-------|------------|
| 1 | Project Setup | Both | 6 | Runnable FastAPI skeleton + Cesium scaffold |
| 2 | Data Layer | S1 | 5 | SQLite models + Pydantic schemas + frozen API contract |
| 3 | TLE Ingestion & Parsing | S1 | 5 | Cached CelesTrak TLEs parsed into the DB |
| 4 | Propagation & Classification | S1 | 6 | TEME positions, lat/lon/alt, LEO/MEO/GEO/HEO |
| 5 | Conjunction Engine | S1 | 6 | Sieve → cKDTree → TCA → ranked risk events |
| 6 | Backend API | S1 | 6 | All REST endpoints + scheduled refresh |
| 7 | Frontend Globe | S2 | 5 | Animated satellites on a 3D globe |
| 8 | Risk Visualization & Interaction | S2 | 4 | Risk polylines + search + info panel |
| 9 | Insights Dashboard | S2 | 4 | Chart.js regime/approach/risk panels |
| 10 | Integration & Deployment | Both | 5 | Live end-to-end system |
| 11 | QA & Documentation | Both | 5 | Validated prototype, README, screenshots |

---

## Phase 1 — Project Setup

Bootstraps the project: dependencies, developer commands, settings, FastAPI app factory, CORS/static serving, and the Cesium frontend scaffold. No external data yet. **Owner: Both.** Output: `make dev` starts a healthy FastAPI server and the Cesium globe loads.

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S1.1 | `specs/spec-S1.1-dependency-declaration/` | — | `pyproject.toml`, `.env.example` | Dependency declaration | Deps: fastapi, uvicorn, skyfield, sgp4, numpy, scipy, sqlalchemy, apscheduler, httpx, pydantic-settings, loguru. Dev extras: pytest, httpx, ruff, pytest-mock | done |
| S1.2 | `specs/spec-S1.2-developer-commands/` | — | `Makefile` | Developer commands | Targets: `venv`, `install`, `install-dev`, `dev` (uvicorn --reload), `test`, `lint`, `seed`, `refresh`, `serve-frontend` | done |
| S1.3 | `specs/spec-S1.3-pydantic-settings/` | S1.1 | `backend/app/core/config.py` | Settings via pydantic-settings | Fields: CELESTRAK_BASE_URL, DEFAULT_GROUP (`active`), TLE_CACHE_DIR, TLE_MAX_AGE_HOURS (2), DATABASE_URL (sqlite), SCREEN_WINDOW_HOURS (24–72), SCREEN_STEP_SECONDS (30–60), COARSE_RADIUS_KM (10–20), RISK_THRESHOLD_KM (5), CESIUM_ION_TOKEN (optional). All from .env | done |
| S1.4 | `specs/spec-S1.4-fastapi-app-factory/` | S1.3 | `backend/app/main.py` | FastAPI app factory | Lifespan: init DB + start APScheduler on startup, shutdown cleanly. Include routers (satellites, conjunctions, stats). GET /health → `{"status":"ok"}` | done |
| S1.5 | `specs/spec-S1.5-cors-static/` | S1.4 | `backend/app/main.py` | CORS + static serving | CORSMiddleware allowing frontend origin. Mount `/static` (or serve `frontend/` in dev) so Cesium can call the API without cross-origin issues | done |
| S1.6 | `specs/spec-S1.6-frontend-scaffold/` | — | `frontend/index.html`, `frontend/src/main.js` | Cesium frontend scaffold | Load CesiumJS (CDN or npm + Vite). Empty `#cesiumContainer`. Vitest configured. No ion token yet (see S7.1) | done |

---

## Phase 2 — Data Layer

Async-free SQLite via SQLAlchemy, ORM models for satellites and conjunctions, all Pydantic schemas, and the **frozen API contract** that lets S1 and S2 work in parallel. **Owner: S1** (S2.5 shared with S2).

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S2.1 | `specs/spec-S2.1-sqlalchemy-engine/` | S1.3, S1.4 | `backend/app/db/database.py` | SQLAlchemy engine + session | `create_engine` (SQLite), `SessionLocal`, `Base`, `get_db()` FastAPI dependency | done |
| S2.2 | `specs/spec-S2.2-satellite-model/` | S2.1 | `backend/app/db/models.py` | Satellite ORM model | Columns: catalog_no (PK), name, intl_designator, line1, line2, epoch, a_km, ecc, inc_deg, mean_motion, regime, group_name, updated_at. Unique on catalog_no | done |
| S2.3 | `specs/spec-S2.3-conjunction-model/` | S2.1, S2.2 | `backend/app/db/models.py` | Conjunction ORM model | Columns: id (PK), sat_a (FK), sat_b (FK), tca, miss_km, rel_vel_kms, window_start, computed_at. Index on miss_km for ranking | done |
| S2.4 | `specs/spec-S2.4-pydantic-schemas/` | S1.1 | `backend/app/models/schemas.py` | All Pydantic schemas | SatelliteOut, SatelliteDetail, PositionSample, PositionsResponse, ConjunctionOut, OrbitalRegionStats, RiskRankingItem, plus error shapes | done |
| S2.5 | `specs/spec-S2.5-api-contract/` | S2.4 | `docs/api/openapi.yaml`, `frontend/mock/` | API contract + mock server | Freeze all endpoint paths/params/schemas. Ship a mock server returning schema-valid sample data so S2 builds the whole frontend in parallel. **Freeze early.** | done |

---

## Phase 3 — TLE Ingestion & Parsing

Fetch a CelesTrak GROUP, cache it respecting the 2-hour cadence, parse + validate TLEs, and persist to SQLite. **Owner: S1.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S3.1 | `specs/spec-S3.1-celestrak-client/` | S1.3 | `backend/app/services/ingestion.py` | CelesTrak GP client | `fetch_group(group, fmt="csv")` → `gp.php?GROUP={group}&FORMAT={fmt}` via httpx. Default group `active`. Returns raw text/JSON | done |
| S3.2 | `specs/spec-S3.2-tle-cache/` | S3.1 | `backend/app/services/ingestion.py` | TLE cache (2-hour cadence) | Cache file + age check; **re-download only if ≥2h old** (one-download-per-update). Catch HTTP 403 and fall back to cached copy. Never fetch on every request | done |
| S3.3 | `specs/spec-S3.3-tle-parser/` | S3.2 | `backend/app/services/tle_parser.py` | TLE field parser | Decode line 1/2: catalog_no, intl_designator, epoch (2-digit year rule, day-of-year→UTC), inclination, RAAN, ecc (implied leading decimal), arg perigee, mean anomaly, mean motion, BSTAR (exponent decode, e.g. `35580-4`→0.0000356) | done |
| S3.4 | `specs/spec-S3.4-tle-checksum/` | S3.3 | `backend/app/services/tle_parser.py` | Checksum validation | Modulo-10 checksum (digits summed, `-`=1). Reject lines failing checksum or ≠69 chars. Surface a clear parse error | done |
| S3.5 | `specs/spec-S3.5-persist-satellites/` | S3.3, S2.2 | `backend/app/services/ingestion.py` | Persist satellites | Upsert parsed records into Satellite table; dedupe by catalog_no; store raw line1/line2 byte-for-byte for re-propagation | done |

---

## Phase 4 — Propagation & Classification

SGP4 propagation (single + vectorized), TEME→geodetic conversion for display, and orbital-regime classification. **Owner: S1.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S4.1 | `specs/spec-S4.1-satrec-builder/` | S3.3 | `backend/app/services/propagation.py` | Satrec builder | `Satrec.twoline2rv(l1, l2)` per sat; assemble `SatrecArray` for bulk. WGS-72 gravity constants (matches TLE generation) | done |
| S4.2 | `specs/spec-S4.2-propagate-single/` | S4.1 | `backend/app/services/propagation.py` | Single-sat propagation | `propagate(sat, times)` → TEME pos (km) + vel (km/s). Surface nonzero SGP4 error codes (e.g. 6 = decayed) instead of returning garbage | done |
| S4.3 | `specs/spec-S4.3-propagate-bulk/` | S4.1 | `backend/app/services/propagation.py` | Vectorized bulk propagation | `propagate_array(sats, jds, frs)` via `SatrecArray.sgp4` → shape `(n_sats, n_times, 3)` TEME km. Drives the conjunction screen | done |
| S4.4 | `specs/spec-S4.4-teme-to-geodetic/` | S4.2 | `backend/app/services/propagation.py` | TEME→geodetic conversion | skyfield `EarthSatellite` / `wgs84.subpoint` → lat/lon/alt for the globe. Keep conjunction math in TEME; only convert for display | done |
| S4.5 | `specs/spec-S4.5-orbital-elements/` | S3.3 | `backend/app/services/classification.py` | Orbital element derivation | `semi_major_axis(n)=(μ/n_rad²)^(1/3)`, μ=398600.4418; `period=1440/n` min; apogee/perigee `a(1±e)`. Used by classification + sieve | done |
| S4.6 | `specs/spec-S4.6-regime-classification/` | S4.5 | `backend/app/services/classification.py` | Regime classification | `e≥0.25→HEO`; else `n≥11.25→LEO`, `1.2≤n<11.25→MEO`, `n<1.2→GEO`. Document chosen thresholds in spec.md | done |

---

## Phase 5 — Conjunction Engine *(technical heart — protect this critical path)*

Sieve → spatial screen → TCA refinement → risk scoring. Built on a brute-force correctness oracle. **Owner: S1.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S5.1 | `specs/spec-S5.1-apogee-perigee-sieve/` | S4.5, S4.6 | `backend/app/services/conjunctions.py` | Apogee/perigee sieve | `reject if perigee_A−apogee_B > pad OR perigee_B−apogee_A > pad`. Default pad ~30 km. O(n) per object; kills the vast majority of pairs (e.g. GEO–LEO) | done |
| S5.2 | `specs/spec-S5.2-window-sampling/` | S4.3, S5.1 | `backend/app/services/conjunctions.py` | Position sampling over window | Propagate surviving candidates over SCREEN_WINDOW_HOURS at SCREEN_STEP_SECONDS → positions[t]. Vectorized | done |
| S5.3 | `specs/spec-S5.3-ckdtree-screen/` | S5.2 | `backend/app/services/conjunctions.py` | cKDTree spatial screen | Per timestep: `cKDTree(P).query_pairs(r=COARSE_RADIUS_KM)`. Coarse radius generous to bridge fast crossings between samples. Output flagged (pair, t_idx) | done |
| S5.4 | `specs/spec-S5.4-tca-refinement/` | S5.3 | `backend/app/services/conjunctions.py` | TCA refinement & miss distance | Dense re-propagation (~1s) bracketed around coarse min; detect range-rate `r_rel·v_rel` zero-crossing → TCA, miss_km, rel_vel_kms | spec-written |
| S5.5 | `specs/spec-S5.5-risk-scoring/` | S5.4, S2.3 | `backend/app/services/conjunctions.py` | Risk scoring + persist | Keep events with miss ≤ RISK_THRESHOLD_KM (5 km, matches SOCRATES). Rank by miss (tie-break rel_vel). Idempotent persist to Conjunction table | pending |
| S5.6 | `specs/spec-S5.6-bruteforce-oracle/` | S5.3 | `backend/tests/services/test_conjunctions.py` | Brute-force correctness oracle | Small-set all-pairs distance check that S5.3's cKDTree result equals brute force. The trust anchor for the whole engine | pending |

---

## Phase 6 — Backend API

All REST endpoints over the frozen contract + the scheduled refresh job. **Owner: S1.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S6.1 | `specs/spec-S6.1-satellites-list-detail/` | S2.4, S2.2 | `backend/app/api/satellites.py` | Satellites list + detail | `GET /satellites` (filter by group/regime, paginated), `GET /satellites/{id}` (metadata + elements + regime). 404 on unknown | pending |
| S6.2 | `specs/spec-S6.2-positions-endpoint/` | S4.2, S4.4 | `backend/app/api/satellites.py` | Positions endpoint | `GET /satellites/{id}/positions?start=&stop=&step=` → sampled lat/lon/alt track for Cesium SampledPositionProperty | pending |
| S6.3 | `specs/spec-S6.3-bulk-positions/` | S4.3, S4.4 | `backend/app/api/satellites.py` | Bulk positions / CZML | `GET /positions` (or `/czml`) for many sats in one call — avoids N requests from the frontend. Vectorized via S4.3 | pending |
| S6.4 | `specs/spec-S6.4-conjunctions-endpoint/` | S5.5, S2.4 | `backend/app/api/conjunctions.py` | Conjunctions endpoints | `GET /conjunctions?threshold=&window=`, `GET /conjunctions/{pair_id}`. Empty result → `[]`, not error | pending |
| S6.5 | `specs/spec-S6.5-stats-endpoint/` | S4.6, S5.5 | `backend/app/api/stats.py` | Stats endpoints | `GET /stats/orbital-regions` (counts per regime, sum to total), `GET /stats/risk-ranking` (top-N by miss_km) | pending |
| S6.6 | `specs/spec-S6.6-scheduler/` | S3.2, S5.5 | `backend/app/services/scheduler.py` | Scheduled refresh | APScheduler job every 2h: re-ingest TLEs (respecting cadence) + re-run screen + persist. Failures isolated, don't crash app | pending |

---

## Phase 7 — Frontend Globe

Cesium globe, API client, satellite entities, time-animated tracks. Built against the S2.5 mock, then wired live. **Owner: S2.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S7.1 | `specs/spec-S7.1-cesium-bootstrap/` | S1.6 | `frontend/src/cesiumView.js` | Cesium globe bootstrap | `new Cesium.Viewer` with **offline Natural Earth imagery** (`TileMapServiceImageryProvider` from `Assets/Textures/NaturalEarthII`); `baseLayerPicker:false`, `geocoder:false`. No ion token needed | pending |
| S7.2 | `specs/spec-S7.2-api-client/` | S2.5 | `frontend/src/api.js` | API client layer | Typed fetch wrappers for every endpoint; base URL switch between mock and live; clean error/empty handling | pending |
| S7.3 | `specs/spec-S7.3-satellite-entities/` | S7.1, S7.2 | `frontend/src/cesiumView.js` | Satellite entities | Render points from `/satellites`, coloured by regime (LEO/MEO/GEO/HEO). Label on hover | pending |
| S7.4 | `specs/spec-S7.4-animation/` | S7.3, S6.3 | `frontend/src/cesiumView.js` | SampledPositionProperty + clock animation | Build per-sat `SampledPositionProperty` from `/positions`; animate on Cesium clock (multiplier, `LOOP_STOP`); `timeline.zoomTo(start,stop)` | pending |
| S7.5 | `specs/spec-S7.5-orbit-path/` | S7.4 | `frontend/src/cesiumView.js` | Orbit path graphic | `path` graphic for selected satellite's trajectory; toggle on/off | pending |

---

## Phase 8 — Risk Visualization & Interaction

Risk polylines between at-risk pairs, search, and the info panel. **Owner: S2.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S8.1 | `specs/spec-S8.1-risk-polylines/` | S7.4, S6.4 | `frontend/src/risk.js` | Risk-pair polylines | Draw a polyline between each at-risk pair from `/conjunctions`, coloured by severity (red ≤ threshold). Description shows TCA / miss / rel-vel | pending |
| S8.2 | `specs/spec-S8.2-polyline-tracking/` | S8.1 | `frontend/src/risk.js` | Polyline tracking | `CallbackProperty` keeps polyline endpoints attached to the two moving entities as the clock advances; rebuild on data refresh | pending |
| S8.3 | `specs/spec-S8.3-search/` | S7.3 | `frontend/src/search.js` | Search & select | Filter entities by name / NORAD id; selecting calls `viewer.flyTo(entity)` + sets `selectedEntity`. Empty/no-match handled | pending |
| S8.4 | `specs/spec-S8.4-info-panel/` | S7.3, S6.1 | `frontend/src/infoPanel.js` | Info panel | Selected satellite's orbital details (regime, a, e, i, period) + any conjunctions it's involved in | pending |

---

## Phase 9 — Insights Dashboard

Chart.js summaries of congestion and risk. **Owner: S2.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S9.1 | `specs/spec-S9.1-regime-chart/` | S7.2, S6.5 | `frontend/src/dashboard.js` | Regime distribution chart | Chart.js doughnut/bar from `/stats/orbital-regions`. Data sums to total satellite count | pending |
| S9.2 | `specs/spec-S9.2-approach-chart/` | S7.2, S6.4 | `frontend/src/dashboard.js` | Close-approach count chart | Count of detected conjunctions (optionally bucketed by miss-distance band) | pending |
| S9.3 | `specs/spec-S9.3-risk-table/` | S7.2, S6.5 | `frontend/src/dashboard.js` | Risk ranking table | Top-N riskiest pairs from `/stats/risk-ranking`, sorted by miss_km; click row → select pair on globe | pending |
| S9.4 | `specs/spec-S9.4-dashboard-refresh/` | S9.1, S9.2, S9.3 | `frontend/src/dashboard.js` | Dashboard refresh wiring | Re-fetch + redraw all panels when backend data refreshes (poll or manual button) | pending |

---

## Phase 10 — Integration & Deployment

Seed data, wire frontend to live backend, end-to-end test, optional containerization + hosting. **Owner: Both.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S10.1 | `specs/spec-S10.1-seed-script/` | S3.5, S5.5 | `backend/scripts/seed.py` | Seed script | `make seed`: initial CelesTrak fetch → parse → persist → run screen → persist conjunctions. Idempotent | pending |
| S10.2 | `specs/spec-S10.2-live-wiring/` | S6.1, S6.4, S6.5, S7.2 | `frontend/src/api.js` | Frontend live wiring | Switch api.js base URL to live backend; verify CORS; replace mock data path | pending |
| S10.3 | `specs/spec-S10.3-e2e-test/` | S10.2, S9.4 | `tests/e2e/` (Playwright) | End-to-end test | Start backend + frontend; satellites render from live data; a known conjunction shows a red link; dashboard counts match API; smoke every endpoint | pending |
| S10.4 | `specs/spec-S10.4-docker/` | S1.1 | `Dockerfile`, `docker-compose.yml` | Containerization (optional) | Multi-stage Dockerfile for backend; compose serving backend + static frontend. Build context = repo root | pending |
| S10.5 | `specs/spec-S10.5-deploy/` | S10.4, S10.1 | Host (Render / Fly.io / EC2) | Deployment (optional) | Deploy container, run seed, expose API + frontend. Capture the public URL for the README | pending |

---

## Phase 11 — QA & Documentation

Validation, the required README, architecture, screenshots, and GitHub collaboration hygiene. **Owner: Both.**

| Spec | Spec Location | Depends On | Location | Feature | Notes | Status |
|------|--------------|-----------|----------|---------|-------|--------|
| S11.1 | `specs/spec-S11.1-readme/` | S10.3 | `README.md` | README | Problem statement; data sources + CelesTrak attribution + 2-hour caching note; architecture; setup instructions; API reference; screenshots | pending |
| S11.2 | `specs/spec-S11.2-architecture-doc/` | S10.3 | `docs/architecture.md` | Architecture diagram | System diagram: ingestion → parse → propagate → screen → API → Cesium/dashboard. Frame note (TEME for math, geodetic for display) | pending |
| S11.3 | `specs/spec-S11.3-screenshots/` | S10.3 | `docs/screenshots/` | Screenshots / GIFs | Globe with animated satellites + red risk links; dashboard panels. Embedded in README | pending |
| S11.4 | `specs/spec-S11.4-github-collab/` | S1.1 | `.github/`, repo settings | GitHub collaboration | Protected `main`; `spec/SX.Y-name` branches; PR-per-spec with review; meaningful commits (`SX.Y(impl): …`); both students contribute | pending |
| S11.5 | `specs/spec-S11.5-demo-acceptance/` | S11.1, S11.3 | `docs/acceptance.md` | Demo & acceptance | Evaluation-criteria checklist: creativity, technical implementation, web-app quality, GitHub usage, documentation clarity. All specs `done` | pending |

---

## Master Spec Index

| Spec | Phase | Location | Feature | Spec Location | Status |
|------|-------|----------|---------|--------------|--------|
| S1.1 | Project Setup | `pyproject.toml`, `.env.example` | Dependency declaration | `specs/spec-S1.1-dependency-declaration/` | done |
| S1.2 | Project Setup | `Makefile` | Developer commands | `specs/spec-S1.2-developer-commands/` | done |
| S1.3 | Project Setup | `backend/app/core/config.py` | pydantic-settings config | `specs/spec-S1.3-pydantic-settings/` | done |
| S1.4 | Project Setup | `backend/app/main.py` | FastAPI app factory | `specs/spec-S1.4-fastapi-app-factory/` | done |
| S1.5 | Project Setup | `backend/app/main.py` | CORS + static serving | `specs/spec-S1.5-cors-static/` | done |
| S1.6 | Project Setup | `frontend/index.html`, `frontend/src/main.js` | Cesium frontend scaffold | `specs/spec-S1.6-frontend-scaffold/` | done |
| S2.1 | Data Layer | `backend/app/db/database.py` | SQLAlchemy engine + session | `specs/spec-S2.1-sqlalchemy-engine/` | done |
| S2.2 | Data Layer | `backend/app/db/models.py` | Satellite ORM model | `specs/spec-S2.2-satellite-model/` | done |
| S2.3 | Data Layer | `backend/app/db/models.py` | Conjunction ORM model | `specs/spec-S2.3-conjunction-model/` | done |
| S2.4 | Data Layer | `backend/app/models/schemas.py` | All Pydantic schemas | `specs/spec-S2.4-pydantic-schemas/` | done |
| S2.5 | Data Layer | `docs/api/openapi.yaml`, `frontend/mock/` | API contract + mock server | `specs/spec-S2.5-api-contract/` | done |
| S3.1 | TLE Ingestion & Parsing | `backend/app/services/ingestion.py` | CelesTrak GP client | `specs/spec-S3.1-celestrak-client/` | done |
| S3.2 | TLE Ingestion & Parsing | `backend/app/services/ingestion.py` | TLE cache (2-hour cadence) | `specs/spec-S3.2-tle-cache/` | done |
| S3.3 | TLE Ingestion & Parsing | `backend/app/services/tle_parser.py` | TLE field parser | `specs/spec-S3.3-tle-parser/` | done |
| S3.4 | TLE Ingestion & Parsing | `backend/app/services/tle_parser.py` | Checksum validation | `specs/spec-S3.4-tle-checksum/` | done |
| S3.5 | TLE Ingestion & Parsing | `backend/app/services/ingestion.py` | Persist satellites | `specs/spec-S3.5-persist-satellites/` | done |
| S4.1 | Propagation & Classification | `backend/app/services/propagation.py` | Satrec builder | `specs/spec-S4.1-satrec-builder/` | done |
| S4.2 | Propagation & Classification | `backend/app/services/propagation.py` | Single-sat propagation | `specs/spec-S4.2-propagate-single/` | done |
| S4.3 | Propagation & Classification | `backend/app/services/propagation.py` | Vectorized bulk propagation | `specs/spec-S4.3-propagate-bulk/` | done |
| S4.4 | Propagation & Classification | `backend/app/services/propagation.py` | TEME→geodetic conversion | `specs/spec-S4.4-teme-to-geodetic/` | done |
| S4.5 | Propagation & Classification | `backend/app/services/classification.py` | Orbital element derivation | `specs/spec-S4.5-orbital-elements/` | done |
| S4.6 | Propagation & Classification | `backend/app/services/classification.py` | Regime classification | `specs/spec-S4.6-regime-classification/` | done |
| S5.1 | Conjunction Engine | `backend/app/services/conjunctions.py` | Apogee/perigee sieve | `specs/spec-S5.1-apogee-perigee-sieve/` | done |
| S5.2 | Conjunction Engine | `backend/app/services/conjunctions.py` | Position sampling over window | `specs/spec-S5.2-window-sampling/` | done |
| S5.3 | Conjunction Engine | `backend/app/services/conjunctions.py` | cKDTree spatial screen | `specs/spec-S5.3-ckdtree-screen/` | done |
| S5.4 | Conjunction Engine | `backend/app/services/conjunctions.py` | TCA refinement & miss distance | `specs/spec-S5.4-tca-refinement/` | spec-written |
| S5.5 | Conjunction Engine | `backend/app/services/conjunctions.py` | Risk scoring + persist | `specs/spec-S5.5-risk-scoring/` | pending |
| S5.6 | Conjunction Engine | `backend/tests/services/test_conjunctions.py` | Brute-force correctness oracle | `specs/spec-S5.6-bruteforce-oracle/` | pending |
| S6.1 | Backend API | `backend/app/api/satellites.py` | Satellites list + detail | `specs/spec-S6.1-satellites-list-detail/` | pending |
| S6.2 | Backend API | `backend/app/api/satellites.py` | Positions endpoint | `specs/spec-S6.2-positions-endpoint/` | pending |
| S6.3 | Backend API | `backend/app/api/satellites.py` | Bulk positions / CZML | `specs/spec-S6.3-bulk-positions/` | pending |
| S6.4 | Backend API | `backend/app/api/conjunctions.py` | Conjunctions endpoints | `specs/spec-S6.4-conjunctions-endpoint/` | pending |
| S6.5 | Backend API | `backend/app/api/stats.py` | Stats endpoints | `specs/spec-S6.5-stats-endpoint/` | pending |
| S6.6 | Backend API | `backend/app/services/scheduler.py` | Scheduled refresh | `specs/spec-S6.6-scheduler/` | pending |
| S7.1 | Frontend Globe | `frontend/src/cesiumView.js` | Cesium globe bootstrap | `specs/spec-S7.1-cesium-bootstrap/` | pending |
| S7.2 | Frontend Globe | `frontend/src/api.js` | API client layer | `specs/spec-S7.2-api-client/` | pending |
| S7.3 | Frontend Globe | `frontend/src/cesiumView.js` | Satellite entities | `specs/spec-S7.3-satellite-entities/` | pending |
| S7.4 | Frontend Globe | `frontend/src/cesiumView.js` | SampledPositionProperty + animation | `specs/spec-S7.4-animation/` | pending |
| S7.5 | Frontend Globe | `frontend/src/cesiumView.js` | Orbit path graphic | `specs/spec-S7.5-orbit-path/` | pending |
| S8.1 | Risk Visualization & Interaction | `frontend/src/risk.js` | Risk-pair polylines | `specs/spec-S8.1-risk-polylines/` | pending |
| S8.2 | Risk Visualization & Interaction | `frontend/src/risk.js` | Polyline tracking | `specs/spec-S8.2-polyline-tracking/` | pending |
| S8.3 | Risk Visualization & Interaction | `frontend/src/search.js` | Search & select | `specs/spec-S8.3-search/` | pending |
| S8.4 | Risk Visualization & Interaction | `frontend/src/infoPanel.js` | Info panel | `specs/spec-S8.4-info-panel/` | pending |
| S9.1 | Insights Dashboard | `frontend/src/dashboard.js` | Regime distribution chart | `specs/spec-S9.1-regime-chart/` | pending |
| S9.2 | Insights Dashboard | `frontend/src/dashboard.js` | Close-approach count chart | `specs/spec-S9.2-approach-chart/` | pending |
| S9.3 | Insights Dashboard | `frontend/src/dashboard.js` | Risk ranking table | `specs/spec-S9.3-risk-table/` | pending |
| S9.4 | Insights Dashboard | `frontend/src/dashboard.js` | Dashboard refresh wiring | `specs/spec-S9.4-dashboard-refresh/` | pending |
| S10.1 | Integration & Deployment | `backend/scripts/seed.py` | Seed script | `specs/spec-S10.1-seed-script/` | pending |
| S10.2 | Integration & Deployment | `frontend/src/api.js` | Frontend live wiring | `specs/spec-S10.2-live-wiring/` | pending |
| S10.3 | Integration & Deployment | `tests/e2e/` | End-to-end test | `specs/spec-S10.3-e2e-test/` | pending |
| S10.4 | Integration & Deployment | `Dockerfile`, `docker-compose.yml` | Containerization | `specs/spec-S10.4-docker/` | pending |
| S10.5 | Integration & Deployment | Host (Render / Fly.io / EC2) | Deployment | `specs/spec-S10.5-deploy/` | pending |
| S11.1 | QA & Documentation | `README.md` | README | `specs/spec-S11.1-readme/` | pending |
| S11.2 | QA & Documentation | `docs/architecture.md` | Architecture diagram | `specs/spec-S11.2-architecture-doc/` | pending |
| S11.3 | QA & Documentation | `docs/screenshots/` | Screenshots / GIFs | `specs/spec-S11.3-screenshots/` | pending |
| S11.4 | QA & Documentation | `.github/`, repo settings | GitHub collaboration | `specs/spec-S11.4-github-collab/` | pending |
| S11.5 | QA & Documentation | `docs/acceptance.md` | Demo & acceptance | `specs/spec-S11.5-demo-acceptance/` | pending |
