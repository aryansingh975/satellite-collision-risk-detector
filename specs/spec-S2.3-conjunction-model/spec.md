# Spec S2.3 — Conjunction ORM Model

## Overview
Adds the `Conjunction` SQLAlchemy ORM model to `backend/app/db/models.py`. Each row
represents a detected close-approach event between two satellites: a primary (sat_a) and
secondary (sat_b), with the time of closest approach (TCA), miss distance, relative
velocity, the screening window start, and when it was computed. An index on `miss_km`
enables fast ranking queries used by the risk dashboard and stats API.

## Dependencies
- S2.1 — SQLAlchemy engine + session (`Base`, `get_db()`)
- S2.2 — `Satellite` ORM model (provides the FK target `satellites.catalog_no`)

## Target Location
`backend/app/db/models.py`

---

## Functional Requirements

### FR-1: Conjunction table columns
- **What**: The `Conjunction` class extends `Base` and declares all required columns.
- **Inputs**: N/A (DDL-level definition)
- **Outputs**: Table `conjunctions` created by `Base.metadata.create_all()`
- **Columns**:
  | Column | Type | Constraints | Description |
  |--------|------|-------------|-------------|
  | `id` | Integer | PK, autoincrement | Surrogate key |
  | `sat_a` | Integer | FK → `satellites.catalog_no`, NOT NULL | Primary satellite NORAD catalog number |
  | `sat_b` | Integer | FK → `satellites.catalog_no`, NOT NULL | Secondary satellite NORAD catalog number |
  | `tca` | DateTime | NOT NULL | Time of closest approach (UTC) |
  | `miss_km` | Float | NOT NULL | Miss distance at TCA (km) |
  | `rel_vel_kms` | Float | NOT NULL | Relative speed at TCA (km/s) |
  | `window_start` | DateTime | NOT NULL | Start of the screening window that produced this event |
  | `computed_at` | DateTime | NOT NULL, default=utcnow | When this record was written |
- **Edge cases**: `sat_a` and `sat_b` must reference existing `Satellite` rows (enforced by FK); rows with unknown catalog numbers must be rejected at DB level.

### FR-2: Index on miss_km
- **What**: A SQLAlchemy `Index` on `miss_km` exists in the model, ensuring range queries (`miss_km <= threshold`) and `ORDER BY miss_km` used by `/stats/risk-ranking` run efficiently.
- **Inputs**: N/A
- **Outputs**: `ix_conjunctions_miss_km` index present after `create_all()`
- **Edge cases**: Index must survive an in-memory SQLite round-trip used in tests.

### FR-3: Relationship back-references (optional but recommended)
- **What**: SQLAlchemy `relationship()` attributes on `Conjunction` pointing to the two
  `Satellite` objects (`satellite_a`, `satellite_b`) so callers can do
  `conj.satellite_a.name` without a second query.
- **Inputs**: N/A
- **Outputs**: `conjunction.satellite_a` / `conjunction.satellite_b` accessible after
  a session load.
- **Edge cases**: `foreign_keys` parameter is required because there are two FKs to the
  same table — omitting it raises `AmbiguousForeignKeysError`.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `Base.metadata.create_all(engine)` creates the `conjunctions` table with all 8 columns (id, sat_a, sat_b, tca, miss_km, rel_vel_kms, window_start, computed_at).
- [ ] **Outcome 2**: `ix_conjunctions_miss_km` index is present in SQLite `sqlite_master` after `create_all`.
- [ ] **Outcome 3**: Inserting a `Conjunction` row with valid FK satellite references succeeds; inserting with a non-existent `sat_a` / `sat_b` raises an `IntegrityError`.
- [ ] **Outcome 4**: `conjunction.satellite_a.name` returns the correct satellite name without an extra query (relationship works).
- [ ] **Outcome 5**: The `Satellite` stub at the bottom of `models.py` (currently `id = Column(Integer, primary_key=True)` only) is fully replaced by the complete model per S2.2.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_conjunction_table_created**: After `create_all`, `conjunctions` appears in `inspect(engine).get_table_names()`.
2. **test_conjunction_columns**: `inspect(engine).get_columns("conjunctions")` returns columns named id, sat_a, sat_b, tca, miss_km, rel_vel_kms, window_start, computed_at.
3. **test_conjunction_miss_km_index**: `ix_conjunctions_miss_km` appears in `inspect(engine).get_indexes("conjunctions")`.
4. **test_insert_conjunction_valid**: Insert two `Satellite` rows then one `Conjunction` row; session commit succeeds; `session.query(Conjunction).count() == 1`.
5. **test_conjunction_fk_enforced**: Insert a `Conjunction` with `sat_a=99999` (no matching satellite) in a WAL-enabled SQLite instance; commit raises `IntegrityError`.
6. **test_conjunction_relationship**: After inserting valid rows and re-querying, `conj.satellite_a.name` equals the name used during insert.
7. **test_computed_at_default**: Insert a `Conjunction` without supplying `computed_at`; the column is populated automatically.

### Mocking Strategy
- Use an **in-memory SQLite** engine (`sqlite:///:memory:`) created fresh per test via the `conftest.py` pattern already established.
- No external HTTP; no CelesTrak calls.
- Fixtures: two minimal `Satellite` rows (catalog_no 25544 "ISS" and 20580 "HST") used by all FK tests.
- Enable SQLite FK enforcement per connection: `PRAGMA foreign_keys = ON` (SQLite disables them by default).

### Coverage Expectation
- All 8 columns, the index, both FK paths, and the `computed_at` default are exercised.

---

## References
- roadmap.md row S2.3, Notes column; CLAUDE.md §Orbital Mechanics Constants; SQLAlchemy docs on `relationship(foreign_keys=...)` for self-referential or multi-FK scenarios.
