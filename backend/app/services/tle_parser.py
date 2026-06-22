"""S3.3 — TLE field parser.

Decodes raw Two-Line Element set strings into TLERecord dataclasses ready
for persistence and SGP4 propagation. Raw line1/line2 are preserved byte-for-byte
so satellites can be re-propagated deterministically.

TLE column references use the CelesTrak FAQ format (1-indexed).
Python slice equivalents: col N → index N-1; col A–B → index [A-1:B].
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


class TLEParseError(ValueError):
    """Raised when a TLE line cannot be parsed. Subclass of ValueError."""


@dataclass
class TLERecord:
    # --- line 1 fields ---
    catalog_no: int
    classification: str
    intl_designator: str
    epoch_year: int  # 2-digit as stored in TLE
    epoch_day: float  # day-of-year + fractional day
    mean_motion_dot: float  # first derivative of mean motion / 2 (rev/day²)
    mean_motion_ddot: float  # second derivative of mean motion / 6 (rev/day³)
    bstar: float  # BSTAR drag term (1/earth_radii)
    element_set_no: int

    # --- line 2 fields ---
    inc_deg: float
    raan_deg: float
    ecc: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    mean_motion: float  # rev/day
    rev_at_epoch: int

    # --- derived ---
    epoch: datetime  # UTC, timezone-aware

    # --- raw (preserved byte-for-byte for re-propagation) ---
    line1: str
    line2: str


def compute_checksum(line: str) -> int:
    """Compute the TLE modulo-10 checksum over the first 68 characters.

    Digit characters contribute their face value; '-' contributes 1; all others 0.
    """
    total = 0
    for ch in line[:68]:
        if ch.isdigit():
            total += int(ch)
        elif ch == "-":
            total += 1
    return total % 10


def _validate_one_line(line: str, line_no: int) -> None:
    if len(line) != 69:
        raise TLEParseError(f"TLE line {line_no} must be 69 chars, got {len(line)}")
    checksum_char = line[68]
    if not checksum_char.isdigit():
        raise TLEParseError(
            f"TLE line {line_no} checksum character {checksum_char!r} is not a digit"
        )
    computed = compute_checksum(line)
    expected = int(checksum_char)
    if computed != expected:
        raise TLEParseError(
            f"TLE line {line_no} checksum mismatch: computed={computed}, expected={expected}"
        )


def validate_checksum(line1: str, line2: str) -> None:
    """Validate the modulo-10 checksum of both TLE lines; fail-fast on line 1.

    Raises TLEParseError if either line is not 69 chars or its checksum fails.
    """
    _validate_one_line(line1, 1)
    _validate_one_line(line2, 2)


def _decode_bstar(field: str) -> float:
    """Decode NORAD decimal-point-free exponent notation to float.

    Format: [±]NNNNN[±]E  (8 chars)
    The mantissa has an implied leading '0.' prefix.
    Example: ' 35580-4' → 0.35580 × 10⁻⁴ = 3.558e-5
    """
    if len(field) != 8:
        raise TLEParseError(f"Exponent field must be 8 chars, got {len(field)}: {field!r}")

    mantissa_sign = field[0]  # ' ', '+', or '-'
    mantissa_digits = field[1:6]  # 5 digits
    exp_sign = field[6]  # '+' or '-'
    exp_digit = field[7]  # 1 digit

    sign = -1.0 if mantissa_sign == "-" else 1.0
    try:
        mantissa = float("0." + mantissa_digits)
        exponent = int(exp_sign + exp_digit)
    except ValueError as exc:
        raise TLEParseError(f"Cannot decode exponent field {field!r}") from exc

    return sign * mantissa * (10.0**exponent)


def _epoch_to_datetime(year2: int, day_frac: float) -> datetime:
    """Convert 2-digit TLE year + fractional day-of-year to a UTC datetime.

    Rule: year2 ≥ 57 → 1900s (Sputnik 1 launched 1957);  year2 < 57 → 2000s.
    Formula: Jan 1 of resolved year + timedelta(days=day_frac - 1).
    """
    year = 1900 + year2 if year2 >= 57 else 2000 + year2
    jan1 = datetime(year, 1, 1, tzinfo=timezone.utc)
    return jan1 + timedelta(days=day_frac - 1)


def _parse_line1(line1: str) -> dict:
    """Extract all fields from TLE line 1 (cols 1–69, 1-indexed).

    Raises TLEParseError on wrong length, wrong line number, or unparseable field.
    """
    if len(line1) != 69:
        raise TLEParseError(f"TLE line 1 must be 69 chars, got {len(line1)}")
    if line1[0] != "1":
        raise TLEParseError(f"TLE line 1 must start with '1', got {line1[0]!r}")

    try:
        return {
            "catalog_no": int(line1[2:7]),
            "classification": line1[7],
            "intl_designator": line1[9:17].strip(),
            "epoch_year": int(line1[18:20]),
            "epoch_day": float(line1[20:32]),
            "mean_motion_dot": float(line1[33:43]),
            "mean_motion_ddot": _decode_bstar(line1[44:52]),
            "bstar": _decode_bstar(line1[53:61]),
            "element_set_no": int(line1[64:68]),
        }
    except TLEParseError:
        raise
    except (ValueError, IndexError) as exc:
        raise TLEParseError(f"Line 1 parse error: {exc}") from exc


def _parse_line2(line2: str) -> dict:
    """Extract all fields from TLE line 2 (cols 1–69, 1-indexed).

    Raises TLEParseError on wrong length, wrong line number, or unparseable field.
    """
    if len(line2) != 69:
        raise TLEParseError(f"TLE line 2 must be 69 chars, got {len(line2)}")
    if line2[0] != "2":
        raise TLEParseError(f"TLE line 2 must start with '2', got {line2[0]!r}")

    try:
        return {
            "catalog_no": int(line2[2:7]),
            "inc_deg": float(line2[8:16]),
            "raan_deg": float(line2[17:25]),
            "ecc": float("0." + line2[26:33]),  # implied leading decimal
            "arg_perigee_deg": float(line2[34:42]),
            "mean_anomaly_deg": float(line2[43:51]),
            "mean_motion": float(line2[52:63]),
            "rev_at_epoch": int(line2[63:68]),
        }
    except (ValueError, IndexError) as exc:
        raise TLEParseError(f"Line 2 parse error: {exc}") from exc


def parse_tle(line1: str, line2: str) -> TLERecord:
    """Parse a TLE pair into a TLERecord.

    Validates checksums first, then extracts all fields, checks catalog number
    consistency, and computes the epoch datetime.

    Raises:
        TLEParseError: on checksum failure or any structural/field-level parse error.
    """
    validate_checksum(line1, line2)
    f1 = _parse_line1(line1)
    f2 = _parse_line2(line2)

    if f1["catalog_no"] != f2["catalog_no"]:
        raise TLEParseError(
            f"Catalog number mismatch: line1={f1['catalog_no']}, line2={f2['catalog_no']}"
        )

    epoch = _epoch_to_datetime(f1["epoch_year"], f1["epoch_day"])

    return TLERecord(
        catalog_no=f1["catalog_no"],
        classification=f1["classification"],
        intl_designator=f1["intl_designator"],
        epoch_year=f1["epoch_year"],
        epoch_day=f1["epoch_day"],
        mean_motion_dot=f1["mean_motion_dot"],
        mean_motion_ddot=f1["mean_motion_ddot"],
        bstar=f1["bstar"],
        element_set_no=f1["element_set_no"],
        inc_deg=f2["inc_deg"],
        raan_deg=f2["raan_deg"],
        ecc=f2["ecc"],
        arg_perigee_deg=f2["arg_perigee_deg"],
        mean_anomaly_deg=f2["mean_anomaly_deg"],
        mean_motion=f2["mean_motion"],
        rev_at_epoch=f2["rev_at_epoch"],
        epoch=epoch,
        line1=line1,
        line2=line2,
    )
