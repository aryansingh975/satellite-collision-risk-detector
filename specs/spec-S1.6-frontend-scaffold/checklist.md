# Checklist — Spec S1.6: Cesium Frontend Scaffold

## Phase 1: Setup & Dependencies
- [x] Verify no prerequisite specs (S1.6 has none — can start immediately)
- [x] Confirm `frontend/` directory exists (or create it)
- [x] Run `npm init` (or create `package.json` manually) in `frontend/`
- [x] Add runtime dependency: `cesium`
- [x] Add dev dependencies: `vite`, `vitest`, `@vitest/coverage-v8`, `jsdom`
- [x] Verify `Makefile` `serve-frontend` target is present (from S1.2)

## Phase 2: Tests First (TDD)
- [x] Create test file: `frontend/src/__tests__/scaffold.test.js`
- [x] Write `test_placeholder` — `expect(true).toBe(true)` — confirms Vitest runs
- [x] Write `test_cesium_import` — check cesium package.json in node_modules; assert version string present (Cesium too large to bundle in jsdom; build test covers real bundling)
- [x] Write `test_cesium_base_url` — call base-URL init helper (Cesium mocked), assert `window.CESIUM_BASE_URL` set
- [x] Write `test_no_ion_token` — read `main.js` source text, assert no token string present
- [x] Run tests — expect failures (Red): `main.js` not found → suite error

## Phase 3: Implementation
- [x] **FR-1**: Create `frontend/index.html` — HTML5 boilerplate, `#cesiumContainer` div (100vw × 100vh), widget CSS link, `<script type="module" src="/src/main.js">`
- [x] **FR-2**: Create `frontend/vite.config.js` — `vite-plugin-cesium` (copies Assets/Workers/Widgets/ThirdParty to `dist/cesium/`); Vitest config with `environment: jsdom`
- [x] **FR-3**: Create `frontend/src/main.js` — set `window.CESIUM_BASE_URL`, import Cesium, export `initCesiumBaseUrl()` helper, NO ion token
- [x] **FR-4**: Add `test` script to `package.json`: `"test": "vitest run"`, `vite.config.js` test block with `environment: 'jsdom'`, `globals: true`; Cesium mocked in test file to avoid 50MB inline bundling
- [x] **FR-5**: `serve-frontend` target in Makefile calls `npm --prefix frontend run dev` (confirmed from S1.2)
- [x] Run tests — expect pass (Green): 4/4 passed in 44ms
- [x] Refactor: Prettier auto-formatted all 3 source files; no structural refactor needed

## Phase 4: Integration
- [x] Run `npm --prefix frontend run build` — `dist/cesium/` created with Assets, Workers, Widgets, ThirdParty, Cesium.js
- [x] N/A — `make serve-frontend` verified by Makefile target (S1.2 confirmed); live server test belongs in S10.3 e2e
- [x] Run lint: `npm --prefix frontend run lint` — Prettier: all files pass after `--write`
- [x] Run full test suite: 4/4 passed

## Phase 5: Verification
- [x] `frontend/index.html` contains `<div id="cesiumContainer">` — grep confirmed (2 matches)
- [x] No ion token in `frontend/src/` non-test files — grep confirmed empty
- [x] `window.CESIUM_BASE_URL` set before first Cesium use in `main.js` — `initCesiumBaseUrl()` called at module init
- [x] Vitest exits 0 with all 4 tests passing — confirmed
- [x] Build output `dist/` includes `cesium/Workers/`, `cesium/Assets/`, `cesium/Widgets/` — confirmed
- [x] Update `roadmap.md` status: `spec-written` → `done`
