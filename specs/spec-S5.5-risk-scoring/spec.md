# Spec S5.5 — Risk Scoring + Persist

## Overview
After TCA refinement (S5.4) produces a list of `TCARefinement` results — each carrying a satellite
pair, TCA timestamp, miss distance, and relative velocity — this spec applies the risk filter,
ranks survivors, and persists them to the Conjunction table. Only events with
`miss_km ≤ RISK_THRESHOLD_KM` (default 5 km, matching CelesTrak SOCRATES) are kept. Survivors are
ranked by ascending `miss_km`; ties broken by descending `rel_vel_kms` (higher closing speed = more
energetic encounter at the same miss distance). Persistence is idempotent: all prior Conjunction
records for the same `window_start` are replaced before inserting the new ranked set, so re-running
the screen for the same window never accumulates duplicates.

**Important framing**: this tool reports *potential close approaches* (miss distance). There is no
covariance in TLEs, so collision probability is not computed and must not be stated.

## Dependencies
- S5.4 (TCA refinement & miss distance) — must be `done`
- S2.3 (Conjunction ORM model) — must be `done`

## Target Location
`backend/app/services/conjunctions.py`

---

## Functional Requirements

### FR-1: Filter by risk threshold
- **What**: Accept the list of `TCARefinement | None` from `refine_tca`; discard `None` entries
  (propagation failures from S5.4) and discard any refinement whose `miss_km > RISK_THRESHOLD_KM`.
- **Inputs**: `refinements: list[TCARefinement | None]`, `risk_threshold_km: float`
  (typically `settings.RISK_THRESHOLD_KM = 5.0`).
- **Outputs**: `list[TCARefinement]` — only events where `miss_km ≤ risk_threshold_km`.
- **Edge cases**:
  - All entries are `None` → return empty list immediately, no DB write.
  - No entry passes the threshold → return empty list; persist call later clears old records and
    writes nothing.
  - `risk_threshold_km ≤ 0` → return empty list (no event can have negative miss distance).

### FR-2: Rank by miss distance (tie-break: relative velocity)
- **What**: Sort the filtered results ascending by `miss_km`; within equal `miss_km` values sort
  descending by `rel_vel_kms` (more energetic encounter ranks higher risk).
- **Inputs**: Filtered `list[TCARefinement]` from FR-1.
- **Outputs**: Same list, re-ordered.
- **Edge cases**:
  - Single element → returned as-is (sort is a no-op).
  - All `miss_km` identical → ordering by `rel_vel_kms` descending determines rank.

### FR-3: Map satellite indices to catalog numbers
- **What**: `sat_a_idx` and `sat_b_idx` in `TCARefinement` are positional indices into the Satrec
  list used during the screen. Before persisting, map each index to the corresponding NORAD catalog
  number (integer) using a `catalog_nos: list[int]` lookup passed by the caller.
- **Inputs**: `catalog_nos: list[int]` (same length and ordering as the `satrec_list` from S5.4).
- **Outputs**: `(catalog_no_a, catalog_no_b)` integer pairs, with `catalog_no_a < catalog_no_b`
  (canonical ordering mirrors the (i < j) invariant from S5.1).
- **Edge cases**:
  - Index out of range for `catalog_nos` → raise `IndexError` immediately (contract violation by
    the caller; do not silently skip).

### FR-4: Idempotent persist to Conjunction table
- **What**: Within a single DB transaction, delete all existing `Conjunction` rows where
  `window_start == window_start_dt`, then bulk-insert the ranked list from FR-2. The
  `window_start` column is the idempotency key — re-running the screen for the same window always
  produces an identical result set.
- **Inputs**: `db: Session` (SQLAlchemy), `ranked: list[TCARefinement]`,
  `catalog_nos: list[int]`, `window_start_dt: datetime`.
- **Outputs**: `list[Conjunction]` — the newly created ORM instances (flushed but the caller
  controls commit).
- **Edge cases**:
  - `ranked` is empty → delete old records for the window, insert nothing, return `[]`.
  - `window_start_dt` is timezone-aware UTC → strip tzinfo before storing (SQLite stores naive
    datetimes; the column type is `DateTime` without timezone).
  - FK violation (`sat_a` / `sat_b` not in `satellites` table) → let SQLAlchemy propagate the
    `IntegrityError`; do not swallow it. Caller is responsible for ensuring satellites are persisted
    before calling this function.
  - `computed_at` set to `datetime.utcnow()` at insert time (not re-used from a previous run).

