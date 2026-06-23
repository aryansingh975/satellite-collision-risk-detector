"""S11.2 — Tests that docs/architecture.md exists and contains required sections."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
ARCH_DOC = REPO_ROOT / "docs" / "architecture.md"


def _content() -> str:
    return ARCH_DOC.read_text(encoding="utf-8")


def test_architecture_doc_exists():
    assert ARCH_DOC.is_file(), "docs/architecture.md must exist"


def test_architecture_doc_has_diagram_section():
    text = _content()
    pattern = r"^#{1,3}\s+(System\s+Diagram|Architecture)"
    assert re.search(pattern, text, re.MULTILINE | re.IGNORECASE), (
        "Must have a 'System Diagram' or 'Architecture' heading"
    )
    has_diagram = "```" in text or "graph " in text
    assert has_diagram, "Must contain a diagram block (fenced code or Mermaid graph)"


def test_architecture_doc_has_coordinate_frame_section():
    text = _content()
    assert re.search(r"coordinate.?frames?", text, re.IGNORECASE), (
        "Must have a 'Coordinate Frames' section"
    )
    assert "TEME" in text, "Must mention TEME coordinate frame"


def test_architecture_doc_has_tech_stack_section():
    text = _content()
    assert re.search(r"^#{1,3}\s+Tech\s+Stack", text, re.MULTILINE | re.IGNORECASE), (
        "Must have a 'Tech Stack' heading"
    )
    table_rows = [
        line for line in text.splitlines()
        if line.strip().startswith("|") and "|" in line[1:]
    ]
    assert len(table_rows) >= 8, f"Tech Stack table needs ≥8 rows, found {len(table_rows)}"


def test_architecture_doc_has_constants_section():
    text = _content()
    assert "398600" in text, "Must contain the gravitational constant μ = 398600.4418 km³/s²"
    assert "5 km" in text, "Must state the 5 km risk threshold"


def test_architecture_doc_mentions_scheduler():
    text = _content()
    assert re.search(r"scheduler|APScheduler", text, re.IGNORECASE), (
        "Must mention the APScheduler 2-h feedback loop"
    )
