/**
 * Build a lookup index from the entity list returned by loadSatelliteEntities.
 * Avoids scanning viewer.entities.values on every keystroke.
 *
 * @param {Array} entities - Cesium Entity objects (id, name, properties.catalog_no)
 * @returns {Array<{entity, nameNorm, catalogNoStr}>}
 */
export function buildSearchIndex(entities) {
  return entities.map((entity) => ({
    entity,
    nameNorm: (entity.name ?? "").toLowerCase(),
    catalogNoStr: String(entity.properties?.catalog_no ?? ""),
  }));
}

/**
 * Filter the index for entities matching query by name (case-insensitive substring)
 * or by exact catalog number string. Empty / whitespace-only query returns all.
 *
 * @param {string} query
 * @param {Array} index - from buildSearchIndex
 * @returns {Array} matching Entity objects
 */
export function searchEntities(query, index) {
  const trimmed = query.trim();
  if (trimmed === "") return index.map((e) => e.entity);
  const lower = trimmed.toLowerCase();
  return index
    .filter((e) => e.nameNorm.includes(lower) || e.catalogNoStr === trimmed)
    .map((e) => e.entity);
}

/**
 * Set viewer.selectedEntity and fly to the entity.
 * Passing null/undefined clears the selection and returns a resolved promise.
 *
 * @param {object|null|undefined} entity
 * @param {object} viewer - Cesium Viewer (or stub)
 * @returns {Promise}
 */
export function selectAndFly(entity, viewer) {
  if (entity == null) {
    viewer.selectedEntity = undefined;
    return Promise.resolve();
  }
  viewer.selectedEntity = entity;
  return viewer.flyTo(entity);
}

/**
 * Wire the #search-input element to filter satellite entities and populate
 * #search-results. Clicking a result selects and flies to that satellite.
 *
 * @param {object} viewer - Cesium Viewer
 * @param {Array} entities - from loadSatelliteEntities
 */
export function initSearch(viewer, entities) {
  const input = document.getElementById("search-input");
  if (!input) {
    console.warn("[S8.3] initSearch: #search-input not found in DOM");
    return;
  }
  const resultsList = document.getElementById("search-results");
  if (!resultsList) {
    console.warn("[S8.3] initSearch: #search-results not found in DOM");
    return;
  }

  const index = buildSearchIndex(entities);

  input.addEventListener("input", () => {
    const matches = searchEntities(input.value, index);
    resultsList.innerHTML = "";

    if (matches.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No results found";
      li.setAttribute("disabled", "true");
      resultsList.appendChild(li);
      return;
    }

    for (const entity of matches) {
      const li = document.createElement("li");
      const catNo = entity.properties?.catalog_no ?? "";
      li.textContent = `${entity.name} (${catNo})`;
      li.addEventListener("click", () => selectAndFly(entity, viewer));
      resultsList.appendChild(li);
    }
  });
}
