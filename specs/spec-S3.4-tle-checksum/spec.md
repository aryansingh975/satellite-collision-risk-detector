# Spec S3.4 — TLE Checksum Validation

## Overview
Each TLE line carries a modulo-10 checksum in its last character (position 69). Digits contribute
their face value; minus signs contribute 1; all other characters contribute 0. The sum of the first
68 characters modulo 10 must equal the checksum digit at position 69. Lines that are not exactly
69 characters long or whose checksum does not match must be rejected with a clear, structured parse
error so corrupt or truncated TLEs never reach the propagator.

## Dependencies
- S3.3 (TLE field parser) — checksum validation wraps the same `tle_parser.py` module; parsed
  fields are only returned when both lines pass.

## Target Location
`backend/app/services/tle_parser.py`

---

## Functional Requirements

### FR-1: Line length enforcement
- **What**: Before computing the checksum, verify that each TLE line is exactly 69 characters long.
- **Inputs**: A single TLE line string (line 1 or line 2).
- **Outputs**: Raises `TLEParseError` (a dedicated exception) with a message naming the line number
  and actual length when the condition `len(line) != 69` is true.
- **Edge cases**: Lines with trailing newline stripped before measurement; empty string; line with
  extra spaces; line with 68 or 70 chars.

### FR-2: Modulo-10 checksum computation
- **What**: Sum the contribution of each of the first 68 characters: digit → its int value;
  `-` → 1; everything else → 0. Return `total % 10`.
- **Inputs**: The first 68 characters of a valid-length TLE line.
- **Outputs**: An integer 0–9 representing the computed checksum.
- **Edge cases**: Line containing only spaces/letters (sum = 0, checksum = 0); line with all
  nines (sum = 9×n, checksum = sum%10).

### FR-3: Checksum digit comparison
- **What**: Compare the computed checksum from FR-2 against `int(line[68])` (the 69th character).
- **Inputs**: A TLE line that has already passed FR-1.
- **Outputs**: Raises `TLEParseError` with the line number, computed value, and expected value when
  they differ. Returns cleanly (no error) when they match.
- **Edge cases**: Checksum digit is not a decimal digit (e.g. a letter or space) — treat as a
  parse error, not a ValueError.

### FR-4: Two-line validation entry-point
- **What**: A single public function `validate_checksum(line1: str, line2: str) -> None` that
  applies FR-1 through FR-3 to both lines in sequence (line 1 first).
- **Inputs**: The two raw TLE strings (newlines already stripped by caller).
- **Outputs**: Raises `TLEParseError` on the first failing line; returns `None` on success.
- **Edge cases**: Both lines invalid — only the first error is raised (fail-fast).

### FR-5: Integration with the field parser
- **What**: The existing `parse_tle(line1, line2)` function (S3.3) must call `validate_checksum`
  before extracting fields, so callers can never receive parsed data from a corrupt TLE.
- **Inputs**: Unchanged — same `(line1, line2)` signature.
- **Outputs**: `TLEParseError` propagates unchanged if raised by `validate_checksum`; parsed dict
  returned as before on success.
- **Edge cases**: Ensure `TLEParseError` is importable from `tle_parser` by downstream modules.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `validate_checksum` raises `TLEParseError` for a line with length ≠ 69,
  naming the actual length in the error message.
- [ ] **Outcome 2**: `validate_checksum` raises `TLEParseError` for a line whose checksum digit
  does not match the computed value, including both values in the error message.
- [ ] **Outcome 3**: `validate_checksum` passes silently for a real ISS TLE (catalog 25544) whose
  checksums are known-correct.
- [ ] **Outcome 4**: `parse_tle` (S3.3 entry-point) raises `TLEParseError` when given a TLE
  with a corrupted checksum digit, confirming FR-5 integration.
- [ ] **Outcome 5**: A TLE with a deliberately flipped checksum digit (e.g. `0→1`) is rejected
  before any field is parsed.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_line_too_short**: Pass a 68-char line to `validate_checksum`; expect `TLEParseError`
   mentioning length.
2. **test_line_too_long**: Pass a 70-char line; expect `TLEParseError`.
3. **test_valid_iss_line1_checksum**: Use the real ISS TLE line 1 (catalog 25544, published SGP4
   test vector); expect no exception.
4. **test_valid_iss_line2_checksum**: Same for line 2.
5. **test_corrupted_checksum_digit**: Take the ISS TLE line 1, replace char at index 68 with
   `str((int(line1[68]) + 1) % 10)`; expect `TLEParseError` with computed vs expected in message.
6. **test_minus_counted_as_one**: Construct a synthetic 69-char line where the only non-zero
   contributions are known minuses; assert the computed checksum equals the expected value.
7. **test_parse_tle_rejects_corrupt_checksum**: Call the S3.3 `parse_tle` with a corrupt-checksum
   TLE; expect `TLEParseError` (integration test for FR-5).
8. **test_checksum_digit_not_decimal**: Replace the checksum char with `'X'`; expect
   `TLEParseError`, not `ValueError`.

### Mocking Strategy
- No external HTTP needed — all tests use hardcoded TLE strings (ISS or synthetic).
- Use the ISS TLE from the SGP4 library's own test vectors for known-valid checksums.
- DB not involved — this is a pure parsing function.

### Coverage Expectation
- `compute_checksum`, `validate_checksum`, and the `TLEParseError` path in `parse_tle` all
  covered; all eight test cases above pass.

---

## References
- roadmap.md S3.4 row (Phase 3 table + Master Spec Index)
- CLAUDE.md: "Persist TLE `line1`/`line2` byte-for-byte" — validation is the gate that ensures
  only correct bytes enter the DB
- TLE format spec: https://celestrak.org/columns/v04n03/ (checksum algorithm, section 4)
