import * as Cesium from "cesium";

export function initCesiumBaseUrl(baseUrl = "/cesium/") {
  window.CESIUM_BASE_URL = baseUrl;
}

// Set runtime base URL for Cesium asset loading.
// vite-plugin-cesium also handles this at build time via Vite define;
// this covers environments that bypass the build step.
initCesiumBaseUrl();

console.log(`CesiumJS ${Cesium.VERSION} loaded`);
