import { describe, it, expect, vi, beforeEach } from "vitest";

// Hoist mock factories so they are in scope when vi.mock() factories execute.
const {
  MockChart,
  mockFetchOrbitalRegions,
  mockFetchConjunctions,
  mockFetchRiskRanking,
} = vi.hoisted(() => {
  const MockChart = vi.fn().mockImplementation(function (canvas, config) {
    this.data = config.data;
    this.options = config.options;
    this.destroy = vi.fn();
  });
  const mockFetchOrbitalRegions = vi.fn();
  const mockFetchConjunctions = vi.fn();
  const mockFetchRiskRanking = vi.fn();
  return {
    MockChart,
    mockFetchOrbitalRegions,
    mockFetchConjunctions,
    mockFetchRiskRanking,
  };
});

// Replace Chart.js with a lightweight stub so jsdom's lack of canvas does not matter.
vi.mock("chart.js/auto", () => ({ default: MockChart }));

// Replace api.js so no live HTTP is ever made.
vi.mock("../api.js", () => ({
  fetchOrbitalRegions: mockFetchOrbitalRegions,
  fetchConjunctions: mockFetchConjunctions,
  fetchRiskRanking: mockFetchRiskRanking,
}));

import {
  initRegimeChart,
  regimeTooltipLabel,
  initApproachChart,
  bucketizeConjunctions,
  renderRiskTable,
  initRiskTable,
} from "../dashboard.js";

const STATS = { leo: 10, meo: 2, geo: 5, heo: 1, total: 18 };

describe("S9.1 — Regime Distribution Chart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Provide a fresh canvas in jsdom for every test.
    document.body.innerHTML = '<canvas id="regimeChart"></canvas>';
  });

  // FR-3 / Outcome 1
  it("test_initRegimeChart_returns_chart_instance", async () => {
    mockFetchOrbitalRegions.mockResolvedValue(STATS);
    const chart = await initRegimeChart();
    expect(chart).toBeDefined();
    expect(typeof chart.destroy).toBe("function");
    expect(chart.data).toBeDefined();
  });

  // FR-2 / Outcome 2
  it("test_initRegimeChart_data_matches_api", async () => {
    mockFetchOrbitalRegions.mockResolvedValue(STATS);
    const chart = await initRegimeChart();
    expect(chart.data.datasets[0].data).toEqual([10, 2, 5, 1]);
  });

  // FR-1 / Outcome 3 — null response yields zero-state chart
  it("test_initRegimeChart_null_response", async () => {
    mockFetchOrbitalRegions.mockResolvedValue(null);
    const chart = await initRegimeChart();
    expect(chart).toBeDefined();
    expect(chart.data.datasets[0].data).toEqual([0, 0, 0, 0]);
  });

  // FR-4 / Outcome 4 — percentage tooltip, normal case (10/18 = 55.6%)
  it("test_tooltip_percentage_normal", () => {
    const context = {
      parsed: 10,
      dataset: { data: [10, 2, 5, 1] },
      label: "LEO",
    };
    const result = regimeTooltipLabel(context);
    expect(result).toContain("10");
    expect(result).toContain("55.6%");
  });

  // FR-4 / Outcome 4 — zero-total guard: no NaN or Infinity
  it("test_tooltip_percentage_zero_total", () => {
    const context = {
      parsed: 0,
      dataset: { data: [0, 0, 0, 0] },
      label: "LEO",
    };
    const result = regimeTooltipLabel(context);
    expect(result).not.toContain("NaN");
    expect(result).not.toContain("Infinity");
    expect(result).toContain("0%");
  });

  // FR-2 / Outcome 2 — labels order
  it("test_initRegimeChart_labels", async () => {
    mockFetchOrbitalRegions.mockResolvedValue(STATS);
    const chart = await initRegimeChart();
    expect(chart.data.labels).toEqual(["LEO", "MEO", "GEO", "HEO"]);
  });

  // FR-3 — missing canvas throws a descriptive error
  it("test_initRegimeChart_missing_canvas", async () => {
    document.body.innerHTML = ""; // no canvas
    await expect(initRegimeChart()).rejects.toThrow("#regimeChart");
  });
});

