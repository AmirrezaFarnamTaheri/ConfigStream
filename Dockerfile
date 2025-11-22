# Multi-stage build for ConfigStream
# Stage 1: Build Go Tester
FROM golang:1.21-alpine AS builder

WORKDIR /app
# Leverage Docker cache for Go modules
COPY src/go/tester/go.mod ./
# Copy go.sum if it exists, otherwise we might generate it.
# Since list_files only showed go.mod, we only copy go.mod.
# If go.sum existed, we should copy it too.
# RUN go mod download
RUN go mod tidy && go mod download

COPY src/go/tester/main.go .
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
