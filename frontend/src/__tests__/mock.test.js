import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const FIXTURES = join(__dirname, "../../mock/fixtures");

function loadFixture(name) {
  return JSON.parse(readFileSync(join(FIXTURES, name), "utf-8"));
}

const VALID_REGIMES = new Set(["LEO", "MEO", "GEO", "HEO"]);

describe("S2.5 — API Contract + Mock Server", () => {
  describe("test_satellites_fixture_schema", () => {
    it("satellites.json is a non-empty array with required fields and valid regimes", () => {
      const sats = loadFixture("satellites.json");
      expect(Array.isArray(sats)).toBe(true);
      expect(sats.length).toBeGreaterThan(0);
      for (const sat of sats) {
        expect(typeof sat.catalog_no).toBe("number");
        expect(typeof sat.name).toBe("string");
        expect(typeof sat.epoch).toBe("string");
        expect(typeof sat.updated_at).toBe("string");
        expect(sat.regime === null || VALID_REGIMES.has(sat.regime)).toBe(true);
      }
    });
  });

  describe("test_satellite_detail_fixture_schema", () => {
    it("satellite_detail.json has all SatelliteDetail fields and catalog_no 25544", () => {
      const sat = loadFixture("satellite_detail.json");
      expect(sat.catalog_no).toBe(25544);
      expect(typeof sat.name).toBe("string");
      expect(typeof sat.epoch).toBe("string");
      expect(typeof sat.updated_at).toBe("string");
      expect(typeof sat.line1).toBe("string");
      expect(typeof sat.line2).toBe("string");
      expect(sat.line1.length).toBeGreaterThan(0);
      expect(sat.line2.length).toBeGreaterThan(0);
    });
  });

  describe("test_positions_fixture_schema", () => {
    it("positions.json has catalog_no 25544 and ≥10 valid position samples", () => {
      const posResp = loadFixture("positions.json");
      expect(posResp.catalog_no).toBe(25544);
      expect(Array.isArray(posResp.positions)).toBe(true);
      expect(posResp.positions.length).toBeGreaterThanOrEqual(10);
      for (const p of posResp.positions) {
        expect(typeof p.time).toBe("string");
        expect(p.lat).toBeGreaterThanOrEqual(-90);
        expect(p.lat).toBeLessThanOrEqual(90);
        expect(p.lon).toBeGreaterThanOrEqual(-180);
        expect(p.lon).toBeLessThanOrEqual(180);
        expect(p.alt_km).toBeGreaterThan(0);
      }
    });
  });

  describe("test_conjunctions_fixture_schema", () => {
    it("conjunctions.json has ≥3 items, valid fields, and at least one miss_km ≤ 5", () => {
      const conj = loadFixture("conjunctions.json");
      expect(Array.isArray(conj)).toBe(true);
      expect(conj.length).toBeGreaterThanOrEqual(3);
      for (const c of conj) {
        expect(typeof c.sat_a).toBe("number");
        expect(typeof c.sat_b).toBe("number");
        expect(c.miss_km).toBeGreaterThan(0);
        expect(c.rel_vel_kms).toBeGreaterThan(0);
      }
      const hasRiskEvent = conj.some((c) => c.miss_km <= 5);
      expect(hasRiskEvent).toBe(true);
    });
  });

  describe("test_orbital_regions_total", () => {
    it("orbital_regions.json satisfies leo + meo + geo + heo === total", () => {
      const stats = loadFixture("orbital_regions.json");
      expect(typeof stats.leo).toBe("number");
      expect(typeof stats.meo).toBe("number");
      expect(typeof stats.geo).toBe("number");
      expect(typeof stats.heo).toBe("number");
      expect(typeof stats.total).toBe("number");
      expect(stats.leo + stats.meo + stats.geo + stats.heo).toBe(stats.total);
    });
  });

  describe("test_risk_ranking_sequential", () => {
    it("risk_ranking.json has sequential ranks and non-decreasing miss_km", () => {
      const ranking = loadFixture("risk_ranking.json");
      expect(Array.isArray(ranking)).toBe(true);
      expect(ranking.length).toBeGreaterThanOrEqual(5);
      for (let i = 0; i < ranking.length; i++) {
        expect(ranking[i].rank).toBe(i + 1);
      }
      for (let i = 1; i < ranking.length; i++) {
        expect(ranking[i].miss_km).toBeGreaterThanOrEqual(
          ranking[i - 1].miss_km,
        );
      }
    });
  });

  describe("test_positions_bulk_fixture_schema", () => {
    it("positions_bulk.json is an array of ≥2 PositionsResponse items with valid shape", () => {
      const bulk = loadFixture("positions_bulk.json");
      expect(Array.isArray(bulk)).toBe(true);
      expect(bulk.length).toBeGreaterThanOrEqual(2);
      for (const item of bulk) {
        expect(typeof item.catalog_no).toBe("number");
        expect(typeof item.name).toBe("string");
        expect(Array.isArray(item.positions)).toBe(true);
        expect(item.positions.length).toBeGreaterThan(0);
      }
    });
  });

  describe("test_all_regimes_represented", () => {
    it("satellites.json contains at least one satellite per regime (LEO, MEO, GEO, HEO)", () => {
      const sats = loadFixture("satellites.json");
      const regimes = new Set(sats.map((s) => s.regime));
      expect(regimes.has("LEO")).toBe(true);
      expect(regimes.has("MEO")).toBe(true);
      expect(regimes.has("GEO")).toBe(true);
      expect(regimes.has("HEO")).toBe(true);
    });
  });
});
