# ── Stage 1: build ───────────────────────────────────────────────────────────
# Compile the Vite + CesiumJS app into a static dist/ bundle.
FROM node:18-alpine AS builder

WORKDIR /app
# Install deps from lock file before copying source for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────────
# Serve the static bundle with nginx (tiny footprint).
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
