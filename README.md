# ConfigStream v2.0.6

[![ConfigStream Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![Pipeline Health Check](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml)

**The Network Intelligence Platform for the Open Internet.**

ConfigStream is a modular, sovereignty-grade anti-censorship platform. It aggregates, tests, and distributes resilient proxy configurations using a **Strict "Zero Budget" Architecture**.

We leverage the free tiers of GitHub Actions, Pages, and public APIs to build a resilient, distributed network without spending a cent on infrastructure.

> **🔒 Security & Stability Update (v2.0.6):** This release resolves critical backend logic flaws (determinism, chaining) and frontend architectural issues (caching, navigation, sanitization). See `CHANGELOG.md` for details.

---

## 🚀 Key Features

### 🛡️ Resilient Core (Hybrid Engine)
*   **Python Logic:** Orchestrates washing, chaining, and intelligence.
*   **Go Speed:** High-concurrency raw socket testing via custom binary.
*   **Wasm Verification:** Client-side verification in the browser for edge ground truth.

### 🌊 Smart Washing & Chaining
*   **Proxy Washing:** Wraps flagged/dirty proxies in Cloudflare WARP tunnels using deterministic, stable key rotation.
*   **Smart Chains:** Automatically builds topology-aware chains (e.g., Intranet -> Relay -> Exit) to bypass DPI.
*   **Deterministic IPs:** Generates stable, non-colliding internal IPs for consistent routing tables.

### 🌐 Advanced Analytics & Globe
*   **3D Globe Visualization:** Interactive real-time view of active proxy nodes with zoom and auto-spin controls.
*   **Telemetry Dashboard:** Tracks network health, threats neutralized, and rejection reasons.
*   **Feature Vectors:** Static vector search for finding "similar" high-quality proxies.

### ⚡ Performance & Caching
*   **PWA Architecture:** Fully offline-capable dashboard with Service Worker.
*   **Smart Updates:** `UpdateDetector` polls for changes efficiently (4min interval) without wasting bandwidth.
*   **Compressed Storage:** Client-side caching uses compression (Gzip/Brotli) to minimize storage footprint.
*   **Zero-Cost Distribution:** Uses GitHub Pages with optimized caching strategies.

### 🔌 Universal Adapters
*   **Surge:** Native policy export.
*   **Loon:** Native configuration export.
*   **Quantumult X:** Server node export.
*   **Shadowrocket:** Base64 subscription links.
*   **SIP008:** Standard JSON format for Shadowsocks.

---

## 📚 Documentation

*   [**Architecture Deep Dive**](docs/wiki/project/02-architecture.md): System design and data flow.
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

AGPL-3.0 License.
