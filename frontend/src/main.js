import * as Cesium from "cesium";
import {
  initViewer,
  loadSatelliteEntities,
  initHoverLabel,
  initOrbitPathSelection,
  setupClock,
  loadAnimatedTracks,
} from "./cesiumView.js";
import { fetchAndRenderRisk, startRiskRefresh } from "./risk.js";
import { initSearch } from "./search.js";
import { initInfoPanel } from "./infoPanel.js";
import { fetchSatellite, fetchConjunctions } from "./api.js";
import {
  initRegimeChart,
  initApproachChart,
  initRiskTable,
  wireRefreshBtn,
  startAutoRefresh,
} from "./dashboard.js";

export function initCesiumBaseUrl(baseUrl = "/cesium/") {
  window.CESIUM_BASE_URL = baseUrl;
}

initCesiumBaseUrl();

// <script type="module"> is deferred, so the DOM is ready when this runs.
// DOMContentLoaded listener handles any environment that loads this module early.
document.addEventListener("DOMContentLoaded", async () => {
  const viewer = initViewer("cesiumContainer");
  initHoverLabel(viewer);
  initOrbitPathSelection(viewer);
  const entities = await loadSatelliteEntities(viewer);
  initSearch(viewer, entities);
  initInfoPanel(viewer, fetchSatellite, fetchConjunctions);

  // Animate over a 6-hour window starting now (60× real-time speed).
  const start = new Date().toISOString();
  const stop = new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString();
  setupClock(viewer, start, stop, 60);

  // Load dashboard and animated tracks in parallel — don't block charts on heavy propagation.
  const [regimeChart, approachChart] = await Promise.all([
    initRegimeChart(),
    initApproachChart(),
    initRiskTable(viewer),
    fetchAndRenderRisk(viewer),
    loadAnimatedTracks(viewer, start, stop, 300),  // 300s step = 73 samples, much faster
  ]);

  startRiskRefresh(viewer);
  const charts = { regime: regimeChart, approach: approachChart };
  wireRefreshBtn(charts, viewer);
  startAutoRefresh(charts, viewer);
  // Expose handles for Playwright e2e tests (harmless in production).
  window.__charts = charts;
  window.__appReady = true;
});

console.log(`CesiumJS ${Cesium.VERSION} loaded`);
