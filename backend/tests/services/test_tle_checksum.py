"""Tests for S3.4 — TLE checksum validation (backend/app/services/tle_parser.py)."""

import pytest

from app.services.tle_parser import TLEParseError, compute_checksum, parse_tle, validate_checksum

# 2008 ISS TLE from Vallado SGP4 test vectors — both lines have correct checksum digit 7.
ISS_LINE1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927"
ISS_LINE2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"


# ---------------------------------------------------------------------------
# FR-1: line length enforcement
# ---------------------------------------------------------------------------


def test_line_too_short():
    """FR-1: 68-char line 1 raises TLEParseError mentioning the actual length."""
    short = ISS_LINE1[:68]
    assert len(short) == 68
    with pytest.raises(TLEParseError, match="68"):
        validate_checksum(short, ISS_LINE2)


def test_line_too_long():
    """FR-1: 70-char line 1 raises TLEParseError mentioning the actual length."""
    long = ISS_LINE1 + "0"
    assert len(long) == 70
    with pytest.raises(TLEParseError, match="70"):
        validate_checksum(long, ISS_LINE2)


# ---------------------------------------------------------------------------
# FR-2 / FR-3: checksum computation and comparison
# ---------------------------------------------------------------------------


def test_valid_iss_line1_checksum():
    """FR-3 / Outcome 3: real ISS TLE line 1 passes silently."""
    validate_checksum(ISS_LINE1, ISS_LINE2)  # must not raise


def test_valid_iss_line2_checksum():
    """FR-3 / Outcome 3: real ISS TLE line 2 passes silently."""
    validate_checksum(ISS_LINE1, ISS_LINE2)  # must not raise


def test_corrupted_checksum_digit():
    """FR-3 / Outcome 2 & 5: flipped checksum digit raises TLEParseError with both values."""
    bad_digit = str((int(ISS_LINE1[68]) + 1) % 10)
    bad_line1 = ISS_LINE1[:68] + bad_digit
    with pytest.raises(TLEParseError, match=r"computed|expected"):
        validate_checksum(bad_line1, ISS_LINE2)


def test_minus_counted_as_one():
    """FR-2: minus signs each contribute 1 to the checksum sum."""
    # Body: 5 minus signs + 63 spaces = 68 chars. Expected checksum = 5 % 10 = 5.
    body = "-" * 5 + " " * 63
    assert len(body) == 68
    assert compute_checksum(body + "5") == 5


# ---------------------------------------------------------------------------
# FR-5: integration with parse_tle
# ---------------------------------------------------------------------------


def test_parse_tle_rejects_corrupt_checksum():
    """FR-5 / Outcome 4: parse_tle raises TLEParseError when checksum is bad."""
    bad_digit = str((int(ISS_LINE1[68]) + 1) % 10)
    bad_line1 = ISS_LINE1[:68] + bad_digit
    with pytest.raises(TLEParseError):
        parse_tle(bad_line1, ISS_LINE2)


def test_checksum_digit_not_decimal():
    """FR-3 edge case: non-digit checksum char raises TLEParseError, not ValueError."""
    bad_line1 = ISS_LINE1[:68] + "X"
    with pytest.raises(TLEParseError):
        validate_checksum(bad_line1, ISS_LINE2)
