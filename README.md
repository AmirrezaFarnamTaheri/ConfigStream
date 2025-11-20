# ConfigStream 🌊

[![CI Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/pipeline.yml)
[![License](https://img.shields.io/github/license/AmirrezaFarnamTaheri/ConfigStream)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**ConfigStream** is a high-performance, intelligent, and self-hostable platform for aggregating, testing, and distributing free VPN/Proxy configurations. It transforms public proxy sources into a clean, secure, and auto-updating subscription stream for your favorite clients.

![Dashboard Preview](frontend/assets/images/favicon.ico)

## 🚀 Features

### 📡 Aggregation & Intelligence
-   **Massive Aggregation**: Fetches proxies from hundreds of public sources (text, JSON, Base64) concurrently.
-   **Smart Scoring**: Ranks sources by reliability, uniqueness, and geo-diversity using `SourceQualityTracker`.
-   **Anomaly Detection**: `AnomalyDetector` flags suspicious data spikes and potential poisoning attacks.
-   **Adaptive Scheduling**: Uses exponential backoff for dead sources and prioritized re-testing for reliable ones.

### 🛡️ Security First
-   **Deep Inspection**: Detects header stripping, DNS hijacking, and MITM attempts.
-   **Honey Pot Detection**: Identifies and blocks proxies that redirect traffic to malicious sites.
-   **Blocklist Integration**: Automatically filters IPs against FireHol Level 1 (botnets, malware).
-   **Fuzz Testing**: Parsers are hardened against malformed inputs using `hypothesis`.

### ⚡ Performance & Protocols
-   **Multi-Protocol Support**: V2Ray (VMess, VLESS), Trojan, Shadowsocks, Hysteria 2, Tuic, and SSH.
-   **Universal Converter**: Built-in API to convert subscriptions to **Clash**, **Sing-box**, **Surge**, **Loon**, and **Quantumult X**.
-   **WARP Generation**: Built-in tool to generate optimized Cloudflare WARP configurations.

### 🖥️ Modern Dashboard & PWA
-   **Real-Time Feed**: Watch the aggregation pipeline in real-time via WebSocket.
-   **Interactive Map**: Visualize proxy locations on a global map.
-   **Historical Charts**: Track proxy availability trends over 24h/7d.
-   **PWA Support**: Install the dashboard as a native-like app on mobile and desktop.

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
| `/ws/feed` | `WS` | Real-time WebSocket feed of pipeline events. |
| `/api/convert` | `GET` | Convert an external subscription URL to various formats. |
| `/subscribe/{format}` | `GET` | Download the local subscription in `clash`, `singbox`, `surge`, etc. |
| `/health` | `GET` | Server health check. |

See [docs/API.md](docs/API.md) for full documentation.

---

## 砖 Architecture

ConfigStream is built with a modular "Split Brain" architecture:
1.  **Worker**: A background process (`configstream merge`) that fetches, tests, and saves proxies to the `output/` directory. It uses `asyncio` for high concurrency.
2.  **Server**: A lightweight FastAPI web server that serves the `output/` files, provides the API, and hosts the PWA frontend.

For a deep dive, read [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🤝 Contributing

Contributions are welcome! We have a roadmap including machine learning scheduling and Rust acceleration.
Please check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the **GPL-3.0 License**.