// ---------------------------------------------------------------------------
// S9.2 — Close-Approach Count Chart
// ---------------------------------------------------------------------------

describe("S9.2 — Close-Approach Count Chart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '<canvas id="approachChart"></canvas>';
  });

  // FR-4 / Outcome 1
  it("test_initApproachChart_returns_chart_instance", async () => {
    mockFetchConjunctions.mockResolvedValue([
      { miss_km: 0.5 },
      { miss_km: 2.3 },
    ]);
    const chart = await initApproachChart();
    expect(chart).toBeDefined();
    expect(typeof chart.destroy).toBe("function");
    expect(chart.data).toBeDefined();
  });

  // FR-2 / FR-3 / Outcome 2
  it("test_initApproachChart_bucket_counts", async () => {
    mockFetchConjunctions.mockResolvedValue([
      { miss_km: 0.5 },
      { miss_km: 1.5 },
      { miss_km: 2.5 },
      { miss_km: 3.5 },
      { miss_km: 4.5 },
    ]);
    const chart = await initApproachChart();
    expect(chart.data.datasets[0].data).toEqual([1, 1, 1, 1, 1]);
  });

  // FR-1 / Outcome 3
  it("test_initApproachChart_empty_response", async () => {
    mockFetchConjunctions.mockResolvedValue([]);
    const chart = await initApproachChart();
    expect(chart).toBeDefined();
    expect(chart.data.datasets[0].data).toEqual([0, 0, 0, 0, 0]);
  });

  // FR-4 / Outcome 5
  it("test_initApproachChart_missing_canvas", async () => {
    document.body.innerHTML = ""; // no canvas
    await expect(initApproachChart()).rejects.toThrow("#approachChart");
  });

  // FR-3 / Outcome 2 — labels
  it("test_initApproachChart_labels", async () => {
    mockFetchConjunctions.mockResolvedValue([]);
    const chart = await initApproachChart();
    expect(chart.data.labels).toEqual([
      "< 1 km",
      "1–2 km",
      "2–3 km",
      "3–4 km",
      "4–5 km",
    ]);
  });
});

// ---------------------------------------------------------------------------
// S9.2 — bucketizeConjunctions (pure function — no DOM needed)
// ---------------------------------------------------------------------------

describe("S9.2 — bucketizeConjunctions", () => {
  // FR-2 / Outcome 4 — one event per band
  it("test_bucketizeConjunctions_bands", () => {
    const result = bucketizeConjunctions([
      { miss_km: 0.5 },
      { miss_km: 1.5 },
      { miss_km: 2.5 },
      { miss_km: 3.5 },
      { miss_km: 4.5 },
    ]);
    expect(result).toEqual([1, 1, 1, 1, 1]);
  });

  it("test_bucketizeConjunctions_empty", () => {
    expect(bucketizeConjunctions([])).toEqual([0, 0, 0, 0, 0]);
  });

  // boundary: 1.0 → band 1 (1–2 km), 2.0 → band 2 (2–3 km)
  it("test_bucketizeConjunctions_boundary", () => {
    expect(bucketizeConjunctions([{ miss_km: 1.0 }, { miss_km: 2.0 }])).toEqual(
      [0, 1, 1, 0, 0],
    );
  });

  // events above threshold silently dropped
  it("test_bucketizeConjunctions_over_threshold", () => {
    expect(bucketizeConjunctions([{ miss_km: 5.1 }])).toEqual([0, 0, 0, 0, 0]);
  });
});

// ---------------------------------------------------------------------------
// S9.3 — Risk Ranking Table
// ---------------------------------------------------------------------------

