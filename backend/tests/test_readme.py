"""S11.1 — README content assertions.

Reads README.md from the project root and asserts each functional requirement
is satisfied. No external HTTP; no DB; pure file I/O.
"""

from pathlib import Path

README = (Path(__file__).parent.parent.parent / "README.md").read_text(encoding="utf-8")
README_LOWER = README.lower()


def test_readme_problem_statement():
    """FR-1: overview mentions miss-distance screening and disclaims collision probability."""
    assert "miss distance" in README_LOWER or "close approach" in README_LOWER, (
        "README must mention 'miss distance' or 'close approach'"
    )
    assert "not collision probability" in README_LOWER or (
        "collision probability" in README_LOWER and "not" in README_LOWER
    ), "README must disclaim collision probability"


def test_readme_celestrak_attribution():
    """FR-2: data-sources credits CelesTrak, states 2-hour cadence, mentions cache/403 fallback."""
    assert "celestrak" in README_LOWER, "README must mention CelesTrak"
    assert "2 hour" in README_LOWER or "2-hour" in README_LOWER, (
        "README must state the 2-hour update cadence"
    )
    assert "403" in README or "cache" in README_LOWER, (
        "README must mention HTTP 403 fallback or local cache policy"
    )


def test_readme_architecture():
    """FR-3: architecture section describes the full pipeline and correct frame conventions."""
    assert "ingestion" in README_LOWER, "README must describe the ingestion step"
    assert "propagation" in README_LOWER or "propagate" in README_LOWER, (
        "README must describe the propagation step"
    )
    assert "sgp4" in README_LOWER, "README must mention SGP4"
    assert "teme" in README_LOWER or "geodetic" in README_LOWER, (
        "README must mention the TEME or geodetic frame convention"
    )


def test_readme_setup_commands():
    """FR-4: getting-started section contains the required make commands."""
    assert "make seed" in README, "README must include 'make seed' in setup instructions"
    assert "make local-dev" in README or "make dev" in README, (
        "README must include 'make local-dev' or 'make dev' in setup instructions"
    )


def test_readme_api_endpoints():
    """FR-5: API reference covers all major endpoints."""
    required = [
        "/conjunctions",
        "/satellites",
        "/stats/orbital-regions",
        "/stats/risk-ranking",
        "/health",
    ]
    for endpoint in required:
        assert endpoint in README, f"README API reference must include endpoint: {endpoint}"


def test_readme_no_placeholders():
    """FR-7: no draft/placeholder language from the original skeleton remains."""
    assert "Planned Features" not in README, (
        "README must not contain 'Planned Features' section (remove draft content)"
    )
    assert "Current Status: Prototype" not in README and "Current Status" not in README, (
        "README must not contain 'Current Status' placeholder section"
    )
    # Unchecked checkboxes (- [ ] items) indicate draft TODOs that must be removed
    import re

    unchecked = re.findall(r"^- \[ \]", README, re.MULTILINE)
    assert not unchecked, (
        f"README must not contain unchecked TODO checkboxes; "
        f"found {len(unchecked)}: {unchecked[:3]}"
    )