### FR-5: Public orchestration function
- **What**: `score_and_persist(refinements, catalog_nos, window_start_dt, risk_threshold_km, db)`
  composes FR-1 → FR-2 → FR-3 → FR-4 in order and returns the persisted `list[Conjunction]`.
  This is the single entry point called by S6.6 (scheduler) and S10.1 (seed script).
- **Inputs**: As above across FR-1…FR-4.
- **Outputs**: `list[Conjunction]` (same as FR-4).
- **Edge cases**: Inherits all edge cases from FR-1…FR-4 (empty input, threshold = 0, etc.).

---

## Tangible Outcomes

- [ ] **Outcome 1**: Given 3 `TCARefinement` results with miss distances `[2.1, 4.9, 6.0]` km and
  `RISK_THRESHOLD_KM=5.0`, `score_and_persist` persists exactly 2 Conjunction rows
  (`miss_km` 2.1 and 4.9) and returns them ordered by `miss_km` ascending.
- [ ] **Outcome 2**: Calling `score_and_persist` twice for the same `window_start_dt` results in
  exactly the same row count (idempotency) — no duplicate Conjunction records accumulate.
- [ ] **Outcome 3**: When all refinements are `None` or all miss distances exceed the threshold,
  `score_and_persist` returns `[]` and the Conjunction table is empty for that `window_start`.
- [ ] **Outcome 4**: Two events with identical `miss_km` are ordered so the one with higher
  `rel_vel_kms` appears first (lower index in the returned list).
- [ ] **Outcome 5**: The `tca` field stored in the DB matches the `tca` datetime from the
  `TCARefinement`, with `tzinfo` stripped (naive UTC).
- [ ] **Outcome 6**: `sat_a` and `sat_b` columns store the NORAD catalog numbers (not positional
  indices), with `sat_a < sat_b` in every row.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_filter_by_threshold**: Provide 4 refinements with `miss_km` values `[1.0, 4.9, 5.0, 5.1]`
   and threshold `5.0`; assert only the events with `miss_km ≤ 5.0` survive (3 events).
2. **test_filter_all_none**: Provide a list of `[None, None]`; assert the returned list is `[]`.
3. **test_rank_by_miss_then_vel**: Provide 3 events with `miss_km = [3.0, 1.5, 3.0]` and
   `rel_vel_kms = [7.0, 5.0, 9.0]`; assert ordering is `[1.5km/5kms, 3.0km/9kms, 3.0km/7kms]`.
4. **test_persist_idempotent**: Using an in-memory SQLite DB with two Satellite rows, call
   `score_and_persist` twice with the same `window_start_dt`; assert `db.query(Conjunction).count()`
   equals the number of events in one call, not doubled.
5. **test_persist_empty_clears_old**: Insert 2 Conjunction rows manually for a `window_start_dt`,
   then call `score_and_persist` with an all-`None` input for the same window; assert the table
   is empty for that window.
6. **test_persist_tca_naive**: Pass a `tca` that is timezone-aware UTC; assert the stored
   `Conjunction.tca` has `tzinfo is None`.
7. **test_persist_catalog_order**: Provide a refinement where `sat_a_idx=5` maps to catalog 40000
   and `sat_b_idx=2` maps to catalog 25544; assert the persisted row has `sat_a=25544`,
   `sat_b=40000` (canonical `sat_a < sat_b`).
8. **test_score_and_persist_full_pipeline**: End-to-end: 2 valid refinements, 1 None, threshold 5 km;
   assert correct count, correct ordering, correct catalog numbers in DB.

### Mocking Strategy
- DB: in-memory SQLite (`sqlite:///:memory:`) with `Base.metadata.create_all(engine)` in setup;
  use a `Session` scoped to each test; dispose engine in teardown (follows project `conftest.py`).
- No CelesTrak HTTP — pure computation + DB test.
- Build `TCARefinement` instances directly in tests (no SGP4 needed for S5.5 unit tests).
- Satellite rows must be pre-inserted (FK constraint) before calling `score_and_persist`.

### Coverage Expectation
- All public functions (`score_and_persist`) and any extracted helpers have at least one test.
- Every edge case in FR-1…FR-4 is exercised by at least one test.

---

## References
- roadmap.md (S5.5 row + Notes), CLAUDE.md (RISK_THRESHOLD_KM=5, SOCRATES calibration, no
  collision-probability claim)
- S5.4 spec — `TCARefinement` dataclass interface
- S2.3 spec — `Conjunction` ORM model (`id`, `sat_a`, `sat_b`, `tca`, `miss_km`, `rel_vel_kms`,
  `window_start`, `computed_at`)
