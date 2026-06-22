.PHONY: venv install install-dev local-dev dev local-test test local-lint lint seed refresh serve-frontend

# ── Environment ──────────────────────────────────────────────────────────────

venv:
	uv venv .venv --python 3.11

install: venv
	uv pip install -e ".[dev]"

install-dev: install

# ── Backend ───────────────────────────────────────────────────────────────────

local-dev:
	.venv/Scripts/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

dev: local-dev

local-test:
	.venv/Scripts/python -m pytest backend/tests/ -v --tb=short

test: local-test

local-lint:
	.venv/Scripts/python -m ruff check backend/ && .venv/Scripts/python -m ruff format --check backend/

lint: local-lint

# ── Data ─────────────────────────────────────────────────────────────────────

seed:
	.venv/Scripts/python backend/scripts/seed.py

refresh:
	.venv/Scripts/python backend/scripts/refresh.py

# ── Frontend ──────────────────────────────────────────────────────────────────

serve-frontend:
	npm --prefix frontend run dev
