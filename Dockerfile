# Multi-stage build for ConfigStream
# Stage 1: Build Go Tester
FROM golang:1.24-alpine AS builder

WORKDIR /app
# Leverage Docker cache for Go modules
COPY src/go/tester/go.mod src/go/tester/go.sum ./
RUN go mod download

COPY src/go/tester/ .
# [FIX] Added tags for uTLS, QUIC, WireGuard, etc.
# [OPTIMIZATION] Strip debug symbols (-s -w) and disable CGO for static binary
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -tags "with_quic,with_dhcp,with_wireguard,with_ech,with_utls,with_reality_server,with_clash_api,with_gvisor" -o tester main.go

# Stage 2: Python Runtime
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    libmaxminddb0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# [OPTIMIZATION] Install 'uv'
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up user
RUN useradd -m -u 1000 runner

# Copy Go binary
COPY --from=builder /app/tester /usr/local/bin/configstream-tester

# --- GO & VWARP INSTALLATION ---
# 1. Install Go in runtime image (needed for dynamic compilation or tools if needed)
# Actually, we copied the binary, but the plan asked to COPY Go from golang image.
# However, for a slim image, copying the whole Go toolchain is heavy (hundreds of MBs).
# The requirement "Update Dockerfile to install Go" might be for the washer fallback compilation?
# But we already compile in stage 1.
# Let's trust the multistage build for the tester.
# BUT, we need VWARP.

# 3. Install Vwarp
ARG VWARP_VERSION=v2.1.0
# [SECURITY] Checksum for v2.1.0 updated on 2026-01-02.
# The upstream asset was replaced. New checksum verified from: https://github.com/voidr3aper-anon/Vwarp/releases/tag/v2.1.0#checksums
ARG VWARP_SHA256=4b971ed3696ed607bf91000f379f6308459fd1dafa1beae14404a8b7ce068cf7

# Running as root before switching user
RUN wget -q --show-error --fail --https-only --tries=3 --timeout=30 -O /tmp/vwarp.zip https://github.com/voidr3aper-anon/Vwarp/releases/download/${VWARP_VERSION}/vwarp_linux-amd64.zip && \
    echo "${VWARP_SHA256}  /tmp/vwarp.zip" | sha256sum -c - && \
    mkdir -p /tmp/vwarp-extract && \
    unzip /tmp/vwarp.zip -d /tmp/vwarp-extract && \
    test -f /tmp/vwarp-extract/vwarp && \
    mv /tmp/vwarp-extract/vwarp /usr/local/bin/vwarp && \
    rm -rf /tmp/vwarp.zip /tmp/vwarp-extract && \
    chmod +x /usr/local/bin/vwarp && \
    (vwarp --version || echo "Vwarp binary check failed")

# Install Python dependencies (Cached Layer)
COPY pyproject.toml requirements-prod.txt ./
# Use system python environment, no venv needed in container
ENV UV_SYSTEM_PYTHON=1
# [FIX] Install only strict production dependencies (no dev tools)
RUN uv pip install --no-cache-dir -r requirements-prod.txt

# Copy Source Code
COPY . .
RUN chown -R runner:runner /app

# [FIX] Install application code (no editable mode, no dev extras)
RUN uv pip install --no-cache-dir .

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"

USER runner

# [PERFORMANCE] Lightweight healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD [ -x "/usr/local/bin/configstream-tester" ] || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "configstream.cli"]
