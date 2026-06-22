# Spec S4.4 — TEME to Geodetic Conversion

## Overview
Converts TEME (True Equator Mean Equinox) position vectors produced by SGP4 propagation into
geodetic latitude, longitude, and altitude (WGS-84 ellipsoid) for display on the Cesium globe.
This is a **display-only** step: conjunction math always stays in TEME; geodetic coordinates are
computed solely at the API boundary where the frontend needs lat/lon/alt. The implementation uses
skyfield's `EarthSatellite` + `wgs84.subpoint` path, which handles the full TEME→ITRF→geodetic
chain internally.

## Dependencies
- **S4.2** — Single-sat propagation (provides TEME pos/vel and the `Satrec` object)

## Target Location
`backend/app/services/propagation.py`

---

## Functional Requirements

### FR-1: Convert a single TEME position at a given epoch to geodetic coordinates
- **What**: Given a skyfield `EarthSatellite` (built from a satellite's TLE line1/line2) and a
  sequence of UTC datetimes, return a list of `(lat_deg, lon_deg, alt_km)` tuples.
- **Inputs**:
  - `line1: str`, `line2: str` — raw TLE lines stored byte-for-byte in the DB
  - `times: list[datetime]` — UTC datetime objects (timezone-aware or naive UTC)
- **Outputs**:
  - `list[dict]` with keys `"lat"` (float, degrees), `"lon"` (float, degrees), `"alt_km"` (float)
  - One dict per input time. Order matches `times`.
- **Edge cases**:
  - Empty `times` list → return `[]`
  - SGP4 propagation error (decayed satellite, error code ≠ 0) → skip that timestep and log a
    warning; do not raise; caller receives a shorter list or an entry marked with `None` values
  - Malformed TLE (cannot build `EarthSatellite`) → raise `ValueError` with a clear message
    including catalog number if available

### FR-2: Use skyfield `wgs84.subpoint` for the TEME→geodetic conversion
- **What**: The conversion must go through `skyfield.api.EarthSatellite` and `wgs84.subpoint()`
  (not a hand-rolled matrix multiply). This ensures correctness and matches the library the project
  already depends on.
- **Inputs**: Same TLE lines + times as FR-1
- **Outputs**: `GeographicPosition` attributes: `.latitude.degrees`, `.longitude.degrees`,
  `.elevation.km`
- **Edge cases**:
  - Altitude ≪ 0 (re-entered satellite) → include the point but log a debug warning; the caller
    (positions endpoint) may filter it

### FR-3: Function signature and naming
- **What**: The public function is named `teme_to_geodetic(line1, line2, times)` and lives in
  `backend/app/services/propagation.py` alongside the existing propagation helpers.
- **Inputs**: `line1: str`, `line2: str`, `times: Sequence[datetime]`
- **Outputs**: `list[dict[str, float | None]]`
- **Constraint**: Conjunction math (S5.x) must never call this function; it is only wired into
  the positions API (S6.2 / S6.3). No TEME→geodetic conversion in the conjunction pipeline.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `teme_to_geodetic(iss_line1, iss_line2, [t])` returns a dict with numeric
      `lat`, `lon`, `alt_km` keys for the ISS at a known epoch; values are within ±0.1° / ±1 km
      of a reference computed independently.
- [ ] **Outcome 2**: Passing an empty `times=[]` list returns `[]` without error.
- [ ] **Outcome 3**: Passing a malformed TLE raises `ValueError`.
- [ ] **Outcome 4**: A decayed satellite (SGP4 error code ≠ 0 for one timestep) causes that
      timestep to be skipped (or returned as `None` values) rather than crashing the call.
- [ ] **Outcome 5**: `teme_to_geodetic` is not imported anywhere in `conjunctions.py` — the TEME
      frame boundary is maintained.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

1. **test_teme_to_geodetic_iss_known_epoch** — Feed ISS TLE (catalog 25544) and a known UTC
   timestamp; assert returned lat/lon/alt are within ±0.5° and ±5 km of the reference values
   from a skyfield cross-check.
2. **test_teme_to_geodetic_multiple_times** — Feed 3 timestamps; assert output list length == 3
   and each entry has `lat`, `lon`, `alt_km` keys.
3. **test_teme_to_geodetic_empty_times** — Pass `times=[]`; assert result is `[]`.
4. **test_teme_to_geodetic_malformed_tle** — Pass garbage strings as line1/line2; assert
   `ValueError` is raised.
5. **test_teme_to_geodetic_decayed_sat** — Mock the underlying skyfield call to raise an error
   for one of two timesteps; assert the healthy timestep is returned and the error timestep is
   skipped (list length == 1) and a warning is logged.
6. **test_teme_to_geodetic_negative_alt_logged** — Simulate a sub-zero altitude result; assert
   the point is still included in the output (not dropped), and a debug/warning log was emitted.

### Mocking Strategy
- **No live CelesTrak calls** — TLE lines are passed directly as string fixtures; no HTTP needed.
- **ISS fixture** — Use the standard ISS TLE (NORAD 25544) embedded in `conftest.py`:
  ```
  line1 = "1 25544U 98067A   21001.00000000  .00001000  00000-0  20000-4 0  9999"
  line2 = "2 25544  51.6400 339.7000 0001020  88.0000 272.1000 15.48919522263636"
  ```
  (A realistic but static fixture — adjust epoch as needed.)
- **Decayed sat mock** — Patch `EarthSatellite` or the internal `.at()` propagation to raise /
  return an error-coded result for targeted timesteps.
- **In-memory DB** — Not required for this spec; no DB writes in propagation.py.

### Coverage Expectation
- All public functions (`teme_to_geodetic`) have tests for: normal case (single + multiple times),
  empty input, malformed TLE, decayed-sat error path, and negative-altitude warning path.

---

## References
- `roadmap.md` — Phase 4 table, S4.4 row
- `CLAUDE.md` — "Keep conjunction math in TEME; convert to geodetic only at the display boundary";
  skyfield `EarthSatellite` + `wgs84.subpoint`; WGS-72 for SGP4 (WGS-84 geodetic surface for
  `wgs84.subpoint` is correct — these are two different uses of two different standards)
