import { describe, it, expect, vi } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Mock Cesium so tests don't bundle the 50MB library in jsdom.
// Actual Cesium bundling is verified by `npm run build` (Outcome 2).
vi.mock("cesium", () => ({ VERSION: "1.x-mock" }));

describe("S1.6 — Cesium Frontend Scaffold", () => {
  it("test_placeholder — Vitest is configured and runs", () => {
    expect(true).toBe(true);
  });

  it("test_cesium_import — cesium npm package is installed with a valid version", () => {
    const pkgPath = join(
      __dirname,
      "..",
      "..",
      "node_modules",
      "cesium",
      "package.json",
    );
    const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
    expect(typeof pkg.version).toBe("string");
    expect(pkg.version.length).toBeGreaterThan(0);
  });

  it("test_cesium_base_url — initCesiumBaseUrl sets window.CESIUM_BASE_URL", async () => {
    const { initCesiumBaseUrl } = await import("../main.js");
    delete window.CESIUM_BASE_URL;
    initCesiumBaseUrl();
    expect(typeof window.CESIUM_BASE_URL).toBe("string");
    expect(window.CESIUM_BASE_URL.length).toBeGreaterThan(0);
  });

  it("test_no_ion_token — main.js contains no hardcoded Cesium ion token", () => {
    const mainPath = join(__dirname, "..", "main.js");
    const source = readFileSync(mainPath, "utf-8");
    expect(source).not.toMatch(/Ion\.defaultAccessToken/);
    expect(source).not.toMatch(/eyJhbGci/);
  });
});
