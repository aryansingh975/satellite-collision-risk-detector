import { describe, it, expect, vi, beforeEach } from "vitest";

// vi.hoisted runs before vi.mock so these refs are available in the factory.
const {
  MockViewer,
  MockTMSProvider,
  MockImageryLayer,
  mockBuildModuleUrl,
  mockIon,
  MockColor,
  MockCartesian3,
  MockEntity,
  MockPointGraphics,
  MockLabelGraphics,
  MockSSEH,
  MockSSET,
  mockFetchSatellites,
  MockSampledPositionProperty,
  MockJulianDate,
  MockClockRange,
  MockInterpolationAlgorithm,
  mockFetchBulkPositions,
  MockPathGraphics,
  MockColorMaterialProperty,
  MockConstantProperty,
} = vi.hoisted(() => {
  // S7.1 mocks
  const MockViewer = vi.fn().mockImplementation(() => ({ destroy: vi.fn() }));
  const MockTMSProvider = vi.fn().mockImplementation(() => ({}));
  MockTMSProvider.fromUrl = vi.fn().mockResolvedValue({});
  const MockImageryLayer = { fromProviderAsync: vi.fn().mockReturnValue({}) };
  const mockBuildModuleUrl = vi.fn((path) => path);
  const mockIon = { defaultAccessToken: undefined };

  // S7.3 mocks — Cesium colour constants (plain objects, not vi.fn)
  const MockColor = {
    YELLOW: { _name: "YELLOW" },
    GREEN: { _name: "GREEN" },
    CYAN: { _name: "CYAN" },
    RED: { _name: "RED" },
    WHITE: {
      _name: "WHITE",
      withAlpha: vi.fn((a) => ({ _name: "WHITE_ALPHA", _alpha: a })),
    },
  };

  // Cartesian3.fromDegrees returns a plain position object for inspection
  const MockCartesian3 = {
    fromDegrees: vi.fn((lon, lat, height) => ({
      _lon: lon,
      _lat: lat,
      _height: height,
    })),
  };

  // Entity/graphics constructors — shallow-spread opts so properties are directly readable
  const MockEntity = vi.fn().mockImplementation((opts) => ({ ...opts }));
  const MockPointGraphics = vi.fn().mockImplementation((opts) => ({ ...opts }));
  const MockLabelGraphics = vi.fn().mockImplementation((opts) => ({ ...opts }));

  // ScreenSpaceEventHandler — each construction produces a fresh instance with a _handlers map
  const MockSSEH = vi.fn().mockImplementation(() => {
    const inst = {
      _handlers: {},
      setInputAction: vi.fn((fn, type) => {
        inst._handlers[type] = fn;
      }),
    };
    return inst;
  });
  const MockSSET = { MOUSE_MOVE: "MOUSE_MOVE" };

  const mockFetchSatellites = vi.fn();

  // S7.4 mocks
  const MockSampledPositionProperty = vi.fn().mockImplementation(() => ({
    addSample: vi.fn(),
    setInterpolationOptions: vi.fn(),
  }));
  const MockJulianDate = {
    fromIso8601: vi.fn((iso) => ({ _iso: iso })),
  };
  const MockClockRange = { LOOP_STOP: "LOOP_STOP" };
  const MockInterpolationAlgorithm = { LAGRANGE: "LAGRANGE" };
  const mockFetchBulkPositions = vi.fn();

  // S7.5 mocks
  const MockPathGraphics = vi.fn().mockImplementation((opts) => ({ ...opts }));
  const MockColorMaterialProperty = vi.fn().mockImplementation((color) => ({
    _color: color,
  }));
  const MockConstantProperty = vi
    .fn()
    .mockImplementation((val) => ({ _val: val }));

  return {
    MockViewer,
    MockTMSProvider,
    MockImageryLayer,
    mockBuildModuleUrl,
    mockIon,
    MockColor,
    MockCartesian3,
    MockEntity,
    MockPointGraphics,
    MockLabelGraphics,
    MockSSEH,
    MockSSET,
    mockFetchSatellites,
    MockSampledPositionProperty,
    MockJulianDate,
    MockClockRange,
    MockInterpolationAlgorithm,
    mockFetchBulkPositions,
    MockPathGraphics,
    MockColorMaterialProperty,
    MockConstantProperty,
  };
});

vi.mock("cesium", () => ({
  Viewer: MockViewer,
  TileMapServiceImageryProvider: MockTMSProvider,
  ImageryLayer: MockImageryLayer,
  buildModuleUrl: mockBuildModuleUrl,
  Ion: mockIon,
  Color: MockColor,
  Cartesian3: MockCartesian3,
  Entity: MockEntity,
  PointGraphics: MockPointGraphics,
  LabelGraphics: MockLabelGraphics,
  ScreenSpaceEventHandler: MockSSEH,
  ScreenSpaceEventType: MockSSET,
  SampledPositionProperty: MockSampledPositionProperty,
  JulianDate: MockJulianDate,
  ClockRange: MockClockRange,
  InterpolationAlgorithm: MockInterpolationAlgorithm,
  PathGraphics: MockPathGraphics,
  ColorMaterialProperty: MockColorMaterialProperty,
  ConstantProperty: MockConstantProperty,
}));

