# ConfigStream

[![ConfigStream Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![Pipeline Health Check](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/healthcheck.yml)

**The Network Intelligence Platform for the Open Internet.**

ConfigStream is an automated, high-performance system that aggregates, tests, and distributes censorship-resistant proxy configurations (VLESS, VMess, Trojan, Shadowsocks) using a "Zero Budget" architecture.

---

## 🚀 Features

*   **Hybrid Engine:** Combines Python's intelligence with Go's raw networking power to verify thousands of proxies in seconds.
*   **Proxy Washing:** Automatically wraps "dirty" or blocked IPs in secure WireGuard tunnels (via WARP) to bypass 403 Forbidden blocks.
*   **Smart Routing:** Generates "Intranet Bridges" and "IPv6 Portals" to route traffic intelligently around censorship firewalls.
*   **Zero-Trust Security:**
    *   **Active Honeypot Detection:** Scans for dangerous open ports (SSH/Telnet) to reject surveillance nodes.
    *   **Passive Intelligence:** Checks IP reputation against VirusTotal.
*   **Fuzzy Fingerprinting:** Uses advanced hashing to remove 40% of "fake unique" duplicates that plague other aggregators.

---

## 📚 Documentation

We believe in "Zero to Hero" documentation.

*   [**Wiki Home**](docs/wiki/Home.md): Start here.
*   [**Architecture**](docs/wiki/Architecture.md): How the Sidecar pattern works.
*   [**Security**](docs/wiki/Security.md): Deep dive into Honeypot detection and Washing.
*   [**Engineering**](docs/wiki/Engineering.md): The algorithms behind scoring and deduplication.
*   [**API Reference**](docs/wiki/API_Reference.md): JSON output schemas.

---

## 📦 Usage

### Subscription Links
For the best experience, visit our [**Frontend Dashboard**](https://amirrezafarnamtaheri.github.io/ConfigStream/).

Direct Links (replace with your URL):
*   **Universal (Base64):** `https://.../output/base64.txt`
*   **Sing-box (Sniper/Router):** `https://.../output/singbox.json`
*   **Sing-box (Tank/VPN):** `https://.../output/singbox-vpn.json`
*   **Clash:** `https://.../output/clash.yaml`

### Running Locally

You can run the entire pipeline locally using Docker.

```bash
# Build and run
docker compose up --build

# The output will be available in the local output/ directory
```

---

## 🛠️ Development

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for our roadmap and style guide.

**Quick Start:**

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## 📜 License

This project is licensed under the MIT License.
