# Checklist — Spec S1.3: Settings via pydantic-settings

## Phase 1: Setup & Dependencies
- [x] Verify S1.1 is `done` (pydantic-settings listed in pyproject.toml)
- [x] Create `backend/app/core/__init__.py` if it does not exist
- [x] Create `backend/app/core/config.py` (target file)

## Phase 2: Tests First (TDD)
- [x] Create `backend/tests/core/` directory and `__init__.py`
- [x] Write `backend/tests/core/test_config.py` with all 8 tests listed in spec (11 tests total)
- [x] Run tests — expect failures (Red): 11/11 failed with ModuleNotFoundError

## Phase 3: Implementation
- [x] Implement `Settings(BaseSettings)` with all fields from FR-1
- [x] Add `model_config = SettingsConfigDict(env_file=..., extra="ignore")`
- [x] Add `@field_validator` constraints for FR-3 range rules
- [x] Declare module-level `settings = Settings()` singleton (FR-4)
- [x] Run tests — expect pass (Green): 11/11 passed
- [x] Refactor if needed (no duplication, clean validators)

## Phase 4: Integration
- [x] Confirm `from app.core.config import settings` works from `backend/` root
- [x] Confirm `.env.example` lists all fields with example/default values (fixed CELESTRAK_BASE_URL to GP endpoint)
- [x] Run lint: ruff check + format — All checks passed, 2 files already formatted
- [x] Run full backend test suite: 27/27 passed (no regressions in S1.1/S1.2 tests)

## Phase 5: Verification
- [x] All 5 tangible outcomes pass (verified manually)
- [x] No hardcoded secrets/tokens anywhere in `config.py`
- [x] `CESIUM_ION_TOKEN` is `Optional[str]` defaulting to `None`
- [x] Numeric fields are correct Python types (int vs float), not strings
- [x] Update `roadmap.md` status: `spec-written` → `done`
