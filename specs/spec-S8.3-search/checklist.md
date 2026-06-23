# Checklist — Spec S8.3: Search & Select

## Phase 1: Setup & Dependencies
- [x] Verify S7.3 (Satellite entities) is `done` — entities are in `_entityRegistry`
- [x] Create `frontend/src/search.js` (new module)
- [x] Create `frontend/src/__tests__/search.test.js` (new test file)
- [x] Confirm Vitest + jsdom are configured (`frontend/vite.config.js` or `vitest.config.js`)
- [x] No new npm dependencies needed (pure DOM + Cesium stub)

## Phase 2: Tests First (TDD)
- [x] Write test file: `frontend/src/__tests__/search.test.js`
- [x] test_buildSearchIndex_empty — empty input → empty index
- [x] test_buildSearchIndex_nonEmpty — index maps catalog_no to entity
- [x] test_searchEntities_nameSubstring — case-insensitive name match
- [x] test_searchEntities_catalogNo — exact numeric NORAD id match
- [x] test_searchEntities_empty_query — `""` returns all
- [x] test_searchEntities_whitespace_query — `"  "` returns all
- [x] test_searchEntities_noMatch — `"XYZNONEXISTENT"` returns `[]`
- [x] test_selectAndFly_validEntity — sets selectedEntity, calls flyTo
- [x] test_selectAndFly_null — clears selectedEntity, resolves without flyTo
- [x] test_initSearch_missingDom — no throw when `#search-input` absent
- [x] test_initSearch_typing — input event populates `#search-results`
- [x] test_initSearch_noMatch — shows "No results found" li
- [x] test_initSearch_click — click on result calls flyTo with correct entity
- [x] Run tests: `npm --prefix frontend run test` — expect failures (Red)

## Phase 3: Implementation
- [x] Implement `buildSearchIndex(entities)` — build Map keyed by entity
- [x] Implement `searchEntities(query, index)` — name substring + catalog_no exact match
- [x] Implement `selectAndFly(entity, viewer)` — flyTo + selectedEntity
- [x] Implement `initSearch(viewer, entities)` — DOM wiring, input event, results list, click handler
- [x] Run tests: `npm --prefix frontend run test` — expect pass (Green) — 17/17 ✓
- [x] Refactor if needed (no logic changes, only clarity)

## Phase 4: Integration
- [x] Wire into `frontend/src/main.js`: import `initSearch`, call after `loadSatelliteEntities`
- [x] Ensure `index.html` has `<input id="search-input">` and `<ul id="search-results">` elements
- [x] Run lint: `npm --prefix frontend run lint` — clean ✓
- [x] Run full test suite: `npm --prefix frontend run test` — 104/104 ✓

## Phase 5: Verification
- [x] All 8 tangible outcomes pass
- [x] No hardcoded secrets or tokens
- [x] Missing DOM elements log a warning (not an uncaught exception)
- [x] Empty / no-match queries handled without errors
- [x] Update roadmap.md status: `spec-written` → `done` (after verify-spec passes)
