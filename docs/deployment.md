# Deployment Guide

## Prerequisites
- **Python 3.10+**
- **Go 1.21+** (for tester)
- **Node.js** (optional, for frontend dev)

## Installation

1.  **Clone Repository**
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
    cd ConfigStream
    ```

2.  **Install Python Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Build/Install Tester (Optional but recommended)**
    The project uses a Go-based high-performance tester.
    ```bash
    # Ensure configstream-tester binary is in PATH or root
    # Build from source if available or download release
    ```

4.  **Update GeoIP Databases**
    Download `GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb` from MaxMind and place them in `data/`.

## Running the Pipeline

To run the full aggregation and testing pipeline:

```bash
python -m configstream.pipeline
```

This will:
1.  Fetch proxies from sources.
2.  Test them using the Go tester (or Python fallback).
3.  Generate `metadata.json` and proxy lists in `output/`.

## Deployment

The `frontend/` directory contains the web interface. It expects `output/` contents to be served or accessible (e.g., via `api/`).

For GitHub Pages:
1.  Run pipeline.
2.  Copy `output/*` to `frontend/data/` or configure fetch paths.
3.  Deploy `frontend/` to Pages.

## Environment Variables

- `WARP_KEY_POOL`: JSON list of WARP keys.
- `MAX_WORKERS`: Concurrency limit.
