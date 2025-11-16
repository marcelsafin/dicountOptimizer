# Production Dockerfile for Shopping Optimizer
# Uses multi-stage build for smaller image size and better security
#
# Build: docker build -t shopping-optimizer .
# Run: docker run -p 3000:3000 --env-file .env shopping-optimizer
#
# Image size optimization:
# - Multi-stage build separates build dependencies from runtime
# - Uses slim Python base image
# - Removes build artifacts and caches
# - Final image size: ~200MB (vs ~1GB for full Python image)

# Stage 1: Builder
# This stage installs all dependencies including build tools
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies to user site-packages
# This allows us to copy them to the runtime stage
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
# This stage only contains what's needed to run the application
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY agents/ ./agents/
COPY templates/ ./templates/
COPY static/ ./static/
COPY app.py .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env var, default to 3000)
EXPOSE 3000

# Health check using curl (more reliable than Python requests in container)
# Checks /health endpoint every 30s, allows 40s startup time
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# Run with Gunicorn + Uvicorn workers (async-capable)
# Workers: 2 * CPU cores + 1 (default 4 for 2-core systems)
# Timeout: 120s for long-running AI operations
# Graceful timeout: 30s for clean shutdown
CMD gunicorn app:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-4} \
    --bind 0.0.0.0:${PORT:-3000} \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info}
