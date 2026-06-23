# Spec S6.3 — Bulk Positions / CZML

## Overview
Provides a single `GET /positions` endpoint that returns sampled geodetic position tracks for
multiple satellites in one HTTP round-trip, eliminating the N-requests-per-satellite problem the
frontend would face if it relied solely on the single-satellite S6.2 endpoint. Propagation is
vectorised across all requested satellites using `SatrecArray` (S4.3); per-satellite geodetic
conversion uses `teme_to_geodetic` (S4.4). The S7.4 animation feature consumes this endpoint
to build `SampledPositionProperty` objects for all visible satellites at once.

## Dependencies
- S4.3 — `propagate_array` / `build_satrec_array` (vectorized TEME propagation)
- S4.4 — `teme_to_geodetic` (TEME → geodetic conversion for display)

## Target Location
`backend/app/api/satellites.py` — new route added to the existing `router`
Response schema: `backend/app/models/schemas.py` — new `BulkPositionsResponse`

---

## Functional Requirements

### FR-1: Endpoint signature
- **What**: `GET /positions?ids=<cat1,cat2,...>&start=<ISO>&stop=<ISO>&step=<int>`
- **Inputs**:
  - `ids` (required) — comma-separated NORAD catalog numbers (integers); 1–500 IDs per request
  - `start` (required) — propagation window start, ISO-8601 UTC datetime
  - `stop` (required) — propagation window end, ISO-8601 UTC datetime
  - `step` (optional, default 60) — step size in seconds; range [1, 3600]
- **Outputs**: `BulkPositionsResponse` — a list of `PositionsResponse` objects, one per
  satellite found in the DB; unknown IDs are silently skipped
- **Edge cases**:
  - `ids` list is empty → `422 Unprocessable Entity`
  - `start >= stop` → `422 Unprocessable Entity`
  - window > 30 days → `422 Unprocessable Entity`
  - none of the requested IDs exist in DB → empty `satellites` list (not an error)
  - `ids` list > 500 → `422 Unprocessable Entity`

### FR-2: Vectorized propagation
- **What**: After loading satellite ORM rows, build a `SatrecArray` with
  `build_satrec_array([(s.line1, s.line2) for s in sats])` and call `propagate_array` once
  over the full time grid — one SGP4 call for all satellites instead of N calls.
- **Inputs**: `SatrecArray`, Julian date arrays `jds` and `frs` derived from the time grid
- **Outputs**: TEME position array of shape `(n_sats, n_times, 3)` + error codes
- **Edge cases**: Satellites where SGP4 returns a non-zero error code for **any** timestep are
  excluded from the response with a `WARNING` log entry; the other satellites are still returned

### FR-3: Geodetic conversion per satellite
- **What**: For each satellite that survived the error-code filter, call `teme_to_geodetic`
  with its `line1`/`line2` and the shared time list to get lat/lon/alt_km samples
- **Why**: `teme_to_geodetic` uses skyfield's `EarthSatellite` (display boundary); the TEME
  positions from `propagate_array` are used only for the error-code mask, not passed to
  Cesium directly. Conjunction math is never called from this path.
- **Outputs**: list of `PositionSample` per satellite
- **Edge cases**: Timesteps skipped by `teme_to_geodetic` (NaN position) reduce the sample
  count for that satellite; the response still includes the satellite with fewer samples

### FR-4: Response schema
- **What**: Return `BulkPositionsResponse(satellites=list[PositionsResponse])`, where each
  inner `PositionsResponse` has `catalog_no`, `name`, and `positions: list[PositionSample]`
- **Inputs**: results from FR-3
- **Outputs**: JSON-serialised `BulkPositionsResponse`
- **Edge cases**: Zero matching satellites → `{"satellites": []}` (not 404)

### FR-5: Logging
- **What**: Every request logs `request_id`, the count of requested IDs, the count found,
  the count returned (after error-code filter), start/stop/step, and total elapsed time

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /positions?ids=25544,33591&start=...&stop=...&step=60` returns JSON
  with a `satellites` array containing two entries (one per found satellite), each with a
  non-empty `positions` list.
- [ ] **Outcome 2**: An `ids` value that includes unknown catalog numbers returns only the
  entries that exist in the DB — no 404, no error key in the response.
- [ ] **Outcome 3**: `GET /positions` with `start >= stop` returns HTTP 422.
- [ ] **Outcome 4**: `GET /positions` with no `ids` parameter returns HTTP 422.
- [ ] **Outcome 5**: `GET /positions` with `ids` > 500 entries returns HTTP 422.
- [ ] **Outcome 6**: A single call to `propagate_array` is used instead of N calls to
  `propagate` — verified in tests by asserting `propagate_array` is called exactly once.
- [ ] **Outcome 7**: `BulkPositionsResponse` schema is present in `schemas.py` and exported.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_bulk_positions_returns_two_satellites**: Seed DB with two sats; call
   `GET /positions?ids=<id1>,<id2>&start=...&stop=...&step=60`; assert `satellites` list
   has length 2, each entry has `catalog_no`, `name`, and at least one `PositionSample`.
2. **test_bulk_positions_unknown_id_skipped**: Request IDs where one is unknown; assert only
   the known satellite appears in the response (no error).
3. **test_bulk_positions_all_unknown_returns_empty**: All IDs unknown; assert `{"satellites": []}`.
4. **test_bulk_positions_start_gte_stop_422**: `start == stop` → HTTP 422.
5. **test_bulk_positions_empty_ids_422**: No `ids` param → HTTP 422.
6. **test_bulk_positions_too_many_ids_422**: `ids` with 501 entries → HTTP 422.
7. **test_bulk_positions_window_too_large_422**: Window > 30 days → HTTP 422.
8. **test_bulk_positions_uses_propagate_array**: Mock `propagate_array` + `teme_to_geodetic`; assert
   `propagate_array` called exactly once for a two-satellite request.
9. **test_bulk_positions_error_satellite_excluded**: Patch `teme_to_geodetic` to raise `ValueError`
   for one satellite; assert that satellite is absent from response, other satellite present.
10. **test_bulk_positions_response_schema**: Assert response is a valid `BulkPositionsResponse`
    (pydantic parse succeeds, `satellites` key present).

### Mocking Strategy
- CelesTrak HTTP: not involved in this endpoint — no mocking needed
- Propagation: mock `app.api.satellites.propagate_array` and
  `app.api.satellites.teme_to_geodetic` for unit tests; use real propagation with ISS TLE
  fixture for one integration test
- DB: in-memory SQLite via `conftest.py`; seed satellite rows with known TLEs

### Coverage Expectation
- All FRs covered by at least one test; all 422 branches exercised; error-code exclusion path tested

---

## References
- roadmap.md S6.3 row (Phase 6, Backend API)
- CLAUDE.md: frame convention (TEME for math, geodetic only at display boundary), WGS-72, no
  hardcoded tokens, request_id in all logs
