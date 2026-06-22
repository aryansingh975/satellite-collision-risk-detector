"""Tests for S1.2 — Developer Commands (Makefile).

All tests are pure text-parsing — no shell execution, no mocking needed.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
MAKEFILE = REPO_ROOT / "Makefile"

REQUIRED_TARGETS = [
    "venv",
    "install",
    "install-dev",
    "local-dev",
    "dev",
    "local-test",
    "test",
    "local-lint",
    "lint",
    "seed",
    "refresh",
    "serve-frontend",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_makefile() -> str:
    assert MAKEFILE.exists(), f"Makefile not found at {MAKEFILE}"
    return MAKEFILE.read_text(encoding="utf-8")


def _extract_targets(content: str) -> set[str]:
    """Return all Make target names (lines of the form 'name:' or 'name: deps')."""
    targets = set()
    for line in content.splitlines():
        # Target lines: start with a non-whitespace word followed by ':'
        # Exclude variable assignments (contain '=') and lines starting with '#'
        m = re.match(r"^([A-Za-z0-9_][A-Za-z0-9_-]*)\s*:", line)
        if m and "=" not in line.split(":")[0]:
            targets.add(m.group(1))
    return targets


def _extract_phony(content: str) -> set[str]:
    """Return all names declared in .PHONY lines."""
    phony: set[str] = set()
    for line in content.splitlines():
        if line.startswith(".PHONY"):
            # .PHONY: target1 target2 ...
            rest = line.split(":", 1)[1] if ":" in line else ""
            phony.update(rest.split())
    return phony


def _recipe_lines_for(target: str, content: str) -> list[str]:
    """Return the tab-indented recipe lines that belong to `target`."""
    lines = content.splitlines()
    in_target = False
    recipe: list[str] = []
    target_re = re.compile(rf"^{re.escape(target)}\s*[:\s]")
    for line in lines:
        if target_re.match(line):
            in_target = True
            continue
        if in_target:
            if line.startswith("\t") or line.startswith("    "):
                recipe.append(line)
            elif line.strip() == "" or line.startswith("#"):
                continue
            else:
                break  # next target or directive — stop
    return recipe


def _combined_recipe(*targets: str, content: str) -> str:
    """Return combined recipe text for a set of aliased targets."""
    all_lines: list[str] = []
    for t in targets:
        all_lines.extend(_recipe_lines_for(t, content))
    return "\n".join(all_lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_makefile_exists():
    """Makefile must exist at the project root."""
    assert MAKEFILE.exists(), f"Makefile not found at {MAKEFILE}"


def test_makefile_has_required_targets():
    """Every required Make target must appear as a recipe target."""
    content = _read_makefile()
    targets = _extract_targets(content)
    missing = [t for t in REQUIRED_TARGETS if t not in targets]
    assert not missing, f"Missing Make targets: {missing}\nFound: {sorted(targets)}"


def test_makefile_phony_declares_all_targets():
    """.PHONY must list all required targets so Make never confuses them with files."""
    content = _read_makefile()
    phony = _extract_phony(content)
    missing = [t for t in REQUIRED_TARGETS if t not in phony]
    assert not missing, f"Targets not in .PHONY: {missing}\nFound in .PHONY: {sorted(phony)}"


def test_makefile_venv_command_uses_uv():
    """`venv` recipe must invoke `uv` (not bare python -m venv)."""
    content = _read_makefile()
    recipe = _combined_recipe("venv", content=content)
    assert recipe, "No recipe lines found for target 'venv'"
    assert "uv" in recipe, f"'uv' not found in venv recipe:\n{recipe}"


def test_makefile_install_uses_uv_pip():
    """`install` recipe must reference `uv pip install`."""
    content = _read_makefile()
    recipe = _combined_recipe("install", content=content)
    assert recipe, "No recipe lines found for target 'install'"
    assert "uv pip install" in recipe, f"'uv pip install' not found in install recipe:\n{recipe}"


def test_makefile_dev_uses_uvicorn_reload():
    """`local-dev` / `dev` recipe must reference uvicorn with --reload flag."""
    content = _read_makefile()
    recipe = _combined_recipe("local-dev", "dev", content=content)
    assert recipe, "No recipe lines found for 'local-dev' or 'dev'"
    assert "uvicorn" in recipe, f"'uvicorn' not found in dev recipe:\n{recipe}"
    assert "--reload" in recipe, f"'--reload' not found in dev recipe:\n{recipe}"


def test_makefile_test_runs_pytest():
    """`local-test` / `test` recipe must reference pytest."""
    content = _read_makefile()
    recipe = _combined_recipe("local-test", "test", content=content)
    assert recipe, "No recipe lines found for 'local-test' or 'test'"
    assert "pytest" in recipe, f"'pytest' not found in test recipe:\n{recipe}"


def test_makefile_lint_runs_ruff():
    """`local-lint` / `lint` recipe must reference ruff."""
    content = _read_makefile()
    recipe = _combined_recipe("local-lint", "lint", content=content)
    assert recipe, "No recipe lines found for 'local-lint' or 'lint'"
    assert "ruff" in recipe, f"'ruff' not found in lint recipe:\n{recipe}"


def test_makefile_seed_runs_seed_script():
    """`seed` recipe must invoke the seed script."""
    content = _read_makefile()
    recipe = _combined_recipe("seed", content=content)
    assert recipe, "No recipe lines found for target 'seed'"
    assert "seed" in recipe.lower(), f"seed script invocation not found in recipe:\n{recipe}"


def test_makefile_serve_frontend_uses_npm():
    """`serve-frontend` recipe must use npm to start the Vite dev server."""
    content = _read_makefile()
    recipe = _combined_recipe("serve-frontend", content=content)
    assert recipe, "No recipe lines found for target 'serve-frontend'"
    assert "npm" in recipe, f"'npm' not found in serve-frontend recipe:\n{recipe}"
