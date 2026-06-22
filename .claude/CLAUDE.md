# Satellite Collision Risk Detector — Claude Code Context

## Project
Tracks satellites from TLE orbital data, predicts close approaches (conjunctions), and visualizes
positions, orbits, and collision risk on a 3D globe with an insights dashboard.
Backend: Python 3.11 / FastAPI + skyfield/sgp4. Frontend: CesiumJS. Storage: SQLite.
Graded two-person student project — deliverable is a working web app + a GitHub repo.

## Developers
- **Student 1 — Data & Backend**: Nishant (nishantgaurav23@gmail.com) → branch: `feature/satcollision-nishant`
- **Student 2 — Web App & Visualization**: `<teammate>` → branch: `feature/satcollision-<name>`
- Main branch: integration only. All code via feature branches → PR → main.

## Key Rules
- NEVER commit to main directly. Always use feature branches → PR.
- NEVER hardcode secrets/tokens (e.g. Cesium ion token). All via `.env` → `config.py`.
- NEVER add Claude as co-author in commits.
- Git author: nishantgaurav23 / nishantgaurav23@gmail.com (S1); teammate sets their own.
- RESPECT CelesTrak limits: data updates every **2 hours**; **one-download-per-update**. Cache locally; never re-fetch fresh data; on HTTP 403 fall back to the cached copy. Hammering the API gets the IP firewalled.
- Conjunction math stays in **TEME/ECI** (relative geometry is frame-independent within one instant). Convert to geodetic lat/lon/alt ONLY for display.
- Use **WGS-72** gravity constants in SGP4 (matches how TLEs are generated). Do not switch to WGS-84.
- Propagate only a few days to ~2 weeks from TLE epoch — accuracy degrades after that.
- This tool reports **potential close approaches** (miss distance), NOT collision probability — there is no covariance in TLEs. Never overstate it.

## Orbital Mechanics — Libraries & Constants
| Concern | Choice | Notes |
|---------|--------|-------|
| Bulk propagation | `sgp4` `SatrecArray` | Vectorized TEME pos/vel for the conjunction screen |
| Display positions | `skyfield` `EarthSatellite` + `wgs84.subpoint` | TEME → geodetic lat/lon/alt |
| Neighbour search | `scipy.spatial.cKDTree` | `query_pairs(r)` per timestep, O(n log n) |
| μ (GM_earth) | `398600.4418` km³/s² | semi-major axis `a=(μ/n_rad²)^(1/3)` |
| Risk threshold | `5` km at TCA | matches CelesTrak SOCRATES |
| Regime split | `e≥0.25→HEO`; `n≥11.25→LEO`; `1.2≤n<11.25→MEO`; `n<1.2→GEO` | document in the spec |

## Tech Stack
- FastAPI + uvicorn
- SQLAlchemy + SQLite
- skyfield + sgp4 (orbital mechanics)
- NumPy + SciPy `cKDTree` (spatial screen)
- httpx (CelesTrak fetch) + tenacity (retry)
- APScheduler (2-hourly refresh)
- CesiumJS (3D globe) + Chart.js (dashboard)
- pydantic-settings (config), Loguru (logging)

## Project Structure
```
backend/app/
├── main.py                 # FastAPI entry point, lifespan (DB + scheduler), routers
├── core/
│   └── config.py           # All settings from .env (pydantic-settings)
├── db/
│   ├── database.py         # SQLAlchemy engine + get_db()
│   └── models.py           # Satellite + Conjunction ORM models
├── models/
│   └── schemas.py          # Pydantic request/response models
├── api/
│   ├── satellites.py       # /satellites, /satellites/{id}, /positions
│   ├── conjunctions.py     # /conjunctions
│   └── stats.py            # /stats/orbital-regions, /stats/risk-ranking
└── services/
    ├── ingestion.py        # CelesTrak fetch + 2h cache + persist
    ├── tle_parser.py       # TLE field parse + checksum validation
    ├── propagation.py      # SGP4/skyfield → TEME + geodetic
    ├── classification.py   # orbital elements + LEO/MEO/GEO/HEO
    ├── conjunctions.py     # sieve → cKDTree → TCA → risk score
    └── scheduler.py        # APScheduler 2h refresh + re-screen
backend/scripts/seed.py     # initial fetch + screen + populate DB
backend/tests/              # pytest (mirror app structure)
frontend/
├── index.html
└── src/
    ├── main.js             # app entry
    ├── cesiumView.js       # globe, entities, SampledPositionProperty, clock
    ├── api.js              # fetch wrappers (mock ↔ live)
    ├── risk.js             # at-risk polylines
    ├── search.js           # search + select
    ├── infoPanel.js        # selected-satellite details
    └── dashboard.js        # Chart.js panels
specs/                      # spec-{id}-{slug}/{spec.md, checklist.md}
roadmap.md                  # full spec index (source of truth)
```

