# Spec S2.4 — All Pydantic Schemas

## Overview
Defines all Pydantic request/response models used across the API surface. These schemas sit in
`backend/app/models/schemas.py` and are the single source of truth for what every endpoint
returns. They also serve as the contract that S2.5 freezes into `openapi.yaml` and the mock
server. Schemas must mirror the ORM models (S2.2, S2.3) faithfully but expose only what the
frontend/consumers need — no raw ORM objects should leak out of the API layer.

## Dependencies
- S1.1 (pydantic available via pyproject.toml)

## Target Location
`backend/app/models/schemas.py`

---

## Functional Requirements

### FR-1: SatelliteOut — list-level satellite representation
- **What**: Lightweight schema returned by `GET /satellites` (the paginated list).
- **Inputs**: Satellite ORM row
- **Outputs**: `catalog_no` (int), `name` (str), `intl_designator` (str | None), `epoch`
  (datetime), `regime` (str | None), `group_name` (str | None), `updated_at` (datetime)
- **Edge cases**: `intl_designator`, `regime`, `group_name` may be None — fields must be Optional

### FR-2: SatelliteDetail — full satellite detail
- **What**: Rich schema returned by `GET /satellites/{id}`. Extends SatelliteOut with all
  orbital elements.
- **Inputs**: Satellite ORM row (full)
- **Outputs**: All SatelliteOut fields **plus** `a_km` (float | None), `ecc` (float | None),
  `inc_deg` (float | None), `mean_motion` (float | None), `line1` (str), `line2` (str)
- **Edge cases**: Orbital element columns are nullable during ingestion before classification
  runs — must be Optional[float]

### FR-3: PositionSample — single position snapshot
- **What**: One time-stamped geodetic position used to build `SampledPositionProperty` in
  Cesium.
- **Inputs**: Propagation output for one satellite at one instant
- **Outputs**: `time` (datetime, ISO-8601), `lat` (float, degrees), `lon` (float, degrees),
  `alt_km` (float, km above WGS-84 ellipsoid)
- **Edge cases**: Altitude is **kilometres**, not metres — document in the field description to
  avoid Cesium unit confusion (Cesium expects metres; the frontend converts)

### FR-4: PositionsResponse — sampled track for one satellite
- **What**: Envelope returned by `GET /satellites/{id}/positions`.
- **Inputs**: `catalog_no`, list of PositionSample
- **Outputs**: `catalog_no` (int), `name` (str), `positions` (list[PositionSample])
- **Edge cases**: Empty positions list is valid (decayed sat / no propagation window)

### FR-5: ConjunctionOut — conjunction event
- **What**: Schema returned by `GET /conjunctions` and `GET /conjunctions/{pair_id}`.
- **Inputs**: Conjunction ORM row + joined satellite names
- **Outputs**: `id` (int), `sat_a` (int), `sat_b` (int), `sat_a_name` (str), `sat_b_name`
  (str), `tca` (datetime), `miss_km` (float), `rel_vel_kms` (float), `window_start`
  (datetime), `computed_at` (datetime)
- **Edge cases**: `sat_a_name`/`sat_b_name` come from joined Satellite rows — if the satellite
  was deleted, name falls back to the catalog number as string

### FR-6: OrbitalRegionStats — regime count summary
- **What**: Schema returned by `GET /stats/orbital-regions`.
- **Inputs**: Aggregated counts per regime
- **Outputs**: `leo` (int), `meo` (int), `geo` (int), `heo` (int), `total` (int)
- **Edge cases**: `total` must equal `leo + meo + geo + heo`; satellites with a null regime
  are excluded from counts (document this)

### FR-7: RiskRankingItem — risk ranking entry
- **What**: One row of `GET /stats/risk-ranking`, sorted ascending by `miss_km`.
- **Inputs**: Conjunction row + satellite names
- **Outputs**: `rank` (int, 1-based), `sat_a` (int), `sat_b` (int), `sat_a_name` (str),
  `sat_b_name` (str), `miss_km` (float), `rel_vel_kms` (float), `tca` (datetime)
- **Edge cases**: `rank` is computed server-side, not stored; empty result → empty list

### FR-8: Error shapes
- **What**: Consistent error envelope for 4xx/5xx responses.
- **Outputs**: `ErrorDetail` with `detail` (str)
- **Edge cases**: FastAPI's default `HTTPException` already produces `{"detail": ...}` — this
  schema simply documents it for OpenAPI; no custom exception handler needed yet

---

## Tangible Outcomes

- [ ] **Outcome 1**: `from app.models.schemas import SatelliteOut, SatelliteDetail, PositionSample, PositionsResponse, ConjunctionOut, OrbitalRegionStats, RiskRankingItem` succeeds with no import errors.
- [ ] **Outcome 2**: Each schema validates a dict constructed from the corresponding ORM fixture without raising `ValidationError`.
- [ ] **Outcome 3**: Optional fields (regime, intl_designator, orbital elements) accept `None` without raising.
- [ ] **Outcome 4**: `model_config = ConfigDict(from_attributes=True)` is set on schemas that are constructed from ORM objects, so `Schema.model_validate(orm_row)` works.
- [ ] **Outcome 5**: `OrbitalRegionStats` raises `ValidationError` (or the test asserts manually) when `total != leo+meo+geo+heo` — or a `model_validator` enforces this invariant.
- [ ] **Outcome 6**: All schemas appear in the auto-generated `/docs` OpenAPI UI (wired indirectly via the API endpoints that return them).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_satellite_out_from_orm**: Build a `Satellite` ORM instance (no DB), call
   `SatelliteOut.model_validate(sat)` → assert all fields present and match.
2. **test_satellite_detail_from_orm**: Same with full element fields populated.
3. **test_satellite_detail_optional_elements**: Satellite with `a_km=None`, `ecc=None`, etc. →
   `SatelliteDetail` validates without error; optional fields are None.
4. **test_position_sample_fields**: Construct `PositionSample(time=..., lat=0.0, lon=0.0,
   alt_km=400.0)` → assert `alt_km` is 400.0 (not 400000).
5. **test_positions_response_empty**: `PositionsResponse(catalog_no=25544, name="ISS",
   positions=[])` → valid, `positions` is `[]`.
6. **test_conjunction_out_from_fixture**: Construct `ConjunctionOut` from a dict mirroring a
   Conjunction row (with sat_a_name/sat_b_name provided) → all fields match.
7. **test_orbital_region_stats_total**: `OrbitalRegionStats(leo=100, meo=20, geo=10, heo=5,
   total=135)` → valid. If a `model_validator` is added, test that mismatched total raises.
8. **test_risk_ranking_item**: Construct with `rank=1` and valid fields → validates.
9. **test_error_detail**: `ErrorDetail(detail="not found")` → `detail` field is "not found".
10. **test_satellite_out_missing_optional**: Omitting `regime` from dict → field is None, no
    error.

### Mocking Strategy
- No external I/O in this spec — schemas are pure Pydantic; tests only build model instances
  and dicts
- DB: in-memory SQLAlchemy models used only to verify `from_attributes=True` round-trip; no
  real DB connection needed (construct ORM instances directly without adding to a session)

### Coverage Expectation
- All 8 schema classes have at least one test; all Optional fields exercised with None

---

## References
- roadmap.md row S2.4 (Notes column)
- CLAUDE.md — Pydantic models for all data in/out; `backend/app/models/schemas.py` as target
- S2.2 (`Satellite` ORM) and S2.3 (`Conjunction` ORM) — field names and types
- S2.5 (API contract) — consumes these schemas to generate `openapi.yaml`
- S6.1–S6.5 — endpoints that return these schemas
