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

## 2. The Data Plane (The Hybrid Engine)

To test 10,000+ proxies in minutes on a free runner, Python's `asyncio` loop is not enough—the GIL (Global Interpreter Lock) becomes a bottleneck. We solve this with a hybrid approach.

### The Go Sidecar (`src/go/tester`)
*   **Role**: Mass connectivity testing.
*   **Mechanism**: A compiled Go binary. Python spawns it as a subprocess and communicates via standard I/O (JSON streaming).
*   **Performance**: Go spawns thousands of lightweight Goroutines, allowing us to saturate the network interface without CPU blocking.
*   **Features**:
    *   **TCP/UDP Checks**: Fast socket opening.
    *   **TLS Handshake**: Verifies the certificate validity.
    *   **uTLS Integration**: Randomized Client Hello fingerprinting to bypass anti-bot protections on proxy servers.

### Sing-box Integration (`singbox2proxy`)
*   **Role**: Testing complex, modern protocols (Hysteria 2, Tuic, VLESS-Reality).
*   **Mechanism**: Since these protocols require complex client-side state machines, we wrap the official `sing-box` core.
*   **Process**:
    1.  Python generates a temporary, minimal `config.json` for `sing-box`.
    2.  Spawns `sing-box` listening on a random local port.
    3.  Python sends a request through that local port to a test URL (`http://cp.cloudflare.com/generate_204`).
    4.  If it returns 204, the proxy works.

## 3. The Edge Plane (WASM)

To decentralize testing and provide users with truth from *their* perspective, we moved testing to the browser.

*   **WebAssembly (WASM)**: We compile the Go tester code to WASM (`tester.wasm`).
*   **Limitations & Solutions**:
    *   Browsers cannot open raw TCP sockets.
    *   **Solution 1 (WebSocket)**: For `vmess+ws`, `vless+ws`, `trojan+ws`, the WASM module uses the browser's native WebSocket API to perform a real handshake and connectivity test.
    *   **Solution 2 (HTTP/Relay)**: For raw TCP protocols, we are experimenting with a "Relay" approach (future roadmap) or falling back to simple HTTP latency checks if a CORS-enabled endpoint is available.

## Memory Management Strategy

Running on a 7GB RAM shared runner requires strict discipline.

1.  **Streaming, Not Loading**: We never load the full dataset into a list. We process in chunks of 50.
2.  **Generators**: We use Python generators (`yield`) to pass data between stages.
3.  **Garbage Collection**: We explicitly delete large objects and call `gc.collect()` after heavy batch processing phases.
4.  **Artifact Passing**: For the "Merge" job, we don't pass raw objects. We pass optimized SQLite files and compressed JSON, minimizing the I/O overhead between GitHub Actions jobs.

## Data Flow & Sharding

To scale indefinitely, we use the **Matrix Strategy**:

1.  **Sharding**: Source files are split into `sources/batch_1.txt` through `batch_6.txt`.
2.  **Parallel Execution**: GitHub starts 6 independent VMs.
    *   VM 1 processes Batch 1.
    *   VM 2 processes Batch 2.
    *   ...
3.  **Intelligence Synchronization**:
    *   How do VMs share "History" or "Blocklist" data?
    *   They download a *common* cache at the start.
    *   At the end, they upload their *deltas* (new findings) as artifacts.
4.  **Merge Job**:
    *   The final job downloads all 6 artifact sets.
    *   It executes `scripts/merge_batches.py` to consolidate the SQLite databases and proxy lists into a single master dataset.
    *   This master dataset generates the final `metadata.json` and subscriptions.

This architecture allows ConfigStream to scale linearly. To double capacity, we just add more batch files and increase the matrix size in `pipeline.yml`.
