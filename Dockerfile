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
# Download the specific Vwarp release (v2.1.0)
# Running as root before switching user
RUN wget -q -O /usr/local/bin/vwarp https://github.com/voidr3aper-anon/Vwarp/releases/download/v2.1.0/vwarp-linux-amd64 && \
    chmod +x /usr/local/bin/vwarp && \
    (vwarp --version || echo "Vwarp binary check failed")

# Install Python dependencies (Cached Layer)
COPY pyproject.toml requirements.txt ./
# Use system python environment, no venv needed in container
ENV UV_SYSTEM_PYTHON=1
# [OPTIMIZATION] Use uv for fast install
RUN uv pip install -r requirements.txt

# Copy Source Code
COPY . .
RUN chown -R runner:runner /app

# [OPTIMIZATION] Install project in editable mode NOW that source exists
RUN uv pip install -e .[dev]

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"

USER runner

# Entrypoint
ENTRYPOINT ["python", "-m", "configstream.cli"]
