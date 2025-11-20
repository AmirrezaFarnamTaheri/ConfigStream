# Architecture Overview 🏗️

ConfigStream is designed as a modern, asynchronous data pipeline. It prioritizes speed, modularity, and resilience.

## High-Level Diagram

```mermaid
graph TD
    A[Sources (TXT/URL)] -->|Fetcher| B(Raw Configs)
    B -->|Parser| C(Proxy Objects)
    C -->|Deduplication| D(Unique Proxies)
    D -->|Security Check| E{Safe?}
    E -- No --> F[Discard / Log]
    E -- Yes --> G[Tester Queue]
    G -->|Sing-box Core| H{Working?}
    H -- Yes --> I[Result Store]
    H -- No --> J[History Tracker]
    I -->|Output Gen| K[JSON/YAML Files]
    K -->|FastAPI| L[Web Dashboard / API]
```

## Core Components

### 1. Ingestion Layer (`fetcher.py`)
-   **Concurrency**: Uses `asyncio` and `aiohttp` to fetch from hundreds of sources simultaneously.
-   **Adaptive Control**: Implements AIMD (Additive Increase, Multiplicative Decrease) to adjust concurrency based on network health.
-   **Intelligence**: `SourceQualityTracker` monitors source reliability over time. Sources that consistently fail are penalized with exponential backoff to save bandwidth.
-   **Anomaly Detection**: `AnomalyDetector` flags sources that suddenly return too much or too little data (potential poisoning attacks).

### 2. Processing Layer (`pipeline.py`)
-   **Streaming**: Data is processed in chunks (batches) rather than loading everything into memory, allowing operation on low-RAM VPS instances.
-   **Parsing**: Robust parsers convert messy base64/text blobs into structured `Proxy` objects (Pydantic models).
-   **Fuzzing**: Parsers are fuzz-tested (`hypothesis`) to prevent crashes on malformed input.

### 3. Validation Layer (`testers.py`)
-   **Engine**: Uses `sing-box` (via `singbox2proxy`) as the testing core for accurate results across all protocols (VMess, VLESS, etc.).
-   **Checks**:
    -   **Latency**: Measures TCP handshake and HTTP response time.
    -   **Integrity**: Checks for header stripping and malicious modifications.
    -   **GeoIP**: Resolves IP to Country/ASN using a local MMDB database (zero latency).
-   **Blocklist**: `BlocklistManager` checks IPs against FireHol Level 1 to filter out known botnets and abusers.

### 4. Presentation Layer (`server.py` & `frontend/`)
-   **Backend**: FastAPI serves static assets and dynamic API endpoints.
-   **Frontend**: A vanilla JS dashboard (no build step required) that consumes JSON data. It features virtual scrolling (via pagination/filtering logic) for performance.
-   **Tools**: Includes a subscription converter and WARP generator.

## Data Persistence

-   **SQLite**: Used for `source_quality.db` and `anomaly.db` to track long-term stats.
-   **JSON/YAML**: Final output is static files in `output/`, making it easy to host on GitHub Pages or CDN.

## Security Model

1.  **Input Sanitization**: All external data is treated as untrusted.
2.  **Secret Scanning**: Pre-commit hooks prevent leaking keys.
3.  **Dependency Management**: Locked dependencies ensure reproducible builds.
4.  **Least Privilege**: Docker containers run as non-root (configured in `Dockerfile`).

## Future Roadmap

-   [ ] integration of Reinforcement Learning for scheduler tuning.
-   [ ] Real-time websocket updates for the dashboard.
-   [ ] Support for SSH tunnels and more exotic protocols.
