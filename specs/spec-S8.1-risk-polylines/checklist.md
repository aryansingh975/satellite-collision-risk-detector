# Checklist — Spec S8.1: Risk-pair Polylines

## Phase 1: Setup & Dependencies
- [x] Verify S7.4 is `done` (SampledPositionProperty + clock animation — entity positions resolve via `.getValue(time)`)
- [x] Verify S6.4 is `done` (conjunctions endpoint — `GET /conjunctions` returns `ConjunctionOut[]`)
- [x] Confirm `frontend/src/risk.js` does not yet exist (new file)
- [x] Confirm test file `frontend/src/__tests__/risk.test.js` does not yet exist (new file)
- [x] No new npm packages needed — Cesium and Vitest are already in `package.json`

## Phase 2: Tests First (TDD)
- [x] Create `frontend/src/__tests__/risk.test.js`
- [x] Write `vi.hoisted` + `vi.mock("cesium", ...)` block (Entity, PolylineGraphics, ColorMaterialProperty, Color.RED, Color.ORANGE)
- [x] Write `vi.mock("../api.js", ...)` block mocking `fetchConjunctions`
- [x] Write `makeViewer()` factory with `getById`, `add`, `remove`, `values`, `clock.currentTime`
- [x] Write failing tests for FR-1 (`buildDescription`): tests 1–3
- [x] Write failing tests for FR-2 (`severityColor`): tests 4–5
- [x] Write failing tests for FR-3 (`buildPolylineEntity`): tests 6–10
- [x] Write failing tests for FR-4 (`loadRiskPolylines`): tests 11–14
- [x] Write failing tests for FR-5 (`clearRiskPolylines`): tests 15–17
- [x] Write failing tests for FR-6 (`fetchAndRenderRisk`): tests 18–20
- [x] Run `npm --prefix frontend run test` — expect all new tests to fail (Red)

## Phase 3: Implementation
- [x] Create `frontend/src/risk.js` with imports: `* as Cesium from "cesium"`, `{ fetchConjunctions } from "./api.js"`
- [x] Implement `buildDescription(conj)` — FR-1 → tests 1–3 pass (Green)
- [x] Implement `severityColor(miss_km)` — FR-2 → tests 4–5 pass (Green)
- [x] Implement `buildPolylineEntity(posA, posB, conj)` — FR-3 → tests 6–10 pass (Green)
- [x] Implement `loadRiskPolylines(viewer, conjunctions)` — FR-4 → tests 11–14 pass (Green)
- [x] Implement `clearRiskPolylines(viewer)` — FR-5 → tests 15–17 pass (Green)
- [x] Implement `fetchAndRenderRisk(viewer)` — FR-6 → tests 18–20 pass (Green)
- [x] Run full Vitest suite — all 20 new tests green, no regressions

## Phase 4: Integration
- [x] Import and call `fetchAndRenderRisk(viewer)` from `frontend/src/main.js` after `loadAnimatedTracks` completes
- [x] Verify `risk.js` is not imported by `cesiumView.js` (keep modules decoupled — main.js orchestrates)
- [x] Run lint: `npm --prefix frontend run lint` (Prettier) — no errors
- [x] Run full Vitest suite again after wiring

## Phase 5: Verification
- [x] Outcome 1: all 6 functions exported from `risk.js` ✓
- [x] Outcome 2: fixture with 2 conjunctions → 2 `risk-*` entities ✓
- [x] Outcome 3: miss 0.5 km → RED; miss 3.0 km → ORANGE ✓
- [x] Outcome 4: missing satellite entity → conjunction silently skipped ✓
- [x] Outcome 5: `clearRiskPolylines` removes risk-* only ✓
- [x] Outcome 6: fetch error → returns 0, no throw ✓
- [x] Outcome 7: `npm --prefix frontend run test` all pass ✓
- [x] No hardcoded secrets or tokens
- [x] No Cesium ion token used
- [x] Update `roadmap.md` status: `spec-written` → `done` (after implement + verify pass)
