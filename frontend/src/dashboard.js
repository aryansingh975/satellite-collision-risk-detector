import Chart from "chart.js/auto";
import {
  fetchOrbitalRegions,
  fetchConjunctions,
  fetchRiskRanking,
} from "./api.js";
import { selectAndFly } from "./search.js";

const LABELS = ["LEO", "MEO", "GEO", "HEO"];
const COLORS = ["#38bdf8", "#86efac", "#fbbf24", "#c084fc"];
const COLORS_DIM = ["rgba(56,189,248,0.15)", "rgba(134,239,172,0.15)", "rgba(251,191,36,0.15)", "rgba(192,132,252,0.15)"];

const APPROACH_LABELS = ["< 1 km", "1–2 km", "2–3 km", "3–4 km", "4–5 km"];
const APPROACH_COLORS = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22d3ee"];

function updateStatCard(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function getSeverity(miss_km) {
  if (miss_km < 1) return { label: "CRITICAL", rowCls: "sev-critical", badgeCls: "badge-critical" };
  if (miss_km < 2) return { label: "HIGH",     rowCls: "sev-high",     badgeCls: "badge-high" };
  if (miss_km < 3) return { label: "MED",      rowCls: "sev-medium",   badgeCls: "badge-medium" };
  return              { label: "LOW",      rowCls: "sev-low",      badgeCls: "badge-low" };
}

// ---------------------------------------------------------------------------
// S9.1 — Regime Distribution Chart
// ---------------------------------------------------------------------------

export function regimeTooltipLabel(context) {
  const count = context.parsed;
  const total = context.dataset.data.reduce((a, b) => a + b, 0);
  const pct = total === 0 ? "0.0" : ((count / total) * 100).toFixed(1);
  return `${context.label}: ${count} (${pct}%)`;
}

export async function initRegimeChart() {
  const canvas = document.getElementById("regimeChart");
  if (!canvas) {
    throw new Error("#regimeChart canvas element not found in DOM");
  }

  const stats = await fetchOrbitalRegions();
  const d = stats ?? { leo: 0, meo: 0, geo: 0, heo: 0 };
  const total = (d.leo ?? 0) + (d.meo ?? 0) + (d.geo ?? 0) + (d.heo ?? 0);
  updateStatCard("stat-total-sats", total > 0 ? total.toLocaleString() : "—");

  return new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: LABELS,
      datasets: [
        {
          data: [d.leo, d.meo, d.geo, d.heo],
          backgroundColor: COLORS,
          hoverBackgroundColor: COLORS,
          borderColor: COLORS_DIM,
          borderWidth: 2,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#94a3b8",
            font: { size: 10 },
            padding: 10,
            boxWidth: 10,
            boxHeight: 10,
          },
        },
        tooltip: {
          backgroundColor: "rgba(8,10,18,0.95)",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f1f5f9",
          bodyColor: "#94a3b8",
          callbacks: { label: regimeTooltipLabel },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// S9.2 — Close-Approach Count Chart
// ---------------------------------------------------------------------------

export function bucketizeConjunctions(conjunctions) {
  const counts = [0, 0, 0, 0, 0];
  for (const { miss_km } of conjunctions) {
    if (miss_km > 5) continue;
    const band = Math.min(Math.floor(miss_km), 4);
    counts[band]++;
  }
  return counts;
}

export async function initApproachChart() {
  const canvas = document.getElementById("approachChart");
  if (!canvas) {
    throw new Error("#approachChart canvas element not found in DOM");
  }

  const conjunctions = await fetchConjunctions();
  const counts = bucketizeConjunctions(conjunctions);
  updateStatCard("stat-conjunctions", conjunctions.length);

  return new Chart(canvas, {
    type: "bar",
    data: {
      labels: APPROACH_LABELS,
      datasets: [
        {
          label: "Conjunctions",
          data: counts,
          backgroundColor: APPROACH_COLORS.map((c) => c + "99"),
          borderColor: APPROACH_COLORS,
          borderWidth: 1,
          borderRadius: 4,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(8,10,18,0.95)",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f1f5f9",
          bodyColor: "#94a3b8",
          callbacks: {
            label: (context) => `${context.label}: ${context.parsed.y} event${context.parsed.y !== 1 ? "s" : ""}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#64748b", font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255,255,255,0.06)" },
          ticks: { color: "#64748b", font: { size: 10 }, precision: 0 },
          title: { display: false },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// S9.3 — Risk Ranking Table
// ---------------------------------------------------------------------------

export function renderRiskTable(items, viewer, tableEl) {
  const tbody = tableEl.querySelector("tbody");
  tbody.innerHTML = "";

  if (items.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 7;
    td.textContent = "No risk events detected";
    td.style.cssText = "text-align:center;color:#475569;padding:12px 0;";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  for (const item of items) {
    const tr = document.createElement("tr");
    const sev = getSeverity(item.miss_km);
    tr.classList.add(sev.rowCls);

    const tcaFormatted = item.tca.replace("T", " ").slice(0, 19);
    for (const text of [
      item.rank,
      item.sat_a_name,
      item.sat_b_name,
      item.miss_km.toFixed(3),
      item.rel_vel_kms.toFixed(2),
      tcaFormatted,
    ]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.appendChild(td);
    }

    // Severity badge column (7th — index 6, not checked by existing tests)
    const tdSev = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `sev-badge ${sev.badgeCls}`;
    badge.textContent = sev.label;
    tdSev.appendChild(badge);
    tr.appendChild(tdSev);

    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => {
      if (!viewer?.entities) return;
      const entity = viewer.entities.getById(`sat-${item.sat_a}`);
      if (entity == null) return;
      selectAndFly(entity, viewer);
    });
    tbody.appendChild(tr);
  }
}

export async function initRiskTable(viewer, limit = 10) {
  const tableEl = document.getElementById("riskTable");
  if (!tableEl) {
    throw new Error("#riskTable element not found in DOM");
  }
  const items = await fetchRiskRanking(limit);
  if (items.length > 0) updateStatCard("stat-closest", items[0].miss_km.toFixed(2));
  else updateStatCard("stat-closest", "—");
  renderRiskTable(items, viewer, tableEl);
}

// ---------------------------------------------------------------------------
// S9.4 — Dashboard Refresh Wiring
// ---------------------------------------------------------------------------

export function updateTimestamp() {
  const el = document.getElementById("lastUpdated");
  if (!el) return;
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  el.textContent = `Last updated: ${hh}:${mm}:${ss}`;
}

export async function refreshDashboard(charts, viewer) {
  const [regionsResult, conjsResult, rankingResult] = await Promise.allSettled([
    fetchOrbitalRegions(),
    fetchConjunctions(),
    fetchRiskRanking(10),
  ]);

  if (regionsResult.status === "fulfilled") {
    const d = regionsResult.value ?? { leo: 0, meo: 0, geo: 0, heo: 0 };
    charts.regime.data.datasets[0].data = [d.leo, d.meo, d.geo, d.heo];
    charts.regime.update();
    const total = (d.leo ?? 0) + (d.meo ?? 0) + (d.geo ?? 0) + (d.heo ?? 0);
    updateStatCard("stat-total-sats", total > 0 ? total.toLocaleString() : "—");
  }

  if (conjsResult.status === "fulfilled") {
    const conjs = conjsResult.value ?? [];
    charts.approach.data.datasets[0].data = bucketizeConjunctions(conjs);
    charts.approach.update();
    updateStatCard("stat-conjunctions", conjs.length);
  }

  if (rankingResult.status === "fulfilled") {
    const items = rankingResult.value ?? [];
    const tableEl = document.getElementById("riskTable");
    if (tableEl) renderRiskTable(items, viewer, tableEl);
    if (items.length > 0) updateStatCard("stat-closest", items[0].miss_km.toFixed(2));
  }

  updateTimestamp();
}

export function wireRefreshBtn(charts, viewer) {
  const btn = document.getElementById("refreshBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Refreshing…";
    await refreshDashboard(charts, viewer);
    btn.disabled = false;
    btn.textContent = "⟳ Refresh";
  });
}

export function startAutoRefresh(charts, viewer, intervalMs = 120_000) {
  return setInterval(() => refreshDashboard(charts, viewer), intervalMs);
}
