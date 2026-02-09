# Getting Started

This guide walks you through setting up ConfigStream locally — from cloning the repo to running your first pipeline and inspecting the output.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core pipeline, parsers, generators, intelligence |
| **Go** | 1.21+ | High-performance tester sidecar (optional but recommended) |
| **Git** | Any | Version control |
| **Docker** | Any (optional) | Containerized runs via `docker-compose` |

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Python Dependencies
```bash
pip install -e ".[dev]"
```
This installs ConfigStream in editable mode along with development tools (`pytest`, `black`, `flake8`, `mypy`, `playwright`).

### 4. Build the Go Tester (Recommended)
The Go tester provides 10-50x faster proxy testing than the Python fallback.
```bash
cd src/go/tester
go mod tidy
go build -o configstream-tester .
mv configstream-tester ../../../
cd ../../..
```
If you skip this step, the pipeline falls back to a slower Python-based tester.

### 5. Download Routing Databases (Optional)
For domestic bypass routing (e.g., `.ir` domains → DIRECT):
```bash
python -m configstream.cli update-databases
```
Downloads `geosite.db` and `geoip.db` into `data/singbox/`.

---

## First Run

### Run a Single Batch
Process one batch file (the smallest unit of work):
```bash
python -m configstream merge --sources sources/batch_1.txt --output output/ --verbose
```

This will:
1. Fetch all URLs in `batch_1.txt`.
2. Parse proxy URIs from the fetched content.
3. Test each proxy for connectivity and latency.
4. Generate output files (`singbox.json`, `clash.yaml`, `base64.txt`, etc.) in `output/`.

### Inspect the Output
```bash
# Check how many proxies were found
python -c "import json; d=json.load(open('output/metadata.json')); print(f'Valid: {d.get(\"total_valid_proxies\", 0)}')"

# View the Sing-box config
cat output/singbox.json | python -m json.tool | head -50
```

### Merge Multiple Batches
In CI, 14 batches run in parallel on separate VMs. To simulate the merge locally:
```bash
# Run batches 1-3 separately
python -m configstream merge --sources sources/batch_1.txt --output shard_1/
python -m configstream merge --sources sources/batch_2.txt --output shard_2/
python -m configstream merge --sources sources/batch_3.txt --output shard_3/

# Merge all shards
python -m scripts.merge_batches
```

### Docker (Alternative)
```bash
docker-compose up --build
```
This runs the full pipeline in a container with all dependencies pre-installed.

---

## Configuration

Configuration is managed via environment variables (or a `.env` file in the project root).

### Essential Variables

| Variable | Default | Purpose |
|---|---|---|
| `MAX_WORKERS` | `0` (auto) | Concurrency limit for testing |
| `TEST_TIMEOUT` | `10` | Seconds before a proxy test times out |
| `WARP_KEY_POOL` | `[]` | JSON array of WARP credentials for washing/shielding |
| `EVASION_MODE` | `aggressive` | Evasion level: `standard`, `stealth`, `aggressive` |
| `UPDATE_INTERVAL_HOURS` | `6` | Publish interval shown in metadata |

### Example `.env` File
```bash
MAX_WORKERS=50
TEST_TIMEOUT=10
EVASION_MODE=aggressive
WARP_KEY_POOL='[{"id":"...","private_key":"...","peer_public_key":"..."}]'
```

See [Configuration Reference](Configuration.md) for the full list of 30+ variables.

---

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit -x

# E2E tests (requires Playwright)
playwright install --with-deps
pytest tests/e2e

# Linting
black --check .
flake8 src tests
mypy src
```

---

## What's Next?

- **[Architecture](02-architecture.md)** — Understand the pipeline, hybrid engine, and intelligence layer.
- **[Protocols](03-protocols.md)** — Learn how 26+ protocols are parsed and validated.
- **[Contributing](09-contributing.md)** — Set up your dev environment and submit PRs.
- **[Troubleshooting](10-troubleshooting.md)** — Fix common issues.
