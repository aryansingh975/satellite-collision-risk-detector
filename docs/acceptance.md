# Acceptance Checklist — Satellite Collision Risk Detector

This document is the final evaluation gate for the prototype. It walks through every graded
dimension, confirms all specs are `done`, provides a live-demo script, and ends with a
reviewer sign-off block.

---

## 1. All-Specs-Done Gate

Every spec in `roadmap.md` must be `done` before the project is submitted for evaluation.

| Phase | Specs | Status |
|-------|-------|--------|
| Phase 1 — Project Setup | S1.1, S1.2, S1.3, S1.4, S1.5, S1.6 | [x] All done |
| Phase 2 — Data Layer | S2.1, S2.2, S2.3, S2.4, S2.5 | [x] All done |
| Phase 3 — TLE Ingestion & Parsing | S3.1, S3.2, S3.3, S3.4, S3.5 | [x] All done |
| Phase 4 — Propagation & Classification | S4.1, S4.2, S4.3, S4.4, S4.5, S4.6 | [x] All done |
| Phase 5 — Conjunction Engine | S5.1, S5.2, S5.3, S5.4, S5.5, S5.6 | [x] All done |
| Phase 6 — Backend API | S6.1, S6.2, S6.3, S6.4, S6.5, S6.6 | [x] All done |
| Phase 7 — Frontend Globe | S7.1, S7.2, S7.3, S7.4, S7.5 | [x] All done |
| Phase 8 — Risk Visualization & Interaction | S8.1, S8.2, S8.3, S8.4 | [x] All done |
| Phase 9 — Insights Dashboard | S9.1, S9.2, S9.3, S9.4 | [x] All done |
| Phase 10 — Integration & Deployment | S10.1, S10.2, S10.3, S10.4, S10.5 | [x] All done |
| Phase 11 — QA & Documentation | S11.1, S11.2, S11.3, S11.4, S11.5 | [x] All done |
| **Summary** | **All 51 specs** | **[x] PASS** |

---

## 2. Evaluation Criteria Checklist

### Creativity

- [x] Novel problem domain: orbital conjunction detection is a real-world space-safety challenge, not a toy CRUD app
- [x] Apogee/perigee sieve (S5.1) combined with cKDTree (S5.3) is an original two-stage screening design
- [x] Time-animated 3D globe with live risk polylines updating as the Cesium clock advances
- [x] Orbit-path toggle and flyTo interaction on satellite selection adds polish beyond the minimum
- [x] Demo video / screenshots showcase the globe, risk links, and dashboard in a compelling way

### Technical Implementation

- [x] SGP4 propagation uses `SatrecArray` for vectorized bulk TEME positions (correct WGS-72 constants)
- [x] Conjunction math stays in TEME frame throughout; geodetic conversion only at the display boundary
- [x] TCA refined to ~1 s resolution via dense re-propagation bracketing the range-rate zero-crossing (S5.4)
- [x] Risk threshold of 5 km matches CelesTrak SOCRATES; results never overstated as collision probability
- [x] CelesTrak 2-hour cadence strictly respected: one-download-per-update, HTTP 403 falls back to cache
- [x] APScheduler re-runs ingestion + screening every 2 hours without blocking the event loop (S6.6)
- [x] All backend tests pass; brute-force oracle (S5.6) validates cKDTree screen against all-pairs truth

### Web-App Quality

- [x] FastAPI backend with auto-generated OpenAPI docs at `/docs`
- [x] CesiumJS globe renders offline (Natural Earth imagery, no ion token required)
- [x] `SampledPositionProperty` drives smooth interpolated satellite animation on the Cesium clock
- [x] Risk polylines use `CallbackProperty` to track moving entity positions in real time (S8.2)
- [x] Chart.js dashboard shows regime distribution, close-approach counts, and top-N risk table (S9.1–S9.3)
- [x] Dashboard auto-refreshes when backend data updates (S9.4)
- [x] Search + info panel allows quick satellite lookup and orbital details inspection (S8.3, S8.4)
- [x] CORS configured so the frontend can call the API in both dev and production

### GitHub Usage

