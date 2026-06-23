// Risk-pair polylines — S8.1 / S8.2
import * as Cesium from "cesium";
import { fetchConjunctions } from "./api.js";

export function buildDescription(conj) {
  return (
    `${conj.sat_a_name} / ${conj.sat_b_name}\n` +
    `TCA: ${conj.tca}\n` +
    `Miss: ${conj.miss_km.toFixed(3)} km\n` +
    `Rel vel: ${conj.rel_vel_kms.toFixed(3)} km/s`
  );
}

export function severityColor(miss_km) {
  if (miss_km <= 1.0) return Cesium.Color.RED;
  return Cesium.Color.ORANGE;
}

export function buildPolylineEntity(posA, posB, conj) {
  return new Cesium.Entity({
    id: `risk-${conj.id}`,
    name: `${conj.sat_a_name} ↔ ${conj.sat_b_name}`,
    description: buildDescription(conj),
    polyline: new Cesium.PolylineGraphics({
      positions: [posA, posB],
      width: 2,
      material: new Cesium.ColorMaterialProperty(severityColor(conj.miss_km)),
    }),
  });
}

// Returns a CallbackProperty whose callback reads both entity positions at render
// time, so the polyline tracks the moving satellites as the clock advances.
// Returns undefined when either position is unavailable, hiding the polyline.
export function buildCallbackPositions(entityA, entityB) {
  return new Cesium.CallbackProperty((time) => {
    const posA = entityA.position?.getValue(time);
    const posB = entityB.position?.getValue(time);
    if (!posA || !posB) return undefined;
    return [posA, posB];
  }, false);
}

export function loadRiskPolylines(viewer, conjunctions) {
  let count = 0;
  for (const conj of conjunctions) {
    const entityA = viewer.entities.getById(`sat-${conj.sat_a}`);
    const entityB = viewer.entities.getById(`sat-${conj.sat_b}`);
    if (!entityA || !entityB) continue;
    const positions = buildCallbackPositions(entityA, entityB);
    viewer.entities.add(
      new Cesium.Entity({
        id: `risk-${conj.id}`,
        name: `${conj.sat_a_name} ↔ ${conj.sat_b_name}`,
        description: buildDescription(conj),
        polyline: new Cesium.PolylineGraphics({
          positions,
          width: 2,
          material: new Cesium.ColorMaterialProperty(
            severityColor(conj.miss_km),
          ),
        }),
      }),
    );
    count++;
  }
  return count;
}

export function clearRiskPolylines(viewer) {
  const toRemove = viewer.entities.values.filter((e) =>
    e.id?.startsWith("risk-"),
  );
  for (const e of toRemove) viewer.entities.remove(e);
}

export async function fetchAndRenderRisk(viewer) {
  let conjunctions;
  try {
    conjunctions = await fetchConjunctions();
  } catch (err) {
    console.error("[S8.1] fetchAndRenderRisk: fetch failed", err);
    return 0;
  }
  clearRiskPolylines(viewer);
  if (!conjunctions?.length) return 0;
  return loadRiskPolylines(viewer, conjunctions);
}

export function startRiskRefresh(viewer, intervalMs = 120_000) {
  return setInterval(() => fetchAndRenderRisk(viewer), intervalMs);
}

export function stopRiskRefresh(handle) {
  clearInterval(handle);
}
