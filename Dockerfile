# Multi-stage build for ConfigStream
# Stage 1: Build Go Tester
FROM golang:1.21-alpine AS builder

WORKDIR /app
# Leverage Docker cache for Go modules
COPY src/go/tester/go.mod src/go/tester/go.sum ./
RUN go mod download

COPY src/go/tester/main.go .
RUN go build -o tester main.go

# Stage 2: Python Runtime
FROM python:3.12-slim

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
# We need to ensure pip is upgraded
RUN pip install --upgrade pip && pip install --user --no-cache-dir -e .[dev]

# Copy Source Code
COPY --chown=runner:runner . .

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Entrypoint
ENTRYPOINT ["python", "-m", "configstream.cli"]
