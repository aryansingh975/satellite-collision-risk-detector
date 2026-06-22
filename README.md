# 🛰️ Satellite Collision Risk Detector

A prototype system for identifying potential collision risks between Earth-orbiting satellites using publicly available orbital data.

> ⚠️ This project is currently under active development and is not yet production-ready.

---

## Overview

The Satellite Collision Risk Detector is designed to analyze satellite orbital data, propagate future positions, and identify close approaches that may represent potential collision risks.

The project combines orbital mechanics, data analysis, and interactive visualization to provide insights into satellite conjunction events.

---

## Objectives

- Retrieve and process satellite orbital data (TLEs)
- Propagate satellite orbits using SGP4
- Screen for close approaches between satellites
- Visualize satellite positions in a 3D globe environment
- Build a foundation for collision risk assessment

---

## Planned Features

### Core Functionality
- [ ] Fetch satellite TLE data
- [ ] Orbit propagation using SGP4
- [ ] Conjunction screening engine
- [ ] Distance-based risk detection
- [ ] Collision event reporting

### Visualization
- [ ] Interactive 3D Earth visualization
- [ ] Real-time satellite tracking
- [ ] Risk highlighting
- [ ] Orbital path display

### Analysis & Insights
- [ ] Risk dashboards
- [ ] Close-approach summaries
- [ ] Historical conjunction analysis
- [ ] Satellite metadata integration

---

## Technology Stack

### Backend
- Python
- SGP4
- Skyfield

### Frontend
- CesiumJS

### Development Tools
- Git
- GitHub
- VS Code

---

## Project Structure

```text
satellite-collision-risk-detector/
│
├── backend/
├── frontend/
├── docs/
├── specs/
├── roadmap.md
├── checklist.md
└── README.md
```

---

## Current Status

**Development Phase:** Prototype

Current work focuses on:

- Project architecture
- Orbital propagation pipeline
- Conjunction screening logic
- Frontend visualization setup

---

## Data Sources

Primary source:

- CelesTrak General Perturbations (GP) data

Potential future integrations:

- Space-Track
- Additional satellite catalogs

---

## Disclaimer

This project is intended for educational and research purposes.

The current prototype uses simplified distance-based conjunction screening and should not be used for operational collision avoidance decisions.

---

## Roadmap

See `roadmap.md` for planned milestones and implementation details.

---

## Author

Aryan Singh
