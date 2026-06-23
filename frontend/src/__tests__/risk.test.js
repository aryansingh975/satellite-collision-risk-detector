import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// vi.hoisted runs before vi.mock so these refs are available in the factory.
const {
  MockEntity,
  MockPolylineGraphics,
  MockColorMaterialProperty,
  MockColor,
  MockCallbackProperty,
  mockFetchConjunctions,
} = vi.hoisted(() => {
  const MockEntity = vi.fn().mockImplementation((opts) => ({ ...opts }));
  const MockPolylineGraphics = vi
    .fn()
    .mockImplementation((opts) => ({ ...opts }));
  const MockColorMaterialProperty = vi.fn().mockImplementation((color) => ({
    _color: color,
  }));
  const MockColor = {
    RED: { _name: "RED" },
    ORANGE: { _name: "ORANGE" },
  };
  const MockCallbackProperty = vi
    .fn()
    .mockImplementation((cb, isConst) => ({ _cb: cb, isConstant: isConst }));
  const mockFetchConjunctions = vi.fn();

  return {
    MockEntity,
    MockPolylineGraphics,
    MockColorMaterialProperty,
    MockColor,
    MockCallbackProperty,
    mockFetchConjunctions,
  };
});

vi.mock("cesium", () => ({
  Entity: MockEntity,
  PolylineGraphics: MockPolylineGraphics,
  ColorMaterialProperty: MockColorMaterialProperty,
  Color: MockColor,
  CallbackProperty: MockCallbackProperty,
}));

vi.mock("../api.js", () => ({
  fetchConjunctions: mockFetchConjunctions,
}));

import {
  buildDescription,
  severityColor,
  buildPolylineEntity,
  loadRiskPolylines,
  clearRiskPolylines,
  fetchAndRenderRisk,
  buildCallbackPositions,
  startRiskRefresh,
  stopRiskRefresh,
} from "../risk.js";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_TIME = { _iso: "2025-01-01T00:00:00Z" };

const CONJ_CLOSE = {
  id: 1,
  sat_a: 25544,
  sat_b: 40000,
  sat_a_name: "ISS (ZARYA)",
  sat_b_name: "DEBRIS-A",
  tca: "2025-01-01T03:30:00Z",
  miss_km: 0.5,
  rel_vel_kms: 7.2,
  window_start: "2025-01-01T00:00:00Z",
  computed_at: "2025-01-01T00:00:01Z",
};

const CONJ_MODERATE = {
  id: 2,
  sat_a: 25544,
  sat_b: 41000,
  sat_a_name: "ISS (ZARYA)",
  sat_b_name: "DEBRIS-B",
  tca: "2025-01-01T05:15:00Z",
  miss_km: 3.0,
  rel_vel_kms: 14.1,
  window_start: "2025-01-01T00:00:00Z",
  computed_at: "2025-01-01T00:00:01Z",
};

const POS_A = { _x: 1000, _y: 2000, _z: 3000 };
const POS_B = { _x: 1001, _y: 2001, _z: 3001 };

function makeSatEntity(catalogNo, pos = POS_A) {
  return {
    id: `sat-${catalogNo}`,
    position: { getValue: vi.fn(() => pos) },
  };
}

function makeRiskEntity(id) {
  return { id: `risk-${id}` };
}

// makeViewer builds a minimal Cesium Viewer stub whose entities list is
// initialised from the provided array. getById, add, and remove stay in sync.
function makeViewer(initialEntities = []) {
  const list = [...initialEntities];

  return {
    entities: {
      getById: vi.fn((id) => list.find((e) => e.id === id) ?? null),
      add: vi.fn((e) => {
        list.push(e);
        return e;
      }),
      remove: vi.fn((e) => {
        const idx = list.indexOf(e);
        if (idx !== -1) list.splice(idx, 1);
      }),
      get values() {
        return list;
      },
    },
    clock: { currentTime: MOCK_TIME },
  };
}

// ─── S8.1 FR-1 — buildDescription ────────────────────────────────────────────

describe("S8.1 FR-1 — buildDescription", () => {
  beforeEach(() => vi.clearAllMocks());

  it("test_buildDescription_contains_sat_names", () => {
    const desc = buildDescription(CONJ_CLOSE);
    expect(desc).toContain("ISS (ZARYA)");
    expect(desc).toContain("DEBRIS-A");
  });

  it("test_buildDescription_contains_tca", () => {
    const desc = buildDescription(CONJ_CLOSE);
    expect(desc).toContain("2025-01-01T03:30:00Z");
  });

  it("test_buildDescription_contains_miss_and_vel", () => {
    const desc = buildDescription(CONJ_CLOSE);
    // miss_km 0.5 → "0.500"; rel_vel_kms 7.2 → "7.200"
    expect(desc).toContain("0.500");
    expect(desc).toContain("7.200");
  });
});

