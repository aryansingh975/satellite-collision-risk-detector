"""Tests for S10.4 + S10.5 — Containerization and Deployment configuration."""

import re
import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# .dockerignore tests
# ---------------------------------------------------------------------------


def test_dockerignore_exists():
    """.dockerignore must exist at the repo root."""
    assert (REPO_ROOT / ".dockerignore").exists(), ".dockerignore not found at repo root"


def _dockerignore_lines() -> set:
    content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    return {
        ln.strip()
        for ln in content.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }


def test_dockerignore_excludes_secrets():
    """.dockerignore must exclude .env, .venv, and satellite_tracking.db."""
    lines = _dockerignore_lines()
    required_patterns = [".env", ".venv", "satellite_tracking.db"]
    missing = [p for p in required_patterns if not any(p in ln for ln in lines)]
    assert not missing, f"Missing exclusion patterns in .dockerignore: {missing}"


def test_dockerignore_excludes_git_and_cache():
    """.dockerignore must exclude .git/ and __pycache__."""
    lines = _dockerignore_lines()

    required_patterns = [".git", "__pycache__"]
    missing = [p for p in required_patterns if not any(p in ln for ln in lines)]
    assert not missing, f"Missing exclusion patterns in .dockerignore: {missing}"


# ---------------------------------------------------------------------------
# Dockerfile tests
# ---------------------------------------------------------------------------


def test_dockerfile_exists():
    """A Dockerfile must exist at the repo root."""
    assert (REPO_ROOT / "Dockerfile").exists(), "Dockerfile not found at repo root"


def test_dockerfile_multistage():
    """Dockerfile must use a multi-stage build (≥2 FROM directives)."""
    content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    from_lines = [ln for ln in content.splitlines() if re.match(r"^\s*FROM\s+", ln, re.IGNORECASE)]
    assert len(from_lines) >= 2, f"Expected ≥2 FROM stages, found {len(from_lines)}: {from_lines}"


def test_dockerfile_has_builder_stage():
    """Dockerfile must name the first stage 'builder'."""
    content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"FROM\s+\S+\s+AS\s+builder", content, re.IGNORECASE), (
        "Dockerfile missing 'FROM ... AS builder' stage"
    )


def test_dockerfile_exposes_8000():
    """Dockerfile runtime stage must EXPOSE port 8000."""
    content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"EXPOSE\s+8000", content), "Dockerfile does not EXPOSE 8000"


def test_dockerfile_no_hardcoded_secrets():
    """Dockerfile must not contain hardcoded secrets or API tokens."""
    content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    forbidden = [
        r"(?i)CESIUM_ION_TOKEN\s*=\s*\S{5,}",
        r"(?i)PASSWORD\s*=\s*\S+",
        r"(?i)SECRET\s*=\s*\S+",
        r"(?i)API_KEY\s*=\s*\S+",
    ]
    for pat in forbidden:
        match = re.search(pat, content)
        assert not match, (
            f"Potential hardcoded secret in Dockerfile (pattern '{pat}'): {match.group()}"
        )


# ---------------------------------------------------------------------------
# docker-compose.yml tests
# ---------------------------------------------------------------------------


def test_compose_exists():
    """docker-compose.yml must exist at the repo root."""
    assert (REPO_ROOT / "docker-compose.yml").exists(), "docker-compose.yml not found at repo root"


def _load_compose() -> dict:
    content = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    return yaml.safe_load(content)


def test_compose_services():
    """docker-compose.yml must define 'backend' and 'frontend' services."""
    compose = _load_compose()
    services = compose.get("services", {})
    assert "backend" in services, f"Missing 'backend' service; found: {list(services)}"
    assert "frontend" in services, f"Missing 'frontend' service; found: {list(services)}"


def test_compose_backend_ports():
    """Backend service must expose port 8000."""
    compose = _load_compose()
    ports = compose["services"]["backend"].get("ports", [])
    assert any("8000" in str(p) for p in ports), f"Port 8000 not mapped in backend service: {ports}"