vi.mock("../api.js", () => ({
  fetchSatellites: mockFetchSatellites,
  fetchBulkPositions: mockFetchBulkPositions,
}));

import {
  initViewer,
  regimeColour,
  buildSatelliteEntity,
  loadSatelliteEntities,
  initHoverLabel,
  buildSampledPosition,
  setupClock,
  loadAnimatedTracks,
} from "../cesiumView.js";

// ─── S7.1 — Cesium Globe Bootstrap ───────────────────────────────────────────

describe("S7.1 — Cesium Globe Bootstrap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIon.defaultAccessToken = undefined;
    // Re-apply implementations after clearAllMocks (which only clears call history, not impls).
    MockViewer.mockImplementation(() => ({ destroy: vi.fn() }));
    MockTMSProvider.mockImplementation(() => ({}));
    MockTMSProvider.fromUrl.mockResolvedValue({});
    MockImageryLayer.fromProviderAsync.mockReturnValue({});
    mockBuildModuleUrl.mockImplementation((path) => path);
  });

  it("test_initViewer_returns_viewer", () => {
    const result = initViewer("cesiumContainer");
    expect(MockViewer).toHaveBeenCalledOnce();
    expect(result).toBe(MockViewer.mock.results[0].value);
  });

  it("test_initViewer_disables_baseLayerPicker", () => {
    initViewer("cesiumContainer");
    const [, opts] = MockViewer.mock.calls[0];
    expect(opts.baseLayerPicker).toBe(false);
  });

  it("test_initViewer_disables_geocoder", () => {
    initViewer("cesiumContainer");
    const [, opts] = MockViewer.mock.calls[0];
    expect(opts.geocoder).toBe(false);
  });

  it("test_initViewer_uses_NaturalEarth_imagery", () => {
    initViewer("cesiumContainer");
    expect(MockTMSProvider.fromUrl).toHaveBeenCalledOnce();
    const [url] = MockTMSProvider.fromUrl.mock.calls[0];
    expect(url).toContain("NaturalEarthII");
  });

  it("test_initViewer_exports_singleton", () => {
    // Second call should destroy the first viewer and return a new instance.
    const first = initViewer("cesiumContainer");
    const second = initViewer("cesiumContainer");
    expect(first.destroy).toHaveBeenCalledOnce();
    expect(second).not.toBe(first);
  });

  it("test_initViewer_no_ion_token", () => {
    initViewer("cesiumContainer");
    expect(mockIon.defaultAccessToken).toBeUndefined();
  });
});

// ─── S7.3 — Satellite Entities ───────────────────────────────────────────────

const ISS_SAT = {
  catalog_no: 25544,
  name: "ISS (ZARYA)",
  regime: "LEO",
  lat_deg: 28.5,
  lon_deg: -80.7,
  alt_km: 408.0,
};

const GEO_SAT = {
  catalog_no: 99999,
  name: "GEO-TEST",
  regime: "GEO",
  lat_deg: 0.0,
  lon_deg: 77.0,
  alt_km: 35786.0,
};

function makeViewer() {
  const list = [];
  return {
    entities: {
      add: vi.fn((e) => {
        list.push(e);
        return e;
      }),
      removeAll: vi.fn(() => {
        list.length = 0;
      }),
      get values() {
        return list;
      },
      _list: list,
    },
    scene: {
      pick: vi.fn(() => undefined),
      canvas: {},
    },
    clock: {
      startTime: null,
      stopTime: null,
      currentTime: null,
      clockRange: null,
      multiplier: null,
      shouldAnimate: false,
    },
    timeline: { zoomTo: vi.fn() },
    destroy: vi.fn(),
  };
}

