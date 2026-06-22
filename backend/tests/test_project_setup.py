"""Tests for S1.1 — Dependency Declaration (pyproject.toml + .env.example)."""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

REQUIRED_RUNTIME_DEPS = [
    "fastapi",
    "uvicorn",
    "skyfield",
    "sgp4",
    "numpy",
    "scipy",
    "sqlalchemy",
    "apscheduler",
    "httpx",
    "pydantic-settings",
    "loguru",
    "tenacity",
]

REQUIRED_DEV_DEPS = [
    "pytest",
    "pytest-mock",
    "ruff",
    "respx",
    "httpx",
]

REQUIRED_ENV_KEYS = [
    "CELESTRAK_BASE_URL",
    "DEFAULT_GROUP",
    "TLE_CACHE_DIR",
    "TLE_MAX_AGE_HOURS",
    "DATABASE_URL",
    "SCREEN_WINDOW_HOURS",
    "SCREEN_STEP_SECONDS",
    "COARSE_RADIUS_KM",
    "RISK_THRESHOLD_KM",
    "CESIUM_ION_TOKEN",
]


def _load_pyproject() -> dict:
    path = REPO_ROOT / "pyproject.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


def test_pyproject_is_valid_toml():
    """pyproject.toml parses without error."""
    data = _load_pyproject()
    assert isinstance(data, dict)


def test_runtime_deps_declared():
    """All required runtime packages appear in [project.dependencies]."""
    data = _load_pyproject()
    deps_raw = data["project"]["dependencies"]
    deps_lower = [d.lower() for d in deps_raw]

    missing = []
    for pkg in REQUIRED_RUNTIME_DEPS:
        if not any(pkg.lower() in dep for dep in deps_lower):
            missing.append(pkg)

    assert not missing, f"Missing runtime deps: {missing}"


def test_dev_extras_declared():
    """All required dev packages appear in [project.optional-dependencies.dev]."""
    data = _load_pyproject()
    dev_deps_raw = data["project"]["optional-dependencies"]["dev"]
    dev_deps_lower = [d.lower() for d in dev_deps_raw]

    missing = []
    for pkg in REQUIRED_DEV_DEPS:
        if not any(pkg.lower() in dep for dep in dev_deps_lower):
            missing.append(pkg)

    assert not missing, f"Missing dev deps: {missing}"


def test_requires_python():
    """requires-python must be set to >=3.11."""
    data = _load_pyproject()
    requires = data["project"]["requires-python"]
    assert requires.startswith(">=3.11"), f"requires-python is '{requires}', expected '>=3.11'"


def test_env_example_exists():
    """.env.example must exist at the repo root."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), f".env.example not found at {REPO_ROOT}"


def test_env_example_keys():
    """Every required env key appears as a variable name in .env.example."""
    env_example = REPO_ROOT / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    defined_keys = {
        line.split("=")[0].strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    missing = [key for key in REQUIRED_ENV_KEYS if key not in defined_keys]
    assert not missing, f"Missing env keys in .env.example: {missing}"