## Core Flow
```
CelesTrak GP API → ingestion.py (fetch + 2h cache)
→ tle_parser.py (parse + checksum)
→ db/models.py (persist satellites)
→ propagation.py (SGP4 → TEME pos/vel; skyfield → lat/lon/alt)
→ classification.py (a, e, period → LEO/MEO/GEO/HEO)
→ conjunctions.py (apogee/perigee sieve → cKDTree screen → TCA refine → risk score → persist)
→ api/* (REST endpoints)
→ frontend (Cesium globe + animated tracks + red risk polylines + Chart.js dashboard)
scheduler.py re-runs the whole chain every 2 hours.
```

## Spec Folder Convention
Each spec has a dedicated folder under `specs/`:
```
specs/spec-{id}-{slug}/        # e.g. specs/spec-S5.1-apogee-perigee-sieve/
  spec.md        ← detailed specification
  checklist.md   ← implementation progress tracker
```
Full spec index is in `roadmap.md`.

## Spec-Driven Development Commands (the 4 phases)

| Command | Invocation | Phase | Purpose |
|---------|------------|-------|---------|
| **Create spec** | `/create-spec S5.1 apogee-perigee-sieve` | 1 · Create Spec | Creates `spec.md` + `checklist.md` from roadmap. |
| **Check deps** | `/check-spec-deps S5.1` | 2 · Verify Spec | Verifies all prerequisite specs are `done` and their tests pass. |
| **Implement spec** | `/implement-spec S5.1` | 3 · Implement Spec | TDD implementation following spec + checklist. |
| **Verify spec** | `/verify-spec S5.1` | 4 · Verify Implement | Post-implementation audit: tests, lint, outcomes, wiring. |

**Status lifecycle** (Status column in `roadmap.md`):
`pending` → `spec-written` (after `/create-spec`) → `done` (after `/implement-spec` + `/verify-spec` pass).
A spec may not start Phase 1 until every spec in its **Depends On** is `done`.

## Commands
```bash
# Local (uv, no Docker)
make venv           # Create .venv at root
make install        # uv pip install -r pyproject.toml
make install-dev    # Install + pytest/ruff
make local-dev      # uvicorn with hot reload
make local-test     # pytest
make local-lint     # ruff check + format
make seed           # Initial CelesTrak fetch + screen + populate SQLite
make refresh        # Force a TLE refresh + re-screen (respects 2h cadence)

# Frontend
make serve-frontend # Vite dev server for frontend/
npm --prefix frontend run test   # Vitest

# Docker (optional — Phase 10)
make dev            # docker-compose up --build
make test           # pytest in container
```

## Environment
- **venv**: `.venv` at project root (Python 3.11)
- **Package manager**: `uv` — single source of truth: `pyproject.toml` (NO requirements.txt)
- **Install**: `uv pip install -r pyproject.toml`
- **Docker build context**: repo root (not ./backend)

## Testing
- Backend from project root: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short`
- **Mock all external HTTP** (CelesTrak) — use `respx` or an httpx `MockTransport`. Never hit the live API in tests.
- Use known fixtures: the ISS TLE (catalog 25544) and the published SGP4 verification vectors for propagation accuracy tests.
- `conftest.py`: in-memory SQLite test DB, sample TLE fixtures, mocked CelesTrak responses; dispose engine in teardown.
- Frontend: Vitest (+ jsdom) for logic; Playwright for the few true end-to-end checks.
- A file is NEVER considered done until its tests pass.

## Code Standards
- **Async for I/O** (CelesTrak fetch, endpoints). **Sync NumPy/SciPy** for propagation + screening (CPU-bound); offload long screens to a background task / threadpool rather than blocking the event loop.
- Pydantic models for all data in/out (`backend/app/models/schemas.py`).
- Tenacity (3 attempts, exponential backoff) on the CelesTrak fetch.
- Loguru for logging — always include `request_id` in log context.
- Ruff for linting and formatting (line length: 100); Prettier for the frontend.
- Keep conjunction math in TEME; convert to geodetic only at the display boundary.
- Persist TLE `line1`/`line2` byte-for-byte so satellites can be re-propagated deterministically.