// ─── S8.1 FR-2 — severityColor ───────────────────────────────────────────────

describe("S8.1 FR-2 — severityColor", () => {
  beforeEach(() => vi.clearAllMocks());

  it("test_severityColor_very_close", () => {
    expect(severityColor(0.5)).toBe(MockColor.RED);
    expect(severityColor(1.0)).toBe(MockColor.RED);
  });

  it("test_severityColor_moderate", () => {
    expect(severityColor(1.1)).toBe(MockColor.ORANGE);
    expect(severityColor(3.0)).toBe(MockColor.ORANGE);
    expect(severityColor(5.0)).toBe(MockColor.ORANGE);
  });
});

// ─── S8.1 FR-3 — buildPolylineEntity ─────────────────────────────────────────

describe("S8.1 FR-3 — buildPolylineEntity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockEntity.mockImplementation((opts) => ({ ...opts }));
    MockPolylineGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
  });

  it("test_buildPolylineEntity_id", () => {
    const entity = buildPolylineEntity(POS_A, POS_B, { ...CONJ_CLOSE, id: 42 });
    expect(entity.id).toBe("risk-42");
  });

  it("test_buildPolylineEntity_name", () => {
    const entity = buildPolylineEntity(POS_A, POS_B, CONJ_CLOSE);
    expect(entity.name).toBe("ISS (ZARYA) ↔ DEBRIS-A");
  });

  it("test_buildPolylineEntity_polyline_positions", () => {
    const entity = buildPolylineEntity(POS_A, POS_B, CONJ_CLOSE);
    expect(entity.polyline.positions).toEqual([POS_A, POS_B]);
  });

  it("test_buildPolylineEntity_polyline_width", () => {
    const entity = buildPolylineEntity(POS_A, POS_B, CONJ_CLOSE);
    expect(entity.polyline.width).toBe(2);
  });

  it("test_buildPolylineEntity_material_color", () => {
    // CONJ_CLOSE.miss_km = 0.5 → RED
    const entity = buildPolylineEntity(POS_A, POS_B, CONJ_CLOSE);
    expect(entity.polyline.material._color).toBe(MockColor.RED);
  });
});

// ─── S8.1 FR-4 — loadRiskPolylines ───────────────────────────────────────────

describe("S8.1 FR-4 — loadRiskPolylines", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockEntity.mockImplementation((opts) => ({ ...opts }));
    MockPolylineGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
  });

  it("test_loadRiskPolylines_adds_both_entities", () => {
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisA = makeSatEntity(40000, POS_B);
    const satDebrisB = makeSatEntity(41000, POS_B);
    const v = makeViewer([satISS, satDebrisA, satDebrisB]);

    const count = loadRiskPolylines(v, [CONJ_CLOSE, CONJ_MODERATE]);

    expect(count).toBe(2);
    expect(v.entities.add).toHaveBeenCalledTimes(2);
    const addedIds = v.entities.add.mock.calls.map((c) => c[0].id);
    expect(addedIds).toContain("risk-1");
    expect(addedIds).toContain("risk-2");
  });

  it("test_loadRiskPolylines_skips_missing_sat", () => {
    // sat-40000 (DEBRIS-A) is missing → CONJ_CLOSE skipped, CONJ_MODERATE added
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisB = makeSatEntity(41000, POS_B);
    const v = makeViewer([satISS, satDebrisB]);

    const count = loadRiskPolylines(v, [CONJ_CLOSE, CONJ_MODERATE]);

    expect(count).toBe(1);
    expect(v.entities.add).toHaveBeenCalledTimes(1);
    expect(v.entities.add.mock.calls[0][0].id).toBe("risk-2");
  });

  it("test_loadRiskPolylines_skips_null_position", () => {
    // S8.2: null position is now handled lazily inside the CallbackProperty callback,
    // not at load time — the entity IS added even if position is temporarily null.
    // The callback returns undefined to hide the polyline until both positions are valid.
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisA = {
      id: "sat-40000",
      position: { getValue: vi.fn(() => null) },
    };
    const satDebrisB = makeSatEntity(41000, POS_B);
    const v = makeViewer([satISS, satDebrisA, satDebrisB]);

    const count = loadRiskPolylines(v, [CONJ_CLOSE, CONJ_MODERATE]);

    // Both added — null position deferred to callback, not skipped at load time
    expect(count).toBe(2);
    expect(v.entities.add).toHaveBeenCalledTimes(2);
  });

  it("test_loadRiskPolylines_empty_input", () => {
    const v = makeViewer();
    const count = loadRiskPolylines(v, []);
    expect(count).toBe(0);
    expect(v.entities.add).not.toHaveBeenCalled();
  });
});

