# Multi-stage Dockerfile for AI Agent System
# Build stage: Install dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# Runtime stage: Minimal production image
FROM python:3.11-slim

# Set labels for metadata
LABEL maintainer="AI Agent System"
LABEL version="1.0.0"
LABEL description="Production-ready AI Agent with RAG and Planner-Critique"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser database/ ./database/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser monitoring/ ./monitoring/
COPY --chown=appuser:appuser security/ ./security/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/data/chromadb && \
    chown -R appuser:appuser /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check using the monitoring health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop"]
