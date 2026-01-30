# 02. Architecture & Design

## The "Resilient Core" Architecture

ConfigStream operates on a unique architecture we call the **"Resilient Core"**. It is designed to function in ephemeral, resource-constrained environments (like CI runners) while maintaining the statefulness and intelligence of a persistent server.

### System Overview

The system consists of three main layers:
1.  **The Control Plane (Python)**: Orchestration, business logic, parsing, and data management.
2.  **The Data Plane (Go/Sing-box)**: High-performance raw socket operations, protocol handshakes, and encryption.
3.  **The Edge Plane (WASM/JS)**: Client-side visualization, verification, and filtering.

```mermaid
graph TD
    subgraph "CI Environment (GitHub Actions)"
        A[Sources (Text/API)] -->|Fetch| B(Fetcher Module)
        B -->|Raw Content| C(Parser Module)
        C -->|Proxy Objects| D{Deduplication}
        D -->|Unique Proxies| E(Validation Layer)
        E -->|Safe Configs| F[Hybrid Tester Engine]

        subgraph "Hybrid Tester Engine"
            F -->|Complex Protocols| G[Sing-box Tester]
            F -->|Raw Socket/Perf| H[Go Batch Tester]
        end

        G -->|Results| I[Result Aggregator]
        H -->|Results| I

        I -->|Working Proxies| J(Intelligence Layer)
        subgraph "Intelligence Layer"
            J --> K[GeoIP Resolver]
            J --> L[Source Quality Tracker]
            J --> M[Anomaly Detector]
        end

        K --> N[Output Generator]
    end

    N -->|Artifacts| O[GitHub Pages / Mirrors]

    subgraph "Client Side (Browser)"
        O --> P[Frontend PWA]
        P -->|Verify| Q[WASM Tester]
    end
```

## 1. The Control Plane (Python)

Implemented in `src/configstream/`, this layer is the "brain."

*   **Pipeline Orchestration**: `pipeline.py` and `pipeline_stages.py` manage the flow of data. We use an **Async Generator** pattern (`source_producer` -> `Queue` -> `processing_consumer`) to stream data through the system, keeping memory usage constant regardless of input size.
*   **State Management via Cache**:
    *   Since the runner is wiped after every job, we persist state (reliability scores, history) in SQLite databases (`data/*.db`).
    *   These files are hashed and stored in GitHub Actions Cache (`actions/cache`).
    *   On startup, the pipeline tries to restore the cache. If successful, it loads the "memory" of previous runs.
*   **Concurrency Manager**: `concurrency_manager.py` dynamically adjusts the number of parallel tasks based on CPU load. If the runner is struggling, it backs off to prevent an OOM (Out Of Memory) kill.
*   **AIMD Control**: We use Additive Increase / Multiplicative Decrease (AIMD) algorithm for throughput tuning. If success rate drops or latency spikes, we reduce concurrency. If stable, we probe for higher throughput.

### The Intelligence Layer: Washing & Smart Chains

