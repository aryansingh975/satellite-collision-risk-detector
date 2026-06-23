import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

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
    this.update = vi.fn();
  });
  return {
    MockChart,
    mockFetchOrbitalRegions: vi.fn(),
    mockFetchConjunctions: vi.fn(),
    mockFetchRiskRanking: vi.fn(),
  };
});

vi.mock("chart.js/auto", () => ({ default: MockChart }));
vi.mock("../api.js", () => ({
  fetchOrbitalRegions: mockFetchOrbitalRegions,
  fetchConjunctions: mockFetchConjunctions,
  fetchRiskRanking: mockFetchRiskRanking,
}));
vi.mock("../search.js", () => ({ selectAndFly: vi.fn() }));

import {
  refreshDashboard,
  updateTimestamp,
  startAutoRefresh,
  wireRefreshBtn,
} from "../dashboard.js";

// Synthetic chart objects — no real Chart.js needed.
const makeCharts = () => ({
  regime: { data: { datasets: [{ data: [] }] }, update: vi.fn() },
  approach: { data: { datasets: [{ data: [] }] }, update: vi.fn() },
});

// Flush all pending microtasks (safe when NOT using fake timers).
const flushMicrotasks = () => new Promise((r) => setTimeout(r, 0));

describe("S9.4 — Dashboard Refresh Wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = `
      <table id="riskTable"><thead></thead><tbody></tbody></table>
      <span id="lastUpdated"></span>
      <button id="refreshBtn">Refresh</button>
    `;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // FR-1 / Outcome 1 — both charts updated with correct data
  it("test_refreshDashboard_updates_both_charts", async () => {
    mockFetchOrbitalRegions.mockResolvedValue({
      leo: 100,
      meo: 20,
      geo: 10,
      heo: 5,
    });
    mockFetchConjunctions.mockResolvedValue([
      { miss_km: 0.5 },
      { miss_km: 2.5 },
    ]);
    mockFetchRiskRanking.mockResolvedValue([]);

    const charts = makeCharts();
    await refreshDashboard(charts, null);

    expect(charts.regime.data.datasets[0].data).toEqual([100, 20, 10, 5]);
    expect(charts.regime.update).toHaveBeenCalledOnce();
    expect(charts.approach.data.datasets[0].data).toEqual([1, 0, 1, 0, 0]);
    expect(charts.approach.update).toHaveBeenCalledOnce();
  });

  // FR-1 / Outcome 2 — one fetch failure must not abort the others
  it("test_refreshDashboard_partial_failure_isolation", async () => {
    mockFetchOrbitalRegions.mockRejectedValue(new Error("Network error"));
    mockFetchConjunctions.mockResolvedValue([{ miss_km: 1.5 }]);
    mockFetchRiskRanking.mockResolvedValue([]);

    const charts = makeCharts();
    await expect(refreshDashboard(charts, null)).resolves.toBeUndefined();

    // Regime chart skipped because its fetch failed.
    expect(charts.regime.update).not.toHaveBeenCalled();
    // Approach chart still updated.
    expect(charts.approach.update).toHaveBeenCalledOnce();
  });

  // FR-1 / Outcome 1 — empty / zero data is valid; update() still called
  it("test_refreshDashboard_empty_data", async () => {
    mockFetchOrbitalRegions.mockResolvedValue({});
    mockFetchConjunctions.mockResolvedValue([]);
    mockFetchRiskRanking.mockResolvedValue([]);

    const charts = makeCharts();
    await expect(refreshDashboard(charts, null)).resolves.not.toThrow();
    expect(charts.regime.update).toHaveBeenCalledOnce();
    expect(charts.approach.update).toHaveBeenCalledOnce();
  });

  // FR-3 / Outcome 4 — timestamp written with correct format
  it("test_updateTimestamp_sets_text", () => {
    updateTimestamp();
    const span = document.getElementById("lastUpdated");
    expect(span.textContent).toMatch(/^Last updated: \d{2}:\d{2}:\d{2}$/);
  });

  // FR-3 / Outcome 4 — absent element must not throw
  it("test_updateTimestamp_missing_element", () => {
    document.body.innerHTML = "";
    expect(() => updateTimestamp()).not.toThrow();
  });

  // FR-2 / Outcome 3 — button disabled during in-flight refresh, re-enabled after
  it("test_refreshBtn_disabled_during_refresh", async () => {
    let resolveRegions;
    mockFetchOrbitalRegions.mockReturnValue(
      new Promise((r) => {
        resolveRegions = r;
      }),
    );
    mockFetchConjunctions.mockResolvedValue([]);
    mockFetchRiskRanking.mockResolvedValue([]);

    const charts = makeCharts();
    wireRefreshBtn(charts, null);

    const btn = document.getElementById("refreshBtn");
    expect(btn.disabled).toBe(false);

    btn.click();

    // Synchronous state change happens before the first await inside the handler.
    expect(btn.disabled).toBe(true);
    expect(btn.textContent).toBe("Refreshing…");

    // Let the in-flight refresh complete.
    resolveRegions({ leo: 0, meo: 0, geo: 0, heo: 0 });
    await flushMicrotasks();

    expect(btn.disabled).toBe(false);
  });

  // FR-4 / Outcome 5 — returns an ID; clearInterval stops subsequent firings
  it("test_startAutoRefresh_returns_id_and_fires", async () => {
    vi.useFakeTimers();
    mockFetchOrbitalRegions.mockResolvedValue({
      leo: 0,
      meo: 0,
      geo: 0,
      heo: 0,
    });
    mockFetchConjunctions.mockResolvedValue([]);
    mockFetchRiskRanking.mockResolvedValue([]);

    const charts = makeCharts();
    const id = startAutoRefresh(charts, null, 5_000);

    expect(id).toBeDefined();

    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockFetchOrbitalRegions).toHaveBeenCalledOnce();

    clearInterval(id);
    mockFetchOrbitalRegions.mockClear();

    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockFetchOrbitalRegions).not.toHaveBeenCalled();
  });
});
