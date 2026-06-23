# Spec S8.1 — Risk-pair Polylines

## Overview
Create `frontend/src/risk.js` to fetch conjunction events from `GET /conjunctions` and render
a Cesium `PolylineGraphics` entity between each at-risk satellite pair on the globe. Polylines
are coloured by severity (red for very close, orange for within threshold) and carry a description
showing TCA, miss distance, and relative velocity. This module provides static polylines at the
current clock time; S8.2 adds dynamic `CallbackProperty` tracking as the clock advances.

## Dependencies
- S7.4 — SampledPositionProperty + clock animation (satellite entities have `.position.getValue(time)`)
- S6.4 — Conjunctions endpoint (`GET /conjunctions` returns `ConjunctionOut[]`)

## Target Location
`frontend/src/risk.js` (new file)

---

## Functional Requirements

### FR-1: Build conjunction description string
- **What**: `buildDescription(conj)` returns a human-readable multi-line string for the polyline
  entity's `description` property.
- **Inputs**: `conj` — one `ConjunctionOut` object with fields `sat_a_name`, `sat_b_name`, `tca`
  (ISO datetime string), `miss_km` (float), `rel_vel_kms` (float).
- **Outputs**: String containing all five fields; exact format is up to implementation but must
  include each field for the Cesium info-box to be useful.
- **Edge cases**: `tca` as a raw ISO string from the API; `miss_km` / `rel_vel_kms` formatted
  to 3 decimal places.

### FR-2: Severity colour mapping
- **What**: `severityColor(miss_km)` → `Cesium.Color` based on how close the approach is.
- **Rules**:
  - `miss_km ≤ 1.0` → `Cesium.Color.RED`
  - `1.0 < miss_km ≤ 5.0` → `Cesium.Color.ORANGE`
  - (All values above the 5 km RISK_THRESHOLD_KM will not reach this function in practice
    because `/conjunctions` already filters them out.)
- **Inputs**: `miss_km` (float)
- **Outputs**: `Cesium.Color` constant

### FR-3: Build polyline entity for one conjunction
- **What**: `buildPolylineEntity(posA, posB, conj)` creates a `Cesium.Entity` connecting two
  Cartesian3 positions with a coloured polyline.
- **Inputs**:
  - `posA`, `posB` — `Cesium.Cartesian3` for the two satellites
  - `conj` — `ConjunctionOut`
- **Outputs**: `Cesium.Entity` with:
  - `id`: `"risk-{conj.id}"`
  - `name`: `"{sat_a_name} ↔ {sat_b_name}"`
  - `description`: result of `buildDescription(conj)`
  - `polyline`: `Cesium.PolylineGraphics` with `positions: [posA, posB]`, `width: 2`,
    `material: Cesium.ColorMaterialProperty(severityColor(conj.miss_km))`
- **Edge cases**: Positions are plain Cartesian3 values; no validation needed (caller ensures
  they are non-null before calling this function).

### FR-4: Load risk polylines from a conjunction list
- **What**: `loadRiskPolylines(viewer, conjunctions)` iterates over conjunctions, resolves
  satellite entity positions, and adds polyline entities to the viewer.
- **Inputs**: `viewer` — Cesium Viewer; `conjunctions` — `ConjunctionOut[]`
- **Outputs**: integer count of polylines actually added
- **Logic**:
  1. For each conjunction, look up `viewer.entities.getById("sat-{conj.sat_a}")` and
     `viewer.entities.getById("sat-{conj.sat_b}")`.
  2. If either entity is missing, skip (graceful degradation — satellite may not be in current
     page/group).
  3. Call `entity.position.getValue(viewer.clock.currentTime)` on each. If either returns
     `null` / `undefined`, skip.
  4. Call `buildPolylineEntity(posA, posB, conj)` and add to `viewer.entities`.
- **Edge cases**: empty `conjunctions` → return 0 immediately; viewer with no sat entities → 0.

### FR-5: Clear risk polylines
- **What**: `clearRiskPolylines(viewer)` removes all entities whose `id` starts with `"risk-"`.
- **Inputs**: `viewer` — Cesium Viewer
- **Outputs**: void
- **Edge cases**: no risk entities present → no-op; satellite entities (id starts with `"sat-"`)
  must not be removed.

### FR-6: Fetch and render (top-level entry point)
- **What**: `fetchAndRenderRisk(viewer)` fetches `/conjunctions`, clears stale polylines, then
  renders the new set.
- **Inputs**: `viewer` — Cesium Viewer
- **Outputs**: Promise<int> — count of polylines added (0 on empty or error)
- **Logic**:
  1. `await fetchConjunctions()` from `api.js`.
  2. On fetch error: log with `console.error("[S8.1] ...")` and return 0 — no crash.
  3. On empty / null result: return 0.
  4. `clearRiskPolylines(viewer)` to remove stale lines.
  5. `loadRiskPolylines(viewer, conjunctions)` and return count.