const RISK_ITEMS = [
  {
    rank: 1,
    sat_a: 25544,
    sat_b: 45000,
    sat_a_name: "ISS",
    sat_b_name: "STARLINK-1",
    miss_km: 1.23456,
    rel_vel_kms: 7.123,
    tca: "2026-06-23T14:32:01.000Z",
  },
  {
    rank: 2,
    sat_a: 25545,
    sat_b: 45001,
    sat_a_name: "NOAA 15",
    sat_b_name: "STARLINK-2",
    miss_km: 2.5,
    rel_vel_kms: 5.5,
    tca: "2026-06-24T08:00:00.000Z",
  },
  {
    rank: 3,
    sat_a: 25546,
    sat_b: 45002,
    sat_a_name: "TERRA",
    sat_b_name: "STARLINK-3",
    miss_km: 4.999,
    rel_vel_kms: 3.14,
    tca: "2026-06-25T12:00:00.000Z",
  },
];

describe("S9.3 — Risk Ranking Table", () => {
  let tableEl;
  let viewer;

  beforeEach(() => {
    vi.clearAllMocks();
    tableEl = document.createElement("table");
    tableEl.innerHTML =
      "<thead><tr>" +
      "<th>Rank</th><th>Satellite A</th><th>Satellite B</th>" +
      "<th>Miss (km)</th><th>Vel (km/s)</th><th>TCA (UTC)</th>" +
      "</tr></thead><tbody></tbody>";
    viewer = {
      entities: { getById: vi.fn() },
      flyTo: vi.fn().mockResolvedValue(undefined),
      selectedEntity: undefined,
    };
  });

  // FR-5 / Outcome 2 — correct row count
  it("test_renderRiskTable_row_count", () => {
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    const rows = tableEl.querySelectorAll("tbody tr");
    expect(rows.length).toBe(3);
  });

  // FR-1 / Outcome 2 — miss_km formatted to 3 decimal places
  it("test_renderRiskTable_miss_km_format", () => {
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    const cells = tableEl.querySelectorAll("tbody tr:first-child td");
    expect(cells[3].textContent).toBe("1.235");
  });

  // FR-1 / Outcome 2 — rel_vel_kms formatted to 2 decimal places
  it("test_renderRiskTable_rel_vel_format", () => {
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    const cells = tableEl.querySelectorAll("tbody tr:first-child td");
    expect(cells[4].textContent).toBe("7.12");
  });

  // FR-1 / Outcome 2 — TCA formatted as "YYYY-MM-DD HH:MM:SS"
  it("test_renderRiskTable_tca_format", () => {
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    const cells = tableEl.querySelectorAll("tbody tr:first-child td");
    expect(cells[5].textContent).toBe("2026-06-23 14:32:01");
  });

  // FR-3 / Outcome 3 — empty → "No risk events" single row
  it("test_renderRiskTable_empty", () => {
    renderRiskTable([], viewer, tableEl);
    const rows = tableEl.querySelectorAll("tbody tr");
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain("No risk events");
  });

  // FR-2 / Outcome 5 — click row selects satellite A on globe
  it("test_renderRiskTable_row_click_selects", () => {
    const fakeEntity = { id: "sat-25544" };
    viewer.entities.getById.mockReturnValue(fakeEntity);
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    tableEl.querySelector("tbody tr").click();
    expect(viewer.entities.getById).toHaveBeenCalledWith("sat-25544");
    expect(viewer.flyTo).toHaveBeenCalledWith(fakeEntity);
  });

  // FR-2 / Outcome 5 — entity not found → no error thrown
  it("test_renderRiskTable_entity_not_found", () => {
    viewer.entities.getById.mockReturnValue(null);
    renderRiskTable(RISK_ITEMS, viewer, tableEl);
    expect(() => tableEl.querySelector("tbody tr").click()).not.toThrow();
  });

  // FR-4 / Outcome 4 — missing #riskTable throws descriptive error
  it("test_initRiskTable_missing_table", async () => {
    document.body.innerHTML = "";
    await expect(initRiskTable(viewer)).rejects.toThrow("#riskTable");
  });

  // FR-1 / Outcome 1 — resolves and calls fetchRiskRanking with default limit
  it("test_initRiskTable_calls_fetch", async () => {
    document.body.innerHTML =
      '<table id="riskTable"><thead></thead><tbody></tbody></table>';
    mockFetchRiskRanking.mockResolvedValue(RISK_ITEMS);
    await initRiskTable(viewer);
    expect(mockFetchRiskRanking).toHaveBeenCalledWith(10);
  });
});
