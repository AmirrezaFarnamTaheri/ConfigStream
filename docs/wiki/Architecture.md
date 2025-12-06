# ConfigStream Architecture

## 1. High-Level Overview

ConfigStream operates as a **Streaming Pipeline**. Unlike traditional batch processors that load everything into memory, ConfigStream processes data in streams to handle massive datasets (100k+ proxies) with minimal memory footprint (aiming for <7GB RAM in CI).

### The "Zero Budget" Constraint
We run on GitHub Actions standard runners (2-core, 7GB RAM). This constraint dictates our architecture:
*   **No Database Service**: We use SQLite (`source_quality.db`) and JSON artifacts.
*   **No Long-Running Server**: The "server" is the CI pipeline execution time.
*   **Statelessness**: Each run must recover state from previous artifacts (cache restoration).

## 2. Component Diagram

```mermaid
graph TD
    Sources[Source URLs/Files] -->|Async Fetch| Fetcher
    Fetcher -->|Raw Text| Queue[Bounded Queue]
    Queue -->|Async| Consumers[Parallel Consumers]

    subgraph Consumers
        Parser[Heuristic Parser] -->|Proxy Objects| Validator[Security Validator]
        Validator -->|Safe Proxies| Tester[Hybrid Tester]
        Tester -->|Go/Python| Results
    end

    Results -->|Working Proxies| Aggregator
    Aggregator -->|Ranked List| Intelligence[Intelligence Layer]

    subgraph Intelligence
        Washer[Proxy Washer (WARP)]
        Geo[GeoIP Resolver]
        Vector[Feature Vectorizer]
    end

    Intelligence --> Output[Output Generators]
    Output --> Artifacts[JSON/Sub/Clash]
```

## 3. Core Subsystems

### 3.1. The Fetcher (`src/configstream/fetcher_core`)
*   **Resilience**: Implements `AdaptiveTimeout` (adjusts based on history) and `CircuitBreaker` (stops hammering dead hosts).
*   **Concurrency**: Uses `asyncio.Semaphore` to limit concurrent connections.
*   **User-Agent Rotation**: Rotates fingerprints to evade blocking.

### 3.2. The Parser (`src/configstream/parsers`)
*   **Heuristic Extraction**: Doesn't just base64 decode. It scans for protocol prefixes (`vmess://`, `ss://`), cleans garbage, and handles obfuscated content.
*   **Content Sniffing**: Detects HTML error pages/captive portals to avoid parsing garbage.

### 3.3. The Hybrid Tester (`src/configstream/testers`)
*   **Primary (Go)**: A sidecar binary (`src/go/tester`) built on `sing-box`. It binds to ephemeral ports, runs actual connection tests (SOCKS5 handshake + HTTP GET), and returns latency. Supports concurrent testing of 50-100 proxies.
*   **Secondary (Python)**: Fallback logic using `aiohttp` and `singbox2proxy` if the binary fails or is missing.
*   **Honeypot Detection**: Checks if the proxy is intercepting traffic by verifying signatures from a canary server.

### 3.4. The Intelligence Layer (`src/configstream/intelligence`)
*   **Proxy Washer**: The crown jewel. It takes a "dirty" proxy (blocked IP) and chains it to a clean Cloudflare WARP endpoint via WireGuard.
    *   *Mechanism*: `User <-> Relay (Dirty Proxy) <-> WARP (Clean IP) <-> Target`.
*   **Vectorization**: Converts proxy attributes (latency, stability, country, uptime) into feature vectors for ranking.

### 3.5. Output Logic (`src/configstream/output_logic.py`)
*   **Formatters**:
    *   `singbox.json`: The "Sniper" config (Optimized for routing).
    *   `singbox-vpn.json`: The "Tank" config (Tun mode, heavy resilience).
    *   `clash.yaml`: Legacy support.
*   **Steganography**: Encrypts the subscription in a PNG image (`stealth_cover.png`) to bypass DPI.

## 4. Data Flow Lifecycle

1.  **Initialize**: Load config, blocklists, and cache.
2.  **Shard**: Split sources into batches (e.g., Batch 1-10).
3.  **Process (Parallel)**:
    *   Consumer pulls source.
    *   Fetch -> Parse -> Validate -> Dedup -> Test.
    *   Update Stats.
4.  **Merge**: Combine results from all batches.
5.  **Enhance**: Run Proxy Washer on dirty candidates.
6.  **Publish**: Upload artifacts.
