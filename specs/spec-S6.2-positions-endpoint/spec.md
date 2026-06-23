# Spec S6.2 — Positions Endpoint

## Overview
Exposes `GET /satellites/{id}/positions?start=&stop=&step=` — a sampled lat/lon/alt track
for a single satellite over a caller-specified time window.  The response feeds Cesium's
`SampledPositionProperty` so the frontend can animate one satellite's ground track without
doing any propagation itself.  Propagation is done by calling `teme_to_geodetic` (S4.4),
which uses skyfield + WGS-84 subpoint for the TEME→geodetic conversion — the display-only
boundary.  Conjunction math must never come through this path.

## Dependencies
- **S4.2** — `build_satrec` / `propagate` (single-sat SGP4 propagation in TEME)
- **S4.4** — `teme_to_geodetic` (TEME→geodetic via skyfield; display boundary)

## Target Location
`backend/app/api/satellites.py` — new route added to the existing `router`.

---

## Functional Requirements

### FR-1: Route signature and query parameters
- **What**: `GET /satellites/{id}/positions` returns a sampled position track.
- **Inputs**:
  - `sat_id: int` — path parameter; the satellite's `catalog_no` (primary key).
  - `start: datetime` — ISO-8601 UTC datetime (query param, required); propagation window start.
  - `stop: datetime` — ISO-8601 UTC datetime (query param, required); propagation window end.
  - `step: int` — step size in **seconds** (query param, default `60`, min `1`, max `3600`).
- **Outputs**: `PositionsResponse` — `catalog_no`, `name`, `positions: list[PositionSample]`.
- **Edge cases**:
  - `start >= stop` → HTTP 422 with a clear message ("start must be before stop").
  - `stop - start > 30 days` → HTTP 422 ("window too large; maximum is 30 days").
  - Unknown `sat_id` → HTTP 404 ("Satellite {id} not found").
  - `step` out of range `[1, 3600]` → automatic HTTP 422 from FastAPI (Query constraint).

### FR-2: Time grid generation
- **What**: Build a list of UTC `datetime` objects from `start` to `stop` (inclusive) at
  `step`-second intervals.
- **Inputs**: `start`, `stop`, `step` (validated per FR-1).
- **Outputs**: `list[datetime]`; minimum length 1 (when `stop == start + step` or less).
- **Edge cases**: If `step > (stop - start).total_seconds()`, a single sample at `start`
  is still emitted (do not produce an empty list for a valid, non-zero-width window).

### FR-3: Propagation to geodetic positions
- **What**: Call `teme_to_geodetic(sat.line1, sat.line2, times)` to convert the time grid
  to a list of `{"lat", "lon", "alt_km"}` dicts.
- **Inputs**: `line1`, `line2` from the DB row; `times` from FR-2.
- **Outputs**: One `PositionSample` per returned dict (timesteps skipped by `teme_to_geodetic`
  for NaN positions are silently omitted — they are already logged at WARNING level inside
  `teme_to_geodetic`).
- **Edge cases**:
  - SGP4/skyfield raises `ValueError` (malformed TLE) → surface as HTTP 500 with a logged error.
  - All timesteps produce NaN (e.g. fully decayed satellite) → return empty `positions: []`
    with HTTP 200 (not an error; the frontend handles empty gracefully).

### FR-4: Logging with request_id
- **What**: Every handler invocation binds a fresh `uuid4` request_id via
  `logger.contextualize(request_id=...)` and emits a DEBUG entry with the key params.
- **Inputs**: Any call to the endpoint.
- **Outputs**: Structured Loguru log line; no change to response shape.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /satellites/25544/positions?start=2024-01-01T00:00:00&stop=2024-01-01T01:00:00&step=60`
  returns HTTP 200 with `catalog_no=25544`, `name` set, and `positions` containing ~61 samples,
  each with `lat`, `lon`, and `alt_km` (ISS orbits at ~400 km).
- [ ] **Outcome 2**: `GET /satellites/99999/positions?start=...&stop=...` returns HTTP 404.
- [ ] **Outcome 3**: `start >= stop` returns HTTP 422 with `detail` containing "start must be before stop".
- [ ] **Outcome 4**: Window exceeding 30 days returns HTTP 422.
- [ ] **Outcome 5**: `positions` list is empty (HTTP 200) when all timesteps are NaN (decayed sat stub).
- [ ] **Outcome 6**: Response validates against the `PositionsResponse` Pydantic schema — no extra keys,
  no missing required fields.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_positions_iss_basic** — seed DB with ISS TLE (catalog 25544); call
   `GET /satellites/25544/positions?start=2024-01-01T00:00:00Z&stop=2024-01-01T01:00:00Z&step=60`;
   assert 200, `catalog_no=25544`, `len(positions) >= 1`, all samples have `lat`, `lon`, `alt_km`.

2. **test_positions_step_respected** — same as above with `step=300`; assert `len(positions) <= 13`
   (60 min / 5 min = 12 steps + 1 inclusive endpoint).

3. **test_positions_unknown_satellite** — call with a non-existent `sat_id`; assert HTTP 404.

4. **test_positions_start_not_before_stop** — `start == stop`; assert HTTP 422 with message
   containing "start must be before stop".

5. **test_positions_window_too_large** — `stop - start = 31 days`; assert HTTP 422.

6. **test_positions_step_out_of_range** — `step=0` and `step=7200`; assert HTTP 422 for both
   (FastAPI Query validation).

7. **test_positions_decayed_satellite** — mock `teme_to_geodetic` to return `[]`; assert HTTP 200
   with `positions: []`.

8. **test_positions_response_schema** — assert response body parses cleanly as `PositionsResponse`
   (all required fields present, types correct).

### Mocking Strategy
- CelesTrak HTTP: not needed for this spec (positions endpoint reads from DB, not live).
- DB: in-memory SQLite via `conftest.py`; seed with a known Satellite row (ISS TLE, catalog 25544).
- `teme_to_geodetic`: mock for the decayed-satellite test only; real call for accuracy tests.
- Never hit the live CelesTrak API in tests.

### Coverage Expectation
- All four FRs covered; each edge case (404, 422×3, empty positions) has its own test.

---

## References
- `roadmap.md` — S6.2 row (Phase 6 table + Master Spec Index)
- `CLAUDE.md` — frame conventions (TEME for math, geodetic for display), WGS-72 rule, Loguru
- `backend/app/services/propagation.py` — `teme_to_geodetic`, `build_satrec`
- `backend/app/models/schemas.py` — `PositionSample`, `PositionsResponse` (already defined in S2.4)
