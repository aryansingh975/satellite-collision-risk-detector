# Spec S2.2 — Satellite ORM Model

## Overview
Defines the `Satellite` SQLAlchemy ORM model that persists parsed TLE records to the SQLite database.
Each row represents one satellite (or debris object) identified by its NORAD catalog number. The model
stores the raw TLE lines byte-for-byte so satellites can be re-propagated deterministically at any time,
plus the derived orbital elements used by the classification and conjunction engines.

## Dependencies
- S2.1 — SQLAlchemy engine + session (`Base`, `engine`, `SessionLocal` from `backend/app/db/database.py`)

## Target Location
`backend/app/db/models.py`

---

## Functional Requirements

### FR-1: Satellite table definition
- **What**: A SQLAlchemy `DeclarativeBase` model class `Satellite` mapped to the `satellites` table.
- **Inputs**: Constructed by ingestion code (`ingestion.py` / `seed.py`) with data from the TLE parser.
- **Outputs**: ORM object readable via `SessionLocal`; table auto-created by `Base.metadata.create_all`.
- **Columns**:
  | Column | Type | Constraints | Notes |
  |--------|------|-------------|-------|
  | `catalog_no` | `Integer` | Primary key | NORAD catalog number (5-digit, ≤99999) |
  | `name` | `String(24)` | Not null | Satellite name from TLE line 0 |
  | `intl_designator` | `String(11)` | Nullable | International designator (COSPAR ID) |
  | `line1` | `String(69)` | Not null | Raw TLE line 1, byte-for-byte |
  | `line2` | `String(69)` | Not null | Raw TLE line 2, byte-for-byte |
  | `epoch` | `DateTime` | Not null | UTC epoch derived from TLE line 1 |
  | `a_km` | `Float` | Nullable | Semi-major axis (km), from `(μ/n_rad²)^(1/3)` |
  | `ecc` | `Float` | Nullable | Eccentricity (dimensionless, 0–1) |
  | `inc_deg` | `Float` | Nullable | Inclination (degrees) |
  | `mean_motion` | `Float` | Nullable | Mean motion (rev/day) |
  | `regime` | `String(8)` | Nullable | `LEO`, `MEO`, `GEO`, or `HEO` |
  | `group_name` | `String(64)` | Nullable | CelesTrak group (e.g. `active`, `stations`) |
  | `updated_at` | `DateTime` | Not null, default `utcnow` | Last upsert timestamp |

### FR-2: Primary key and uniqueness
- **What**: `catalog_no` is the integer primary key. There must be exactly one row per satellite.
- **Inputs**: Same `catalog_no` supplied by the TLE parser on repeated ingestion runs.
- **Outputs**: Upsert semantics (insert or update) when called from ingestion; no duplicate rows.
- **Edge cases**: Two TLEs with the same catalog number in one feed → only one row retained.

### FR-3: Raw TLE storage
- **What**: `line1` and `line2` stored as 69-character strings, exactly as received from CelesTrak.
- **Inputs**: Raw text lines from the TLE file, no stripping or normalisation beyond trailing newline.
- **Outputs**: Re-propagating from the stored lines produces the same orbit as propagating from the original.
- **Edge cases**: Line shorter or longer than 69 chars → ingestion layer (S3.3/S3.4) rejects before reaching here.

### FR-4: Table creation via `Base.metadata.create_all`
- **What**: Importing `models.py` registers `Satellite` on `Base`; calling `Base.metadata.create_all(engine)` creates the `satellites` table.
- **Inputs**: The shared `Base` from `database.py`.
- **Outputs**: SQLite file contains the `satellites` table with all columns and the PK index.
- **Edge cases**: Called on an existing database → idempotent (no error, no data loss).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `Base.metadata.create_all(engine)` with an in-memory SQLite engine creates a `satellites` table containing all 13 specified columns.
- [ ] **Outcome 2**: Inserting two `Satellite` objects with the same `catalog_no` in separate sessions raises an `IntegrityError` (proving the PK constraint works).
- [ ] **Outcome 3**: A `Satellite` row can be round-tripped: inserted then queried by `catalog_no`, and all fields match the inserted values.
- [ ] **Outcome 4**: `line1` and `line2` are stored and retrieved without any modification (byte-for-byte equality).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_satellite_table_created**: After `create_all`, inspect `engine.dialect.get_columns(conn, "satellites")` — assert all 13 columns exist with correct types.
2. **test_satellite_insert_and_query**: Insert a `Satellite` with known field values; query by PK; assert every field matches.
3. **test_satellite_pk_uniqueness**: Insert two `Satellite` rows with the same `catalog_no`; assert `IntegrityError` is raised on the second insert within the same session.
4. **test_tle_lines_stored_verbatim**: Insert a satellite using a known ISS TLE (catalog 25544); retrieve and assert `line1` and `line2` are byte-for-byte equal to the input strings.
5. **test_updated_at_defaults_to_now**: Insert a `Satellite` without setting `updated_at`; assert the value is not `None` and is close to `datetime.utcnow()`.
6. **test_nullable_derived_fields**: Insert a `Satellite` with `a_km=None`, `ecc=None`, `regime=None`; assert the row is accepted and those fields read back as `None`.

### Mocking Strategy
- Use an **in-memory SQLite** engine (`create_engine("sqlite:///:memory:")`) — do not touch the file-based DB.
- `conftest.py` creates the engine, calls `create_all`, yields a `SessionLocal`, and drops tables in teardown.
- No external HTTP calls needed; this spec is purely about the ORM schema.

### Coverage Expectation
- All 6 tests above cover: column existence, full round-trip, PK constraint, raw TLE fidelity, default timestamp, nullable optional fields.

---

## References
- `roadmap.md` — Phase 2 table, S2.2 row and Notes
- `CLAUDE.md` — WGS-72 constants, TEME frame convention, no hardcoded secrets, `catalog_no` uniqueness
- S2.1 spec — `Base`, `engine`, `SessionLocal` contract
