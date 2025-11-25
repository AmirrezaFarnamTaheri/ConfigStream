# ConfigStream v2.0.1

[![ConfigStream Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![Pipeline Health Check](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml)

**The Network Intelligence Platform for the Open Internet.**

ConfigStream is a modular, sovereignty-grade anti-censorship platform. It aggregates, tests, and distributes resilient proxy configurations using a **Strict "Zero Budget" Architecture**.

We leverage the free tiers of GitHub Actions, Pages, and public APIs to build a resilient, distributed network without spending a cent on infrastructure.

> **🔒 Security Update (v2.0.1):** This release resolves 18 security vulnerabilities including critical path traversal, race conditions, and DOS protection. See [SECURITY_AUDIT_2025-11.md](docs/SECURITY_AUDIT_2025-11.md) for details.

---

## 🚀 v2.0 Features: Sovereignty & Stealth

### 🕵️ Steganography Transport (Key Rotation)
*   **Invisible Delivery:** Encrypts proxy configurations into standard PNG images (`gallery.png`) to bypass Deep Packet Inspection (DPI) and firewall keyword filtering.
*   **Self-Healing Keys:** Automatically rotates encryption keys every 6 hours. The new key is securely injected into the frontend code during deployment, ensuring perfect synchronization without manual intervention.

### 🌐 Client-Side Edge Verification
*   **WASM Tester:** Moves the verification logic to the user's browser using WebAssembly. This creates a massive, distributed testing network that verifies connectivity from the *user's* perspective (Real Ground Truth).
*   **Zero Server Cost:** By offloading testing to the client, we scale infinitely for free.

### 🏗️ Bring Your Own Worker (BYOW)
*   **Decentralized Exit Nodes:** Users can plug in their own Cloudflare Workers to act as private tunnel endpoints. The frontend dynamically rewrites configurations to route traffic through user-owned infrastructure.

### 🧠 Advanced Intelligence
*   **Pareto Optimization:** Sorts proxies by a weighted score of Latency (50%), Reliability (30%), and Stability (20%).
*   **Static Vector Search:** Uses feature hashing to enable "Similar Proxy" search directly in the browser ($O(1)$ lookup) without heavy ML models.

---

## 📚 Zero to Hero Documentation

We believe in comprehensive, deep documentation.

*   [**Architecture Deep Dive**](docs/wiki/02-architecture.md): The complete system design, data flow, and component analysis.
*   [**Frontend Dashboard**](https://amirrezafarnamtaheri.github.io/ConfigStream/): Real-time visualization and subscription management.

---

## 📦 Usage

### Subscription Links
Direct links to generated configurations (updated every 6 hours):

*   **The Sniper (Routing):** `https://.../output/singbox.json` (Best for speed/rules)
*   **The Tank (VPN):** `https://.../output/singbox-vpn.json` (Best for stability/tun)
*   **The Diplomat (Clash):** `https://.../output/clash.yaml` (Wide compatibility)
*   **Universal:** `https://.../output/base64.txt`

### Running Locally

Run the full pipeline on your machine:

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
*   **No Paid Services:** Do not introduce dependencies on paid APIs or databases.
*   **No Abuse:** Do not add active scanning or aggressive scraping.
*   **Efficiency:** Optimize for CI/CD limits (CPU minutes, storage).

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📜 License

AGPL-3.0 License.