A unique feature of ConfigStream is **"Proxy Washing"**.
1.  **Problem**: Many high-quality proxies are blocked by services like Google, Netflix, or OpenAI due to "dirty" IP reputation (datacenter IPs).
2.  **Solution**: We wrap these "dirty" proxies in a clean, reputable exit node (Cloudflare WARP).
3.  **Smart Chaining**:
    *   **Dirty Proxy (Relay)**: Handles the censorship circumvention (getting out of the user's country).
    *   **Clean Exit (WARP)**: Handles the reputation check (accessing the target site).
    *   **Result**: A "Smart Chain" that is both uncensored and clean.
    *   **Verification**: The pipeline generates these chains and *re-tests* them end-to-end using the Go Tester to ensure connectivity.
    *   **Thread Safety** (v2.0.12): Concurrent WARP key fetching is now protected by `asyncio.Lock` to prevent race conditions when multiple async tasks access shared state.
    *   **Anomaly Detection** (v2.1.0): Moved from heavy machine learning (Isolation Forest/scikit-learn) to robust statistical heuristics (Median Absolute Deviation - MAD). This reduces Docker image size by ~300MB and improves startup time while maintaining high accuracy for outlier detection.

### Output Generation & Side Products

ConfigStream generates multiple output formats:
*   **Standard Adapters**: Sing-box, Clash, Surge, Loon, Quantumult X, Shadowrocket, SIP008 (all include Smart Chains)
*   **Side Products** (v2.0.12):
    *   **OpenVPN**: Individual `.ovpn` files for direct import into OpenVPN clients
    *   **WireGuard**: Individual `.conf` files for native WireGuard clients
    *   **Plain URIs**: Protocol-grouped text files (VMess, VLess, Shadowsocks, etc.)
    *   **ZIP Archive**: Complete package with README and all side products for easy download

## 2. The Data Plane (The Hybrid Engine)

To test 10,000+ proxies in minutes on a free runner, Python's `asyncio` loop is not enough—the GIL (Global Interpreter Lock) becomes a bottleneck. We solve this with a hybrid approach.

### The Go Sidecar (`src/go/tester`)
*   **Role**: Mass connectivity testing.
*   **Mechanism**: A compiled Go binary. Python spawns it as a subprocess and communicates via standard I/O (NDJSON stream).
*   **Performance**: Go spawns thousands of lightweight Goroutines, allowing us to saturate the network interface without CPU blocking.
*   **Features**:
    *   **TCP/UDP Checks**: Fast socket opening.
    *   **HTTP Probes**: GET requests through the outbound to measure latency.
    *   **Sing-box Core**: Uses sing-box outbounds for modern protocol handling.

### Sing-box Integration (`singbox2proxy`)
*   **Role**: Testing complex, modern protocols (Hysteria 2, Tuic, VLESS-Reality).
*   **Mechanism**: Since these protocols require complex client-side state machines, we wrap the official `sing-box` core.
*   **Process**:
    1.  Python generates a temporary, minimal `config.json` for `sing-box`.
    2.  Spawns `sing-box` listening on a random local port.
    3.  Python sends a request through that local port to a test URL (`http://cp.cloudflare.com/generate_204`).
    4.  If it returns 204, the proxy works.

## 3. The Edge Plane (WASM)

To decentralize testing and provide users with truth from *their* perspective, we moved limited verification to the browser.

*   **WebAssembly (WASM)**: We compile the Go tester code to WASM (`tester.wasm`).
*   **Current Limitation**: Browsers cannot open raw TCP/UDP sockets from WASM. The current WASM verifier is limited to local config integrity checks and lightweight logic. Full network testing remains a server-side capability (see `KNOWN_ISSUES.md`).

## 4. Frontend Architecture (Edge Plane)

The frontend is a Progressive Web App (PWA) designed for resilience and offline capability.

*   **Self-Hosted Dependencies** (v2.1.0): To ensure accessibility in restricted network environments (where CDNs like unpkg or jsdelivr might be blocked), all critical libraries (`Three.js`, `Globe.gl`, `Chart.js`, `Feather`) are self-hosted within the `assets/libs/` directory. The application attempts to load from CDN for performance but automatically falls back to local copies upon failure.
*   **Real-Time Stats**: Connects to the `metadata.json` API to render live threat maps and performance graphs.
*   **WASM Verifier**: Runs a subset of the Go tester logic in the browser for "Turbo-Verify", allowing users to verify config integrity locally without sending private keys to the server.

## Memory Management Strategy

Running on a 7GB RAM shared runner requires strict discipline.

1.  **Streaming, Not Loading**: We never load the full dataset into a list. We process in chunks of 50.
2.  **Generators**: We use Python generators (`yield`) to pass data between stages.
3.  **Garbage Collection**: We explicitly delete large objects and call `gc.collect()` after heavy batch processing phases.
4.  **Artifact Passing**: For the "Merge" job, we don't pass raw objects. We pass optimized SQLite files and compressed JSON, minimizing the I/O overhead between GitHub Actions jobs.
5.  **Smart Deduplication** (v2.0.12): The `seen_keys` set now uses efficient eviction strategy, only removing oldest 10% when approaching the 200,000 key limit. Previous implementation created full list copies causing memory spikes. New implementation uses `difference_update()` for O(n) eviction instead of O(n²).

## Data Flow & Sharding

To scale indefinitely, we use the **Matrix Strategy**:

1.  **Sharding**: Source files are split into `sources/batch_1.txt` through `batch_14.txt`.
2.  **Parallel Execution**: GitHub starts 14 independent VMs.
    *   VM 1 processes Batch 1.
    *   VM 2 processes Batch 2.
    *   ...
3.  **Intelligence Synchronization**:
    *   How do VMs share "History" or "Blocklist" data?
    *   They download a *common* cache at the start.
    *   At the end, they upload their *deltas* (new findings) as artifacts.
4.  **Merge Job**:
    *   The final job downloads all 14 artifact sets.
    *   It executes `scripts/merge_batches.py` to consolidate the SQLite databases and proxy lists into a single master dataset.
    *   This master dataset generates the final `metadata.json` and subscriptions.

This architecture allows ConfigStream to scale linearly. To double capacity, we just add more batch files and increase the matrix size in `pipeline.yml`.
