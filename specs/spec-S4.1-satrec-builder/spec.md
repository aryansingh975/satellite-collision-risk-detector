# Spec S4.1 — Satrec Builder

## Overview
Builds SGP4 satellite records (`Satrec`) from raw TLE line pairs and assembles them into a
vectorized `SatrecArray` for bulk propagation. Each individual record is created via
`Satrec.twoline2rv(line1, line2)` using **WGS-72** gravity constants — the same constants used
when TLEs are generated — so propagated positions are physically consistent with the orbital
elements embedded in the TLE. The `SatrecArray` form enables the vectorized `sgp4` call that
drives the conjunction screening pipeline.

## Dependencies
- S3.3 — TLE field parser (provides validated `line1`/`line2` strings stored byte-for-byte in DB)

## Target Location
`backend/app/services/propagation.py`

---

## Functional Requirements

### FR-1: Build a single `Satrec` from a TLE line pair
- **What**: Given two TLE strings (`line1`, `line2`), return an `sgp4` `Satrec` object initialised
  with WGS-72 gravity constants.
- **Inputs**: `line1: str`, `line2: str` — the raw, byte-for-byte TLE lines as stored in the DB.
- **Outputs**: `sgp4.api.Satrec` — the parsed satellite record ready for propagation.
- **Implementation note**: Call `Satrec.twoline2rv(line1, line2)` (the sgp4 library default is
  WGS-72; do **not** pass `wgs84` or any override that changes gravity constants).
- **Edge cases**:
  - Malformed / wrong-length TLE line → `twoline2rv` raises or returns a record with `error != 0`;
    surface this as a `ValueError` with the catalog number.
  - Lines with a non-zero `satrec.error` after construction → raise `ValueError`.

### FR-2: Build a `SatrecArray` from a list of TLE line pairs
- **What**: Given a sequence of `(line1, line2)` pairs, return an `sgp4.conveniences.SatrecArray`
  suitable for vectorized propagation.
- **Inputs**: `tle_pairs: list[tuple[str, str]]` — ordered list of `(line1, line2)` strings.
- **Outputs**: `sgp4.conveniences.SatrecArray` — stacked array of all records.
- **Implementation note**: Build individual `Satrec` objects (via FR-1) then pass them to
  `SatrecArray.from_satrecs(satrecs)`.
- **Edge cases**:
  - Empty list → return `None` (or raise `ValueError`); document the choice clearly.
  - Any record with `satrec.error != 0` → skip it and log a warning (don't abort the whole batch).
  - Single-element list → must work; `SatrecArray` of one satellite.

### FR-3: WGS-72 gravity constants are used (not WGS-84)
- **What**: The gravity model must be WGS-72 throughout, because TLEs are generated assuming WGS-72.
- **Verification**: Inspect `satrec.whichconst` after construction — it must equal `WGS72` (the
  sgp4 library's `WGS72` constant, value `2`). Tests must assert this.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `build_satrec(line1, line2)` returns an `sgp4.api.Satrec` with
  `satrec.whichconst == WGS72` for valid ISS TLE lines (catalog 25544).
- [ ] **Outcome 2**: `build_satrec_array(tle_pairs)` returns a `SatrecArray` with `len(satrecs)`
  equal to the number of valid pairs supplied.
- [ ] **Outcome 3**: Passing a malformed TLE (wrong line length or bad checksum) to `build_satrec`
  raises `ValueError`.
- [ ] **Outcome 4**: A batch containing one bad TLE among valid ones (via `build_satrec_array`)
  skips the bad record and returns a `SatrecArray` with `len - 1` elements; a warning is logged.
- [ ] **Outcome 5**: An empty list passed to `build_satrec_array` is handled without crashing
  (raises `ValueError` or returns `None`, per documented behaviour).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_build_satrec_returns_satrec**: Pass valid ISS TLE lines → assert return type is
   `Satrec` and `satrec.whichconst == WGS72`.
2. **test_build_satrec_wgs72_constant**: Explicitly assert `satrec.whichconst` equals the library's
   `WGS72` sentinel (not WGS84).
3. **test_build_satrec_malformed_line_raises**: Pass a line1 of wrong length → assert `ValueError`
   is raised.
4. **test_build_satrec_array_valid_batch**: Pass 3 valid TLE pairs → assert result is a
   `SatrecArray` and its length is 3.
5. **test_build_satrec_array_skips_bad_record**: Pass a batch of 3 with one bad pair → assert
   result length is 2 and a warning was logged.
6. **test_build_satrec_array_single_element**: Pass a list with one valid pair → `SatrecArray` of
   length 1 returned without error.
7. **test_build_satrec_array_empty_list**: Pass `[]` → `ValueError` raised (or `None` returned,
   matching documented behaviour).

### Mocking Strategy
- No external HTTP calls in this module — CelesTrak is already cached upstream.
- Use the ISS TLE fixture (catalog 25544) from `conftest.py` as the canonical valid input.
- Use the published SGP4 verification vectors for any propagation-accuracy assertions (kept to
  S4.2 scope here; here just test record construction).
- DB: not needed for this module's unit tests.

### Coverage Expectation
- `build_satrec` and `build_satrec_array` are both 100% covered.
- Both the happy path and every documented edge case have an explicit test.

---

## References
- roadmap.md — Phase 4 row for S4.1, Notes column
- CLAUDE.md — "Use WGS-72 gravity constants in SGP4 (matches how TLEs are generated). Do not switch to WGS-84."
- sgp4 library docs: `Satrec.twoline2rv`, `SatrecArray.from_satrecs`
