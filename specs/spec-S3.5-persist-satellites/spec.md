# Spec S3.5 — Persist Satellites

## Overview
After TLE records are fetched and parsed, they must be durably stored in the SQLite Satellite table so that downstream phases (propagation, classification, conjunction screening) can operate entirely from the local database without re-fetching from CelesTrak. This spec covers the upsert logic that maps parsed TLE data to `Satellite` ORM rows, deduplicates on `catalog_no`, and stores the raw `line1`/`line2` strings byte-for-byte to guarantee deterministic re-propagation at any later point.

## Dependencies
- **S3.3** — TLE field parser (produces the parsed dict that is the input here)
- **S2.2** — Satellite ORM model (defines the table schema this spec writes to)

## Target Location
`backend/app/services/ingestion.py`

---

## Functional Requirements

### FR-1: Upsert parsed satellite records
- **What**: Accept a list of parsed satellite dicts (output of S3.3 `parse_tle`) and write each one to the `Satellite` table using an upsert (insert-or-replace / ON CONFLICT DO UPDATE) keyed on `catalog_no`.
- **Inputs**: `db: Session`, `records: list[dict]` — each dict contains at minimum `catalog_no`, `name`, `intl_designator`, `epoch`, `line1`, `line2`, `mean_motion`, `ecc`, `inc_deg`, and optionally `a_km`, `regime` (populated by later phases; default `None` here).
- **Outputs**: Returns `(inserted: int, updated: int)` counts. Commits the session before returning.
- **Edge cases**:
  - Empty `records` list → commit nothing, return `(0, 0)`.
  - Duplicate `catalog_no` within the same batch → last record wins (or de-dupe before bulk insert — document the chosen behaviour).
  - DB write failure → let the exception propagate; caller handles rollback.

### FR-2: Preserve raw TLE lines byte-for-byte
- **What**: The `line1` and `line2` columns must store the original 69-character TLE strings exactly as received from CelesTrak — no stripping of trailing spaces, no re-formatting.
- **Why**: SGP4 re-propagation must be deterministic; any character mutation could shift the parsed mean-motion or BSTAR and silently corrupt future position predictions.
- **Inputs**: The raw line strings from the parsed record dict.
- **Outputs**: Stored verbatim in the `Satellite.line1` / `Satellite.line2` columns.
- **Edge cases**: Lines that are exactly 69 characters (S3.4 already rejects ≠ 69 lines, so this is a post-validation guarantee).

### FR-3: Deduplicate by catalog_no
- **What**: If a satellite with the same `catalog_no` already exists in the table, update all mutable columns (`name`, `intl_designator`, `epoch`, `line1`, `line2`, `mean_motion`, `ecc`, `inc_deg`, `updated_at`) rather than inserting a duplicate row.
- **Inputs**: Existing rows in `Satellite` table, incoming parsed records.
- **Outputs**: No duplicate rows; `updated_at` is refreshed on every upsert.
- **Edge cases**: First-ever run (table empty) → all rows are inserts. Subsequent runs with unchanged data → rows are updated with the same values (idempotent).

### FR-4: Batch persistence (performance)
- **What**: Use a bulk upsert (SQLAlchemy `insert(...).on_conflict_do_update(...)` for SQLite, or equivalent) rather than issuing one query per record to keep the seed/refresh cycle fast.
- **Inputs**: Full `records` list in a single transaction.
- **Outputs**: All records committed in one transaction; partial writes do not persist on failure.
- **Edge cases**: Very large batches (thousands of active satellites) must not cause memory issues — process in one pass without loading existing rows into Python memory.

---

## Tangible Outcomes

- [ ] **Outcome 1**: Calling `persist_satellites(db, records)` with a list of 3 parsed records inserts 3 rows into an empty Satellite table and returns `(3, 0)`.
- [ ] **Outcome 2**: Calling `persist_satellites(db, records)` a second time with the same records (same `catalog_no` values) updates the existing rows without creating duplicates; total row count remains 3.
- [ ] **Outcome 3**: The stored `line1` and `line2` values are byte-for-byte identical to the input strings (no whitespace stripping or reformatting).
- [ ] **Outcome 4**: Calling with an empty list returns `(0, 0)` and does not touch the DB.
- [ ] **Outcome 5**: After a upsert on an existing row, `updated_at` is more recent than the value from the initial insert.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_persist_satellites_inserts_new_rows**: Given 3 parsed records and an empty DB, `persist_satellites` returns `(3, 0)` and the table contains 3 rows with matching `catalog_no` values.
2. **test_persist_satellites_upserts_on_conflict**: Insert the same 3 records twice; second call should update (not duplicate); `db.query(Satellite).count()` == 3 after both calls.
3. **test_persist_satellites_line_bytes_preserved**: The `line1`/`line2` stored in the DB match the input strings character-for-character (use a known 69-char ISS TLE line as fixture).
4. **test_persist_satellites_empty_list**: `persist_satellites(db, [])` returns `(0, 0)` and issues no DB writes.
5. **test_persist_satellites_updated_at_refreshed**: After an initial persist and a subsequent upsert of the same record, the `updated_at` timestamp on the row is ≥ the first `updated_at`.
6. **test_persist_satellites_dedupes_within_batch**: Pass a batch containing the same `catalog_no` twice; only one row exists in the DB after the call.

### Mocking Strategy
- Use the **in-memory SQLite** test DB configured in `conftest.py` (no mocking of the DB layer itself).
- Do **not** hit CelesTrak — tests construct `records` dicts directly (no HTTP calls).
- Use the ISS TLE fixture (catalog 25544) defined in `conftest.py` as the canonical test record.
- `updated_at` assertions: freeze time via `freezegun` or monkeypatch `datetime.utcnow` if needed.

### Coverage Expectation
- All public functions (`persist_satellites`) have tests for the happy path, the upsert path, the empty-input path, and the byte-preservation invariant.

---

## References
- `roadmap.md` — Phase 3 table, S3.5 row; Master Spec Index
- `CLAUDE.md` — "Persist TLE line1/line2 byte-for-byte so satellites can be re-propagated deterministically"
- `backend/app/db/models.py` — `Satellite` ORM model (S2.2)
- `backend/app/services/tle_parser.py` — parser output format (S3.3)
