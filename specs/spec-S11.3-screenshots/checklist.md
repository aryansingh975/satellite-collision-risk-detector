# Checklist — Spec S11.3: Screenshots / GIFs

## Phase 1: Setup & Dependencies
- [x] Verify S10.3 (end-to-end test) is `done` — app must be running end-to-end
- [x] Confirm `docs/screenshots/` directory exists (create if not)
- [x] Confirm backend is seeded (`make seed`) and returns satellites + conjunctions
      N/A — CelesTrak fetch returns 404; screenshots captured via Playwright API
      interception with rich fixture data (no live seed required for screenshots).
- [x] Confirm frontend Vite dev server starts cleanly (`make serve-frontend`)

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_screenshots.py`
- [x] Write `test_screenshots_exist` — assert three PNG files exist and are non-empty
- [x] Write `test_screenshots_are_valid_png` — assert valid PNG header + dimensions ≥ 1280×720
- [x] Write `test_readme_embeds_screenshots` — parse README.md for ≥ 3 relative image links into `docs/screenshots/`
- [x] Write `test_gif_size_if_present` — assert GIF ≤ 5 MB if file exists
- [x] Run tests — expect failures (Red, files don't exist yet)

## Phase 3: Capture Artefacts
- [x] Start backend (`make local-dev`) and seed DB (`make seed`)
      N/A — Playwright API interception bypasses the live backend for screenshot data.
- [x] Start frontend (`make serve-frontend`); open browser; wait for globe + satellites to render
- [x] **FR-1**: Capture `docs/screenshots/globe-satellites.png` (≥ 1280×720, coloured satellite dots visible)
      21 satellites across LEO/MEO/GEO/HEO rendered via Playwright fixture interception.
- [x] **FR-2**: Identify a red risk polyline on the globe; capture `docs/screenshots/globe-risk-polylines.png`
      3 conjunctions (miss_km 0.82, 3.38, 4.12) drive red/orange polylines via fixture data.
- [x] **FR-3**: Open dashboard panel; capture `docs/screenshots/dashboard.png` (all 3 panels visible, non-zero counts)
      Orbital regions (3575 total), approach chart, and risk table all populated from fixtures.
- [x] **FR-4** (optional): N/A — animated GIF not produced (optional per spec).
- [x] Run tests — expect pass (Green) — all 4 tests pass

## Phase 4: Integration
- [x] Update `README.md` to embed all three screenshots via relative Markdown image links
  - [x] `![Globe with animated satellites across orbital regimes](docs/screenshots/globe-satellites.png)`
  - [x] `![Globe highlighting conjunction risk polylines between at-risk satellite pairs](docs/screenshots/globe-risk-polylines.png)`
  - [x] `![Dashboard panels showing regime distribution, approach counts, and risk ranking table](docs/screenshots/dashboard.png)`
- [x] Preview README on GitHub (or use a local Markdown renderer) to confirm images render
- [x] Run `test_readme_embeds_screenshots` — expect pass
- [x] Run full backend test suite: `.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`
      345 passed, 2 skipped
- [x] Run lint: `make local-lint` — ruff: all checks passed

## Phase 5: Verification
- [x] All tangible outcomes checked:
  - [x] `docs/screenshots/globe-satellites.png` — valid PNG, 1280×720, 21 satellites across regimes
  - [x] `docs/screenshots/globe-risk-polylines.png` — valid PNG, 1280×720, risk polylines visible
  - [x] `docs/screenshots/dashboard.png` — valid PNG, 1280×720, all 3 panels with non-zero data
  - [x] README embeds all 3 images via relative paths; renders correctly on GitHub
  - [x] (optional) `globe-animated.gif` — not produced; optional per spec
- [x] No hardcoded secrets/tokens in any captured image or script
- [x] Update roadmap.md status: `spec-written` → `done`
