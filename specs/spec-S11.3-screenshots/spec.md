# Spec S11.3 — Screenshots / GIFs

## Overview
Capture and embed visual evidence of the working prototype: the 3D Cesium globe showing animated
satellites with red risk polylines between at-risk pairs, plus the Chart.js dashboard panels (regime
distribution, close-approach counts, risk ranking table). Screenshots/GIFs are embedded in the README
and serve as permanent proof that the end-to-end system works for graders and collaborators who cannot
run the app locally.

## Dependencies
- S10.3 (End-to-end test) — the app must be demonstrably running and populated with real data before
  screenshots are taken.

## Target Location
`docs/screenshots/`

---

## Functional Requirements

### FR-1: Globe screenshot with animated satellites
- **What**: A screenshot (PNG) of the Cesium globe showing at least a dozen coloured satellite points
  rendered at their propagated positions, captured while the Cesium clock animation is active.
- **Inputs**: Running frontend (Vite dev server or static build) connected to a seeded backend; Cesium
  clock set to a time with known satellite positions.
- **Outputs**: `docs/screenshots/globe-satellites.png` — 1280×720 px minimum; satellites visible as
  coloured dots; Earth rendered with Natural Earth imagery; no ion-token watermark.
- **Edge cases**: If the backend returns no satellites (empty DB), seed with `make seed` before
  capturing. If CesiumJS renders a blank canvas on first load, wait for tile load to complete.

### FR-2: Globe screenshot with risk polylines
- **What**: A screenshot (PNG) of the globe zoomed/framed to show at least one red risk polyline
  connecting two at-risk satellite pairs from `/conjunctions`.
- **Inputs**: Same running system; at least one conjunction in the DB with miss_km ≤ 5 km.
- **Outputs**: `docs/screenshots/globe-risk-polylines.png` — risk polylines clearly visible in red;
  the two connected satellites labelled or highlighted.
- **Edge cases**: If no conjunctions exist, re-run the screen (`make refresh`) or use a synthetic TLE
  fixture that produces a known close approach. Document this in the screenshot caption.

### FR-3: Dashboard panel screenshots
- **What**: One screenshot (PNG) showing all three Chart.js dashboard panels visible simultaneously
  (regime distribution chart, close-approach count chart, risk ranking table).
- **Inputs**: Running frontend with dashboard populated from `/stats/orbital-regions`,
  `/stats/risk-ranking`, and `/conjunctions`.
- **Outputs**: `docs/screenshots/dashboard.png` — all panels visible; counts non-zero; no JS console
  errors visible in the capture.
- **Edge cases**: If the dashboard sidebar is collapsed, expand it before capturing.

### FR-4: Optional animated GIF
- **What**: A short GIF (≤ 5 MB) showing the Cesium clock animating satellite orbits over ~60 seconds
  of simulated time. Demonstrates the time-dynamic aspect of the globe.
- **Inputs**: Running frontend with `SampledPositionProperty` tracks loaded; Cesium clock at 60×
  speed multiplier.
- **Outputs**: `docs/screenshots/globe-animated.gif` (optional but recommended for README impact).
- **Edge cases**: GIF file size must be ≤ 5 MB to avoid bloating the repo. Use frame-skipping or
  palette optimization (e.g. `ffmpeg -i … -vf "fps=10,scale=640:-1:flags=lanczos,palettegen"`) if
  larger.

### FR-5: README embedding
- **What**: All captured images are referenced in `README.md` via relative Markdown image links so
  they render on GitHub and in the GitHub Pages preview.
- **Inputs**: `docs/screenshots/` files; existing `README.md`.
- **Outputs**: README contains at minimum one embedded image per screenshot (FR-1, FR-2, FR-3); image
  alt-text is descriptive; links use relative paths (`docs/screenshots/globe-satellites.png`).
- **Edge cases**: Paths are case-sensitive on Linux CI — use lowercase filenames matching the actual
  file names exactly.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `docs/screenshots/globe-satellites.png` exists and is a valid PNG ≥ 1280×720 px
      showing coloured satellite dots on the Cesium globe.
- [ ] **Outcome 2**: `docs/screenshots/globe-risk-polylines.png` exists and clearly shows at least one
      red conjunction polyline on the globe.
- [ ] **Outcome 3**: `docs/screenshots/dashboard.png` exists and shows all three dashboard panels with
      non-zero data.
- [ ] **Outcome 4**: `README.md` embeds all three screenshots via relative Markdown image links that
      render correctly on GitHub (verified by previewing the raw Markdown).
- [ ] **Outcome 5** (optional): `docs/screenshots/globe-animated.gif` exists and is ≤ 5 MB.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)

Because this spec is primarily about captured artefacts (not runtime logic), the "tests" are
automated checks that verify the artefacts exist, are the correct format, and are referenced in
the README.

1. **test_screenshots_exist**: Assert that `docs/screenshots/globe-satellites.png`,
   `docs/screenshots/globe-risk-polylines.png`, and `docs/screenshots/dashboard.png` all exist on
   disk and are non-empty (size > 0 bytes).

2. **test_screenshots_are_valid_png**: Use Python's `imghdr` or `PIL/Pillow` to assert each `.png`
   file has a valid PNG header and dimensions ≥ 1280×720.

3. **test_readme_embeds_screenshots**: Parse `README.md` and assert it contains at least three
   Markdown image references (`![`) that include relative paths pointing into `docs/screenshots/`.

4. **test_gif_size_if_present**: If `docs/screenshots/globe-animated.gif` exists, assert its file
   size is ≤ 5 242 880 bytes (5 MB).

### Mocking Strategy
- No external HTTP calls needed — all checks are filesystem and string-parsing operations.
- Tests run against real captured files; if the screenshots haven't been captured yet, tests fail
  (Red) and remain Red until the artefacts are committed (Green).
- Frontend: N/A — no Vitest tests needed; this is a backend/CI verification spec.

### Coverage Expectation
- All four file-existence assertions pass once artefacts are captured and committed.
- README embedding test passes once `README.md` is updated.

---

## References
- roadmap.md row S11.3; CLAUDE.md project rules (no hardcoded tokens, offline Natural Earth imagery).
- S11.1 (README spec) — screenshots are embedded there.
- S10.3 (e2e test) — prerequisite; the live system must be running to capture screenshots.
