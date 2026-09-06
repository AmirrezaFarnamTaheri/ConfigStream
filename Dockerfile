# Multi-stage build for ConfigStream
# SPDX-License-Identifier: AGPL-3.0-or-later

# Stage 1: Build Go Tester
FROM golang:1.26.8-alpine3.24@sha256:34efdd6036c92e155c8b0162a5da7626586b612ea636590035602c970eece564 AS builder

WORKDIR /app
# Leverage Docker cache for Go modules
COPY src/go/tester/go.mod src/go/tester/go.sum ./
RUN go mod download

COPY src/go/tester/ .
# Added tags for uTLS, QUIC, WireGuard, etc.
# Strip debug symbols (-s -w) and disable CGO for static binary
RUN CGO_ENABLED=0 go build -ldflags="-s -w -checklinkname=0" -tags "with_quic,with_dhcp,with_wireguard,with_ech,with_utls,with_reality_server,with_clash_api,with_gvisor" -o tester main.go

# Stage 2: Node.js (only the binary needed for GitHub Actions JS actions)
FROM node:24.20.0-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e AS node-runtime

# Stage 3: Python Runtime
FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS app-base

# OCI image annotations for traceability
LABEL org.opencontainers.image.title="ConfigStream" \
      org.opencontainers.image.description="Automated proxy aggregation, validation, and publishing pipeline" \
      org.opencontainers.image.source="https://github.com/AmirrezaFarnamTaheri/ConfigStream" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

# We need node in the final container to execute JavaScript-based GitHub Actions
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps and pinned production dependencies first for cache locality.
COPY requirements-prod.txt pyproject.toml README.md ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -r requirements-prod.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY sources/ ./sources/
COPY data/ ./data/
COPY --from=builder /app/tester /app/bin/configstream-tester

RUN chmod +x /app/bin/configstream-tester \
    && python -m pip install --no-cache-dir -e . --no-deps

ENTRYPOINT ["python", "-m", "configstream.cli"]
