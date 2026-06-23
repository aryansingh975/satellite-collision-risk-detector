"""S11.3 — Screenshot artefact assertions.

Verifies that the required docs/screenshots/ files exist, are valid PNGs with the
correct minimum dimensions, that the README embeds them, and that the optional GIF
is within the 5 MB size budget.  No external HTTP; no DB; pure file I/O.
"""

import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"

_REQUIRED_PNGS = [
    "globe-satellites.png",
    "globe-risk-polylines.png",
    "dashboard.png",
]

PNG_SIG = b"\x89PNG\r\n\x1a\n"
MIN_WIDTH = 1280
MIN_HEIGHT = 720
GIF_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) from the IHDR chunk of a PNG file."""
    with path.open("rb") as fh:
        sig = fh.read(8)
        assert sig == PNG_SIG, f"{path.name}: invalid PNG signature"
        fh.read(4)  # IHDR chunk length
        chunk_type = fh.read(4)
        assert chunk_type == b"IHDR", f"{path.name}: first chunk is not IHDR"
        width = struct.unpack(">I", fh.read(4))[0]
        height = struct.unpack(">I", fh.read(4))[0]
    return width, height


# ---------------------------------------------------------------------------
# FR-1 / FR-2 / FR-3  –  existence
# ---------------------------------------------------------------------------


def test_screenshots_exist():
    """All three required PNG files must exist and be non-empty."""
    missing = []
    empty = []
    for name in _REQUIRED_PNGS:
        p = SCREENSHOTS_DIR / name
        if not p.exists():
            missing.append(name)
        elif p.stat().st_size == 0:
            empty.append(name)
    assert not missing, f"Missing screenshot(s) in docs/screenshots/: {missing}"
    assert not empty, f"Empty screenshot file(s) in docs/screenshots/: {empty}"


# ---------------------------------------------------------------------------
# FR-1 / FR-2 / FR-3  –  format + dimensions
# ---------------------------------------------------------------------------


def test_screenshots_are_valid_png():
    """Each PNG must have a valid header and be at least 1280 × 720 px."""
    errors: list[str] = []
    for name in _REQUIRED_PNGS:
        p = SCREENSHOTS_DIR / name
        if not p.exists():
            errors.append(f"{name}: file missing (run capture first)")
            continue
        try:
            w, h = _png_dimensions(p)
        except AssertionError as exc:
            errors.append(str(exc))
            continue
        if w < MIN_WIDTH or h < MIN_HEIGHT:
            errors.append(
                f"{name}: dimensions {w}×{h} are below the {MIN_WIDTH}×{MIN_HEIGHT} minimum"
            )
    assert not errors, "PNG validation failures:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# FR-5  –  README embedding
# ---------------------------------------------------------------------------


def test_readme_embeds_screenshots():
    """README.md must contain at least 3 relative image links into docs/screenshots/."""
    readme = REPO_ROOT / "README.md"
    assert readme.exists(), "README.md not found at repo root"
    text = readme.read_text(encoding="utf-8")

    # Match Markdown image syntax: ![...](docs/screenshots/...)
    import re

    pattern = r"!\[[^\]]*\]\(docs/screenshots/[^\)]+\.png\)"
    matches = re.findall(pattern, text)
    assert len(matches) >= 3, (
        f"README.md must embed ≥ 3 images from docs/screenshots/; "
        f"found {len(matches)}: {matches}"
    )


# ---------------------------------------------------------------------------
# FR-4  –  optional GIF size budget
# ---------------------------------------------------------------------------


def test_gif_size_if_present():
    """If the optional animated GIF exists it must be ≤ 5 MiB."""
    gif = SCREENSHOTS_DIR / "globe-animated.gif"
    if not gif.exists():
        return  # optional artefact — skip when absent
    size = gif.stat().st_size
    assert size <= GIF_MAX_BYTES, (
        f"globe-animated.gif is {size / 1024 / 1024:.1f} MiB, exceeds 5 MiB limit"
    )
