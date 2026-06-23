# Checklist — Spec S6.1: Satellites List + Detail

## Phase 1: Setup & Dependencies
- [x] Verify S2.4 (Pydantic schemas) is `done`
- [x] Verify S2.2 (Satellite ORM model) is `done`
- [x] Locate or create `backend/app/api/satellites.py`
- [x] Confirm `SatelliteOut` and `SatelliteDetail` imported from `app.models.schemas`
- [x] Confirm `get_db` dependency available from `app.db.database`

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/api/test_satellites.py`
- [x] Write `test_list_satellites_empty` — empty DB → 200, `[]`
- [x] Write `test_list_satellites_returns_all` — 3 seeded → 3 items ordered by catalog_no
- [x] Write `test_list_filter_by_regime` — LEO filter returns only LEO rows
- [x] Write `test_list_filter_by_group` — group filter returns only matching rows
- [x] Write `test_list_pagination` — limit/offset returns correct slice
- [x] Write `test_list_unknown_regime` — unknown regime → 200, `[]`
- [x] Write `test_detail_known` — seed ISS → GET /satellites/25544 → 200
- [x] Write `test_detail_not_found` — GET /satellites/999999 → 404
- [x] Write `test_detail_schema` — response validates as `SatelliteDetail`
- [x] Write `test_detail_nullable_elements` — null elements → 200, null fields in JSON
- [x] Run tests — expect failures (Red) — 9 failed, 2 passed ✓

## Phase 3: Implementation
- [x] Implement `GET /satellites` router with `group`, `regime`, `limit`, `offset` params
- [x] Implement `GET /satellites/{id}` router returning `SatelliteDetail` or 404
- [x] Add `limit` clamping / validation (max 1000, offset ≥ 0)
- [x] Include `request_id` in Loguru log context for each handler
- [x] Run tests — expect pass (Green) — 11/11 passed ✓
- [x] Refactor if needed (no logic duplication)

## Phase 4: Integration
- [x] Wire router into `backend/app/main.py` (include router, verify prefix) — already wired at `/satellites`
- [x] Confirm `/satellites` and `/satellites/{id}` appear in `GET /openapi.json`
- [x] Run lint: `make local-lint` — all checks passed
- [x] Run full test suite — 250/250 passed (also fixed `test_main.py` StaticPool issue)

## Phase 5: Verification
- [x] All 7 tangible outcomes checked off
- [x] No hardcoded secrets or tokens
- [x] Loguru `request_id` included in handler logs (via `logger.contextualize`)
- [x] No raw ORM objects returned — all responses go through Pydantic schemas
- [x] 404 message matches format: `"Satellite {id} not found"`
- [x] Update `roadmap.md` status: `spec-written` → `done` (after implement + verify pass)
