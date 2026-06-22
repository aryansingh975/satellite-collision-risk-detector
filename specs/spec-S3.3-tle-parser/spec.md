# Spec S3.3 — TLE Field Parser

## Overview
`tle_parser.py` decodes raw Two-Line Element set strings into structured Python objects ready for
persistence and propagation. It extracts every field from TLE line 1 and line 2: catalog number,
international designator, epoch (2-digit year + day-of-year fraction → UTC datetime), inclination,
RAAN, eccentricity (implied leading decimal), argument of perigee, mean anomaly, mean motion, and
BSTAR drag term (compressed exponent notation, e.g. `35580-4` → 0.0000356). The raw line 1/line 2
strings are passed through untouched so satellites can be re-propagated deterministically.

## Dependencies
- S3.2 (TLE cache — provides raw TLE text to parse)

## Target Location
`backend/app/services/tle_parser.py`

---

## Functional Requirements

### FR-1: Parse TLE line 1 fields
- **What**: Extract all named fields from a TLE line 1 string.
- **Inputs**: `line1: str` — exactly 69 characters (or raises); must start with `'1'`.
- **Outputs**: Dataclass/dict with:
  - `catalog_no: int` — columns 3–7 (strip leading zeros)
  - `classification: str` — column 8 (`'U'`, `'S'`, `'C'`)
  - `intl_designator: str` — columns 10–17 (stripped)
  - `epoch_year: int` — columns 19–20 (2-digit; see FR-3 for year resolution)
  - `epoch_day: float` — columns 21–32 (day-of-year + fractional day)
  - `mean_motion_dot: float` — columns 34–43 (first derivative of mean motion / 2)
  - `mean_motion_ddot: float` — columns 45–52 (second derivative, decimal-point-free notation)
  - `bstar: float` — columns 54–61 (drag term, decimal-point-free notation; see FR-4)
  - `element_set_no: int` — columns 65–68
- **Edge cases**: Length ≠ 69 → `TLEParseError`; wrong line number → `TLEParseError`

### FR-2: Parse TLE line 2 fields
- **What**: Extract all named fields from a TLE line 2 string.
- **Inputs**: `line2: str` — exactly 69 characters; must start with `'2'`.
- **Outputs**: Dataclass/dict with:
  - `catalog_no: int` — columns 3–7 (must match line 1)
  - `inc_deg: float` — columns 9–16 (degrees)
  - `raan_deg: float` — columns 18–25 (degrees)
  - `ecc: float` — columns 27–33 (implied decimal: `0.` prepended, e.g. `0013716` → `0.0013716`)
  - `arg_perigee_deg: float` — columns 35–42 (degrees)
  - `mean_anomaly_deg: float` — columns 44–51 (degrees)
  - `mean_motion: float` — columns 53–63 (rev/day)
  - `rev_at_epoch: int` — columns 64–68
- **Edge cases**: Length ≠ 69 → `TLEParseError`; `catalog_no` mismatch between lines → `TLEParseError`

### FR-3: Epoch 2-digit year → UTC datetime
- **What**: Convert `epoch_year` (2-digit) + `epoch_day` (day-of-year fraction) to a Python `datetime` in UTC.
- **Rule**: Year ≥ 57 → 1900s (e.g. 57 → 1957); year < 57 → 2000s (e.g. 24 → 2024). This matches
  the TLE standard (Sputnik 1 was 1957; no active satellite has epoch before 2000 with year < 57).
- **Inputs**: `epoch_year: int`, `epoch_day: float`
- **Outputs**: `datetime` (UTC, timezone-aware)
- **Formula**: `date = Jan 1 of resolved_year + timedelta(days=epoch_day - 1)`
- **Edge cases**: `epoch_day` ≥ 366 on a non-leap year → propagate naturally (timedelta handles rollover)

### FR-4: BSTAR / mean_motion_ddot decimal-point-free notation
- **What**: Decode NASA/NORAD's compressed exponent notation used for BSTAR and mean_motion_ddot.
- **Format**: `±NNNNN±E` where the mantissa has an implied leading `0.` and `±E` is the signed exponent.
  Example: ` 35580-4` → mantissa `0.35580`, exponent `-4` → `0.35580e-4 = 3.558e-5`.
  Negative mantissa example: `-11606-4` → `-0.11606e-4`.
  Zero: `00000-0` → `0.0`.
