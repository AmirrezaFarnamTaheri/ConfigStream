# Multi-stage build for ConfigStream
# Stage 1: Build Go Tester
FROM golang:1.23-alpine AS builder

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

WORKDIR /app

# Set up user
RUN useradd -m -u 1000 runner

# Copy Go binary
COPY --from=builder /app/tester /usr/local/bin/configstream-tester

# Install Python dependencies
COPY pyproject.toml requirements.txt ./
# We need to ensure pip is upgraded
RUN pip install --upgrade pip && pip install --no-cache-dir -e .[dev]

# Copy Source Code
COPY . .
RUN chown -R runner:runner /app

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"

USER runner

# Entrypoint
ENTRYPOINT ["python", "-m", "configstream.cli"]
