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
    libmaxminddb0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# [OPTIMIZATION] Install 'uv'
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up user
RUN useradd -m -u 1000 runner

# Copy Go binary
COPY --from=builder /app/tester /usr/local/bin/configstream-tester

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