def test_compose_frontend_ports():
    """Frontend service must expose port 3000."""
    compose = _load_compose()
    ports = compose["services"]["frontend"].get("ports", [])
    assert any("3000" in str(p) for p in ports), (
        f"Port 3000 not mapped in frontend service: {ports}"
    )


def test_compose_backend_healthcheck():
    """Backend service must define a healthcheck referencing /health."""
    compose = _load_compose()
    hc = compose["services"]["backend"].get("healthcheck", {})
    assert hc, "No healthcheck defined for backend service"
    assert "/health" in str(hc), f"Healthcheck does not reference /health: {hc}"


def test_compose_env_file():
    """Backend service must use 'env_file: .env' — no inline secrets."""
    compose = _load_compose()
    backend = compose["services"]["backend"]
    env_file = backend.get("env_file")
    assert env_file is not None, "Backend service missing 'env_file' directive"
    env_file_str = (
        str(env_file) if not isinstance(env_file, list) else " ".join(str(e) for e in env_file)
    )
    assert ".env" in env_file_str, f"env_file does not reference .env: {env_file}"


def test_compose_volume_defined():
    """A named volume must be declared at the top-level 'volumes:' key."""
    compose = _load_compose()
    volumes = compose.get("volumes", {})
    assert volumes, "No named volumes declared at top-level in docker-compose.yml"


def test_compose_backend_mounts_volume():
    """Backend service must mount the named volume for SQLite persistence."""
    compose = _load_compose()
    backend_volumes = compose["services"]["backend"].get("volumes", [])
    assert backend_volumes, "Backend service has no volume mounts defined"
    # Should have at least one mount containing /app/data
    assert any("/app/data" in str(v) for v in backend_volumes), (
        f"Backend service does not mount a volume at /app/data: {backend_volumes}"
    )


# ---------------------------------------------------------------------------
# S10.5 — Deployment configuration tests (render.yaml + runtime smoke tests)
# ---------------------------------------------------------------------------


# ── render.yaml static tests ─────────────────────────────────────────────────


def test_render_yaml_exists():
    """render.yaml must exist at the repo root for Render.com deployment."""
    assert (REPO_ROOT / "render.yaml").exists(), "render.yaml not found at repo root"


def _load_render_yaml() -> dict:
    content = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(content)


def test_render_yaml_has_web_service():
    """render.yaml must define at least one service of type 'web'."""
    cfg = _load_render_yaml()
    services = cfg.get("services", [])
    assert services, "render.yaml defines no services"
    assert any(s.get("type") == "web" for s in services), (
        f"No 'type: web' service found; types: {[s.get('type') for s in services]}"
    )


def test_render_yaml_health_check_path():
    """render.yaml web service must specify healthCheckPath containing /health."""
    cfg = _load_render_yaml()
    for svc in cfg.get("services", []):
        if svc.get("type") != "web":
            continue
        hc = svc.get("healthCheckPath", "")
        assert "/health" in hc, (
            f"Service '{svc.get('name')}' missing /health in healthCheckPath; got: '{hc}'"
        )


def test_render_yaml_no_hardcoded_secrets():
    """render.yaml must not contain hardcoded secret values."""
    content = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    forbidden_patterns = [
        r"(?i)CESIUM_ION_TOKEN\s*[:=]\s*[A-Za-z0-9._\-]{10,}",
        r"(?i)password\s*:\s*\S{4,}",
        r"(?i)api_key\s*:\s*[A-Za-z0-9]{8,}",
    ]
    for pat in forbidden_patterns:
        m = re.search(pat, content)
        assert not m, f"Potential hardcoded secret in render.yaml (pattern '{pat}'): {m.group()}"


def test_render_yaml_seed_on_boot():
    """render.yaml start or pre-deploy command must invoke seed.py for cold-boot population."""
    cfg = _load_render_yaml()
    for svc in cfg.get("services", []):
        if svc.get("type") != "web":
            continue
        cmd = (svc.get("startCommand") or "") + (svc.get("preDeployCommand") or "")
        assert "seed" in cmd.lower(), (
            f"Service '{svc.get('name')}' neither startCommand nor preDeployCommand runs seed.py"
        )