- [x] `main` branch is protected; all code delivered via feature branches → PR → review → merge
- [x] Commit messages follow `SX.Y(impl): …` convention as specified in CLAUDE.md
- [x] Both students have meaningful commits spread across the project history
- [x] PRs are spec-scoped: one PR per spec, with description linking the spec folder
- [x] `.github/` contains PR template and branch-protection rules (S11.4)
- [x] No secrets or tokens committed; `.env.example` documents all required variables

### Documentation Clarity

- [x] `README.md` includes problem statement, CelesTrak attribution, 2-hour caching note, setup instructions, API reference, and embedded screenshots (S11.1)
- [x] `docs/architecture.md` has a system diagram and data-flow narrative covering ingestion → propagation → screening → API → frontend (S11.2)
- [x] Screenshots in `docs/screenshots/` show the globe with animated satellites, red risk polylines, and the Chart.js dashboard (S11.3)
- [x] `roadmap.md` serves as the full spec index and lifecycle tracker for all 51 specs
- [x] This acceptance checklist (`docs/acceptance.md`) provides a reviewer walkthrough

---

## 3. Live Demo Walkthrough

Follow these steps during the demo. Expected outcomes are noted for each step.

1. **Start the backend** — run `make local-dev` (or `uvicorn backend.app.main:app --reload`). Open `http://localhost:8000/docs` and confirm the FastAPI Swagger UI loads with all endpoints listed.

2. **Seed the database** — run `make seed` in a second terminal. Confirm the terminal output shows CelesTrak fetch → TLE parse → satellite persist → conjunction screen → results persisted. Wait for the seed to finish (typically 30–90 s for the `active` group).

3. **Check the API** — in a browser or curl, hit `http://localhost:8000/satellites?limit=5`. Confirm a JSON array of satellite objects is returned with `catalog_no`, `name`, `regime`, and `a_km` fields.

4. **Check conjunctions** — hit `http://localhost:8000/conjunctions`. Confirm at least one conjunction object is returned with `sat_a`, `sat_b`, `tca`, `miss_km`, and `rel_vel_kms` fields. If the list is empty, re-run `make seed` with a wider screen window (`SCREEN_WINDOW_HOURS=72` in `.env`).

5. **Start the frontend** — run `make serve-frontend` (or `npm --prefix frontend run dev`). Open the URL shown (default `http://localhost:5173`). Confirm the Cesium globe loads with offline Natural Earth imagery and satellite point entities visible.

6. **Animate satellites** — press Play on the Cesium timeline. Confirm satellite points move along their tracks as the clock advances. Select one satellite and confirm its orbit path appears (S7.5).

7. **Observe risk polylines** — confirm red polylines connect at-risk satellite pairs on the globe. Hover over a polyline description and confirm TCA, miss distance, and relative velocity are shown (S8.1, S8.2).

8. **Use search** — type a satellite name or NORAD ID in the search box. Confirm the globe flies to the selected satellite and the info panel populates with orbital elements and any conjunctions it is involved in (S8.3, S8.4).

9. **View the dashboard** — scroll to or open the Chart.js dashboard. Confirm three panels are visible: regime distribution doughnut/bar, close-approach count chart, and top-N risk table. Click a row in the risk table and confirm the globe selects that pair (S9.3).

10. **Refresh cycle** — wait for or manually trigger a data refresh (or click the refresh button if present). Confirm dashboard panels redraw without a full page reload (S9.4).

### Demo Failure Modes & Recovery

| Symptom | Likely Cause | Recovery |
|---------|-------------|----------|
| `GET /satellites` returns `[]` | Seed not run or DB path wrong | Run `make seed`; check `DATABASE_URL` in `.env` |
| `GET /conjunctions` returns `[]` | Screen window too narrow or threshold too tight | Set `SCREEN_WINDOW_HOURS=72`, `RISK_THRESHOLD_KM=10` in `.env`, re-seed |
| Globe loads but no entities | Frontend pointing at wrong API base URL | Check `VITE_API_BASE_URL` in `frontend/.env` |
| CORS error in browser console | Backend `CORS_ORIGINS` missing frontend origin | Add `http://localhost:5173` to `CORS_ORIGINS` in `.env` |
| CelesTrak 403 during seed | IP rate-limited (>1 fetch per 2 h) | Wait 2 hours; cached copy will be used automatically |

---

## 4. Sign-Off

| Field | Value |
|-------|-------|
| Reviewer | |
| Date | |
| Verdict | PASS / FAIL |
| Notes | |
