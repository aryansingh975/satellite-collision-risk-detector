# ── Stage 0: build frontend ───────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 1: builder ─────────────────────────────────────────────────────────
# Install runtime dependencies into an isolated venv using uv (fast resolver).
FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build
# Copy only the dependency manifest first so this layer is cached when source changes.
COPY pyproject.toml .

# Create a venv and install all runtime deps.
# Dev extras (pytest, ruff, etc.) are intentionally omitted from the image.
RUN python -m venv /opt/venv && \
    uv pip install --python /opt/venv -r pyproject.toml

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
# Minimal image: only the installed packages + application source.
FROM python:3.11-slim

# curl is used by the Docker healthcheck defined in docker-compose.yml
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate the venv for all subsequent commands and the running container
ENV PATH="/opt/venv/bin:$PATH"
# Ensure 'backend' package is importable when running from WORKDIR
ENV PYTHONPATH=/app:/app/backend

WORKDIR /app

# Copy built frontend from the Node stage
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Copy application source — keep backend/ and pyproject.toml together
# so hatchling/importlib can locate the package correctly.
COPY backend/ ./backend/
COPY pyproject.toml .

# Data directory — mounted as a named volume at runtime so SQLite and the
# TLE cache survive container restarts (see docker-compose.yml).
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
