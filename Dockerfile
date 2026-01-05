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

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Environment variables (override in docker-compose)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "suksham_vachak.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
