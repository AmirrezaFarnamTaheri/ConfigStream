# ConfigStream 🌊

**ConfigStream** is a high-performance, intelligent, and self-hostable platform for aggregating, testing, and distributing free VPN/Proxy configurations. It transforms public proxy sources into a clean, secure, and auto-updating subscription stream for your favorite clients.

![Dashboard Preview](frontend/assets/images/favicon.ico) <!-- Replace with actual screenshot if available -->

## 🚀 Features

-   **Massive Aggregation**: Fetches proxies from hundreds of public sources (text, JSON, Base64).
-   **Intelligent Testing**:
    -   Validates connectivity and latency against global targets (e.g., Google, Cloudflare).
    -   **Deep Inspection**: Detects header stripping, DNS hijacking, and MITM attempts.
    -   **Smart Scheduling**: Uses exponential backoff for dead sources and adaptive re-testing for reliable proxies.
-   **Security First**:
    -   **Blocklist Integration**: Automatically filters IPs against FireHol Level 1 (botnets, malware).
    -   **Fuzz Testing**: Parsers are hardened against malformed and malicious inputs.
    -   **Secret Scanning**: Prevents accidental leaks of API keys or private data.
-   **Multi-Protocol Support**:
    -   V2Ray (VMess, VLESS)
    -   Trojan
    -   Shadowsocks
    -   Hysteria 2
    -   Tuic
    -   WireGuard (including WARP generation)
-   **Universal Converter**: Built-in API to convert any subscription link to **Clash**, **Sing-box**, or **Base64** formats.
-   **Modern Dashboard**: A responsive, dark-mode web interface to browse, filter, and analyze proxy metrics in real-time.
-   **Dockerized**: One-click deployment with Docker Compose or Render/Railway.

---

## 🛠️ Quick Start

### Option 1: Docker (Recommended)

The easiest way to run ConfigStream. This starts the web server and the background aggregation worker.

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
    cd ConfigStream
    ```

2.  **Start the stack:**
    ```bash
    docker compose up -d
    ```

3.  **Open Dashboard:**
    Visit [http://localhost:8000](http://localhost:8000)

### Option 2: Manual Installation

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions on running without Docker.

---

## 📖 API Reference

The built-in FastAPI server provides endpoints for automation and integration.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/proxies` | `GET` | Get the full list of working proxies (supports filtering). |
| `/api/stats` | `GET` | Get pipeline statistics and metadata. |
| `/api/convert` | `GET` | Convert an external subscription URL to Clash/Sing-box. |
| `/subscribe/{format}` | `GET` | Download the local subscription in `clash`, `singbox`, or `base64`. |
| `/health` | `GET` | Server health check. |

**Example: Convert a Link**
```bash
curl "http://localhost:8000/api/convert?url=https://example.com/subs&target=clash" -o config.yaml
```

---

## 🧱 Architecture

ConfigStream is built with a modular "Split Brain" architecture:
1.  **Worker**: A background process (`configstream merge`) that fetches, tests, and saves proxies to the `output/` directory.
2.  **Server**: A lightweight FastAPI web server that serves the `output/` files and provides utility APIs.

For a deep dive, read [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🛡️ Security

We take security seriously.
-   **No Logs**: The platform does not log user traffic (it aggregates *servers*, it doesn't act as a VPN server itself).
-   **IP Sanitization**: Malicious IPs are blocked before they reach your client.
-   **Verification**: All code is linted (flake8, mypy) and tested (pytest) before release.

---

## 🤝 Contributing

Contributions are welcome! Whether it's adding new sources, fixing bugs, or improving the dashboard.
Please check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the **GPL-3.0 License**.
