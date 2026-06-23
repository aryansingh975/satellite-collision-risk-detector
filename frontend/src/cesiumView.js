import * as Cesium from "cesium";
import { fetchSatellites, fetchBulkPositions } from "./api.js";

let viewer = null;

export function initViewer(containerId) {
  if (viewer !== null) {
    viewer.destroy();
  }

  viewer = new Cesium.Viewer(containerId, {
    baseLayer: Cesium.ImageryLayer.fromProviderAsync(
      Cesium.TileMapServiceImageryProvider.fromUrl(
        Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
      )
    ),
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
  });

  return viewer;
}

export { viewer };

// ─── S7.3 — Satellite Entities ───────────────────────────────────────────────

const _REGIME_COLOUR_MAP = {
  LEO: Cesium.Color.YELLOW,
  MEO: Cesium.Color.GREEN,
  GEO: Cesium.Color.CYAN,
  HEO: Cesium.Color.RED,
};

export function regimeColour(regime) {
  return _REGIME_COLOUR_MAP[regime] ?? Cesium.Color.WHITE;
}

export function buildSatelliteEntity(sat) {
  // No static position — loadAnimatedTracks will assign a SampledPositionProperty.
  return new Cesium.Entity({
    id: `sat-${sat.catalog_no}`,
    name: sat.name,
    point: new Cesium.PointGraphics({
      pixelSize: 6,
      color: regimeColour(sat.regime),
      outlineWidth: 0,
    }),
    label: new Cesium.LabelGraphics({
      text: `${sat.name} (${sat.regime ?? "?"})`,
      show: false,
    }),
    properties: sat,
  });
}

export async function loadSatelliteEntities(v) {
  let satellites;
  try {
    satellites = await fetchSatellites({ limit: 1000 });
  } catch (err) {
    console.error("[S7.3] loadSatelliteEntities: fetch failed", err);
    return [];
  }
  v.entities.removeAll();
  _entityRegistry = [];
  const added = [];
  for (const sat of satellites) {
    const entity = buildSatelliteEntity(sat);
    addOrbitPath(entity);
    v.entities.add(entity);
    _entityRegistry.push(entity);
    added.push(entity);
  }
  return added;
}

export function initHoverLabel(v) {
  let lastHovered = null;
  const handler = new Cesium.ScreenSpaceEventHandler(v.scene.canvas);
  handler.setInputAction((movement) => {
    const picked = v.scene.pick(movement.endPosition);
    if (lastHovered) {
      lastHovered.label.show = false;
      lastHovered = null;
    }
    const entity = picked?.id;
    if (entity?.id?.startsWith?.("sat-")) {
      entity.label.show = true;
      lastHovered = entity;
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
  return handler;
}

// ─── S7.5 — Orbit Path Graphic ───────────────────────────────────────────────

let _entityRegistry = [];

export function addOrbitPath(entity) {
  const color = Cesium.Color.WHITE.withAlpha(0.5);
  entity.path = new Cesium.PathGraphics({
    show: false,
    leadTime: new Cesium.ConstantProperty(5400),
    trailTime: new Cesium.ConstantProperty(5400),
    width: 2,
    material: new Cesium.ColorMaterialProperty(color),
  });
}

export function toggleOrbitPath(entity, visible) {
  if (!entity?.path) return;
  entity.path.show = visible;
}

export function selectSatellite(entity, allEntities = _entityRegistry) {
  for (const e of allEntities) {
    toggleOrbitPath(e, false);
  }
  if (entity) toggleOrbitPath(entity, true);
}

export function initOrbitPathSelection(v) {
  v.selectedEntityChanged.addEventListener((entity) => {
    selectSatellite(entity ?? null);
  });
}

// ─── S7.4 — SampledPositionProperty + Clock Animation ────────────────────────

export function buildSampledPosition(positions) {
  const prop = new Cesium.SampledPositionProperty();
  prop.setInterpolationOptions({
    interpolationAlgorithm: Cesium.InterpolationAlgorithm.LAGRANGE,
    interpolationDegree: 5,
  });
  for (const sample of positions) {
    const jd = Cesium.JulianDate.fromIso8601(sample.time);
    const cart = Cesium.Cartesian3.fromDegrees(
      sample.lon,
      sample.lat,
      sample.alt_km * 1000,
    );
    prop.addSample(jd, cart);
  }
  return prop;
}

export function setupClock(v, startIso, stopIso, multiplier = 60) {
  const startTime = Cesium.JulianDate.fromIso8601(startIso);
  const stopTime = Cesium.JulianDate.fromIso8601(stopIso);
  v.clock.startTime = startTime;
  v.clock.stopTime = stopTime;
  v.clock.currentTime = startTime;
  v.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
  v.clock.multiplier = multiplier;
  v.clock.shouldAnimate = true;
  v.timeline.zoomTo(startTime, stopTime);
}

export async function loadAnimatedTracks(v, start, stop, step = 60) {
  const catalogNos = [];
  const entityMap = {};
  for (const entity of v.entities.values) {
    if (entity.id?.startsWith?.("sat-")) {
      const catNo = parseInt(entity.id.slice(4), 10);
      catalogNos.push(catNo);
      entityMap[catNo] = entity;
    }
  }

  if (catalogNos.length === 0) return 0;

  let response;
  try {
    response = await fetchBulkPositions(catalogNos, start, stop, step);
  } catch (err) {
    console.error("[S7.4] loadAnimatedTracks: fetch failed", err);
    return 0;
  }

  const satellites = response?.satellites;
  if (!satellites?.length) return 0;

  let count = 0;
  for (const posData of satellites) {
    const entity = entityMap[posData.catalog_no];
    if (!entity) continue;
    entity.position = buildSampledPosition(posData.positions);
    count++;
  }
  return count;
}
