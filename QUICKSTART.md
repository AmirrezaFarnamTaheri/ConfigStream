# Quick Start Guide ⚡

This guide will help you get ConfigStream up and running in minutes.

## Prerequisites

-   **Python 3.10+**
-   **Pip**
-   **Git**

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
pip install -e .
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
- `output/proxies.json` (Data)
- `output/base64.txt` (Subscription)
- `output/chosen/` (Best proxies)

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
configstream list-db-backups
```

**Restore Database Backup:**
```bash
configstream restore-db backup_timestamp.db target_db.db
```

**List Proxies (Head):**
```bash
head -n 5 output/all.txt
```
