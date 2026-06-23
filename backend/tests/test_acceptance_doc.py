"""Tests for S11.5: docs/acceptance.md existence and required content."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ACCEPTANCE_DOC = PROJECT_ROOT / "docs" / "acceptance.md"


def _content() -> str:
    return ACCEPTANCE_DOC.read_text(encoding="utf-8")


def test_acceptance_doc_exists():
    assert ACCEPTANCE_DOC.exists(), "docs/acceptance.md is missing"
    assert ACCEPTANCE_DOC.stat().st_size > 0, "docs/acceptance.md is empty"


def test_acceptance_doc_has_five_dimensions():
    text = _content()
    required = [
        "Creativity",
        "Technical Implementation",
        "Web-App Quality",
        "GitHub Usage",
        "Documentation Clarity",
    ]
    for heading in required:
        assert heading in text, f"Missing graded dimension heading: {heading}"


def test_acceptance_doc_has_all_phases():
    text = _content()
    for n in range(1, 12):
        assert f"Phase {n}" in text, f"Missing Phase {n} in acceptance doc"


def test_acceptance_doc_has_demo_steps():
    text = _content()
    # Count lines that start with a digit followed by a period (numbered list items)
    numbered = re.findall(r"^\s*\d+\.", text, re.MULTILINE)
    assert len(numbered) >= 7, (
        f"Demo walkthrough needs at least 7 numbered steps, found {len(numbered)}"
    )


def test_acceptance_doc_has_signoff():
    text = _content()
    for col in ("Reviewer", "Date", "Verdict"):
        assert col in text, f"Sign-off table missing column: {col}"
