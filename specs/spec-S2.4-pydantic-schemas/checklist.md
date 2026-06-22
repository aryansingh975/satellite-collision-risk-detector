# Checklist — Spec S2.4: All Pydantic Schemas

## Phase 1: Setup & Dependencies
- [x] Verify S1.1 is `done` (pydantic in pyproject.toml)
- [x] Locate / create `backend/app/models/schemas.py`
- [x] Confirm `pydantic >= 2.0` is available (uses `model_config`, `ConfigDict`, `model_validator`)

## Phase 2: Tests First (TDD)
- [x] Write `backend/tests/models/test_schemas.py`
- [x] `test_satellite_out_from_orm` — SatelliteOut.model_validate from ORM instance
- [x] `test_satellite_detail_from_orm` — SatelliteDetail with all element fields
- [x] `test_satellite_detail_optional_elements` — None element fields pass validation
- [x] `test_position_sample_fields` — alt_km stored as km (not metres)
- [x] `test_positions_response_empty` — empty positions list is valid
- [x] `test_conjunction_out_from_fixture` — ConjunctionOut from dict with names
- [x] `test_orbital_region_stats_total` — OrbitalRegionStats validates; test total invariant
- [x] `test_risk_ranking_item` — RiskRankingItem with rank=1
- [x] `test_error_detail` — ErrorDetail with detail string
- [x] `test_satellite_out_missing_optional` — optional fields accept None
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `SatelliteOut` (FR-1) — `ConfigDict(from_attributes=True)`
- [x] Implement `SatelliteDetail(SatelliteOut)` (FR-2) — adds element + TLE fields
- [x] Implement `PositionSample` (FR-3) — time, lat, lon, alt_km
- [x] Implement `PositionsResponse` (FR-4) — catalog_no, name, positions list
- [x] Implement `ConjunctionOut` (FR-5) — includes sat_a_name / sat_b_name
- [x] Implement `OrbitalRegionStats` (FR-6) — leo/meo/geo/heo/total
- [x] Implement `RiskRankingItem` (FR-7) — rank + conjunction fields + names
- [x] Implement `ErrorDetail` (FR-8) — detail: str
- [x] Run tests — expect pass (Green)
- [x] Refactor: consolidate shared base if sensible (keep it DRY but no over-abstraction)

## Phase 4: Integration
- [x] Confirm `from app.models.schemas import ...` works from any api module
- [x] Wire into at least one placeholder endpoint to verify OpenAPI UI renders the schema — N/A at this phase; schemas confirmed importable; endpoints wired in S6.x specs
- [x] Run lint: `make local-lint` (ruff check + format, line length 100)
- [x] Run full backend test suite: `python -m pytest backend/tests/ -v --tb=short` — 72/72 passed

## Phase 5: Verification
- [x] All 6 tangible outcomes checked off in spec.md
- [x] No hardcoded secrets/tokens in schemas.py
- [x] `from_attributes=True` set on every schema that wraps an ORM model
- [x] `alt_km` documented as kilometres (not metres) — field description or comment
- [x] Update roadmap.md status: `spec-written` → `done` (after implement + verify pass)
