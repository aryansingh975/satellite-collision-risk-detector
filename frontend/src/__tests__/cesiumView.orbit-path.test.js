import { describe, it, expect, vi, beforeEach } from "vitest";

// vi.hoisted runs before vi.mock so these refs are available in the factory.
const {
  MockPathGraphics,
  MockColorMaterialProperty,
  MockConstantProperty,
  MockColor,
} = vi.hoisted(() => {
  const MockPathGraphics = vi.fn().mockImplementation((opts) => ({ ...opts }));
  const MockColorMaterialProperty = vi.fn().mockImplementation((color) => ({
    _color: color,
  }));
  const MockConstantProperty = vi
    .fn()
    .mockImplementation((val) => ({ _val: val }));
  const MockColor = {
    WHITE: {
      _name: "WHITE",
      withAlpha: vi.fn((a) => ({ _name: "WHITE_ALPHA", _alpha: a })),
    },
    YELLOW: { _name: "YELLOW" },
    GREEN: { _name: "GREEN" },
    CYAN: { _name: "CYAN" },
    RED: { _name: "RED" },
  };
  return {
    MockPathGraphics,
    MockColorMaterialProperty,
    MockConstantProperty,
    MockColor,
  };
});

vi.mock("cesium", () => ({
  Viewer: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
  TileMapServiceImageryProvider: vi.fn().mockImplementation(() => ({})),
  buildModuleUrl: vi.fn((p) => p),
  Ion: { defaultAccessToken: undefined },
  Color: MockColor,
  Cartesian3: {
    fromDegrees: vi.fn((lon, lat, h) => ({ _lon: lon, _lat: lat, _height: h })),
  },
  Entity: vi.fn().mockImplementation((opts) => ({ ...opts })),
  PointGraphics: vi.fn().mockImplementation((opts) => ({ ...opts })),
  LabelGraphics: vi.fn().mockImplementation((opts) => ({ ...opts })),
  ScreenSpaceEventHandler: vi
    .fn()
    .mockImplementation(() => ({ setInputAction: vi.fn() })),
  ScreenSpaceEventType: { MOUSE_MOVE: "MOUSE_MOVE" },
  SampledPositionProperty: vi.fn().mockImplementation(() => ({
    addSample: vi.fn(),
    setInterpolationOptions: vi.fn(),
  })),
  JulianDate: { fromIso8601: vi.fn((iso) => ({ _iso: iso })) },
  ClockRange: { LOOP_STOP: "LOOP_STOP" },
  InterpolationAlgorithm: { LAGRANGE: "LAGRANGE" },
  PathGraphics: MockPathGraphics,
  ColorMaterialProperty: MockColorMaterialProperty,
  ConstantProperty: MockConstantProperty,
}));

vi.mock("../api.js", () => ({
  fetchSatellites: vi.fn(),
  fetchBulkPositions: vi.fn(),
}));

import {
  addOrbitPath,
  toggleOrbitPath,
  selectSatellite,
} from "../cesiumView.js";

// ─── S7.5 — Orbit Path Graphic ───────────────────────────────────────────────

describe("S7.5 — Orbit Path Graphic", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockPathGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
    MockConstantProperty.mockImplementation((val) => ({ _val: val }));
    MockColor.WHITE.withAlpha.mockImplementation((a) => ({
      _name: "WHITE_ALPHA",
      _alpha: a,
    }));
  });

  // FR-1 + FR-4: addOrbitPath attaches a path with correct structure
  it("test_addOrbitPath_attaches_path", () => {
    const entity = {};
    addOrbitPath(entity);
    expect(entity.path).toBeDefined();
    expect(MockPathGraphics).toHaveBeenCalledOnce();
    const opts = MockPathGraphics.mock.calls[0][0];
    expect(opts.show).toBe(false);
    expect(opts.width).toBe(2);
    // leadTime and trailTime are ConstantProperty(5400)
    expect(MockConstantProperty).toHaveBeenCalledWith(5400);
    // material is a ColorMaterialProperty
    expect(MockColorMaterialProperty).toHaveBeenCalledOnce();
    // colour is WHITE at 50% alpha
    expect(MockColor.WHITE.withAlpha).toHaveBeenCalledWith(0.5);
  });

  // FR-2: toggleOrbitPath — normal cases
  it("test_toggleOrbitPath_shows_path", () => {
    const entity = { path: { show: false } };
    toggleOrbitPath(entity, true);
    expect(entity.path.show).toBe(true);
  });

  it("test_toggleOrbitPath_hides_path", () => {
    const entity = { path: { show: true } };
    toggleOrbitPath(entity, false);
    expect(entity.path.show).toBe(false);
  });

  // FR-2: toggleOrbitPath — edge cases
  it("test_toggleOrbitPath_null_entity", () => {
    expect(() => toggleOrbitPath(null, true)).not.toThrow();
  });

  it("test_toggleOrbitPath_no_path_property", () => {
    const entity = {}; // no path property
    expect(() => toggleOrbitPath(entity, true)).not.toThrow();
    expect(entity.path).toBeUndefined();
  });

  // FR-3: selectSatellite — path management
  it("test_selectSatellite_shows_only_selected_path", () => {
    const entityA = { path: { show: false } };
    const entityB = { path: { show: false } };
    selectSatellite(entityB, [entityA, entityB]);
    expect(entityA.path.show).toBe(false);
    expect(entityB.path.show).toBe(true);
  });

  it("test_deselect_hides_all_paths", () => {
    const entityA = { path: { show: true } };
    const entityB = { path: { show: true } };
    selectSatellite(null, [entityA, entityB]);
    expect(entityA.path.show).toBe(false);
    expect(entityB.path.show).toBe(false);
  });
});
