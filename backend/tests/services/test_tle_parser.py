"""Tests for S3.3 — TLE field parser (backend/app/services/tle_parser.py)."""

from datetime import timezone

import pytest

from app.services.tle_parser import (
    TLEParseError,
    _decode_bstar,
    _epoch_to_datetime,
    parse_tle,
)

# ISS (ZARYA) fixture — catalog 25544, known orbital elements.
# ecc=0.0001486, mean_motion≈15.4931182 rev/day, epoch year=2024, day=123.50765046
ISS_LINE1 = "1 25544U 98067A   24123.50765046  .00015000  00000-0  27268-3 0  9999"
ISS_LINE2 = "2 25544  51.6400 320.0000 0001486 100.0000 260.0000 15.49311820452679"


# ---------------------------------------------------------------------------
# FR-1 / FR-2 / FR-5: top-level parse_tle, ISS-specific assertions
# ---------------------------------------------------------------------------


def test_parse_tle_iss_catalog_no():
    """Outcome 1: catalog_no == 25544."""
    record = parse_tle(ISS_LINE1, ISS_LINE2)
    assert record.catalog_no == 25544


def test_parse_tle_iss_ecc():
    """Outcome 1 / FR-2: eccentricity decoded with implied leading decimal."""
    record = parse_tle(ISS_LINE1, ISS_LINE2)
    assert record.ecc == pytest.approx(0.0001486, abs=1e-7)


def test_parse_tle_iss_mean_motion():
    """Outcome 1 / FR-2: mean motion in rev/day to 4 decimal places."""
    record = parse_tle(ISS_LINE1, ISS_LINE2)
    assert record.mean_motion == pytest.approx(15.4931182, rel=1e-4)


# ---------------------------------------------------------------------------
# FR-3: epoch 2-digit year resolution
# ---------------------------------------------------------------------------


def test_parse_tle_epoch_year_2digit_ge57():
    """year2 ≥ 57 resolves to 1900s (e.g. 57 → 1957)."""
    epoch = _epoch_to_datetime(57, 1.0)
    assert epoch.year == 1957


def test_parse_tle_epoch_year_2digit_lt57():
    """year2 < 57 resolves to 2000s (e.g. 24 → 2024)."""
    epoch = _epoch_to_datetime(24, 1.0)
    assert epoch.year == 2024


def test_parse_tle_epoch_day_to_datetime():
    """Outcome 4: epoch_day fraction produces correct UTC date and hour.

    year=24, day=123.456 → 2024-05-02 at ~10:56 UTC.
    2024 is a leap year: Jan(31)+Feb(29)+Mar(31)+Apr(30)=121 days → day 122=May1, day 123=May2.
    Fractional 0.456 days = 10.944 h → hour 10.
    """
    epoch = _epoch_to_datetime(24, 123.456)
    assert epoch.tzinfo == timezone.utc
    assert epoch.year == 2024
    assert epoch.month == 5
    assert epoch.day == 2
    assert epoch.hour == 10


# ---------------------------------------------------------------------------
# FR-4: BSTAR / decimal-point-free exponent decode
# ---------------------------------------------------------------------------


def test_bstar_decode_positive():
    """Outcome 2: ' 35580-4' → 3.558e-5."""
    assert _decode_bstar(" 35580-4") == pytest.approx(3.558e-5, rel=1e-4)


def test_bstar_decode_negative():
    """Negative mantissa decodes to a negative float."""
    result = _decode_bstar("-11606-4")
    assert result < 0
    assert result == pytest.approx(-1.1606e-5, rel=1e-4)


def test_bstar_decode_zero():
    """All-zero field decodes to exactly 0.0."""
    assert _decode_bstar(" 00000-0") == 0.0


# ---------------------------------------------------------------------------
# FR-2: eccentricity implied decimal
# ---------------------------------------------------------------------------


def test_ecc_implied_decimal():
    """Outcome 3: ecc field '0013716' → 0.0013716 (0. prefix implied)."""
    # Swap in a different 7-char ecc field at positions 26:33; recompute checksum.
    body = ISS_LINE2[:26] + "0013716" + ISS_LINE2[33:68]
    checksum = (sum(int(c) for c in body if c.isdigit()) + body.count("-")) % 10
    line2 = body + str(checksum)
    assert len(line2) == 69
    record = parse_tle(ISS_LINE1, line2)
    assert record.ecc == pytest.approx(0.0013716, abs=1e-7)


# ---------------------------------------------------------------------------
# FR-1 / FR-6: validation / error cases
# ---------------------------------------------------------------------------


def test_parse_tle_line_too_short():
    """Outcome 5: 68-char line 1 raises TLEParseError."""
    with pytest.raises(TLEParseError):
        parse_tle(ISS_LINE1[:68], ISS_LINE2)


def test_parse_tle_wrong_line_number():
    """Line starting with '3' instead of '1' raises TLEParseError."""
    bad_line1 = "3" + ISS_LINE1[1:]
    with pytest.raises(TLEParseError):
        parse_tle(bad_line1, ISS_LINE2)


def test_parse_tle_catalog_mismatch():
    """Outcome 6: mismatched catalog numbers raise TLEParseError."""
    bad_line2 = ISS_LINE2[:2] + "99999" + ISS_LINE2[7:]
    assert len(bad_line2) == 69
    with pytest.raises(TLEParseError):
        parse_tle(ISS_LINE1, bad_line2)


# ---------------------------------------------------------------------------
# FR-5: raw lines preserved byte-for-byte
# ---------------------------------------------------------------------------


def test_raw_lines_preserved():
    """Outcome 7: TLERecord.line1 and .line2 equal the input strings exactly."""
    record = parse_tle(ISS_LINE1, ISS_LINE2)
    assert record.line1 == ISS_LINE1
    assert record.line2 == ISS_LINE2
