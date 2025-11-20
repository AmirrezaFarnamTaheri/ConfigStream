# 02. System Architecture

## The Pipeline

The core of ConfigStream is a linear but highly parallel pipeline designed to run efficiently on standard GitHub Actions runners (2-core, 7GB RAM). It follows a "Map-Reduce" pattern where sources are processed in parallel shards and then merged.

```mermaid
flowchart TD
    subgraph Ingestion ["Phase 1: Ingestion (Async)"]
        A[Sources URLs] -->|Async Fetch| B(Raw Content)
        B -->|Hedged Requests| B
        B -->|Cache Check| B
    end

    subgraph Processing ["Phase 2: Processing (CPU Bound)"]
        B -->|Parse & Normalize| C(Proxy Objects)
        C -->|Deduplicate| D(Unique Proxies)
        D -->|Blocklist Check| D1{Safe?}
        D1 -->|No| X[Discard]
        D1 -->|Yes| E(Candidate Queue)
    end

    subgraph Validation ["Phase 3: Validation (Network IO & FFI)"]
        E -->|Active Probing| F{Honeypot?}
        F -->|Yes| X
        F -->|No| G{Crypto Check}
        G -->|Rust FFI| H{Valid?}
        H -->|No| X
        H -->|Yes| I{Connectivity}
        I -->|uTLS Sidecar| J(Working Proxies)
    end

    subgraph Output ["Phase 4: Output (IO)"]
        J -->|GeoIP Enrichment| K(Enriched Data)
        K -->|Generate Configs| L[Clash/Singbox/Surge/Loon]
        K -->|Update History| M[SQLite DB]
    end

    subgraph Distribution ["Phase 5: Distribution"]
        L -->|Deploy| N[GitHub Pages]
        L -->|Mirror| O[IPFS/Netlify/Vercel]
        L -->|Serve| P[Telegram Bot]
    end

    Ingestion --> Processing --> Validation --> Output --> Distribution
```

### 1. Ingestion (Fetcher)
We use `httpx` for asynchronous HTTP requests. The fetcher is the entry point of data.
-   **Concurrency**: Controlled via `asyncio.Semaphore` to prevent overwhelming the runner's network stack.
-   **Resilience**: Implements **Hedged Requests**. If a request takes longer than the 95th percentile expected time, we fire a second "hedge" request.
-   **Constraint**: Must respect GitHub Actions network limits (bandwidth/IO).

### 2. Parsing & Validation
Parsing is dangerous. Input is untrusted and often malformed.
-   **Strict Types**: We use `Pydantic` models to enforce schema validity.
-   **Auto-Detection**: The `auto_detect.py` module uses heuristics to identify protocols even if the scheme is missing.
-   **Protocol Expansion**: Support for Hysteria 2 (port hopping) and WireGuard (reserved bytes).

### 3. Testing (The Engine)
We employ a hybrid testing engine:
-   **Sing-box**: The primary connectivity tester for complex protocols (VLESS, VMess, Tuic).
-   **Python aiohttp**: For basic HTTP/SOCKS checks.
-   **Rust FFI**: For high-performance Shadowsocks crypto validation (`src/rust/ss_checker`).
-   **Go Sidecar**: For uTLS fingerprint randomization (`src/go/utls_client`) to simulate real browser handshakes.
-   **Honeypot Probe**: Actively scans the proxy IP for suspicious ports (22, 23, 3389) to detect interception nodes.

### 4. Output & Distribution
We generate multiple formats:
-   **Universal**: Base64 subscription.
-   **Clients**: Clash, Sing-box, Surge, Loon, Quantumult X, SIP008.
-   **Metadata**: `metadata.json` for the frontend and bot.

### 5. The Bot Architecture
The ConfigStream Bot operates in two modes:
1.  **Stateless (Cloudflare Worker)**: Fetches `metadata.json` and `proxies.json` from the GitHub Pages CDN and serves them to users. No database required.
2.  **Polling (CLI)**: Runs as a standard Python process (`configstream bot`) for local or server-based deployments.

## AsyncIO Design

Python's `asyncio` is single-threaded, but ideal for IO-bound tasks.
-   **Event Loop**: The default loop is usually sufficient, but `uvloop` can be used for speedup.
-   **Batching**: We process proxies in chunks to avoid OOM errors.

```mermaid
sequenceDiagram
    participant Scheduler
    participant Fetcher
    participant Parser
    participant Security
    participant Tester
    participant Bot

    Scheduler->>Fetcher: Get Source URL
    Fetcher->>Parser: Raw Data
    Parser->>Security: Proxy Object
    Security->>Security: Honeypot Check (Port Scan)
    Security->>Security: Rust FFI Verify
    Security->>Tester: Valid Proxy
    Tester->>Tester: Run Sing-box / uTLS
    Tester-->>Scheduler: Result (Latency)
    Scheduler->>Bot: Update Metadata
```