// ─── S8.1 FR-5 — clearRiskPolylines ──────────────────────────────────────────

describe("S8.1 FR-5 — clearRiskPolylines", () => {
  beforeEach(() => vi.clearAllMocks());

  it("test_clearRiskPolylines_removes_risk", () => {
    const riskEntity = makeRiskEntity(1);
    const v = makeViewer([riskEntity]);

    clearRiskPolylines(v);

    expect(v.entities.remove).toHaveBeenCalledOnce();
    expect(v.entities.remove).toHaveBeenCalledWith(riskEntity);
    expect(v.entities.values).toHaveLength(0);
  });

  it("test_clearRiskPolylines_keeps_sat_entities", () => {
    const satEntity = makeSatEntity(25544);
    const riskEntity = makeRiskEntity(1);
    const v = makeViewer([satEntity, riskEntity]);

    clearRiskPolylines(v);

    expect(v.entities.remove).toHaveBeenCalledOnce();
    expect(v.entities.remove).toHaveBeenCalledWith(riskEntity);
    expect(v.entities.values).toContain(satEntity);
    expect(v.entities.values).not.toContain(riskEntity);
  });

  it("test_clearRiskPolylines_noop_when_empty", () => {
    const v = makeViewer();
    expect(() => clearRiskPolylines(v)).not.toThrow();
    expect(v.entities.remove).not.toHaveBeenCalled();
  });
});

// ─── S8.1 FR-6 — fetchAndRenderRisk ──────────────────────────────────────────

describe("S8.1 FR-6 — fetchAndRenderRisk", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockEntity.mockImplementation((opts) => ({ ...opts }));
    MockPolylineGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
  });

  it("test_fetchAndRenderRisk_success", async () => {
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisA = makeSatEntity(40000, POS_B);
    const staleRisk = makeRiskEntity(0);
    const v = makeViewer([satISS, satDebrisA, staleRisk]);
    mockFetchConjunctions.mockResolvedValue([CONJ_CLOSE]);

    const count = await fetchAndRenderRisk(v);

    // Stale risk entity was removed, new one was added
    expect(count).toBe(1);
    expect(v.entities.remove).toHaveBeenCalledWith(staleRisk);
    expect(v.entities.add).toHaveBeenCalledOnce();
    expect(v.entities.add.mock.calls[0][0].id).toBe("risk-1");
  });

  it("test_fetchAndRenderRisk_empty_result", async () => {
    const staleRisk = makeRiskEntity(0);
    const v = makeViewer([staleRisk]);
    mockFetchConjunctions.mockResolvedValue([]);

    const count = await fetchAndRenderRisk(v);

    expect(count).toBe(0);
    // Stale polyline cleared even on empty result
    expect(v.entities.remove).toHaveBeenCalledWith(staleRisk);
    expect(v.entities.add).not.toHaveBeenCalled();
  });

  it("test_fetchAndRenderRisk_fetch_error", async () => {
    const staleRisk = makeRiskEntity(0);
    const v = makeViewer([staleRisk]);
    mockFetchConjunctions.mockRejectedValue(new Error("Network error"));

    const count = await fetchAndRenderRisk(v);

    expect(count).toBe(0);
    // No clear or add on fetch failure
    expect(v.entities.remove).not.toHaveBeenCalled();
    expect(v.entities.add).not.toHaveBeenCalled();
  });
});

// ─── S8.2 FR-1 — buildCallbackPositions ──────────────────────────────────────

