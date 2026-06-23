# Spec S6.4 — Conjunctions Endpoints

## Overview
Exposes the stored conjunction events via two REST endpoints backed by the Conjunction ORM table
(S2.3). `GET /conjunctions` returns a filtered, ranked list of close-approach events;
`GET /conjunctions/{pair_id}` returns one event by its database id. Both endpoints join the
Satellite table to populate `sat_a_name` / `sat_b_name` (not stored on the Conjunction row).
An empty result set returns `[]`, never an error. Query parameters allow the caller to narrow
results by miss-distance threshold and look-ahead time window.

## Dependencies
- **S5.5** — Risk scoring + persist: populates the Conjunction table this endpoint reads.
- **S2.4** — All Pydantic schemas: `ConjunctionOut` is the response shape.

## Target Location
`backend/app/api/conjunctions.py`

---

## Functional Requirements

### FR-1: `GET /conjunctions` — list with optional filters
- **What**: Return all conjunction events ordered by `miss_km` ascending (closest first).
  Optionally filter by `threshold` (miss distance cap) and `window` (TCA look-ahead hours).
- **Inputs**:
  - `threshold: float` (query, optional, default = `settings.RISK_THRESHOLD_KM` = 5.0) —
    include only rows where `miss_km ≤ threshold`.
  - `window: float` (query, optional, default = `settings.SCREEN_WINDOW_HOURS`) — include only
    rows where `tca ≤ datetime.utcnow() + timedelta(hours=window)`. A value of 0 disables the
    window filter (return all time ranges).
  - `limit: int` (query, optional, default = 100, max = 500) — cap the result list.
- **Outputs**: `list[ConjunctionOut]` (HTTP 200). Empty list when no rows match — **not** a 4xx.
- **Join**: Each `ConjunctionOut` requires `sat_a_name` and `sat_b_name`. Join
  `Satellite` twice (aliased) on `sat_a` / `sat_b` foreign keys.
- **Edge cases**:
  - No conjunctions in DB → `[]`.
  - `threshold=0` → empty list (no event has miss_km ≤ 0).
  - `window` negative → treat as 0 (no window filter, return all).
  - `limit` > 500 → clamp to 500.

### FR-2: `GET /conjunctions/{pair_id}` — single event by id
- **What**: Return one conjunction event by its integer primary key.
- **Inputs**: `pair_id: int` (path).
- **Outputs**: `ConjunctionOut` (HTTP 200) or HTTP 404 `{"detail": "Conjunction not found"}`.
- **Join**: Same satellite-name join as FR-1.
- **Edge cases**: Non-existent id → 404 (never 500).

### FR-3: Satellite name join
- **What**: The `Conjunction` ORM row has `sat_a` / `sat_b` (catalog numbers, FKs to
  `satellites.catalog_no`) and exposes `relationship("Satellite", ...)` as `satellite_a` /
  `satellite_b`. Use these relationships (or an explicit join) to obtain `.name` for each party.
- **Constraint**: `ConjunctionOut.sat_a_name` and `sat_b_name` must be populated on every
  response row — never `None` or empty string when the FK is valid.

### FR-4: Response serialization via `ConjunctionOut`
- **What**: Convert each ORM row to `ConjunctionOut` before returning.
- **Note**: `ConjunctionOut` does **not** carry `model_config = ConfigDict(from_attributes=True)`
  in schemas.py, so construct it explicitly (e.g. `ConjunctionOut(id=row.id, sat_a=row.sat_a,
  sat_a_name=row.satellite_a.name, ...)`).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /conjunctions` returns HTTP 200 with `[]` when the DB is empty.
- [ ] **Outcome 2**: `GET /conjunctions` with seeded rows returns them ordered by `miss_km`
      ascending, each item matching `ConjunctionOut` schema.
- [ ] **Outcome 3**: `threshold` query param correctly caps results to rows where
      `miss_km ≤ threshold`.
- [ ] **Outcome 4**: `window` query param excludes conjunctions whose `tca` is beyond
      `utcnow() + timedelta(hours=window)`.
- [ ] **Outcome 5**: `GET /conjunctions/{pair_id}` returns the correct event for a valid id.
- [ ] **Outcome 6**: `GET /conjunctions/{pair_id}` returns HTTP 404 for an unknown id.
- [ ] **Outcome 7**: `sat_a_name` and `sat_b_name` are populated (non-empty) on all returned rows.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_list_conjunctions_empty**: DB empty → `GET /conjunctions` → 200, body `[]`.
2. **test_list_conjunctions_returns_rows**: Seed one Conjunction + two Satellites → list contains
   one item with correct fields (id, sat_a, sat_b, sat_a_name, sat_b_name, miss_km, tca, …).
3. **test_list_conjunctions_ordered_by_miss_km**: Seed two Conjunctions with different miss_km →
   list is ascending by miss_km.
4. **test_list_conjunctions_threshold_filter**: Seed rows with miss_km=2.0 and miss_km=8.0; query
   `?threshold=5` → only the 2.0 row returned.
5. **test_list_conjunctions_window_filter**: Seed a Conjunction with `tca` far in the future;
   query `?window=1` → excluded. Query `?window=0` → included (window=0 disables filter).
6. **test_list_conjunctions_limit**: Seed 10 rows; query `?limit=3` → exactly 3 items.
7. **test_get_conjunction_by_id**: Seed one Conjunction → `GET /conjunctions/{id}` → 200, correct
   body including sat names.
8. **test_get_conjunction_not_found**: `GET /conjunctions/99999` → 404.

### Mocking Strategy
- DB: in-memory SQLite via `conftest.py`'s `TestingSessionLocal` + test `client` fixture.
- No external HTTP calls needed — this endpoint only reads the local DB.
- Seed ORM objects directly via the test session (insert `Satellite` rows first, then
  `Conjunction` rows to satisfy FK constraints).

### Coverage Expectation
- All 8 tests above pass. Both FR-1 filter paths (threshold + window) independently covered.
  The 404 path covered by test 8.

---

## References
- `roadmap.md` S6.4 row and Phase 6 table — endpoint paths, filter params, empty-result rule.
- `CLAUDE.md` — no hardcoded secrets; `request_id` in log context; Pydantic schemas for all I/O.
- `backend/app/models/schemas.py` — `ConjunctionOut` definition (sat_a_name, sat_b_name included).
- `backend/app/db/models.py` — `Conjunction` ORM model; `satellite_a` / `satellite_b`
  relationships.
- `backend/app/core/config.py` — `RISK_THRESHOLD_KM` (5) and `SCREEN_WINDOW_HOURS` defaults.
