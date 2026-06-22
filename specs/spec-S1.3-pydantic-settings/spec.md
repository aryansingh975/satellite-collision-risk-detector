# Spec S1.3 — Settings via pydantic-settings

## Overview
Centralises all runtime configuration in `backend/app/core/config.py` using `pydantic-settings`.
Every threshold, URL, path, and token is read from a `.env` file (or environment variables) so no
secret or magic number is ever hardcoded. The `Settings` object is instantiated once at import time
and imported wherever configuration is needed.

## Dependencies
- S1.1 (dependency declaration — `pydantic-settings` in `pyproject.toml`)

## Target Location
`backend/app/core/config.py`

---

## Functional Requirements

### FR-1: Settings model with all required fields
- **What**: A `pydantic_settings.BaseSettings` subclass called `Settings` that declares every
  configuration field with a type, default value, and description.
- **Inputs**: Environment variables / `.env` file at repo root (or `backend/.env`)
- **Outputs**: A `Settings` instance importable as `from app.core.config import settings`
- **Fields** (name → type → default):
  | Field | Type | Default |
  |-------|------|---------|
  | `CELESTRAK_BASE_URL` | `str` | `"https://celestrak.org/SOCRATES/query.php"` — actually the GP endpoint: `"https://celestrak.org/GPS/gp.php"` |
  | `DEFAULT_GROUP` | `str` | `"active"` |
  | `TLE_CACHE_DIR` | `Path` | `Path("data/tle_cache")` |
  | `TLE_MAX_AGE_HOURS` | `int` | `2` |
  | `DATABASE_URL` | `str` | `"sqlite:///./satellite_tracking.db"` |
  | `SCREEN_WINDOW_HOURS` | `int` | `72` (within 24–72 h range) |
  | `SCREEN_STEP_SECONDS` | `int` | `60` (within 30–60 s range) |
  | `COARSE_RADIUS_KM` | `float` | `15.0` (within 10–20 km range) |
  | `RISK_THRESHOLD_KM` | `float` | `5.0` (matches CelesTrak SOCRATES) |
  | `CESIUM_ION_TOKEN` | `Optional[str]` | `None` |
- **Edge cases**: Missing optional `CESIUM_ION_TOKEN` must not raise; all numeric bounds must
  be validated (see FR-3)

### FR-2: .env file loading
- **What**: Settings are populated from a `.env` file when present; environment variables
  override `.env` values; missing keys use defaults.
- **Inputs**: `.env` at project root; falls back to OS environment variables
- **Outputs**: Correctly typed field values (e.g. `TLE_MAX_AGE_HOURS` is `int`, not `str`)
- **Edge cases**: `.env` absent → all defaults apply, no error raised

### FR-3: Field validation
- **What**: Validate that numeric fields stay within documented safe ranges.
- **Rules**:
  - `TLE_MAX_AGE_HOURS` ≥ 1
  - `SCREEN_WINDOW_HOURS` in [1, 336] (1 h – 14 days)
  - `SCREEN_STEP_SECONDS` in [10, 3600]
  - `COARSE_RADIUS_KM` > 0
  - `RISK_THRESHOLD_KM` > 0
- **Edge cases**: Out-of-range value → `ValidationError` raised at startup, not silently ignored

### FR-4: Module-level singleton
- **What**: A `settings` singleton is created at module import time so all other modules
  import the same object.
- **Inputs**: None (auto-instantiated)
- **Outputs**: `settings: Settings` accessible via `from app.core.config import settings`
- **Edge cases**: Multiple imports return the same object (Python module cache guarantees this)

---

## Tangible Outcomes

- [ ] **Outcome 1**: `from app.core.config import settings` works without error when `.env` is absent
- [ ] **Outcome 2**: `settings.RISK_THRESHOLD_KM == 5.0` and `settings.DEFAULT_GROUP == "active"` with factory defaults
- [ ] **Outcome 3**: Setting `CESIUM_ION_TOKEN=abc` in env → `settings.CESIUM_ION_TOKEN == "abc"`
- [ ] **Outcome 4**: Setting `RISK_THRESHOLD_KM=-1` raises `pydantic.ValidationError`
- [ ] **Outcome 5**: `settings.TLE_MAX_AGE_HOURS` is type `int`, not `str`

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_defaults**: Instantiate `Settings()` with no env overrides; assert all default values match the table in FR-1
2. **test_env_override**: Set `RISK_THRESHOLD_KM=3.0` via `monkeypatch.setenv`; assert `Settings().RISK_THRESHOLD_KM == 3.0`
3. **test_optional_token_absent**: `Settings().CESIUM_ION_TOKEN is None` — no error
4. **test_optional_token_present**: `monkeypatch.setenv("CESIUM_ION_TOKEN", "tok123")` → `Settings().CESIUM_ION_TOKEN == "tok123"`
5. **test_invalid_risk_threshold**: `monkeypatch.setenv("RISK_THRESHOLD_KM", "-1")` → `pytest.raises(ValidationError)`
6. **test_invalid_tle_max_age**: `monkeypatch.setenv("TLE_MAX_AGE_HOURS", "0")` → `pytest.raises(ValidationError)`
7. **test_types**: Assert `settings.TLE_MAX_AGE_HOURS` is `int`, `settings.COARSE_RADIUS_KM` is `float`
8. **test_singleton**: `from app.core.config import settings as s1, settings as s2` → `s1 is s2`

### Mocking Strategy
- Use `monkeypatch.setenv` / `monkeypatch.delenv` for all env-var overrides — never write a real `.env`
- Instantiate `Settings()` directly in tests (not the module singleton) to get isolated instances
- No CelesTrak HTTP, no DB, no propagation involved

### Coverage Expectation
- All fields covered by at least one test (default + override); all validators exercised

---

## References
- `roadmap.md` — S1.3 row (Phase 1 table + Master Spec Index)
- `CLAUDE.md` — key rules: no hardcoded secrets, all config via `.env` → `config.py`
- pydantic-settings docs: `BaseSettings`, `model_config = SettingsConfigDict(env_file=".env")`
