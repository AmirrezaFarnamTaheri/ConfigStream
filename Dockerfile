# Multi-stage build for ConfigStream
# Stage 1: Build Go Tester
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY src/go/tester/ .
# Initialize module if not present (for reproducible builds)
RUN go mod init configstream-tester || true
RUN go mod tidy
RUN go build -o tester main.go

# Stage 2: Python Runtime
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user
RUN useradd -m -u 1000 runner
USER runner
WORKDIR /app

# Copy Go binary
COPY --from=builder /app/tester /usr/local/bin/configstream-tester

# Install Python dependencies
COPY --chown=runner:runner pyproject.toml requirements.txt ./
RUN pip install --user --no-cache-dir -e .[dev]

# Copy Source Code
COPY --chown=runner:runner . .

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Entrypoint
ENTRYPOINT ["python", "-m", "configstream.cli"]
