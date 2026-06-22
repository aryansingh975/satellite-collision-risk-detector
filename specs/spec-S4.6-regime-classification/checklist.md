# Checklist — Spec S4.6: Regime Classification

## Phase 1: Setup & Dependencies
- [x] Verify S4.5 is `done` (orbital element derivation — provides `n` and `e`)
- [x] Locate `backend/app/services/classification.py` (created by S4.5)
- [x] No new dependencies needed — pure Python, no additional packages

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/services/test_classification.py` (or extend existing)
- [x] Write `test_classify_leo` — `n=15.0, e=0.001` → `"LEO"`
- [x] Write `test_classify_meo` — `n=2.0, e=0.01` → `"MEO"`
- [x] Write `test_classify_geo` — `n=1.0, e=0.0` → `"GEO"`
- [x] Write `test_classify_heo` — `n=2.5, e=0.72` → `"HEO"`
- [x] Write `test_classify_heo_overrides_meo_n` — `n=2.0, e=0.30` → `"HEO"`
- [x] Write `test_classify_boundary_leo` — `n=11.25, e=0.0` → `"LEO"`
- [x] Write `test_classify_boundary_meo_lower` — `n=1.2, e=0.0` → `"MEO"`
- [x] Write `test_classify_boundary_heo` — `n=0.9, e=0.25` → `"HEO"`
- [x] Write `test_classify_just_below_heo` — `n=0.9, e=0.249` → `"GEO"`
- [x] Write `test_classify_invalid_negative_e` — raises `ValueError`
- [x] Write `test_classify_invalid_hyperbolic` — `e=1.0` raises `ValueError`
- [x] Write `test_classify_invalid_negative_n` — raises `ValueError`
- [x] Run tests — expect failures (Red) ✓ confirmed ImportError before implementation

## Phase 3: Implementation
- [x] Implement `classify_regime(n: float, e: float) -> str` in `classification.py`
  - [x] Guard: raise `ValueError` if `e < 0` or `e >= 1` or `n < 0`
  - [x] Branch 1: `e >= 0.25` → return `"HEO"`
  - [x] Branch 2: `n >= 11.25` → return `"LEO"`
  - [x] Branch 3: `n >= 1.2` → return `"MEO"`
  - [x] Branch 4: else → return `"GEO"`
- [x] Wire `classify_regime` into the satellite ingestion pipeline (called when populating `Satellite.regime`)
- [x] Run tests — expect pass (Green) ✓ 30/30 classification + 7/7 persist (172 total)
- [x] Refactor if needed (no logic changes, only clarity)

## Phase 4: Integration
- [x] Verify `Satellite.regime` is populated correctly after `make seed` or the ingestion pipeline
- [x] Run lint: `make local-lint` (ruff check + format, line length 100) ✓ all clean
- [x] Run full test suite: `source .venv/bin/activate && cd backend && python -m pytest tests/ -v --tb=short` ✓ 172 passed

## Phase 5: Verification
- [x] All 10 tangible outcomes in spec.md checked off
- [x] No hardcoded thresholds outside `classify_regime` — thresholds live in one place
- [x] No external HTTP calls; no secrets
- [x] Update roadmap.md status: `spec-written` → `done` (after Phase 4 passes)
