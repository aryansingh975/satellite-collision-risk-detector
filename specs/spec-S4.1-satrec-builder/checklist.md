# Checklist — Spec S4.1: Satrec Builder

## Phase 1: Setup & Dependencies
- [x] Verify S3.3 (TLE field parser) is `done`
- [x] Locate or create `backend/app/services/propagation.py`
- [x] Confirm `sgp4` is listed in `pyproject.toml` (should already be present from S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_propagation.py`
- [x] Write `test_build_satrec_returns_satrec` — valid ISS TLE → `Satrec`, `whichconst == WGS72`
- [x] Write `test_build_satrec_wgs72_constant` — assert `satrec.whichconst` equals `WGS72` sentinel
- [x] Write `test_build_satrec_malformed_line_raises` — wrong-length line → `ValueError`
- [x] Write `test_build_satrec_array_valid_batch` — 3 valid pairs → `SatrecArray` of length 3
- [x] Write `test_build_satrec_array_skips_bad_record` — 3 pairs, 1 bad → length 2 + warning logged
- [x] Write `test_build_satrec_array_single_element` — 1 valid pair → `SatrecArray` of length 1
- [x] Write `test_build_satrec_array_empty_list` — `[]` → `ValueError` (or `None`)
- [x] Run tests — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `build_satrec(line1: str, line2: str) -> Satrec`
  - Call `Satrec.twoline2rv(line1, line2)` (WGS-72 default)
  - Raise `ValueError` if `satrec.error != 0`
- [x] Implement `build_satrec_array(tle_pairs: list[tuple[str, str]]) -> SatrecArray`
  - Raise `ValueError` (or return `None`) for empty input
  - Call `build_satrec` per pair; skip + log warning on `ValueError`
  - Assemble with `SatrecArray(valid_satrecs)` (note: `from_satrecs` not available in sgp4 2.25)
- [x] Run tests — expect pass (Green)
- [x] Refactor if needed (no behaviour changes after Green)

## Phase 4: Integration
- [x] Import `build_satrec` / `build_satrec_array` in downstream modules (S4.2, S4.3) once they exist
- [x] Run lint: `make local-lint` (ruff check + format, line length 100)
- [x] Run full backend test suite: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [x] All 7 tangible outcomes checked off in spec.md
- [x] WGS-72 constants verified via `radiusearthkm==6378.135` and `mu==398600.8` (sgp4 2.25 C ext has no `whichconst` attr)
- [x] No hardcoded secrets or tokens
- [x] Loguru warning emitted on skipped bad records (tested via captured_warnings fixture)
- [x] Update roadmap.md status: `spec-written` → `done` (after /implement-spec + /verify-spec pass)