describe("S7.3 — Satellite Entities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Re-apply constructor implementations after clearAllMocks.
    MockEntity.mockImplementation((opts) => ({ ...opts }));
    MockPointGraphics.mockImplementation((opts) => ({ ...opts }));
    MockLabelGraphics.mockImplementation((opts) => ({ ...opts }));
    MockCartesian3.fromDegrees.mockImplementation((lon, lat, height) => ({
      _lon: lon,
      _lat: lat,
      _height: height,
    }));
    MockSSEH.mockImplementation(() => {
      const inst = {
        _handlers: {},
        setInputAction: vi.fn((fn, type) => {
          inst._handlers[type] = fn;
        }),
      };
      return inst;
    });
    // S7.5 constructors used by addOrbitPath (called inside loadSatelliteEntities)
    MockPathGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
    MockConstantProperty.mockImplementation((val) => ({ _val: val }));
    MockColor.WHITE.withAlpha.mockImplementation((a) => ({
      _name: "WHITE_ALPHA",
      _alpha: a,
    }));
    mockFetchSatellites.mockResolvedValue([ISS_SAT, GEO_SAT]);
  });

  // FR-1: regime colour map

  it("test_regime_colour_known", () => {
    expect(regimeColour("LEO")).toBe(MockColor.YELLOW);
    expect(regimeColour("MEO")).toBe(MockColor.GREEN);
    expect(regimeColour("GEO")).toBe(MockColor.CYAN);
    expect(regimeColour("HEO")).toBe(MockColor.RED);
  });

  it("test_regime_colour_unknown", () => {
    expect(regimeColour("UNKNOWN")).toBe(MockColor.WHITE);
    expect(regimeColour(null)).toBe(MockColor.WHITE);
    expect(regimeColour(undefined)).toBe(MockColor.WHITE);
  });

  // FR-2: build single satellite entity

  it("test_build_entity_id", () => {
    const entity = buildSatelliteEntity(ISS_SAT);
    expect(entity.id).toBe("sat-25544");
  });

  it("test_build_entity_position", () => {
    buildSatelliteEntity(ISS_SAT);
    expect(MockCartesian3.fromDegrees).toHaveBeenCalledWith(
      ISS_SAT.lon_deg,
      ISS_SAT.lat_deg,
      ISS_SAT.alt_km * 1000,
    );
  });

  it("test_build_entity_point_colour", () => {
    const entity = buildSatelliteEntity(ISS_SAT); // LEO → YELLOW
    expect(entity.point.color).toBe(MockColor.YELLOW);
  });

  it("test_build_entity_label_hidden", () => {
    const entity = buildSatelliteEntity(ISS_SAT);
    expect(entity.label.show).toBe(false);
  });

  // FR-3: load all satellites onto the viewer

  it("test_load_entities_adds_to_viewer", async () => {
    const v = makeViewer();
    const result = await loadSatelliteEntities(v);
    expect(result).toHaveLength(2);
    expect(v.entities._list).toHaveLength(2);
    expect(v.entities._list[0].id).toBe("sat-25544");
    expect(v.entities._list[1].id).toBe("sat-99999");
  });

  it("test_load_entities_clears_previous", async () => {
    const v = makeViewer();
    await loadSatelliteEntities(v);
    await loadSatelliteEntities(v);
    // removeAll was called on each load; final list still has exactly 2 entries
    expect(v.entities.removeAll).toHaveBeenCalledTimes(2);
    expect(v.entities._list).toHaveLength(2);
  });

  it("test_load_entities_empty", async () => {
    mockFetchSatellites.mockResolvedValue([]);
    const v = makeViewer();
    const result = await loadSatelliteEntities(v);
    expect(result).toEqual([]);
    expect(v.entities._list).toHaveLength(0);
  });

  it("test_load_entities_api_error", async () => {
    mockFetchSatellites.mockRejectedValue(new Error("Network error"));
    const v = makeViewer();
    // Pre-populate viewer with one entity to verify it is untouched on error.
    v.entities._list.push({ id: "sat-pre" });
    const result = await loadSatelliteEntities(v);
    expect(result).toEqual([]);
    expect(v.entities.removeAll).not.toHaveBeenCalled();
    expect(v.entities._list).toHaveLength(1);
  });

  // FR-4: hover label

  it("test_hover_shows_label", () => {
    const v = makeViewer();
    const entity = buildSatelliteEntity(ISS_SAT);
    v.scene.pick.mockReturnValue({ id: entity });
    const handler = initHoverLabel(v);
    handler._handlers["MOUSE_MOVE"]({ endPosition: { x: 100, y: 100 } });
    expect(entity.label.show).toBe(true);
  });

  it("test_hover_hides_label_on_leave", () => {
    const v = makeViewer();
    const entity = buildSatelliteEntity(ISS_SAT);
    const handler = initHoverLabel(v);
    // First move: over the satellite entity → label shown
    v.scene.pick.mockReturnValueOnce({ id: entity });
    handler._handlers["MOUSE_MOVE"]({ endPosition: { x: 100, y: 100 } });
    expect(entity.label.show).toBe(true);
    // Second move: empty space → label hidden
    v.scene.pick.mockReturnValue(undefined);
    handler._handlers["MOUSE_MOVE"]({ endPosition: { x: 200, y: 200 } });
    expect(entity.label.show).toBe(false);
  });
});

// ─── S7.4 — SampledPositionProperty + Clock Animation ────────────────────────

