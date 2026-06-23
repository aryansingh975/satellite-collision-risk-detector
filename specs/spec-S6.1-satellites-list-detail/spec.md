# Spec S6.1 — Satellites List + Detail

## Overview
Expose the persisted satellite catalogue over HTTP. Two endpoints together make up
this spec: a paginated list endpoint (`GET /satellites`) with optional filters for
group and orbital regime, and a detail endpoint (`GET /satellites/{id}`) that
returns full orbital elements and raw TLE lines for a single satellite.  A 404 is
returned whenever the requested catalog number is absent from the database.

## Dependencies
- S2.4 — Pydantic schemas (`SatelliteOut`, `SatelliteDetail`, `ErrorDetail`)
- S2.2 — `Satellite` ORM model + SQLAlchemy session

## Target Location
`backend/app/api/satellites.py`

---

## Functional Requirements

### FR-1: `GET /satellites` — Paginated list with optional filters
- **What**: Return a JSON array of `SatelliteOut` objects representing satellites
  stored in the database.  Supports optional query-string filters and standard
  offset/limit pagination.
- **Inputs**:
  - `group` (str, optional) — filter by `Satellite.group_name` (case-insensitive
    exact match).
  - `regime` (str, optional) — filter by `Satellite.regime`; accepted values:
    `LEO`, `MEO`, `GEO`, `HEO` (case-insensitive).
  - `limit` (int, default 100, max 1000) — page size.
  - `offset` (int, default 0) — number of rows to skip.
- **Outputs**: `list[SatelliteOut]` — ordered by `catalog_no` ascending.
- **Edge cases**:
  - No satellites in DB → empty list `[]`, HTTP 200.
  - Unknown group / regime → empty list `[]`, HTTP 200 (not an error).
  - `limit` > 1000 → clamp to 1000 (or raise HTTP 422).
  - `offset` < 0 → raise HTTP 422.

### FR-2: `GET /satellites/{id}` — Single satellite detail
- **What**: Return a `SatelliteDetail` object for the satellite identified by its
  NORAD catalog number.
- **Inputs**:
  - `id` (int, path parameter) — `Satellite.catalog_no`.
- **Outputs**: `SatelliteDetail` — includes all `SatelliteOut` fields plus
  `a_km`, `ecc`, `inc_deg`, `mean_motion`, `line1`, `line2`.
- **Edge cases**:
  - Unknown `id` → HTTP 404 with `{"detail": "Satellite {id} not found"}`.
  - Orbital elements nullable (classification not yet run) → return `null` for
    those fields; do not error.

### FR-3: Router registration
- **What**: The router defined in `backend/app/api/satellites.py` must be included
  in `backend/app/main.py` under a prefix (e.g. `/satellites` or root `/`).
- **Inputs**: FastAPI app instance, `APIRouter`.
- **Outputs**: The two endpoints respond at the expected paths.
- **Edge cases**: Router must not shadow any other existing routers.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /satellites` returns HTTP 200 with a JSON array; empty
  DB returns `[]`.
- [ ] **Outcome 2**: `GET /satellites?regime=LEO` returns only LEO satellites
  (verified against DB fixture).
- [ ] **Outcome 3**: `GET /satellites?group=active` returns only satellites in
  the `active` group.
- [ ] **Outcome 4**: `GET /satellites?limit=2&offset=0` returns at most 2
  results; `offset=2` returns the next page.
- [ ] **Outcome 5**: `GET /satellites/25544` returns HTTP 200 with `catalog_no`,
  `name`, `line1`, `line2`, and orbital elements.
- [ ] **Outcome 6**: `GET /satellites/999999` (unknown) returns HTTP 404 with
  `{"detail": "Satellite 999999 not found"}`.
- [ ] **Outcome 7**: Response bodies validate against `SatelliteOut` /
  `SatelliteDetail` Pydantic schemas (no extra or missing required fields).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_list_satellites_empty**: Empty DB → GET /satellites → 200, body `[]`.
2. **test_list_satellites_returns_all**: Seed 3 satellites → GET /satellites → 200,
   3 items ordered by `catalog_no`.
3. **test_list_filter_by_regime**: Seed LEO + GEO satellites → GET
   /satellites?regime=LEO → only LEO rows.
4. **test_list_filter_by_group**: Seed satellites with different `group_name` →
   GET /satellites?group=active → only matching rows.
5. **test_list_pagination**: Seed 5 satellites → GET /satellites?limit=2&offset=2
   → 2 rows starting from the 3rd.
6. **test_list_unknown_regime**: GET /satellites?regime=UNKNOWN → 200, `[]`.
7. **test_detail_known**: Seed ISS (25544) → GET /satellites/25544 → 200,
   `catalog_no=25544`, correct `line1`/`line2`.
8. **test_detail_not_found**: GET /satellites/999999 → 404, detail message.
9. **test_detail_schema**: Response validates as `SatelliteDetail` (all required
   fields present, including `line1`/`line2`).
10. **test_detail_nullable_elements**: Satellite with `a_km=None` → 200, `a_km`
    field is `null` in JSON (no error).

### Mocking Strategy
- Use FastAPI `TestClient` with the in-memory SQLite DB from `conftest.py`.
- No external HTTP calls required for this spec (data is already in DB).
- Seed fixtures directly into the test DB session via SQLAlchemy.
- Reuse ISS TLE fixture from `conftest.py` (catalog 25544).

### Coverage Expectation
- All public route functions have at least one test.
- Both happy-path and 404 error path covered for detail endpoint.
- Filter combinations (group, regime) each tested independently.

---

## References
- `roadmap.md` row S6.1, Phase 6 table
- `CLAUDE.md` — project rules, no hardcoded secrets, Loguru `request_id`
- `backend/app/models/schemas.py` — `SatelliteOut`, `SatelliteDetail`
- `backend/app/db/models.py` — `Satellite` ORM model
