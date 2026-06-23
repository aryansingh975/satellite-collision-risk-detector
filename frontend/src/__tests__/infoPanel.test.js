import { describe, it, expect, vi, beforeEach } from "vitest";
import { initInfoPanel } from "../infoPanel.js";

// ─── DOM fixture ─────────────────────────────────────────────────────────────

function setupDOM() {
  document.body.innerHTML = `
    <div id="info-panel" style="display:none">
      <button id="info-close">×</button>
      <span id="info-name"></span>
      <span id="info-catalog-no"></span>
      <span id="info-intl-designator"></span>
      <span id="info-epoch"></span>
      <span id="info-regime"></span>
      <span id="info-a-km"></span>
      <span id="info-ecc"></span>
      <span id="info-inc-deg"></span>
      <span id="info-period"></span>
      <ul id="info-conjunctions"></ul>
    </div>
  `;
}

// ─── Viewer mock ──────────────────────────────────────────────────────────────

function makeViewer() {
  const listeners = [];
  const viewer = {
    selectedEntity: undefined,
    selectedEntityChanged: {
      addEventListener: vi.fn((fn) => listeners.push(fn)),
    },
  };
  // fire awaits all async listeners so tests can simply `await fire(entity)`
  const fire = async (entity) => {
    for (const fn of listeners) {
      await fn(entity);
    }
  };
  return { viewer, fire };
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const FULL_SAT = {
  catalog_no: 25544,
  name: "ISS (ZARYA)",
  intl_designator: "1998-067A",
  epoch: "2024-01-15T12:00:00Z",
  regime: "LEO",
  a_km: 6778.14,
  ecc: 0.000123,
  inc_deg: 51.64,
  mean_motion: 15.09,
  line1:
    "1 25544U 98067A   24015.50000000  .00000000  00000-0  00000-0 0  9999",
  line2:
    "2 25544  51.6400   0.0000 0001230   0.0000   0.0000 15.09000000000000",
};

function makeConj(id, sat_a, sat_b, sat_a_name, sat_b_name, miss_km) {
  return {
    id,
    sat_a,
    sat_b,
    sat_a_name,
    sat_b_name,
    tca: "2024-01-16T03:22:00Z",
    miss_km,
    rel_vel_kms: 12.345,
    window_start: "2024-01-15T12:00:00Z",
    computed_at: "2024-01-15T11:00:00Z",
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("S8.4 — Info Panel", () => {
  beforeEach(() => {
    setupDOM();
  });

  it("test_show_hide_panel — shows panel on selection, hides on deselect", async () => {
    const { viewer, fire } = makeViewer();
    const fetchSat = vi.fn().mockResolvedValue(FULL_SAT);
    const fetchConj = vi.fn().mockResolvedValue([]);

    initInfoPanel(viewer, fetchSat, fetchConj);

    const panel = document.getElementById("info-panel");
    expect(panel.style.display).toBe("none");

    // select entity with catalog_no → panel shows, fetch is called
    await fire({ properties: { catalog_no: 25544 } });
    expect(panel.style.display).toBe("block");
    expect(fetchSat).toHaveBeenCalledWith(25544);

    // deselect (null entity) → panel hides
    await fire(null);
    expect(panel.style.display).toBe("none");
  });

  it("test_populate_orbital_details — full SatelliteDetail populates all fields", async () => {
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(FULL_SAT),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    expect(document.getElementById("info-name").textContent).toBe(
      "ISS (ZARYA)",
    );
    expect(document.getElementById("info-catalog-no").textContent).toBe(
      "25544",
    );
    expect(document.getElementById("info-regime").textContent).toBe("LEO");
    expect(document.getElementById("info-a-km").textContent).toBe("6778.14");
    expect(document.getElementById("info-ecc").textContent).toBe("0.000123");
    expect(document.getElementById("info-inc-deg").textContent).toBe("51.64");
    expect(document.getElementById("info-period").textContent).toBe("95.43");
  });

  it("test_null_elements_render_dash — null orbital elements render as —", async () => {
    const nullSat = {
      ...FULL_SAT,
      a_km: null,
      ecc: null,
      inc_deg: null,
      mean_motion: null,
    };
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(nullSat),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    expect(document.getElementById("info-a-km").textContent).toBe("—");
    expect(document.getElementById("info-ecc").textContent).toBe("—");
    expect(document.getElementById("info-inc-deg").textContent).toBe("—");
    expect(document.getElementById("info-period").textContent).toBe("—");
  });

  it("test_period_calculation — 1440 / mean_motion toFixed(2)", async () => {
    const sat = { ...FULL_SAT, mean_motion: 15.09 };
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(sat),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    // 1440 / 15.09 = 95.4274... → "95.43"
    expect(document.getElementById("info-period").textContent).toBe("95.43");
  });

  it("test_filters_conjunctions_by_catalog_no — only sat 25544 events shown", async () => {
    const conj1 = makeConj(1, 25544, 99001, "ISS", "DEBRIS-A", 1.2);
    const conj2 = makeConj(2, 25544, 99002, "ISS", "DEBRIS-B", 3.4);
    const conj3 = makeConj(3, 11111, 22222, "OTHER-A", "OTHER-B", 0.5);

    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(FULL_SAT),
      vi.fn().mockResolvedValue([conj1, conj2, conj3]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    const items = document
      .getElementById("info-conjunctions")
      .querySelectorAll("li");
    expect(items).toHaveLength(2);
  });

  it("test_conjunction_partner_name — correct partner name from sat_a / sat_b side", async () => {
    // sat_a = 25544 → partner is sat_b_name
    const conj1 = makeConj(1, 25544, 99001, "STATION-A", "DEBRIS-A", 1.2);
    // sat_b = 25544 → partner is sat_a_name
    const conj2 = makeConj(2, 88888, 25544, "OTHER-SAT", "STATION-B", 0.5);

    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(FULL_SAT),
      vi.fn().mockResolvedValue([conj1, conj2]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    const html = document.getElementById("info-conjunctions").innerHTML;
    expect(html).toContain("DEBRIS-A");
    expect(html).toContain("OTHER-SAT");
    // Own-side names must not appear as partner labels
    expect(html).not.toContain("STATION-A");
    expect(html).not.toContain("STATION-B");
  });

  it("test_no_conjunctions_message — empty array renders 'No conjunctions detected.'", async () => {
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(FULL_SAT),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    expect(document.getElementById("info-conjunctions").textContent).toContain(
      "No conjunctions detected.",
    );
  });

  it("test_close_button_clears_selection — click sets viewer.selectedEntity = undefined", async () => {
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(FULL_SAT),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 25544 } });

    viewer.selectedEntity = { properties: { catalog_no: 25544 } };
    document.getElementById("info-close").click();

    expect(viewer.selectedEntity).toBeUndefined();
  });

  it("test_satellite_not_found — null fetch result shows error, does not throw", async () => {
    const { viewer, fire } = makeViewer();
    initInfoPanel(
      viewer,
      vi.fn().mockResolvedValue(null),
      vi.fn().mockResolvedValue([]),
    );

    await fire({ properties: { catalog_no: 99999 } });

    const panel = document.getElementById("info-panel");
    expect(panel.style.display).toBe("block");
    expect(document.getElementById("info-name").textContent).toContain(
      "Satellite not found",
    );
  });
});
