# Checklist — Spec S3.4: TLE Checksum Validation

## Phase 1: Setup & Dependencies
- [x] Verify S3.3 (TLE field parser) is `done` and its tests pass
- [x] Locate `backend/app/services/tle_parser.py` — checksum code goes here
- [x] No new package dependencies needed (pure Python)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_tle_checksum.py`
- [x] test_line_too_short — 68-char line → TLEParseError mentioning length
- [x] test_line_too_long — 70-char line → TLEParseError
- [x] test_valid_iss_line1_checksum — real ISS TLE line 1 passes silently
- [x] test_valid_iss_line2_checksum — real ISS TLE line 2 passes silently
- [x] test_corrupted_checksum_digit — flipped digit → TLEParseError with computed vs expected
- [x] test_minus_counted_as_one — synthetic line with known minus contributions matches expected checksum
- [x] test_parse_tle_rejects_corrupt_checksum — parse_tle raises TLEParseError on corrupt checksum (FR-5 integration)
- [x] test_checksum_digit_not_decimal — non-digit checksum char → TLEParseError, not ValueError
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Define `TLEParseError` exception class in `tle_parser.py` (if not already present from S3.3)
- [x] Implement `compute_checksum(line: str) -> int` — sum digits + minuses over first 68 chars, mod 10
- [x] Implement `validate_checksum(line1: str, line2: str) -> None` — length check then checksum check for each line
- [x] Wire `validate_checksum` into `parse_tle` (FR-5): call before field extraction
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (e.g. extract `_check_one_line` helper to avoid duplication)

## Phase 4: Integration
- [x] Confirm `TLEParseError` is importable from `backend.app.services.tle_parser` in other modules
- [x] Run lint: `make local-lint` (ruff check + format, line length 100)
- [x] Run full backend test suite: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [x] All 5 tangible outcomes in spec.md checked off
- [x] No hardcoded secrets or tokens introduced
- [x] No external HTTP in tests (all tests use inline TLE strings)
- [x] Update roadmap.md status: `spec-written` → `done` (after /implement-spec + /verify-spec pass)
