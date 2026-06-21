# syntax=docker/dockerfile:1
# AEGIS single-host image: builds the React frontend, then serves it + the
# Firm OS API bridge from one FastAPI process. One container, one URL.

# ---- Stage 1: build the AEGIS frontend (L6) ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/aegis/package.json ./
RUN npm install
COPY frontend/aegis/ ./
RUN npm run build

# ---- Stage 2: Python runtime (Firm OS bridge + static frontend) ----
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY --from=frontend /app/frontend/dist ./frontend/aegis/dist

ENV AEGIS_STATIC_DIR=/app/frontend/aegis/dist
EXPOSE 8000

# PORT is provided by the host (Render/Railway); default 8000 locally.
CMD uvicorn src.api_bridge:app --host 0.0.0.0 --port ${PORT:-8000}
