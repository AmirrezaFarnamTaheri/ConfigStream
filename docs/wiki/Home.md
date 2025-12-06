# ConfigStream Encyclopedia

Welcome to the comprehensive, deep-dive technical documentation for **ConfigStream**. This wiki is designed to take you from zero knowledge to complete system mastery ("Zero to Hero").

ConfigStream is a sovereignty-grade, zero-budget, high-performance anti-censorship platform that aggregates, validates, tests, and distributes VPN configurations using a streaming pipeline architecture.

## 📚 Table of Contents

### 1. [System Architecture](Architecture.md)
*   **The Philosophy**: Zero Budget, Fail-Open, Sovereignty-Grade.
*   **Core Design**: Streaming Pipeline (Producer-Consumer), Event Loop Management.
*   **Component Analysis**: Orchestrator, Fetcher, Parser, Tester, Washer, Output Generator.
*   **Data Flow**: From raw URL to `singbox.json`.

### 2. [The Pipeline](Pipeline.md)
*   **Step-by-Step Breakdown**:
    1.  **Ingestion**: Handling 20,000+ proxy lists, async fetching, circuit breakers.
    2.  **Parsing**: Heuristic extraction, Base64 decoding, protocol detection.
    3.  **Validation**: Security policies, sanitization, strict typing.
    4.  **Testing**: Hybrid Engine (Python + Go Sidecar), latency checks, honeypot detection.
    5.  **Intelligence**: Proxy Washing (WARP), Geodesic Routing, Anomaly Detection.
    6.  **Output**: Generation of Sing-box, Clash, and Subscription formats.

### 3. [Protocol Deep Dive](Protocols.md)
*   **Supported Protocols**: VLESS, VMess, Trojan, Shadowsocks, Hysteria2, TUIC, WireGuard, SSH.
*   **Conversion Logic**: How we map raw text to Sing-box inbound/outbound objects.
*   **Security & Transport**: TLS, uTLS, Reality, fragmenting, and multiplexing.

### 4. [Intelligence Layer](Intelligence.md)
*   **Proxy Washing**: Reviving dead proxies by chaining them through Cloudflare WARP.
*   **Smart Chains**: Geographically optimal routing (e.g., IR -> EU -> US).
*   **Vectors & Scoring**: How we rank proxies using pareto-front analysis.
*   **Adaptive Logic**: Timeouts, retries, and concurrency scaling.

### 5. [Deployment & Operations](Deployment.md)
*   **Zero Budget Infrastructure**: Running entirely on GitHub Actions and Pages.
*   **CI/CD Workflows**: Matrix strategies, sharding, and artifact merging.
*   **Monitoring**: Telemetry, logs, and quality gates.
*   **Mirroring**: Distribution to Telegram, Hugging Face, IPFS, and Google Drive.

### 6. [Security Model](Security.md)
*   **Sanitization**: Preventing log leaks (PII, tokens).
*   **Threat Model**: Malicious configs, honeypots, and active probing.
*   **Transport Security**: Steganography for subscription delivery.

### 7. [Legacy Documentation](Legacy_Wiki.md)
*   Access the previous version of the documentation here: [ConfigStream's Legacy WIKI](../../docs/ConfigStreams_Wiki/Home.md).

---

## 🚀 Quick Start for Developers

```bash
# Clone the repo
git clone https://github.com/your-org/configstream.git
cd configstream

# Install dependencies (Editable mode)
pip install -e ".[dev]"

# Run tests
pytest

# Run a local pipeline batch (dry run)
python -m configstream.cli merge --sources sources/batch_1.txt --output output_local
```

## 🧠 Core Directives
*   **Async Everything**: Blocking I/O is forbidden.
*   **Sanitize Inputs**: Trust no source.
*   **Resilience**: The network is hostile.
