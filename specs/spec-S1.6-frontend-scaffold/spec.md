# Spec S1.6 — Cesium Frontend Scaffold

## Overview
Bootstrap the frontend project: a minimal HTML page with a `#cesiumContainer` div, CesiumJS loaded via npm + Vite (or CDN fallback), and Vitest configured for unit testing. This scaffold has no ion token and does not render any satellite data — it is the clean canvas that S7.1 (Cesium globe bootstrap) and all subsequent frontend specs build on.

## Dependencies
None — S1.6 has no prerequisite specs.

## Target Location
- `frontend/index.html`
- `frontend/src/main.js`
- `frontend/package.json` (Vite + Vitest dev tooling)
- `frontend/vite.config.js`

---

## Functional Requirements

### FR-1: HTML entry point with `#cesiumContainer`
- **What**: `frontend/index.html` must be a valid HTML5 document that includes a `<div id="cesiumContainer">` filling the viewport, a `<script type="module" src="/src/main.js">` tag, and a `<link>` to the CesiumJS widget CSS (`Widgets/widgets.css`).
- **Inputs**: None (static file served by Vite).
- **Outputs**: Browser loads without JS errors; `document.getElementById('cesiumContainer')` resolves to a non-null element.
- **Edge cases**: Missing `#cesiumContainer` breaks S7.1; CSS must make the container full-screen (100vw × 100vh, margin 0).

### FR-2: CesiumJS available as an ES module via Vite
- **What**: CesiumJS installed as an npm package (`cesium`) and importable in `frontend/src/main.js` as `import * as Cesium from 'cesium'`. The Vite config must copy Cesium's static assets (Workers, Assets, Widgets, ThirdParty) to the build output so the engine can locate them at runtime.
- **Inputs**: `npm install cesium` in `frontend/`.
- **Outputs**: `import * as Cesium from 'cesium'` resolves without error; `Cesium.VERSION` is a non-empty string accessible at runtime.
- **Edge cases**: Missing `CESIUM_BASE_URL` setting causes Workers to 404 at runtime — set `window.CESIUM_BASE_URL = '/cesium/'` (or equivalent) before the first Cesium import, and configure Vite to serve assets from that path.

### FR-3: `main.js` — minimal entry, no ion token
- **What**: `frontend/src/main.js` imports Cesium (to confirm the import chain resolves), sets `CESIUM_BASE_URL`, and exports nothing further. It must NOT set `Cesium.Ion.defaultAccessToken` — that belongs in S7.1 or `.env`. A console log confirming Cesium loaded is acceptable.
- **Inputs**: Cesium npm package.
- **Outputs**: Page loads; browser console shows no uncaught errors; no ion token is present anywhere in source.
- **Edge cases**: A hardcoded ion token here would violate the CLAUDE.md rule; reject any token constant.

### FR-4: Vitest configured for frontend unit tests
- **What**: `vitest` and `@vitest/coverage-v8` (or equivalent) are listed as dev dependencies in `frontend/package.json`. `vite.config.js` (or a dedicated `vitest.config.js`) includes a `test` block with `environment: 'jsdom'`, `globals: true`, and a `setupFiles` pointer if needed. `npm --prefix frontend run test` (mapped to `vitest run`) executes and exits 0 on an empty test suite.
- **Inputs**: Dev dependency install.
- **Outputs**: `npm --prefix frontend run test` passes; at least one placeholder test file (`frontend/src/__tests__/placeholder.test.js`) asserts `true === true` and passes.
- **Edge cases**: Vitest must be configured to handle Cesium's ESM-only package without crashing (alias or exclude in the test config); otherwise unrelated test files will fail to import.

### FR-5: `make serve-frontend` starts the Vite dev server
- **What**: The existing `Makefile` target `serve-frontend` must run `npm --prefix frontend run dev` (or `vite --config frontend/vite.config.js`). The dev server must serve `index.html` at `http://localhost:5173` (Vite default) with HMR enabled.
- **Inputs**: Vite installed; `Makefile` target already declared in S1.2.
- **Outputs**: `make serve-frontend` starts without error; `curl http://localhost:5173` returns HTML containing `cesiumContainer`.
- **Edge cases**: Port conflict — Vite will auto-increment; document the default port in comments or README.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `frontend/index.html` exists, contains `<div id="cesiumContainer">`, and passes HTML5 validation (no fatal parse errors).
- [ ] **Outcome 2**: `npm --prefix frontend install && npm --prefix frontend run build` completes without error; the `dist/` output contains `cesium/` asset subdirectory.
- [ ] **Outcome 3**: `npm --prefix frontend run test` exits 0; placeholder test passes.
- [ ] **Outcome 4**: No ion token string appears anywhere in `frontend/src/` source files (`grep -r 'Ion.defaultAccessToken\|eyJhbGci' frontend/src` returns empty).
- [ ] **Outcome 5**: `window.CESIUM_BASE_URL` is set before any Cesium import; Cesium Workers load without 404s when the dev server is running.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_cesium_import**: Import `* as Cesium from 'cesium'` inside a Vitest test and assert `typeof Cesium.VERSION === 'string'` and `Cesium.VERSION.length > 0`. This confirms the package resolves.
2. **test_cesium_base_url**: In a jsdom environment, call the `initCesiumBaseUrl()` helper (extracted from `main.js`) and assert `window.CESIUM_BASE_URL` is set to a non-empty string before the assertion.
3. **test_no_ion_token**: Read `frontend/src/main.js` as a string (via `fs.readFileSync` in the test) and assert it does NOT contain `Ion.defaultAccessToken` or any JWT-like token string.
4. **test_placeholder**: A trivial `expect(true).toBe(true)` to confirm Vitest runs at all.

### Mocking Strategy
- No external HTTP in these tests — Cesium is a local npm package.
- Mock `window.CESIUM_BASE_URL` via jsdom's `global.window` if needed.
- `fs.readFileSync` to inspect source text (no network required).

### Coverage Expectation
- All four public behaviors (Cesium import resolution, base-URL init, no-token invariant, dev-server config) have at least one test; edge cases (token absent, CESIUM_BASE_URL defined) covered.

---

## References
- `roadmap.md` — Phase 1 table, S1.6 row + Notes; Master Spec Index
- `CLAUDE.md` — "NEVER hardcode secrets/tokens"; `make serve-frontend` target; frontend tech stack (CesiumJS + Vite + Vitest)
- CesiumJS Vite integration guide (cesium.com/learn/cesiumjs-learn/cesiumjs-quickstart)
