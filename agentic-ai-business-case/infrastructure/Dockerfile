# Multi-stage Dockerfile for Business Case Generator
# Stage 1: Build React frontend (on native platform to avoid esbuild QEMU crashes)
# Stage 2: Build Python backend with frontend (target platform)

# ============================================================================
# Stage 1: Build Frontend (native platform - avoids esbuild Go binary QEMU crash)
# ============================================================================
FROM --platform=$BUILDPLATFORM node:20-alpine3.21 AS frontend-build

WORKDIR /app/ui

# Copy package files
COPY ui/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY ui/ ./

# Build frontend for production
RUN npm run build

# ============================================================================
# Stage 2: Build Backend with Frontend
# ============================================================================

FROM python:3.11-slim-bookworm AS base

# Force fresh package index and upgrade all packages to latest patched versions
# Addresses openssl CVEs (3.0.18 -> 3.0.19): CVE-2026-31790, CVE-2026-28387,
# CVE-2026-28389, CVE-2026-31789, CVE-2026-28390, CVE-2026-28388
# Previously: linux kernel CVEs (6.1.162 -> 6.1.164+): CVE-2025-37786, CVE-2025-37822,
# CVE-2025-38201, CVE-2025-40082, CVE-2025-71089, CVE-2024-26822, and others
RUN echo "Package cache bust: 2026-04-10" > /dev/null

WORKDIR /app

# Install system dependencies and upgrade all packages to patch CVEs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && apt-get install -y --only-upgrade linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/ ./agents/
COPY prompt_library/ ./prompt_library/
COPY utils/ ./utils/
COPY ui/backend/ ./ui/backend/

# Copy frontend build from stage 1
COPY --from=frontend-build /app/ui/build ./ui/dist

# Create necessary directories
RUN mkdir -p /tmp/input /tmp/output

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/health', timeout=5)"

# Run with Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--chdir", "/app/ui/backend", \
     "app:app"]
