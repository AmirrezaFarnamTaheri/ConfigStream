# ConfigStream v2.0.6

[![ConfigStream Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![Pipeline Health Check](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml)

**The Network Intelligence Platform for the Open Internet.**

ConfigStream is a modular, sovereignty-grade anti-censorship platform. It aggregates, tests, and distributes resilient proxy configurations using a **Strict "Zero Budget" Architecture**.

We leverage the free tiers of GitHub Actions, Pages, and public APIs to build a resilient, distributed network without spending a cent on infrastructure.

> **🔒 v2.1.0 Update:** Enhanced **Washer Revival** (reviving dirty/dead proxies via WARP), **Protocol Normalization**, and **Frontend Defensive Analytics**.

---

## 🚀 Key Features (v2.1)

### 🧩 Universal Parsing & Protocol Support
*   **Structured Ingestion:** Natively parses **Clash YAML** and **V2Ray JSON** subscription blobs, recovering thousands of previously ignored proxies.
*   **Protocol Aliases:** Support for `hy2://`, `wg://`, and password-protected TUIC URLs.
*   **Hysteria2 Normalization:** Automatically fixes `insecure`/`obfs` parameter mismatches to ensure connectivity.
*   **Strict Validation:** Enhanced type safety and validation for VLESS/VMess protocols.

### 🛡️ Resilient Core (Hybrid Engine)
*   **Python Logic:** Orchestrates washing, chaining, and intelligence (Fully Type-Checked).
*   **Go Speed:** High-concurrency raw socket testing via custom binary.
*   **Vwarp Integration:** Uses MASQUE/QUIC scanning to find clean Cloudflare IPs (host:port support), bypassing traditional blocks.
*   **Robust Fetching:** Adaptive timeouts and strict 404/410 handling to prevent wasted cycles.

### 🌊 Smart Washing & Revival
*   **Proxy Revival:** Capable of "reviving" non-working or dirty proxies by wrapping them in clean WARP tunnels.
*   **Thread-Safe Washing:** Optimized locking mechanisms for concurrent washing operations.
*   **Smart Chains:** Automatically builds topology-aware chains (e.g., Intranet -> Relay -> Exit) to bypass DPI.
*   **Deterministic IPs:** Generates stable, non-colliding internal IPs for consistent routing tables.

### 🌐 Advanced Analytics & Globe
*   **3D Globe Visualization:** Interactive real-time view of active proxy nodes.
*   **Real-Time Sync:** WebSocket support for instant updates and differential data fetching.
*   **Source Hygiene:** `SourceQualityTracker` automatically jails failing sources to prevent pipeline pollution.

### ⚡ Performance & Caching
*   **PWA Architecture:** Fully offline-capable dashboard.
*   **Differential Updates:** Clients fetch only changes (deltas), reducing bandwidth by up to 90%.
*   **Compressed Storage:** Client-side caching uses compression.
*   **Zero-Cost Distribution:** Uses GitHub Pages with optimized caching strategies.

### 🔌 Universal Adapters (Expanded)
*   **Surge:** Native policy export (supports VLESS, Hy2, TUIC).
*   **Loon:** Native configuration export (supports VLESS, Hy2, TUIC, WireGuard).
*   **Quantumult X:** Server node export (supports VLESS).
*   **Shadowrocket:** Base64 subscription links (supports VLESS, Hy2, TUIC, Plugins).
*   **SIP008:** Standard JSON format for Shadowsocks.

---

## 📚 Documentation

*   [**Architecture Deep Dive**](docs/wiki/Architecture.md): System design and data flow.
*   [**Frontend Dashboard**](https://amirrezafarnamtaheri.github.io/ConfigStream/): Real-time analytics.

---

## 📦 Usage

### Subscription Links (Updated Every 6 Hours)

*   **The Sniper (Smart Routing):** `https://.../singbox.json` (Best for speed)
*   **The Tank (VPN Mode):** `https://.../singbox-vpn.json` (Best for stability)
*   **The Diplomat (Clash):** `https://.../clash.yaml` (Universal compatibility)
*   **Universal Base64:** `https://.../base64.txt`

### Running Locally

```bash
# Using Docker (Recommended)
docker compose up --build

# Using Python
pip install -e ".[dev]"
configstream merge --sources sources/batch_1.txt
```

---

## 🛠️ Contributing

We operate on a **Zero Budget** constraint.
*   **No Paid Services:** Do not introduce dependencies on paid APIs.
*   **No Abuse:** Do not add active scanning or aggressive scraping.
*   **Efficiency:** Optimize for CI/CD limits (CPU minutes, storage).

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📜 License

AGPL-3.0