# ── pydantic-settings validator tests (in-process, no Docker needed) ─────────


def test_settings_rejects_invalid_tle_max_age(monkeypatch):
    """Settings must raise ValidationError when TLE_MAX_AGE_HOURS is set below 1."""
    from pydantic import ValidationError

    import app.core.config as cfg_module

    monkeypatch.setenv("TLE_MAX_AGE_HOURS", "0")
    with pytest.raises(ValidationError, match="TLE_MAX_AGE_HOURS"):
        cfg_module.Settings()


def test_settings_rejects_invalid_screen_step(monkeypatch):
    """Settings must raise ValidationError when SCREEN_STEP_SECONDS is set below 10."""
    from pydantic import ValidationError

    import app.core.config as cfg_module

    monkeypatch.setenv("SCREEN_STEP_SECONDS", "5")
    with pytest.raises(ValidationError, match="SCREEN_STEP_SECONDS"):
        cfg_module.Settings()


# ── Docker daemon fixture ─────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def docker_available() -> bool:
    """Return True if Docker daemon is reachable in this environment."""
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def docker_image(docker_available) -> str:
    """Build the satellite-risk Docker image once per session; skip if no Docker."""
    if not docker_available:
        pytest.skip("Docker daemon not available")
    tag = "satellite-risk-test:pytest"
    build = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=300,
    )
    assert build.returncode == 0, f"docker build failed:\n{build.stderr.decode()}"
    return tag


# ── Docker runtime smoke tests ────────────────────────────────────────────────


def test_docker_image_health(docker_image):
    """Start a container and assert GET /health returns 200 within 45 s."""
    container = "satellite-risk-pytest-health"
    run = subprocess.run(
        [
            "docker", "run", "-d", "--rm",
            "--name", container,
            "-p", "18765:8000",
            "-e", "DATABASE_URL=sqlite:///./test_health.db",
            "-e", "TLE_CACHE_DIR=/tmp/tle_cache",
            "-e", "CELESTRAK_BASE_URL=https://celestrak.org/GPS/gp.php",
            "-e", "DEFAULT_GROUP=active",
            "-e", 'CORS_ORIGINS=["http://localhost:5173"]',
            docker_image,
        ],
        capture_output=True,
        timeout=30,
    )
    assert run.returncode == 0, f"docker run failed:\n{run.stderr.decode()}"

    try:
        import httpx

        deadline = time.time() + 45
        last_exc: Exception | None = None
        while time.time() < deadline:
            try:
                resp = httpx.get("http://localhost:18765/health", timeout=3)
                assert resp.status_code == 200
                assert resp.json().get("status") == "ok"
                return
            except Exception as exc:
                last_exc = exc
            time.sleep(1)
        pytest.fail(f"/health never returned 200 within 45 s — last error: {last_exc}")
    finally:
        subprocess.run(["docker", "stop", container], capture_output=True, timeout=15)


def test_env_var_validation_in_container(docker_image):
    """Container must exit non-zero when an env var fails pydantic-settings validation."""
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-e", "TLE_MAX_AGE_HOURS=0",  # validator requires ≥ 1
            "-e", "DATABASE_URL=sqlite:///./test.db",
            "-e", "TLE_CACHE_DIR=/tmp/tle_cache",
            docker_image,
            "python", "-c",
            "import backend.app.core.config",  # module-level settings = Settings() will fail
        ],
        capture_output=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0, (
        "Expected non-zero exit when TLE_MAX_AGE_HOURS=0, but container exited 0"
    )
    output = result.stderr.decode() + result.stdout.decode()
    assert any(kw in output.lower() for kw in ("validation", "error", "tle_max_age")), (
        f"Expected a validation error message in container output, got:\n{output}"
    )
