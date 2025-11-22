# syntax=docker/dockerfile:1

# --------------------------------------------------------
# Stage 1: Builder (Compiles dependencies)
# --------------------------------------------------------
FROM golang:1.21-bookworm AS go-builder

WORKDIR /go/src/app
COPY src/go/tester/go.mod ./
# Copy source
COPY src/go/tester/ .
# Build statically linked binary
RUN go mod tidy && \
    CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /usr/local/bin/tester main.go

FROM python:3.11-slim AS py-builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    curl \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Install sing-box
RUN LATEST_URL=$(curl -s "https://api.github.com/repos/SagerNet/sing-box/releases/latest" | grep "browser_download_url.*linux-amd64.tar.gz" | cut -d '"' -f 4) && \
    curl -L -o sing-box.tar.gz $LATEST_URL && \
    tar -xzf sing-box.tar.gz && \
    EXTRACTED_DIR=$(tar -tzf sing-box.tar.gz | head -1 | cut -f1 -d"/") && \
    mv $EXTRACTED_DIR/sing-box /usr/local/bin/ && \
    rm -rf sing-box.tar.gz $EXTRACTED_DIR

# Copy only dependency files first
COPY pyproject.toml README.md ./
COPY src/configstream/__init__.py src/configstream/

# Install dependencies into a virtual environment
RUN pip install --upgrade pip build
RUN pip install --prefix=/install .

# --------------------------------------------------------
# Stage 2: Runner (The actual final image)
# --------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal runtime deps (curl, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy sing-box from py-builder
COPY --from=py-builder /usr/local/bin/sing-box /usr/local/bin/sing-box

# Copy Go tester from go-builder
COPY --from=go-builder /usr/local/bin/tester /usr/local/bin/tester

# Copy installed python packages from py-builder stage
COPY --from=py-builder /install /usr/local

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

# Default Command
CMD ["uvicorn", "configstream.server:app", "--host", "0.0.0.0", "--port", "8000"]
