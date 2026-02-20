# Suksham Vachak - Backend API
# Multi-stage build optimized for ARM64 (Raspberry Pi)

FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt (no dev deps)
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only main

# ============================================
# Production stage
# ============================================
FROM python:3.13-slim AS production

WORKDIR /app

# Copy requirements from builder
COPY --from=builder /app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY suksham_vachak/ ./suksham_vachak/
COPY data/ ./data/

# Copy entrypoint script
COPY scripts/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Create non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port (TCP mode only; UDS mode uses socket file)
EXPOSE 8000

# Environment variables (override in docker-compose)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check: UDS mode uses socket connect, TCP mode uses urllib
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ -n "$UVICORN_UDS" ]; then \
        python -c "import socket; s=socket.socket(socket.AF_UNIX); s.connect('$UVICORN_UDS'); s.close()"; \
    else \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:${UVICORN_PORT:-8000}/api/health')"; \
    fi

# Run the application
ENTRYPOINT ["./docker-entrypoint.sh"]
