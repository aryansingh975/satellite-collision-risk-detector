import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  buildSearchIndex,
  searchEntities,
  selectAndFly,
  initSearch,
} from "../search.js";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

function makeEntity(catalogNo, name) {
  return {
    id: `sat-${catalogNo}`,
    name,
    properties: { catalog_no: catalogNo },
  };
}

const ISS = makeEntity(25544, "ISS (ZARYA)");
const DEBRIS_A = makeEntity(40000, "DEBRIS-A");
const DEBRIS_B = makeEntity(41000, "DEBRIS-B");
const ENTITIES = [ISS, DEBRIS_A, DEBRIS_B];

function makeViewer() {
  return {
    selectedEntity: undefined,
    flyTo: vi.fn(() => Promise.resolve()),
  };
}

// ─── S8.3 FR-1 — buildSearchIndex ────────────────────────────────────────────

describe("S8.3 FR-1 — buildSearchIndex", () => {
  it("test_buildSearchIndex_empty", () => {
    const index = buildSearchIndex([]);
    const size = index.length ?? index.size;
    expect(size).toBe(0);
  });

  it("test_buildSearchIndex_nonEmpty", () => {
    const index = buildSearchIndex(ENTITIES);
    const size = index.length ?? index.size;
    expect(size).toBe(3);
    const entities = index.map((e) => e.entity);
    expect(entities).toContain(ISS);
    expect(entities).toContain(DEBRIS_A);
    expect(entities).toContain(DEBRIS_B);
  });
});

// ─── S8.3 FR-2 — searchEntities ──────────────────────────────────────────────

describe("S8.3 FR-2 — searchEntities", () => {
  let index;

  beforeEach(() => {
    index = buildSearchIndex(ENTITIES);
  });

  it("test_searchEntities_nameSubstring", () => {
    const results = searchEntities("ISS", index);
    expect(results).toContain(ISS);
    expect(results).not.toContain(DEBRIS_A);
    expect(results).not.toContain(DEBRIS_B);
  });

  it("test_searchEntities_nameSubstring_caseInsensitive", () => {
    const results = searchEntities("iss", index);
    expect(results).toContain(ISS);
  });

  it("test_searchEntities_catalogNo", () => {
    const results = searchEntities("25544", index);
    expect(results).toContain(ISS);
    expect(results).not.toContain(DEBRIS_A);
  });

  it("test_searchEntities_empty_query", () => {
    const results = searchEntities("", index);
    expect(results).toHaveLength(3);
    expect(results).toContain(ISS);
    expect(results).toContain(DEBRIS_A);
    expect(results).toContain(DEBRIS_B);
  });

  it("test_searchEntities_whitespace_query", () => {
    const results = searchEntities("   ", index);
    expect(results).toHaveLength(3);
  });

  it("test_searchEntities_noMatch", () => {
    const results = searchEntities("XYZNONEXISTENT", index);
    expect(results).toHaveLength(0);
  });
});

// ─── S8.3 FR-3 — selectAndFly ────────────────────────────────────────────────

describe("S8.3 FR-3 — selectAndFly", () => {
  let viewer;

  beforeEach(() => {
    viewer = makeViewer();
  });

  it("test_selectAndFly_validEntity", async () => {
    const p = selectAndFly(ISS, viewer);
    expect(viewer.selectedEntity).toBe(ISS);
    expect(viewer.flyTo).toHaveBeenCalledOnce();
    expect(viewer.flyTo).toHaveBeenCalledWith(ISS);
    await expect(p).resolves.toBeUndefined();
  });

  it("test_selectAndFly_null", async () => {
    viewer.selectedEntity = ISS;
    const p = selectAndFly(null, viewer);
    expect(viewer.selectedEntity).toBeUndefined();
    expect(viewer.flyTo).not.toHaveBeenCalled();
    await expect(p).resolves.toBeUndefined();
  });

  it("test_selectAndFly_undefined", async () => {
    viewer.selectedEntity = ISS;
    const p = selectAndFly(undefined, viewer);
    expect(viewer.selectedEntity).toBeUndefined();
    expect(viewer.flyTo).not.toHaveBeenCalled();
    await expect(p).resolves.toBeUndefined();
  });
});

// ─── S8.3 FR-4 — initSearch ──────────────────────────────────────────────────

describe("S8.3 FR-4 — initSearch", () => {
  let viewer;

  beforeEach(() => {
    viewer = makeViewer();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("test_initSearch_missingDom", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(() => initSearch(viewer, ENTITIES)).not.toThrow();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("test_initSearch_missing_results", () => {
    document.body.innerHTML = '<input id="search-input">';
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(() => initSearch(viewer, ENTITIES)).not.toThrow();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("test_initSearch_typing", () => {
    document.body.innerHTML = `
      <input id="search-input">
      <ul id="search-results"></ul>
    `;
    initSearch(viewer, ENTITIES);

    const input = document.getElementById("search-input");
    const results = document.getElementById("search-results");

    input.value = "ISS";
    input.dispatchEvent(new Event("input"));

    const items = results.querySelectorAll("li");
    expect(items.length).toBeGreaterThan(0);
    const texts = [...items].map((li) => li.textContent);
    expect(texts.some((t) => t.includes("ISS (ZARYA)"))).toBe(true);
  });

  it("test_initSearch_noMatch", () => {
    document.body.innerHTML = `
      <input id="search-input">
      <ul id="search-results"></ul>
    `;
    initSearch(viewer, ENTITIES);

    const input = document.getElementById("search-input");
    const results = document.getElementById("search-results");

    input.value = "XYZNONEXISTENT";
    input.dispatchEvent(new Event("input"));

    const items = results.querySelectorAll("li");
    expect(items.length).toBe(1);
    expect(items[0].textContent).toContain("No results found");
  });

  it("test_initSearch_click", async () => {
    document.body.innerHTML = `
      <input id="search-input">
      <ul id="search-results"></ul>
    `;
    initSearch(viewer, ENTITIES);

    const input = document.getElementById("search-input");
    const results = document.getElementById("search-results");

    input.value = "ISS";
    input.dispatchEvent(new Event("input"));

    const items = results.querySelectorAll("li");
    items[0].click();

    expect(viewer.flyTo).toHaveBeenCalledOnce();
    expect(viewer.flyTo).toHaveBeenCalledWith(ISS);
    expect(viewer.selectedEntity).toBe(ISS);
  });

  it("test_initSearch_replaces_results_on_each_input", () => {
    document.body.innerHTML = `
      <input id="search-input">
      <ul id="search-results"></ul>
    `;
    initSearch(viewer, ENTITIES);

    const input = document.getElementById("search-input");
    const results = document.getElementById("search-results");

    input.value = "ISS";
    input.dispatchEvent(new Event("input"));
    const firstCount = results.querySelectorAll("li").length;

    input.value = "DEBRIS";
    input.dispatchEvent(new Event("input"));
    const secondCount = results.querySelectorAll("li").length;

    // DEBRIS matches DEBRIS-A and DEBRIS-B → 2 results
    expect(secondCount).toBe(2);
    // First result set (ISS) was replaced
    expect(firstCount).toBe(1);
  });
});
