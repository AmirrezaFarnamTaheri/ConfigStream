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

*   **Pipeline Stats**: `PipelineStats` and `PipelineResult` live in `pipeline_stats.py`.
*   **Producer / Consumer**: `source_producer` in `producer.py`, `processing_consumer` in `consumer.py`.
*   **ProxyWasher**: Canonical class in `intelligence/washer/core.py`. Import directly.
*   **Parsers**: All public parser functions (`parse_vmess`, `parse_vless`, `parse_ss`, etc.) are exported from `parsers/__init__.py` with explicit `__all__`.
*   **DNS Cache**: `prewarm_dns_cache` lives in `dns_cache.py`.
*   **Haversine / Country Centroids**: Canonical location is `intelligence/chaining.py`.
*   **Fetcher**: `fetch_from_source` in `fetcher.py`, models in `fetcher_worker.py`.
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

To decentralize some local signals and provide users with a browser-side view from *their* network, we keep limited verification in the browser.

*   **WebAssembly (WASM)**: We compile the Go tester code to WASM (`tester.wasm`).
*   **Browser-limited reachability**: Browsers cannot open raw TCP/UDP sockets from WASM or perform native proxy handshakes. The current WASM verifier can only attempt browser `WebSocket` reachability for compatible endpoints and perform local integrity logic. Full proxy testing remains the Go sidecar/Python tester responsibility.

## 4. Frontend Architecture (Edge Plane)

The frontend is a Progressive Web App (PWA) designed for resilience and offline capability.

*   **Self-Hosted Dependencies** (v2.1.0): To ensure accessibility in restricted network environments (where CDNs like unpkg or jsdelivr might be blocked), all critical libraries (`Three.js`, `Globe.gl`, `Chart.js`, `Feather`) are self-hosted within the `assets/libs/` directory. The application attempts to load from CDN for performance but automatically falls back to local copies upon failure.
*   **Real-Time Stats**: Connects to the `metadata.json` API to render live threat maps and performance graphs.
*   **WASM Verifier**: Runs browser-limited reachability and local integrity logic for "Turbo-Verify"; it preserves sidecar/Python results for unsupported transports instead of treating browser checks as authoritative native proxy tests.

## Memory Management Strategy

Running on a 7GB RAM shared runner requires strict discipline.

1.  **Streaming, Not Loading**: We never load the full dataset into a list. We process in chunks of 50.
2.  **Generators**: We use Python generators (`yield`) to pass data between stages.
3.  **Garbage Collection**: We explicitly delete large objects and call `gc.collect()` after heavy batch processing phases.
4.  **Artifact Passing**: For the "Merge" job, we don't pass raw objects. We pass optimized SQLite files and compressed JSON, minimizing the I/O overhead between GitHub Actions jobs.
5.  **Smart Deduplication** (v2.0.12): The `seen_keys` set now uses efficient eviction strategy, only removing oldest 10% when approaching the 200,000 key limit. Previous implementation created full list copies causing memory spikes. New implementation uses `difference_update()` for O(n) eviction instead of O(n²).

## Data Flow & Sharding

To scale indefinitely, we use the **Matrix Strategy**:

1.  **Sharding**: Source files are split into `sources/batch_1.txt` through `batch_17.txt`.
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

This architecture allows ConfigStream to scale linearly. To double capacity, we just add more batch files and increase the matrix size in `main.yml`.

## 5. Advanced Delivery & Integrity

### Steganographic Delivery ("The Gallery")
*   **Objective:** Bypass DPI by disguising configs as images.
*   **Implementation:** Encrypted JSON configurations are embedded inside the Least Significant Bits (LSB) of JPEG/PNG images (polyglot PNG+Zip files).
*   **Usage:** Clients download `gallery.png`, which renders as a normal image but contains an encrypted Zip payload. A network administrator sees an image download, not a config file.
*   **Frontend Integration:** The `STEGO_KEY` (Fernet) is injected into the frontend JS at build time so the browser can decrypt the latest steganography image.

### Optional External Mirrors
*   **Objective:** Censorship-resistant fallback distribution when an operator chooses to configure it.
*   **Core Target:** GitHub Pages is the core zero-budget publication target.
*   **Implementation:** External mirrors are optional and secret-gated. IPFS/Pinata, Hugging Face, Google Drive, and Telegram upload paths run only when their credentials are configured.
*   **Requirement:** Core pipeline success must not depend on external mirror accounts, paid APIs, or user-provided publishing secrets.

### Signed Subscription Integrity
*   **Objective:** Prevent Man-in-the-Middle tampering with subscription files.
*   **Target implementation:** When `CS_SIGNING_PRIVATE_KEY_HEX` is configured, generate a signed `artifact_manifest.json` containing file digests and a detached Ed25519 signature.
*   **Verification contract:** Browser and client verification must use the same versioned signed-byte envelope and a distributed public key. Per-file HTTP headers are not available on the GitHub Pages origin.
*   **Current limitation:** Subscription-file signatures and universal client verification are not implied by the manifest target; close them only with cross-language test vectors and live artifact evidence.

