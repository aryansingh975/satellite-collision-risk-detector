// Mock API server for frontend development — S2.5.
//
// Serves fixture data at the same URL paths as the live FastAPI backend so
// that the frontend can be developed without a running backend.
//
// Usage:
//   cd frontend/mock
//   npm install        # first time only
//   npm start          # starts on http://localhost:8001
//
// Base URL convention (set in frontend/.env or shell before running Vite):
//   VITE_API_BASE_URL=http://localhost:8001  → this mock server
//   VITE_API_BASE_URL=http://localhost:8000  → live FastAPI backend

"use strict";

const express = require("express");
const fs = require("fs");
const path = require("path");

const PORT = process.env.MOCK_PORT || 8001;
const FIXTURES_DIR = path.join(__dirname, "fixtures");

// ---------------------------------------------------------------------------
// Load all fixture files at startup — exit immediately if any are missing.
// ---------------------------------------------------------------------------
function loadFixtures() {
  const names = [
    "satellites",
    "satellite_detail",
    "positions",
    "positions_bulk",
    "conjunctions",
    "conjunction_detail",
    "orbital_regions",
    "risk_ranking",
  ];
  const fixtures = {};
  for (const name of names) {
    const filePath = path.join(FIXTURES_DIR, `${name}.json`);
    if (!fs.existsSync(filePath)) {
      console.error(`[mock] FATAL: missing fixture file: ${filePath}`);
      process.exit(1);
    }
    fixtures[name] = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    console.log(`[mock] loaded ${name}.json`);
  }
  return fixtures;
}

const fixtures = loadFixtures();
const app = express();

// ---------------------------------------------------------------------------
// CORS — allow Vite dev server (any origin) to call this mock.
// ---------------------------------------------------------------------------
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  console.log(`[mock] ${new Date().toISOString()}  ${req.method} ${req.path}`);
  next();
});

// ---------------------------------------------------------------------------
// Routes — registered in order from most to least specific.
// ---------------------------------------------------------------------------

// GET /health
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

// GET /satellites/:catalog_no/positions  (must come before /satellites/:catalog_no)
app.get("/satellites/:catalog_no/positions", (req, res) => {
  const catalogNo = parseInt(req.params.catalog_no, 10);
  if (catalogNo === fixtures.positions.catalog_no) {
    return res.json(fixtures.positions);
  }
  const bulk = fixtures.positions_bulk.find((p) => p.catalog_no === catalogNo);
  if (bulk) return res.json(bulk);
  res.status(404).json({ detail: `No positions found for satellite ${catalogNo}` });
});

// GET /satellites/:catalog_no
app.get("/satellites/:catalog_no", (req, res) => {
  const catalogNo = parseInt(req.params.catalog_no, 10);
  if (catalogNo === fixtures.satellite_detail.catalog_no) {
    return res.json(fixtures.satellite_detail);
  }
  const sat = fixtures.satellites.find((s) => s.catalog_no === catalogNo);
  if (sat) return res.json(sat);
  res.status(404).json({ detail: `Satellite ${catalogNo} not found` });
});

// GET /satellites
app.get("/satellites", (req, res) => {
  let sats = fixtures.satellites;
  if (req.query.regime) {
    sats = sats.filter((s) => s.regime === req.query.regime);
  }
  if (req.query.group) {
    sats = sats.filter((s) => s.group_name === req.query.group);
  }
  const skip = parseInt(req.query.skip ?? "0", 10);
  const limit = parseInt(req.query.limit ?? "100", 10);
  res.json(sats.slice(skip, skip + limit));
});

// GET /positions (bulk)
app.get("/positions", (_req, res) => {
  res.json(fixtures.positions_bulk);
});

// GET /conjunctions/:id  (must come before /conjunctions)
app.get("/conjunctions/:id", (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (id === fixtures.conjunction_detail.id) {
    return res.json(fixtures.conjunction_detail);
  }
  const conj = fixtures.conjunctions.find((c) => c.id === id);
  if (conj) return res.json(conj);
  res.status(404).json({ detail: `Conjunction ${id} not found` });
});

// GET /conjunctions
app.get("/conjunctions", (req, res) => {
  const threshold = parseFloat(req.query.threshold ?? "5.0");
  const filtered = fixtures.conjunctions.filter((c) => c.miss_km <= threshold);
  res.json(filtered);
});

// GET /stats/orbital-regions
app.get("/stats/orbital-regions", (_req, res) => {
  res.json(fixtures.orbital_regions);
});

// GET /stats/risk-ranking
app.get("/stats/risk-ranking", (req, res) => {
  const limit = parseInt(req.query.limit ?? "10", 10);
  res.json(fixtures.risk_ranking.slice(0, limit));
});

// 404 fallback for any unrecognised path
app.use((_req, res) => {
  res.status(404).json({ detail: "not found" });
});

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`[mock] Mock API server running at http://localhost:${PORT}`);
  console.log(`[mock] Set VITE_API_BASE_URL=http://localhost:${PORT} in frontend/.env`);
});