- **Inputs**: raw 8-char field string
- **Outputs**: `float`
- **Edge cases**: all-zero field → `0.0`; signs on both mantissa and exponent handled correctly

### FR-5: Top-level `parse_tle(line1, line2)` function
- **What**: Single entry-point that validates both lines and returns a unified parsed record.
- **Inputs**: `line1: str`, `line2: str`
- **Outputs**: `TLERecord` (dataclass or TypedDict) combining all fields from FR-1, FR-2, FR-3, FR-4, plus:
  - `epoch: datetime` (UTC) — computed per FR-3
  - `line1: str`, `line2: str` — raw, byte-for-byte (for deterministic re-propagation)
- **Edge cases**: Checksum is checked in S3.4; `parse_tle` should be composable with the checksum validator but does not duplicate that logic itself.

### FR-6: Custom exception `TLEParseError`
- **What**: All parse failures raise `TLEParseError(message)` — a named, importable exception subclassing `ValueError`.
- **Inputs**: invalid field value, wrong length, line number mismatch, malformed exponent string
- **Outputs**: `TLEParseError` with a descriptive message identifying which field/line failed

---

## Tangible Outcomes

- [ ] **Outcome 1**: `parse_tle(ISS_LINE1, ISS_LINE2)` returns a `TLERecord` with `catalog_no=25544`, `epoch` a UTC-aware datetime, `ecc≈0.0001486`, `mean_motion≈15.49` rev/day.
- [ ] **Outcome 2**: BSTAR field `' 35580-4'` decodes to `3.558e-5` (within floating-point tolerance).
- [ ] **Outcome 3**: Eccentricity field `'0013716'` decodes to `0.0013716`.
- [ ] **Outcome 4**: Epoch `year=24, day=123.456` resolves to a 2024 UTC datetime within seconds of the expected value.
- [ ] **Outcome 5**: `parse_tle` with a 68-char line raises `TLEParseError`.
- [ ] **Outcome 6**: `parse_tle` with mismatched catalog numbers on line1/line2 raises `TLEParseError`.
- [ ] **Outcome 7**: `raw line1` and `raw line2` are preserved byte-for-byte in `TLERecord`.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_parse_tle_iss_catalog_no**: ISS fixture → `catalog_no == 25544`
2. **test_parse_tle_iss_ecc**: ISS fixture → `ecc` matches known value within 1e-7
3. **test_parse_tle_iss_mean_motion**: ISS fixture → `mean_motion` matches to 4 decimal places
4. **test_parse_tle_epoch_year_2digit_ge57**: `epoch_year=57` → year 1957
5. **test_parse_tle_epoch_year_2digit_lt57**: `epoch_year=24` → year 2024
6. **test_parse_tle_epoch_day_to_datetime**: known day-of-year fraction → expected UTC datetime
7. **test_bstar_decode_positive**: `' 35580-4'` → `pytest.approx(3.558e-5, rel=1e-4)`
8. **test_bstar_decode_negative**: `'-11606-4'` → negative float
9. **test_bstar_decode_zero**: `' 00000-0'` → `0.0`
10. **test_ecc_implied_decimal**: `'0013716'` → `0.0013716`
11. **test_parse_tle_line_too_short**: 68-char line1 → `TLEParseError`
12. **test_parse_tle_wrong_line_number**: line starting with `'3'` → `TLEParseError`
13. **test_parse_tle_catalog_mismatch**: mismatched catalog numbers → `TLEParseError`
14. **test_raw_lines_preserved**: `TLERecord.line1` and `.line2` equal the input strings exactly

### Mocking Strategy
- No external I/O in `tle_parser.py` — pure string parsing, no mocking needed.
- Use hardcoded ISS TLE strings as fixtures (catalog 25544, a published TLE from the SGP4 verification set).
- Cross-check epoch and orbital elements against known published values.

### Coverage Expectation
- All public functions (`parse_tle`, `_decode_bstar`, epoch helper) have tests; every edge case in FR-1 through FR-6 is covered.

---

## References
- roadmap.md (S3.3 row + Notes), CLAUDE.md (project rules, WGS-72 note, TEME frame convention)
- TLE format reference: CelesTrak "FAQs: Two-Line Element Set Format" (columns, exponent notation)
- SGP4 verification vectors: Vallado et al. (2006) for known ISS epoch/elements
