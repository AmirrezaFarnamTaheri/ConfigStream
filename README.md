# ConfigStream

[![ConfigStream Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![Pipeline Health Check](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml)

**The Network Intelligence Platform for the Open Internet.**

ConfigStream is an automated, high-performance system that aggregates, tests, and distributes censorship-resistant proxy configurations (VLESS, VMess, Trojan, Shadowsocks) using a **Strict "Zero Budget" Architecture**.

We leverage the free tiers of GitHub Actions, Pages, and public APIs to build a resilient, distributed network without spending a cent on infrastructure.

---

## 🚀 Key Features

### 🧠 Intelligence Core
*   **Hybrid Engine:** Combines Python's flexibility with a high-performance Go sidecar to verify thousands of proxies in seconds.
*   **Proxy Washing:** Automatically wraps "dirty" or blocked IPs in secure WireGuard tunnels (via Cloudflare WARP) to bypass region blocks.
*   **Pareto Optimization:** Sorts proxies not just by latency, but by a weighted score of **Reliability, Uptime, and Success Rate**.

### 🛡️ Zero-Abuse Security
*   **Passive Verification:** We reject active scanning (port scanning) to protect our infrastructure and respect the net. We use **VirusTotal** and **IP Reputation** lists instead.
*   **Honeypot Avoidance:** Detects and filters out surveillance nodes and fake proxies.
*   **Safe FFI:** Optional Rust-based Shadowsocks verification (disabled by default in CI to save build minutes).

### ⚡ Client-Side Edge Computing
*   **WASM Tester:** (Experimental) Moves the verification logic to the user's browser via WebAssembly, creating a distributed, decentralized testing network.
*   **Static Vector Search:** (Roadmap) Pre-computed similarity indexes allow for "Smart Filtering" directly in the frontend.

---

## 📚 Zero to Hero Documentation

We believe in comprehensive, deep documentation.

*   [**Architecture Deep Dive**](ARCHITECTURE.md): The complete system design, data flow, and component analysis.
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
python -m configstream.cli merge --sources sources/batch_1.txt
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

MIT License.