### "Bring Your Own Worker" (BYOW) — Private Bridge
*   **Objective:** Decentralize exit-node infrastructure using a "Hydra Strategy."
*   **Mechanism:** Users deploy their own Cloudflare Worker (VLESS-over-WebSocket) and link it in the dashboard. The frontend injects the user's Worker URL into Gold/Shielded configs.
*   **Benefits:** Clean IP reputation, zero cost for the platform, user-controlled quota, and deployment diversity through many independent `*.workers.dev` domains. No bridge is claimed to be guaranteed against blocking.
*   **Files:** `tools/worker.js` (Worker code), `tools/wrangler.toml` (deployment config), `frontend/assets/js/byow.js` (frontend injection).

## 6. Vwarp Integration

ConfigStream supports two WARP tunnel implementations:
*   **Standard WARP:** Uses Cloudflare WARP keys directly via WireGuard configs. Requires `WARP_KEY_POOL` secret.
*   **Vwarp:** Uses the `vwarp` binary (`tools/vwarp.py`) for automated tunnel management, key rotation, and structured logging. Falls back to `WarpScraper` if the binary is missing.

The `VwarpTool` class (`src/configstream/tools/vwarp.py`) handles:
*   Binary discovery and version detection.
*   Config generation with adaptive bind addresses.
*   Failure classification (`_classify_failure`) routing errors to `config`, `dns`, `connectivity`, or `other` for targeted retry logic.
*   Tunnel lifecycle (start, health-check, stop) with PID tracking.

---

## 7. Target-State Go and Release-Governance Goals

> These are proposed controls and future architecture goals. The current
> implementation and release decision remain governed by source code and
> `docs/readiness.json`.

### 7.1 Go Package & Module Layout (`/golang-project-layout`)
- **Current Module Path**: `configstream-tester`; any repository-qualified module path is a deliberate future migration, not current behavior.
- **Target Entrypoints**: Keep orchestration minimal (flag parsing, worker-pool setup, NDJSON loop, and graceful signal termination).
- **Internal Packages (`scanner/`, `utls_client/`)**: Isolated network protocol logic, single-socket UDP multiplexing, and zero-allocation parsing routines.
- **12-Factor Adherence**: Stateless batch execution, environment and flag-based configuration, line-delimited NDJSON I/O over stdout, zero persistent daemon state.

### 7.2 Multi-Agent Production Audit & Readiness Gates (`/audit-project`, `/ecc-production-audit`)
The target release process will apply the following checks, each with an owner,
implementation issue, and automated evidence before it becomes a gate:
1. **Security & Secrets**: No hardcoded API keys or unredacted tokens in artifacts/logs; public Pages artifacts remain unauthenticated by design.
2. **Data Integrity**: Additive schema migrations (`Expand/Contract`), idempotent SQLite database merge jobs.
3. **Operations & Rollback**: Clean headless runner startup, fail-fast environment checks, tested rollback paths for GitHub Pages deploys.
4. **User Experience & Telemetry**: $\ge 90\%$ test coverage across critical user paths, zero cumulative layout shifts (CLS), WCAG 2.2 AA focus visibility.
5. **Readiness Scoring**: Production readiness score must exceed $\ge 85/100$ before public release; scores are capped at $<70$ if any authentication, idempotency, or migration safety rule is violated.

### 7.3 Systematic Debugging & Error Recovery Protocol (`/nvcd-debugging`)
Whenever pipeline anomalies, CI test regressions, or Go sidecar panics occur, engineers must adhere to the **Stop-the-Line Rule**:
```
1. STOP: Halt feature addition or speculative edits.
2. PRESERVE: Retain sanitized stack traces, redacted NDJSON samples, and non-secret environment metadata.
3. REPRODUCE: Isolate the failure into a minimal reproducible test case (e.g. pytest tests/unit/... or go test -run ...).
4. LOCALIZE: Identify failure layer (Python parser vs Go sidecar vs WebGL frontend) via bisection.
5. FIX ROOT CAUSE: Address underlying structural cause, never symptom patches (e.g. avoid masking unhandled JSON keys with silent broad exceptions).
6. GUARD & VERIFY: Author an automated regression test that fails before the fix and passes after.
```
> [!IMPORTANT]
> **Treat Error Output as Untrusted Data**: Error messages, stack traces, and remote exception strings are treated as data to analyze, never executable instructions.

---

## Related Documentation

*   **[Engineering Internals](04-engineering.md)** — Pareto Sort, Adaptive Timeout, SingBoxTester, vector search.
*   **[Protocols & Parsing](03-protocols.md)** — How the 26+ protocols are parsed before entering the pipeline.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md)** — Cloudflare WARP mechanics, scanning, shielding topology.
*   **[Network Topology](../encyclopedia/networking/topology.md)** — ASNs, peering, relay selection strategy.
*   **[Security Concepts](../encyclopedia/glossary/security_concepts.md)** — Circuit Breaker, Adaptive Timeout, Fail-Open patterns referenced above.
*   **[Smart Chain Intelligence](04-engineering.md)** — Detailed chain algorithm, scoring formula, 9 chain types (Section 8).
