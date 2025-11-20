# Quick Start Guide ⚡

This guide will help you get ConfigStream up and running in minutes.

## Prerequisites

-   **Docker** & **Docker Compose** (Recommended for most users)
-   **Python 3.11+** (Only if running manually)
-   **Git**

---

## 🐳 Method 1: Docker (Production Ready)

This is the standard deployment method. It isolates dependencies and ensures consistency.

### 1. Clone the Repository
```bash
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream
```

### 2. Build and Run
```bash
docker compose up --build -d
```
*This command builds the image and starts two containers: `configstream_web` (dashboard) and `configstream_worker` (aggregator).*

### 3. Access the Dashboard
Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

### 4. Monitor Logs
To see the aggregation process in action:
```bash
docker compose logs -f worker
```

---

## 🐍 Method 2: Manual Setup (Development)

Use this if you are developing features or debugging.

### 1. Setup Virtual Environment
```bash
python3 -11 -m venv venv
source venv/bin/activate  # Linux/macOS
# or 'venv\Scripts\activate' on Windows
```

### 2. Install Dependencies
```bash
pip install -e ".[dev]"
```
*This installs the project in editable mode with development tools.*

### 3. Initialize Data
Download the required GeoIP databases (optional but recommended for flags):
```bash
mkdir -p data
# Manually place GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in ./data/
# Or rely on the pipeline to attempt a public mirror download.
```

### 4. Run the Aggregator (Worker)
This command fetches proxies, tests them, and writes results to `output/`.
```bash
configstream merge --sources sources/batch_1.txt --output output/ --max-workers 50 --timeout 10
```

### 5. Run the Web Server
Start the API and serve the frontend:
```bash
uvicorn configstream.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## ☁️ Cloud Deployment

### Render.com
1.  Fork this repository.
2.  Create a new **Web Service** on Render.
3.  Connect your repo.
4.  Render will automatically detect `render.yaml` (Blueprints) or `Dockerfile`.
5.  Set environment variable `OUTPUT_DIR` to `/var/data/output` and mount a persistent disk to `/var/data` if you want persistence.

### Railway
1.  Deploy from GitHub repo.
2.  Railway will build using the `Dockerfile`.
3.  Add a Volume for `/app/data` to persist intelligence databases.

---

## 🛠 CLI Tools

ConfigStream comes with a CLI for utility tasks.

**Generate Cloudflare WARP Configs:**
```bash
configstream generate-warp --count 3
```
*Generates 3 WireGuard configurations compatible with WARP.*

**Update Blocklists:**
(Happens automatically during pipeline run, but logic is in `src/configstream/security/blocklist.py`)
