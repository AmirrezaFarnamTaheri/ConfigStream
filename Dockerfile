# Multi-stage build for ConfigStream
# SPDX-License-Identifier: AGPL-3.0-or-later

# Stage 1: Build Go Tester
FROM golang:1.23-alpine@sha256:8bee1901f1e530bfb4a7850aa7a479d17ae3a18beb6e09064ed54cfd245b7191 AS builder

WORKDIR /app
# Leverage Docker cache for Go modules
COPY src/go/tester/go.mod src/go/tester/go.sum ./
RUN go mod download

COPY src/go/tester/ .
# Added tags for uTLS, QUIC, WireGuard, etc.
# Strip debug symbols (-s -w) and disable CGO for static binary
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -tags "with_quic,with_dhcp,with_wireguard,with_ech,with_utls,with_reality_server,with_clash_api,with_gvisor" -o tester main.go

# Stage 2: Node.js (only the binary needed for GitHub Actions JS actions)
FROM node:24-slim@sha256:24dc26ef1e3c3690f27ebc4136c9c186c3133b25563ae4d7f0692e4d1fe5db0e AS node-runtime

# Stage 3: Python Runtime
FROM python:3.12-slim@sha256:a64ac5be6928c6a94f00b16e09cdf3ba3edd44452d10ffa4516a58004873573e AS app-base

# OCI image annotations for traceability
LABEL org.opencontainers.image.title="ConfigStream"
LABEL org.opencontainers.image.description="Sovereignty-grade, zero-budget anti-censorship platform — aggregates, validates, and distributes resilient proxy configurations."
LABEL org.opencontainers.image.url="https://github.com/AmirrezaFarnamTaheri/ConfigStream"
LABEL org.opencontainers.image.source="https://github.com/AmirrezaFarnamTaheri/ConfigStream"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"
LABEL org.opencontainers.image.vendor="ConfigStream Contributors"
LABEL org.opencontainers.image.version="3.2.0"

# Install build/runtime dependencies. The production stage removes download
# tools after the verified Vwarp binary and Python environment are installed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    tini \
    libmaxminddb0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Install 'uv'
COPY --from=ghcr.io/astral-sh/uv:0.11.32@sha256:2381d6aa60c326b71fd40023f921a0a3b8f91b14d5db6b90402e65a635053709 /uv /uvx /bin/

# Match the GitHub-hosted Ubuntu runner UID so bind-mounted workspace and
# runner command files remain writable when this image is used as a job container.
ARG RUNNER_UID=1001
RUN useradd -m -u "${RUNNER_UID}" runner

# Copy Go binary
COPY --from=builder /app/tester /usr/local/bin/configstream-tester

# Install the prebuilt Vwarp binary with architecture-specific checksum proof.
ARG TARGETARCH
ARG VWARP_VERSION=v2.2.2
# [SECURITY] Release checksums pinned per architecture.
ARG VWARP_SHA256_AMD64=90619d5e8ceec07fe09b967904f490d5a45f812951f7fae4cb375b60207b6312
ARG VWARP_SHA256_ARM64=54adb472363f74dd83be93157b5491189d295bd1318de8637265db4f3b834168

# Running as root before switching user
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) VWARP_ARCH="amd64"; VWARP_SHA256="${VWARP_SHA256_AMD64}" ;; \
      arm64) VWARP_ARCH="arm64"; VWARP_SHA256="${VWARP_SHA256_ARM64}" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fSsL --retry 3 --max-time 30 --proto =https -o /tmp/vwarp.zip "https://github.com/voidr3aper-anon/Vwarp/releases/download/${VWARP_VERSION}/vwarp_linux-${VWARP_ARCH}.zip" && \
    echo "${VWARP_SHA256}  /tmp/vwarp.zip" | sha256sum -c - && \
    unzip -tq /tmp/vwarp.zip && \
    mkdir -p /tmp/vwarp-extract && \
    unzip -Z1 /tmp/vwarp.zip > /tmp/vwarp-filelist && \
    grep -Eq '^(|.*/)?vwarp$' /tmp/vwarp-filelist && \
    ! grep -Eq '(^|/)\.\.(/|$)' /tmp/vwarp-filelist && \
    VWARP_ENTRY="$(grep -E '^(|.*/)?vwarp$' /tmp/vwarp-filelist | head -n1)" && \
    unzip -j /tmp/vwarp.zip "$VWARP_ENTRY" -d /tmp/vwarp-extract && \
    install -m 0755 /tmp/vwarp-extract/vwarp /usr/local/bin/vwarp && \
    rm -rf /tmp/vwarp.zip /tmp/vwarp-extract /tmp/vwarp-filelist && \
    (vwarp version || (echo "Vwarp binary check failed" >&2; exit 1))

# Install Python dependencies (Cached Layer)
COPY pyproject.toml requirements-prod.txt ./
# Use system python environment, no venv needed in container
ENV UV_SYSTEM_PYTHON=1
# Install only strict production dependencies (no dev tools)
RUN uv pip install --no-cache-dir -r requirements-prod.txt

# Copy Source Code
COPY . .
RUN chown -R runner:runner /app

# Install application code without re-resolving the pinned production set.
RUN uv pip install --no-cache-dir --no-deps .

# Set Environment
ENV PATH="/home/runner/.local/bin:$PATH"
ENV PYTHONPATH="/app/src"
# sing-box ≥1.11 deprecated legacy wireguard outbound; ≥1.12 fatally
# rejects WG configs without this.  Required for chain proxy testing.
ENV ENABLE_DEPRECATED_WIREGUARD_OUTBOUND=true

# CI target: includes Node because JavaScript GitHub Actions execute inside job containers.
FROM app-base AS ci-runner
USER root
RUN apt-get update && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/include/node /usr/local/include/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && \
    node --version
USER runner
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-m", "configstream.container_healthcheck"]
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "configstream.cli"]

# Default production target: no Node toolchain or npm dependency tree.
FROM app-base AS runtime
USER root
RUN apt-get purge -y curl unzip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /bin/uv /bin/uvx
USER runner
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-m", "configstream.container_healthcheck"]
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "configstream.cli"]