- **Edge cases**: API returns `[]` (no conjunctions at threshold) → clear any stale polylines,
  return 0.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `risk.js` exports `buildDescription`, `severityColor`, `buildPolylineEntity`,
  `loadRiskPolylines`, `clearRiskPolylines`, and `fetchAndRenderRisk`.
- [ ] **Outcome 2**: For a fixture with two conjunctions (miss 0.5 km and miss 3.0 km), calling
  `loadRiskPolylines` adds exactly 2 entities with ids `risk-1` and `risk-2`.
- [ ] **Outcome 3**: The `risk-1` polyline entity uses `Cesium.Color.RED` and `risk-2` uses
  `Cesium.Color.ORANGE` based on their miss distances.
- [ ] **Outcome 4**: A conjunction whose satellite is absent from the viewer is silently skipped
  (count not incremented, no exception thrown).
- [ ] **Outcome 5**: `clearRiskPolylines` removes all `risk-*` entities and leaves `sat-*`
  entities untouched.
- [ ] **Outcome 6**: `fetchAndRenderRisk` returns 0 and does not throw when `fetchConjunctions`
  rejects.
- [ ] **Outcome 7**: All Vitest tests pass (`npm --prefix frontend run test`).

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
All tests live in `frontend/src/__tests__/risk.test.js`.

1. **test_buildDescription_contains_sat_names** — description string includes both `sat_a_name`
   and `sat_b_name`.
2. **test_buildDescription_contains_tca** — description includes the TCA ISO string.
3. **test_buildDescription_contains_miss_and_vel** — description includes `miss_km` and
   `rel_vel_kms` formatted to 3 decimal places.
4. **test_severityColor_very_close** — `miss_km ≤ 1.0` returns `Cesium.Color.RED`.
5. **test_severityColor_moderate** — `1.0 < miss_km ≤ 5.0` returns `Cesium.Color.ORANGE`.
6. **test_buildPolylineEntity_id** — entity `id` is `"risk-42"` for `conj.id = 42`.
7. **test_buildPolylineEntity_name** — entity `name` is `"{sat_a_name} ↔ {sat_b_name}"`.
8. **test_buildPolylineEntity_polyline_positions** — `polyline.positions` equals `[posA, posB]`.
9. **test_buildPolylineEntity_polyline_width** — `polyline.width === 2`.
10. **test_buildPolylineEntity_material_color** — `ColorMaterialProperty` called with RED for
    miss 0.5 km.
11. **test_loadRiskPolylines_adds_both_entities** — two valid conjunctions → 2 entities added,
    count = 2.
12. **test_loadRiskPolylines_skips_missing_sat** — `getById` returns null for one sat → that
    conjunction skipped, count = 1 not 2.
13. **test_loadRiskPolylines_skips_null_position** — `getValue` returns null → conjunction
    skipped.
14. **test_loadRiskPolylines_empty_input** — empty array → 0, no `entities.add` calls.
15. **test_clearRiskPolylines_removes_risk** — risk-* entities removed from viewer.
16. **test_clearRiskPolylines_keeps_sat_entities** — sat-* entities untouched.
17. **test_clearRiskPolylines_noop_when_empty** — no risk entities → no error.
18. **test_fetchAndRenderRisk_success** — fetches conjunctions, calls clearRiskPolylines, returns
    count.
19. **test_fetchAndRenderRisk_empty_result** — API returns `[]` → clears stale polylines,
    returns 0.
20. **test_fetchAndRenderRisk_fetch_error** — `fetchConjunctions` rejects → returns 0, no
    throw.

### Mocking Strategy
- **Cesium**: mock via `vi.hoisted` + `vi.mock("cesium", ...)`. Need:
  `Entity`, `PolylineGraphics`, `ColorMaterialProperty`, `Color` (RED, ORANGE).
- **api.js**: mock `fetchConjunctions` via `vi.mock("../api.js", ...)`.
- **Viewer**: use a local `makeViewer()` factory (same pattern as `cesiumView.test.js`) with
  `entities.getById`, `entities.add`, `entities.remove`, `entities.values`, and
  `clock.currentTime`.
- Satellite entities in the viewer need `position.getValue(time)` mocked to return a Cartesian3
  or null.

### Coverage Expectation
- All 6 exported functions have at least one test; every edge case (missing entity, null position,
  empty input, fetch error) is covered.

---

## References
- [roadmap.md](../../roadmap.md) — Phase 8, S8.1 row
- [CLAUDE.md](../../.claude/CLAUDE.md) — project rules, RISK_THRESHOLD_KM = 5 km
- [frontend/src/api.js](../../frontend/src/api.js) — `fetchConjunctions` wrapper
- [frontend/src/cesiumView.js](../../frontend/src/cesiumView.js) — entity id scheme (`sat-{catalog_no}`)
- [backend/app/models/schemas.py](../../backend/app/models/schemas.py) — `ConjunctionOut` fields
- [frontend/src/__tests__/cesiumView.test.js](../../frontend/src/__tests__/cesiumView.test.js) — test pattern to follow