describe("S8.2 FR-1 — buildCallbackPositions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockCallbackProperty.mockImplementation((cb, isConst) => ({
      _cb: cb,
      isConstant: isConst,
    }));
  });

  it("test_buildCallbackPositions_returns_callback_property", () => {
    const entityA = makeSatEntity(25544, POS_A);
    const entityB = makeSatEntity(40000, POS_B);
    buildCallbackPositions(entityA, entityB);
    expect(MockCallbackProperty).toHaveBeenCalledOnce();
    expect(MockCallbackProperty).toHaveBeenCalledWith(
      expect.any(Function),
      false,
    );
  });

  it("test_buildCallbackPositions_callback_returns_positions", () => {
    const entityA = makeSatEntity(25544, POS_A);
    const entityB = makeSatEntity(40000, POS_B);
    buildCallbackPositions(entityA, entityB);
    const cb = MockCallbackProperty.mock.calls[0][0];
    const result = cb(MOCK_TIME);
    expect(result).toEqual([POS_A, POS_B]);
  });

  it("test_buildCallbackPositions_callback_returns_undefined_when_posA_null", () => {
    const entityA = {
      id: "sat-25544",
      position: { getValue: vi.fn(() => null) },
    };
    const entityB = makeSatEntity(40000, POS_B);
    buildCallbackPositions(entityA, entityB);
    const cb = MockCallbackProperty.mock.calls[0][0];
    const result = cb(MOCK_TIME);
    expect(result).toBeUndefined();
  });

  it("test_buildCallbackPositions_callback_returns_undefined_when_posB_null", () => {
    const entityA = makeSatEntity(25544, POS_A);
    const entityB = {
      id: "sat-40000",
      position: { getValue: vi.fn(() => null) },
    };
    buildCallbackPositions(entityA, entityB);
    const cb = MockCallbackProperty.mock.calls[0][0];
    const result = cb(MOCK_TIME);
    expect(result).toBeUndefined();
  });
});

// ─── S8.2 FR-2 — loadRiskPolylines uses CallbackProperty ─────────────────────

describe("S8.2 FR-2 — loadRiskPolylines (tracking)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockEntity.mockImplementation((opts) => ({ ...opts }));
    MockPolylineGraphics.mockImplementation((opts) => ({ ...opts }));
    MockColorMaterialProperty.mockImplementation((color) => ({
      _color: color,
    }));
    MockCallbackProperty.mockImplementation((cb, isConst) => ({
      _cb: cb,
      isConstant: isConst,
    }));
  });

  it("test_loadRiskPolylines_positions_is_callback_property", () => {
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisA = makeSatEntity(40000, POS_B);
    const v = makeViewer([satISS, satDebrisA]);

    loadRiskPolylines(v, [CONJ_CLOSE]);

    expect(MockCallbackProperty).toHaveBeenCalledOnce();
    const cbInstance = MockCallbackProperty.mock.results[0].value;
    const addedEntity = v.entities.add.mock.calls[0][0];
    expect(addedEntity.polyline.positions).toBe(cbInstance);
  });

  it("test_loadRiskPolylines_missing_sat_guard_preserved", () => {
    // sat-40000 missing → CONJ_CLOSE skipped; sat-41000 present → CONJ_MODERATE added
    const satISS = makeSatEntity(25544, POS_A);
    const satDebrisB = makeSatEntity(41000, POS_B);
    const v = makeViewer([satISS, satDebrisB]);

    const count = loadRiskPolylines(v, [CONJ_CLOSE, CONJ_MODERATE]);

    expect(count).toBe(1);
    expect(v.entities.add.mock.calls[0][0].id).toBe("risk-2");
  });
});

// ─── S8.2 FR-3 — startRiskRefresh / stopRiskRefresh ──────────────────────────

describe("S8.2 FR-3 — startRiskRefresh / stopRiskRefresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockFetchConjunctions.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("test_startRiskRefresh_calls_fetchAndRender_after_interval", async () => {
    const v = makeViewer();
    const handle = startRiskRefresh(v, 1000);

    expect(mockFetchConjunctions).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1000);
    expect(mockFetchConjunctions).toHaveBeenCalledOnce();

    stopRiskRefresh(handle);
  });

  it("test_startRiskRefresh_calls_repeatedly", async () => {
    const v = makeViewer();
    const handle = startRiskRefresh(v, 1000);

    await vi.advanceTimersByTimeAsync(2000);
    expect(mockFetchConjunctions).toHaveBeenCalledTimes(2);

    stopRiskRefresh(handle);
  });

  it("test_stopRiskRefresh_prevents_further_calls", async () => {
    const v = makeViewer();
    const handle = startRiskRefresh(v, 1000);

    await vi.advanceTimersByTimeAsync(1000);
    expect(mockFetchConjunctions).toHaveBeenCalledOnce();

    stopRiskRefresh(handle);
    await vi.advanceTimersByTimeAsync(1000);
    // Still only one call after stop
    expect(mockFetchConjunctions).toHaveBeenCalledOnce();
  });
});
