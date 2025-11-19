# syntax=docker/dockerfile:1

# --------------------------------------------------------
# Stage 1: Builder (Compiles dependencies)
# --------------------------------------------------------
FROM python:3.11-slim AS builder

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
PYTHONDONTWRITEBYTECODE=1 \
PIP_NO_CACHE_DIR=1 \
PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system build tools (needed for some python C-extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
gcc \
libc-dev \
&& rm -rf /var/lib/apt/lists/*

# Copy only dependency files first to leverage Docker cache
COPY pyproject.toml README.md ./
COPY src/configstream/__init__.py src/configstream/

# Install dependencies into a virtual environment
RUN pip install --upgrade pip build
# Install project + dependencies into /install directory
RUN pip install --prefix=/install .

# --------------------------------------------------------
# Stage 2: Runner (The actual final image)
# --------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal runtime deps (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
curl \
&& rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create persistent volume directories
RUN mkdir -p data output sources

# Set environment variables
ENV OUTPUT_DIR=/app/output \
DATA_DIR=/app/data \
FRONTEND_DIR=/app/frontend

# Expose the Web Port
EXPOSE 8000

# Healthcheck to ensure web server is up
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
CMD curl -f http://localhost:8000/health || exit 1

# Default Command: Start Web Server AND Worker (managed via script or compose)
# By default, we run the web server. Users can override command to run 'configstream merge ...'
CMD ["uvicorn", "configstream.server:app", "--host", "0.0.0.0", "--port", "8000"]
