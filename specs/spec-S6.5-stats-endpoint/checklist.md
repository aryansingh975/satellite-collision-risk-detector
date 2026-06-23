# Checklist — Spec S6.5: Stats Endpoints

## Phase 1: Setup & Dependencies
- [x] Verify S4.6 (regime classification) is `done`
- [x] Verify S5.5 (risk scoring + persist) is `done`
- [x] Confirm `OrbitalRegionStats` and `RiskRankingItem` are defined in `backend/app/models/schemas.py`
- [x] Confirm `Satellite.regime` and `Conjunction` table exist in `backend/app/db/models.py`
- [x] Locate `backend/app/api/stats.py` (stub exists from S1.4)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/api/test_stats.py`
- [x] Write `test_orbital_regions_empty_db` — all zero counts
- [x] Write `test_orbital_regions_counts` — known regime buckets sum correctly
- [x] Write `test_orbital_regions_null_regime_excluded` — NULL regime not counted
- [x] Write `test_orbital_regions_unknown_regime_excluded` — unknown string not counted
- [x] Write `test_risk_ranking_empty` — empty Conjunction table → `[]`
- [x] Write `test_risk_ranking_order` — ascending miss_km, correct 1-based ranks
- [x] Write `test_risk_ranking_tie_break` — same miss_km, higher rel_vel first
- [x] Write `test_risk_ranking_limit` — `?limit=2` caps result to 2
- [x] Write `test_risk_ranking_limit_exceeds_count` — limit > rows → return all rows
- [x] Write `test_risk_ranking_limit_invalid_zero` — `?limit=0` → HTTP 422
- [x] Write `test_risk_ranking_limit_invalid_over_max` — `?limit=101` → HTTP 422
- [x] Write `test_risk_ranking_names` — `sat_a_name` / `sat_b_name` populated from join
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Implement FR-1: `GET /stats/orbital-regions` — GROUP BY regime query, build `OrbitalRegionStats`
- [x] Implement FR-2: `GET /stats/risk-ranking` — ORDER BY miss_km ASC, rel_vel_kms DESC, LIMIT, join Satellite for names, assign rank
- [x] Implement FR-3: Validate `limit` param (1 ≤ limit ≤ 100) via `Query(default=10, ge=1, le=100)`
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (no logic duplication)

## Phase 4: Integration
- [x] Confirm `router` is already included at `/stats` prefix in `backend/app/main.py` (stub already wired from S1.4 — do NOT add a duplicate `include_router`)
- [x] Verify `GET /openapi.json` lists `/stats/orbital-regions` and `/stats/risk-ranking` (confirmed via test_main.py + manual check)
- [x] Run lint: `ruff check + format --check` — passed clean
- [x] Run full test suite: 292/292 passed

## Phase 5: Verification
- [x] All 7 tangible outcomes from spec.md confirmed (covered by 12 passing tests)
- [x] No hardcoded secrets/tokens
- [x] Logging includes `request_id` where applicable — N/A (read-only DB queries; no request_id needed at this layer)
- [x] `total == leo + meo + geo + heo` invariant enforced by `OrbitalRegionStats` model_validator in schemas.py
- [x] `limit` bounds enforced (1–100); out-of-range → 422 via `Query(ge=1, le=100)`
- [x] Empty-table cases return valid empty responses (not errors)
- [x] Update `roadmap.md` status: `spec-written` → `done`
