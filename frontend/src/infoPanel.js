// infoPanel.js — S8.4
import { fetchSatellite, fetchConjunctions } from "./api.js";

function fmt(val, dp) {
  return val === null || val === undefined ? "—" : Number(val).toFixed(dp);
}

function computePeriod(meanMotion) {
  if (!meanMotion || meanMotion <= 0) return "—";
  return (1440 / meanMotion).toFixed(2);
}

function set(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function populateDetails(sat) {
  set("info-name", sat.name ?? "—");
  set("info-catalog-no", sat.catalog_no != null ? String(sat.catalog_no) : "—");
  set("info-intl-designator", sat.intl_designator ?? "—");
  set("info-epoch", sat.epoch ?? "—");
  set("info-regime", sat.regime ?? "—");
  set("info-a-km", fmt(sat.a_km, 2));
  set("info-ecc", fmt(sat.ecc, 6));
  set("info-inc-deg", fmt(sat.inc_deg, 2));
  set("info-period", computePeriod(sat.mean_motion));
}

function populateConjunctions(catalogNo, conjunctions) {
  const list = document.getElementById("info-conjunctions");
  if (!list) return;

  const matching = (conjunctions ?? [])
    .filter((c) => c.sat_a === catalogNo || c.sat_b === catalogNo)
    .sort((a, b) => a.miss_km - b.miss_km);

  if (matching.length === 0) {
    list.innerHTML = "<li>No conjunctions detected.</li>";
    return;
  }

  list.innerHTML = matching
    .map((c) => {
      const partner = c.sat_a === catalogNo ? c.sat_b_name : c.sat_a_name;
      const tca = String(c.tca).slice(0, 10);
      return `<li>${partner} · TCA: ${tca} · ${Number(c.miss_km).toFixed(3)} km · ${Number(c.rel_vel_kms).toFixed(3)} km/s</li>`;
    })
    .join("");
}

export function initInfoPanel(
  viewer,
  fetchSatelliteFn = fetchSatellite,
  fetchConjunctionsFn = fetchConjunctions,
) {
  const panel = document.getElementById("info-panel");
  const closeBtn = document.getElementById("info-close");

  if (!panel) {
    console.warn("[S8.4] initInfoPanel: #info-panel not found in DOM");
    return;
  }

  let currentCatalogNo = null;

  closeBtn?.addEventListener("click", () => {
    viewer.selectedEntity = undefined;
  });

  viewer.selectedEntityChanged.addEventListener(async (entity) => {
    const catalogNo = entity?.properties?.catalog_no ?? null;

    if (!catalogNo) {
      panel.style.display = "none";
      currentCatalogNo = null;
      return;
    }

    currentCatalogNo = catalogNo;
    panel.style.display = "block";

    const [sat, conjunctions] = await Promise.all([
      fetchSatelliteFn(catalogNo),
      fetchConjunctionsFn(),
    ]);

    // Stale-response guard: a newer selection may have occurred while we were fetching
    if (currentCatalogNo !== catalogNo) return;

    if (!sat) {
      set("info-name", "Satellite not found");
      [
        "info-catalog-no",
        "info-intl-designator",
        "info-epoch",
        "info-regime",
        "info-a-km",
        "info-ecc",
        "info-inc-deg",
        "info-period",
      ].forEach((id) => set(id, "—"));
      const list = document.getElementById("info-conjunctions");
      if (list) list.innerHTML = "";
      return;
    }

    populateDetails(sat);
    populateConjunctions(catalogNo, conjunctions);
  });
}
