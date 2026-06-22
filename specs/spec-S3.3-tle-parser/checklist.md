# Checklist — Spec S3.3: TLE Field Parser

## Phase 1: Setup & Dependencies
- [x] Verify S3.2 (TLE cache) is `done`
- [x] Create `backend/app/services/tle_parser.py` (new file)
- [x] No new pyproject.toml deps needed — stdlib `datetime` only

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_tle_parser.py`
- [x] Add ISS TLE fixture (line1, line2) to `conftest.py` or inline
- [x] Write failing test: `test_parse_tle_iss_catalog_no`
- [x] Write failing test: `test_parse_tle_iss_ecc`
- [x] Write failing test: `test_parse_tle_iss_mean_motion`
- [x] Write failing test: `test_parse_tle_epoch_year_2digit_ge57`
- [x] Write failing test: `test_parse_tle_epoch_year_2digit_lt57`
- [x] Write failing test: `test_parse_tle_epoch_day_to_datetime`
- [x] Write failing test: `test_bstar_decode_positive`
- [x] Write failing test: `test_bstar_decode_negative`
- [x] Write failing test: `test_bstar_decode_zero`
- [x] Write failing test: `test_ecc_implied_decimal`
- [x] Write failing test: `test_parse_tle_line_too_short`
- [x] Write failing test: `test_parse_tle_wrong_line_number`
- [x] Write failing test: `test_parse_tle_catalog_mismatch`
- [x] Write failing test: `test_raw_lines_preserved`
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Define `TLEParseError(ValueError)` in `tle_parser.py`
- [x] Define `TLERecord` dataclass with all fields (including raw `line1`/`line2`)
- [x] Implement `_decode_bstar(field: str) -> float` (exponent notation)
- [x] Implement `_epoch_to_datetime(year2: int, day_frac: float) -> datetime` (2-digit year rule)
- [x] Implement `_parse_line1(line1: str) -> dict` — all FR-1 fields; raise `TLEParseError` on bad length/line number
- [x] Implement `_parse_line2(line2: str) -> dict` — all FR-2 fields; raise `TLEParseError` on bad length/line number
- [x] Implement `parse_tle(line1: str, line2: str) -> TLERecord` — calls both parsers, checks catalog_no match, builds epoch
- [x] Run tests — expect pass (Green) — 14/14 passed
- [x] Refactor if needed (extract helpers, clean up field slicing)

## Phase 4: Integration
- [x] `parse_tle` is importable from `backend/app/services/tle_parser`
- [x] Wiring into `ingestion.py` (S3.5) will import and call `parse_tle` — no wiring needed yet, but confirm the interface is ready
- [x] Run lint: `make local-lint` (ruff check + format, line length 100) — all checks passed
- [x] Run full test suite: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short` — 99/99 passed

## Phase 5: Verification
- [x] All 7 tangible outcomes pass
- [x] No hardcoded secrets or tokens
- [x] `TLERecord.line1` and `.line2` are byte-for-byte copies of input (verified by test)
- [x] BSTAR decode handles all sign combinations
- [x] 2-digit year rule: ≥57 → 1900s, <57 → 2000s
- [x] `TLEParseError` is exported at module level for S3.4 to reuse
- [x] Update roadmap.md status: `spec-written` → `done`
