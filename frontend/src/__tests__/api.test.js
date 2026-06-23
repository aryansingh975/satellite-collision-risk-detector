import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";
import satellitesFixture from "../../mock/fixtures/satellites.json";
import satelliteDetailFixture from "../../mock/fixtures/satellite_detail.json";
import positionsFixture from "../../mock/fixtures/positions.json";
import positionsBulkFixture from "../../mock/fixtures/positions_bulk.json";
import conjunctionsFixture from "../../mock/fixtures/conjunctions.json";
import orbitalRegionsFixture from "../../mock/fixtures/orbital_regions.json";
import riskRankingFixture from "../../mock/fixtures/risk_ranking.json";
import {
  fetchSatellites,
  fetchSatellite,
  fetchPositions,
  fetchBulkPositions,
  fetchConjunctions,
  fetchConjunction,
  fetchOrbitalRegions,
  fetchRiskRanking,
  fetchHealth,
} from "../api.js";

function okResponse(data) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

function errorResponse(status) {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve({ detail: "error" }),
  });
}

describe("S7.2 — API Client Layer", () => {
  let fetchSpy;

  beforeEach(() => {
    fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("test_fetchSatellites_success", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(satellitesFixture));
    const result = await fetchSatellites();
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBeGreaterThan(0);
    expect(result[0]).toHaveProperty("catalog_no");
    expect(result[0]).toHaveProperty("regime");
  });

  it("test_fetchSatellites_empty", async () => {
    fetchSpy.mockReturnValueOnce(okResponse([]));
    const result = await fetchSatellites();
    expect(result).toEqual([]);
  });

  it("test_fetchSatellite_found", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(satelliteDetailFixture));
    const result = await fetchSatellite(25544);
    expect(result.catalog_no).toBe(25544);
  });

  it("test_fetchSatellite_not_found", async () => {
    fetchSpy.mockReturnValueOnce(errorResponse(404));
    const result = await fetchSatellite(99999);
    expect(result).toBeNull();
  });

  it("test_fetchSatellite_server_error", async () => {
    fetchSpy.mockReturnValueOnce(errorResponse(500));
    await expect(fetchSatellite(25544)).rejects.toThrow("500");
  });

  it("test_fetchPositions_success", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(positionsFixture));
    const result = await fetchPositions(
      25544,
      "2026-06-21T00:00:00Z",
      "2026-06-21T01:00:00Z",
    );
    expect(Array.isArray(result.positions)).toBe(true);
    expect(result.positions.length).toBeGreaterThan(0);
    expect(result.positions[0]).toHaveProperty("lat");
    expect(result.positions[0]).toHaveProperty("lon");
    expect(result.positions[0]).toHaveProperty("alt_km");
  });

  it("test_fetchBulkPositions_query_param", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(positionsBulkFixture));
    await fetchBulkPositions(
      [25544, 43013],
      "2026-06-21T00:00:00Z",
      "2026-06-21T01:00:00Z",
    );
    expect(fetchSpy).toHaveBeenCalledOnce();
    const calledUrl = fetchSpy.mock.calls[0][0];
    expect(calledUrl).toMatch(/catalog_nos=25544(?:%2C|,)43013/);
  });

  it("test_fetchConjunctions_success", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(conjunctionsFixture));
    const result = await fetchConjunctions();
    expect(Array.isArray(result)).toBe(true);
    const atRisk = result.filter((c) => c.miss_km <= 5);
    expect(atRisk.length).toBeGreaterThan(0);
  });

  it("test_fetchConjunction_not_found", async () => {
    fetchSpy.mockReturnValueOnce(errorResponse(404));
    const result = await fetchConjunction(9999);
    expect(result).toBeNull();
  });

  it("test_fetchOrbitalRegions", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(orbitalRegionsFixture));
    const result = await fetchOrbitalRegions();
    expect(result.leo + result.meo + result.geo + result.heo).toBe(
      result.total,
    );
  });

  it("test_fetchRiskRanking", async () => {
    fetchSpy.mockReturnValueOnce(okResponse(riskRankingFixture));
    const result = await fetchRiskRanking();
    expect(Array.isArray(result)).toBe(true);
    for (let i = 1; i < result.length; i++) {
      expect(result[i].miss_km).toBeGreaterThanOrEqual(result[i - 1].miss_km);
    }
  });

  it("test_base_url_default", async () => {
    // VITE_API_BASE_URL is unset in the test environment → BASE_URL falls back to
    // http://localhost:8000 (the default live backend address)
    fetchSpy.mockReturnValueOnce(okResponse(satellitesFixture));
    await fetchSatellites();
    const calledUrl = fetchSpy.mock.calls[0][0];
    expect(calledUrl).toMatch(/^http:\/\/localhost:8000/);
  });

  it("test_no_undefined_query_params", async () => {
    fetchSpy.mockReturnValueOnce(okResponse([]));
    await fetchSatellites({});
    const calledUrl = fetchSpy.mock.calls[0][0];
    expect(calledUrl).not.toContain("undefined");
  });
});

// ---------------------------------------------------------------------------
// S10.2 — Frontend Live Wiring
// ---------------------------------------------------------------------------

describe("S10.2 — Frontend Live Wiring", () => {
  let fetchSpy;

  beforeEach(() => {
    fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("test_default_base_url_is_live", async () => {
    // VITE_API_BASE_URL absent → calls go to http://localhost:8000
    fetchSpy.mockReturnValueOnce(okResponse([]));
    await fetchSatellites();
    expect(fetchSpy.mock.calls[0][0]).toMatch(/^http:\/\/localhost:8000/);
  });

  it("test_env_override_respected", async () => {
    // When VITE_API_BASE_URL is set to the mock URL, api.js must use it
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8001");
    vi.resetModules();
    const { fetchSatellites: fetchSatsOverride } = await import("../api.js");
    const spyOverride = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });
    vi.stubGlobal("fetch", spyOverride);
    await fetchSatsOverride();
    expect(spyOverride.mock.calls[0][0]).toMatch(/^http:\/\/localhost:8001/);
  });

  it("test_no_mock_url_hardcoded", () => {
    // localhost:8001 must never appear as a hard-coded default in api.js
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    const src = readFileSync(resolve(__dirname, "../api.js"), "utf-8");
    expect(src).not.toContain("localhost:8001");
  });

  it("test_fetch_conjunctions_uses_base_url", async () => {
    fetchSpy.mockReturnValueOnce(okResponse([]));
    await fetchConjunctions();
    expect(fetchSpy.mock.calls[0][0]).toMatch(
      /^http:\/\/localhost:8000\/conjunctions/,
    );
  });

  it("test_fetch_health_ok", async () => {
    fetchSpy.mockReturnValueOnce(okResponse({ status: "ok" }));
    const result = await fetchHealth();
    expect(result).toEqual({ status: "ok" });
  });
});
