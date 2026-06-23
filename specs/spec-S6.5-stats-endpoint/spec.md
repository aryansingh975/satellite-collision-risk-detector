# Spec S6.5 — Stats Endpoints

## Overview
Implements two read-only stats endpoints over the already-populated SQLite database:
`GET /stats/orbital-regions` returns satellite counts bucketed by regime (LEO/MEO/GEO/HEO)
with a validated total, and `GET /stats/risk-ranking` returns the top-N conjunction events
ordered by miss distance ascending (closest first), with 1-based rank assigned server-side.
Both endpoints read from tables written by S4.6 (regime classification) and S5.5 (risk scoring).
They feed the frontend dashboard (S9.1, S9.3) and are part of the frozen API contract from S2.5.

## Dependencies
- S4.6 — Regime classification (populates `Satellite.regime` column)
- S5.5 — Risk scoring + persist (populates `Conjunction` table)

## Target Location
`backend/app/api/stats.py`

---

## Functional Requirements

### FR-1: `GET /stats/orbital-regions`
- **What**: Return satellite counts per regime and a validated total.
- **Inputs**: No query parameters. Reads `Satellite.regime` from the DB.
- **Outputs**: `OrbitalRegionStats` — `{leo, meo, geo, heo, total}` where
  `total == leo + meo + geo + heo`. Satellites with `regime IS NULL` are excluded
  from all counts. Response is always a single JSON object, never a list.
- **Edge cases**:
  - Empty DB (no satellites) → all counts 0, total 0.
  - All satellites have `regime = NULL` → all counts 0, total 0.
  - Unknown regime string (not one of LEO/MEO/GEO/HEO) → excluded silently.

### FR-2: `GET /stats/risk-ranking`
- **What**: Return top-N conjunction events ranked by miss distance (ascending).
- **Inputs**: Optional query param `limit: int` (default 10, min 1, max 100).
  Reads `Conjunction` table joined with `Satellite` for both names.
- **Outputs**: `list[RiskRankingItem]` — each item has `{rank, sat_a, sat_b,
  sat_a_name, sat_b_name, miss_km, rel_vel_kms, tca}`. `rank` is 1-based
  and computed server-side (not stored). List is ordered by `miss_km ASC`,
  tie-broken by `rel_vel_kms DESC` (faster closing = higher risk).
- **Edge cases**:
  - No conjunctions in DB → return `[]` (empty list), not an error.
  - `limit` < 1 → 422 Unprocessable Entity (Pydantic/FastAPI validation).
  - `limit` > 100 → 422 Unprocessable Entity.
  - `limit` larger than number of events → return all events (no error).

### FR-3: Router wiring
- **What**: The `router` from `stats.py` must be mounted at `/stats` prefix in `main.py`
  so that endpoint paths resolve as `/stats/orbital-regions` and `/stats/risk-ranking`.
- **Inputs**: Existing `main.py` lifespan; `include_router` call.
- **Outputs**: Both routes appear in `GET /openapi.json`.
- **Edge cases**: Router is already stub-mounted — replace stub implementation,
  do not add a duplicate `include_router` call.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /stats/orbital-regions` returns `{"leo":…,"meo":…,"geo":…,"heo":…,"total":…}` where total equals the sum of the four regime counts.
- [ ] **Outcome 2**: With an empty DB, `GET /stats/orbital-regions` returns all zeros.
- [ ] **Outcome 3**: `GET /stats/risk-ranking` returns a JSON array sorted by `miss_km` ascending with correct 1-based `rank` values.
- [ ] **Outcome 4**: `GET /stats/risk-ranking` returns `[]` when the Conjunction table is empty.
- [ ] **Outcome 5**: `GET /stats/risk-ranking?limit=3` returns at most 3 items.
- [ ] **Outcome 6**: `GET /stats/risk-ranking?limit=0` returns HTTP 422.
- [ ] **Outcome 7**: Both endpoints appear in `GET /openapi.json` under `/stats/…`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_orbital_regions_empty_db**: Seed DB with no satellites → expect `{leo:0, meo:0, geo:0, heo:0, total:0}`.
2. **test_orbital_regions_counts**: Insert satellites with known regimes → verify each bucket count and total.
3. **test_orbital_regions_null_regime_excluded**: Insert satellites with `regime=None` → they must not appear in any bucket or total.
4. **test_orbital_regions_unknown_regime_excluded**: Insert a satellite with `regime="UNKNOWN"` → excluded from counts.
5. **test_risk_ranking_empty**: No conjunctions → `GET /stats/risk-ranking` returns `[]`.
6. **test_risk_ranking_order**: Insert 3 conjunctions with different `miss_km` → response ordered ascending; `rank` values are 1, 2, 3.
7. **test_risk_ranking_tie_break**: Two conjunctions with same `miss_km` but different `rel_vel_kms` → higher velocity appears first.
8. **test_risk_ranking_limit**: Insert 5 conjunctions → `?limit=2` returns exactly 2 items.
9. **test_risk_ranking_limit_exceeds_count**: `?limit=20` with only 3 conjunctions → returns 3 items.
10. **test_risk_ranking_limit_invalid_zero**: `?limit=0` → HTTP 422.
11. **test_risk_ranking_limit_invalid_over_max**: `?limit=101` → HTTP 422.
12. **test_risk_ranking_names**: Response items contain `sat_a_name` and `sat_b_name` from the Satellite join.

### Mocking Strategy
- DB: in-memory SQLite via `conftest.py` `TestingSessionLocal`; inject via FastAPI
  `app.dependency_overrides[get_db]`.
- No external HTTP calls in these endpoints — no mocking of CelesTrak needed.
- Seed test data directly via SQLAlchemy ORM inserts in each test or a fixture.

### Coverage Expectation
- All public functions/endpoints have at least one test; all edge cases above covered.

---

## References
- `roadmap.md` — S6.5 row (Phase 6 table + Master Spec Index)
- `CLAUDE.md` — project rules, ORM model column names, Pydantic schema definitions
- `backend/app/models/schemas.py` — `OrbitalRegionStats`, `RiskRankingItem` already defined
- `backend/app/db/models.py` — `Satellite.regime`, `Conjunction` table structure
