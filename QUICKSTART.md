# Quick Start Guide ⚡

This guide will help you get ConfigStream up and running in minutes.

## Prerequisites

-   **Python 3.10+**
-   **Pip**
-   **Git**
-   **Go 1.21+** (Optional, for WASM/Tester builds)

---

## 🚀 Method 1: CLI Pipeline (Recommended)

This is the primary way ConfigStream is designed to run: as a data processing pipeline.

### 1. Clone the Repository
```bash
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream
```

### 2. Install Dependencies
```bash
pip install -e ".[dev]"
```

### 3. Run the Pipeline
Fetch, test, and generate configurations:
```bash
# Simple run
configstream merge --sources sources/batch_1.txt --output output/

# Production run (high concurrency)
configstream merge \
  --sources sources/batch_1.txt \
  --output output/ \
  --max-workers 50 \
  --timeout 15 \
  --max-latency 5000
```

### 4. View Results
The results will be in the `output/` directory:
- `output/proxies.json` (Full proxy list)
- `output/base64.txt` (Base64 subscription)
- `output/chosen/base64.txt` (Top picks per protocol)
- `output/proxies.txt` (Plaintext URIs, grouped by protocol)
- `output/singbox.json` (Smart routing)
- `output/singbox-vpn.json` (TUN/VPN mode)
- `output/singbox-chains.json` (Washed + smart chains only)
- `output/revived.json` (Revived proxies, if any)
- `output/shadowrocket.txt` (Shadowrocket format)
- `output/quantumult.conf` (Quantumult X format)
- `output/surge.conf` (Surge format)
- `output/loon.conf` (Loon format)
- `output/sip008.json` (SIP008 Shadowsocks format)
- `output/side_products.zip` (OpenVPN/WireGuard pack + URIs)
- `output/protocols/*.txt` (Per-protocol URI lists: vless.txt, trojan.txt, etc.)
- `output/protocols/*.json` (Per-protocol Sing-box configs)
- `output/countries/*.json` (Per-country Sing-box configs)
- `output/metadata.json` (Pipeline stats)

---

## 🐳 Method 2: Docker (Containerized)

Use this to run the pipeline or the web server in a container.

### 1. Build and Run
```bash
docker compose up --build
```
*This starts the full stack: aggregation worker and web dashboard.*

### 2. Access Dashboard
Open **[http://localhost:8000](http://localhost:8000)** to view the local dashboard.

---

## 🐍 Method 3: Local Development Server

To run the web dashboard locally without Docker:

### 1. Generate Data
First, run the pipeline (Method 1) to create `output/` files.

### 2. Start Server
```bash
uvicorn configstream.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🛠 CLI Tools

**Generate Cloudflare WARP Configs:**
```bash
configstream generate-warp --count 3
```

**Update GeoIP Databases:**
```bash
configstream update-databases
```

**Manage Database Backups:**
```bash
configstream backup
```