const SAMPLE_POSITIONS = [
  { time: "2025-01-01T00:00:00Z", lat: 28.5, lon: -80.7, alt_km: 408 },
  { time: "2025-01-01T00:01:00Z", lat: 29.0, lon: -80.0, alt_km: 410 },
  { time: "2025-01-01T00:02:00Z", lat: 29.5, lon: -79.3, alt_km: 412 },
];

describe("S7.4 — SampledPositionProperty + Clock Animation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockSampledPositionProperty.mockImplementation(() => ({
      addSample: vi.fn(),
      setInterpolationOptions: vi.fn(),
    }));
    MockJulianDate.fromIso8601.mockImplementation((iso) => ({ _iso: iso }));
    MockCartesian3.fromDegrees.mockImplementation((lon, lat, height) => ({
      _lon: lon,
      _lat: lat,
      _height: height,
    }));
  });

  // FR-2: buildSampledPosition

  it("test_buildSampledPosition_empty", () => {
    const prop = buildSampledPosition([]);
    expect(MockSampledPositionProperty).toHaveBeenCalledOnce();
    expect(prop.setInterpolationOptions).toHaveBeenCalledOnce();
    expect(prop.addSample).not.toHaveBeenCalled();
  });

  it("test_buildSampledPosition_samples", () => {
    const prop = buildSampledPosition(SAMPLE_POSITIONS);
    expect(prop.addSample).toHaveBeenCalledTimes(3);
    expect(MockCartesian3.fromDegrees).toHaveBeenCalledTimes(3);
    expect(MockCartesian3.fromDegrees).toHaveBeenLastCalledWith(
      -79.3,
      29.5,
      412000,
    );
  });

  // FR-3: setupClock

  it("test_setupClock_sets_fields", () => {
    const v = makeViewer();
    setupClock(v, "2025-01-01T00:00:00Z", "2025-01-01T06:00:00Z");
    const [startJD, stopJD] = MockJulianDate.fromIso8601.mock.results.map(
      (r) => r.value,
    );
    expect(v.clock.startTime).toBe(startJD);
    expect(v.clock.stopTime).toBe(stopJD);
    expect(v.clock.currentTime).toBe(startJD);
    expect(v.clock.clockRange).toBe(MockClockRange.LOOP_STOP);
    expect(v.clock.multiplier).toBe(60);
    expect(v.clock.shouldAnimate).toBe(true);
    expect(v.timeline.zoomTo).toHaveBeenCalledWith(startJD, stopJD);
  });

  it("test_setupClock_custom_multiplier", () => {
    const v = makeViewer();
    setupClock(v, "2025-01-01T00:00:00Z", "2025-01-01T06:00:00Z", 300);
    expect(v.clock.multiplier).toBe(300);
  });

  // FR-4: loadAnimatedTracks

  it("test_loadAnimatedTracks_no_entities", async () => {
    const v = makeViewer();
    const count = await loadAnimatedTracks(
      v,
      "2025-01-01T00:00:00Z",
      "2025-01-01T06:00:00Z",
    );
    expect(count).toBe(0);
    expect(mockFetchBulkPositions).not.toHaveBeenCalled();
  });

  it("test_loadAnimatedTracks_updates_position", async () => {
    const v = makeViewer();
    const entity = { id: "sat-25544", position: null };
    v.entities._list.push(entity);
    mockFetchBulkPositions.mockResolvedValue({
      satellites: [
        { catalog_no: 25544, name: "ISS", positions: SAMPLE_POSITIONS },
      ],
    });
    const count = await loadAnimatedTracks(
      v,
      "2025-01-01T00:00:00Z",
      "2025-01-01T06:00:00Z",
    );
    expect(count).toBe(1);
    expect(entity.position).toBe(
      MockSampledPositionProperty.mock.results[0].value,
    );
  });

  it("test_loadAnimatedTracks_missing_entity", async () => {
    const v = makeViewer();
    const entity = { id: "sat-25544", position: null };
    v.entities._list.push(entity);
    mockFetchBulkPositions.mockResolvedValue({
      satellites: [
        { catalog_no: 25544, name: "ISS", positions: SAMPLE_POSITIONS },
        { catalog_no: 99999, name: "OTHER", positions: [] },
      ],
    });
    const count = await loadAnimatedTracks(
      v,
      "2025-01-01T00:00:00Z",
      "2025-01-01T06:00:00Z",
    );
    expect(count).toBe(1);
  });

  it("test_loadAnimatedTracks_fetch_error", async () => {
    const v = makeViewer();
    v.entities._list.push({ id: "sat-25544", position: null });
    mockFetchBulkPositions.mockRejectedValue(new Error("Network error"));
    const count = await loadAnimatedTracks(
      v,
      "2025-01-01T00:00:00Z",
      "2025-01-01T06:00:00Z",
    );
    expect(count).toBe(0);
  });
});
