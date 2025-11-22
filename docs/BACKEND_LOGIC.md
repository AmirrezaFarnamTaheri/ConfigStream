# Backend Logic & Architecture Deep Dive

This document provides a detailed look into the internal mechanics of the ConfigStream pipeline.

## Pipeline Stages (`src/configstream/pipeline.py`)

The pipeline operates as a streaming "Producer-Consumer" system to handle high throughput with constant memory usage.

### 1. Ingestion (Producer)
*   **Module:** `fetcher.py`
*   **Logic:**
    *   Reads `sources/batch_*.txt`.
    *   Fetches URLs asynchronously using `httpx`.
    *   **Smart Features:**
        *   **Adaptive Timeout:** Adjusts timeout based on historical latency of the host.
        *   **Quality Check:** Skips sources that have failed consecutively (`SourceQualityTracker`).
        *   **Anomaly Detection:** Checks content length/line count against history (`AnomalyDetector`). Spikes are blocked.
    *   **Output:** Puts raw config lines into an `asyncio.Queue`.

### 2. Parsing (Consumer)
*   **Module:** `parsers.py`, `auto_detect.py`
*   **Logic:**
    *   Consumes lines from the queue.
    *   **Auto-detection:** Tries to guess protocol (vmess, ss, etc.) from URI scheme or content.
    *   **Normalization:** Converts diverse formats into a standard `Proxy` model (`models.py`).
    *   **Deduplication:** Hashes `(protocol, ip, port, credentials)` to skip duplicate processing.

### 3. Validation
*   **Module:** `security_validator.py`
*   **Logic:**
    *   **Syntax Check:** Ensures critical fields (IP, Port, UUID) are present.
    *   **Safety Check:** Blocks private IPs, loopbacks, and dangerous ports (e.g., 25, 22).
    *   **Honeypot Check:** Uses `HoneyPotDetector` to spot fake proxies.

### 4. Testing
*   **Module:** `testers.py`
*   **Logic:**
    *   **Smart Schedule:** Checks `TestResultCache`. If a proxy was tested recently and works, it might skip retesting (depending on policy).
    *   **Sing-box:** Uses `sing-box` binary for accurate connectivity testing (URL Test to `http://www.gstatic.com/generate_204`).
    *   **Metrics:** Captures Latency and Jitter.

### 5. Intelligence & Scoring
*   **Module:** `score.py`, `source_quality.py`
*   **Logic:**
    *   **Scoring:** `calculate_health_score` assigns 0-100 based on:
        *   Latency (Sigmoid curve)
        *   Uptime History
        *   Security Features (TLS, AEAD)
    *   **Feedback Loop:** Updates `source_quality.db` with the success rate of the source batch.

### 6. Output
*   **Module:** `output.py`, `adapters.py`
*   **Logic:**
    *   **Filtering:** Removes duplicates (keeping best latency).
    *   **GeoIP:** Resolves country/city for final list.
    *   **Formatting:** Generates:
        *   `proxies.json` (Master list)
        *   `clash.yaml`, `singbox.json` (Client configs)
        *   `metadata.json` (Frontend stats)
        *   `adapters/*.conf` (Surge, Loon, etc.)

## Data Storage

*   **SQLite Databases (`data/`)**:
    *   `anomaly.db`: History of source content sizes.
    *   `source_quality.db`: Trust scores for sources.
    *   `test_cache.db`: Caches proxy test results (validity, latency).
*   **File System (`output/`)**:
    *   Ephemeral build artifacts published to GitHub Pages.

## Concurrency Model

*   **Asyncio:** The core loop handles I/O bound tasks (fetching).
*   **ThreadExecutor:** CPU-bound parsing is offloaded to threads.
*   **Semaphores:** `ConcurrencyManager` limits parallel tests to prevent file descriptor exhaustion.
