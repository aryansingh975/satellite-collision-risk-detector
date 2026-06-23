# Spec S8.3 — Search & Select

## Overview
Provides a search-and-select UI that lets users filter the satellite entity collection by name or
NORAD catalog number. When the user picks a match, the Cesium viewer flies to that entity and sets
it as `selectedEntity` so the orbit path and (later) info panel react. Empty queries and no-match
queries are handled gracefully without throwing.

## Dependencies
- S7.3 — Satellite entities (entities added to the viewer and tracked in `_entityRegistry`)

## Target Location
`frontend/src/search.js`

---

## Functional Requirements

### FR-1: Search index build
- **What**: Build an index from the live entity collection so the search function has a fast lookup
  table rather than scanning `viewer.entities.values` on every keystroke.
- **Inputs**: An iterable of Cesium `Entity` objects (the return value of `loadSatelliteEntities`);
  each entity has `entity.id` (`"sat-<catalogNo>"`), `entity.name` (satellite name string), and
  `entity.properties` (raw satellite data including `catalog_no`).
- **Outputs**: Returns the index (an array or Map) for later use by `searchEntities`.
- **Edge cases**: Empty entity list → returns empty index without throwing.

### FR-2: Text search with dual-field matching
- **What**: `searchEntities(query, index)` filters the index for entities whose name contains
  `query` (case-insensitive substring) **or** whose `catalog_no` string equals `query` exactly
  (after stripping whitespace).
- **Inputs**: `query` (string), `index` (built by FR-1).
- **Outputs**: Array of matching `Entity` objects, may be empty.
- **Edge cases**:
  - Empty string → return all entities (no filtering).
  - Whitespace-only string → treated as empty.
  - Numeric string that matches a catalog number exactly (e.g. `"25544"`) → returns ISS even if
    "25544" does not appear in the name.
  - Query matches multiple entities → all matches returned.
  - No match → return `[]` (not an error).

### FR-3: Select and fly-to
- **What**: `selectAndFly(entity, viewer)` sets `viewer.selectedEntity = entity` and calls
  `viewer.flyTo(entity)` returning its promise.
- **Inputs**: A Cesium `Entity`, the Cesium `Viewer` instance.
- **Outputs**: Returns the Promise from `viewer.flyTo`.
- **Edge cases**: `entity` is `null` / `undefined` → clear `viewer.selectedEntity` (set to
  `undefined`) and return a resolved promise without calling `flyTo`.

### FR-4: Search input wiring
- **What**: `initSearch(viewer, entities)` attaches an `input` event listener to the
  `#search-input` DOM element. On each input event it calls `searchEntities`, updates the
  `#search-results` list with one `<li>` per match (displaying the satellite name and catalog
  number), and on click of a result item calls `selectAndFly` for that entity.
- **Inputs**: `viewer` (Cesium Viewer), `entities` (array from `loadSatelliteEntities`).
- **Outputs**: No return value; mutates the DOM.
- **Edge cases**:
  - `#search-input` does not exist in the DOM → log a warning and return without throwing.
  - `#search-results` does not exist → log a warning and return without throwing.
  - Rapid successive keystrokes → each input event replaces the previous results list completely.
  - Empty results → `#search-results` shows a single disabled `<li>` with "No results found".

---

## Tangible Outcomes

- [ ] **Outcome 1**: `buildSearchIndex([])` returns an empty index without throwing.
- [ ] **Outcome 2**: `searchEntities("ISS", index)` with an index containing an entity named
  "ISS (ZARYA)" returns that entity.
- [ ] **Outcome 3**: `searchEntities("25544", index)` returns the entity whose catalog_no is 25544
  even if "25544" is not in the name.
- [ ] **Outcome 4**: `searchEntities("", index)` returns all entities.
- [ ] **Outcome 5**: `searchEntities("XYZNONEXISTENT", index)` returns `[]`.
- [ ] **Outcome 6**: `selectAndFly(null, viewer)` clears `viewer.selectedEntity` and returns a
  resolved promise without throwing.
- [ ] **Outcome 7**: `initSearch` with a missing `#search-input` logs a warning and does not
  throw.
- [ ] **Outcome 8**: `initSearch` typing into `#search-input` populates `#search-results` with the
  correct matching satellite names.

---

## Test-Driven Requirements

### Tests to Write First (Red → Green)
1. **test_buildSearchIndex_empty**: `buildSearchIndex([])` returns an index with length/size 0.
2. **test_buildSearchIndex_nonEmpty**: Index built from a fixture entity array has one entry per
   entity; looking up by `catalog_no` finds the entity.
3. **test_searchEntities_nameSubstring**: Case-insensitive substring match on name works.
4. **test_searchEntities_catalogNo**: Exact numeric catalog-number match works.
5. **test_searchEntities_empty_query**: Empty string returns all entities.
6. **test_searchEntities_whitespace_query**: Whitespace-only string returns all entities.
7. **test_searchEntities_noMatch**: Returns `[]` for a query matching nothing.
8. **test_selectAndFly_validEntity**: Calls `viewer.flyTo(entity)` and sets `viewer.selectedEntity`.
9. **test_selectAndFly_null**: Does not call `viewer.flyTo`; clears `selectedEntity`; resolves.
10. **test_initSearch_missingDom**: Does not throw when `#search-input` is absent.
11. **test_initSearch_typing**: Typing into `#search-input` renders matching `<li>` elements in
    `#search-results`.
12. **test_initSearch_noMatch**: Shows "No results found" `<li>` when query has no matches.
13. **test_initSearch_click**: Clicking a result `<li>` calls `viewer.flyTo` with the correct entity.

### Mocking Strategy
- Cesium `Viewer`: plain JS object stub with `{ selectedEntity: undefined, flyTo: vi.fn(() => Promise.resolve()) }`.
- Cesium `Entity`: plain objects `{ id: "sat-25544", name: "ISS (ZARYA)", properties: { catalog_no: 25544 } }`.
- DOM: jsdom (provided by Vitest's `environment: "jsdom"` setting); create `#search-input` and
  `#search-results` in `beforeEach`; clean up in `afterEach`.
- No real Cesium import needed — all Cesium interaction is via the stub viewer.

### Coverage Expectation
- All public exports (`buildSearchIndex`, `searchEntities`, `selectAndFly`, `initSearch`) have at
  least one test; every edge case in FR-1 through FR-4 is exercised.

---

## References
- roadmap.md row S8.3 — Feature: Search & select; Notes: filter by name/NORAD id; `viewer.flyTo`;
  `selectedEntity`; empty/no-match handled.
- CLAUDE.md — frontend test tooling: Vitest + jsdom; no real API calls in unit tests.
