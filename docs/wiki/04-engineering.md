# 04. Engineering & Internals

This document is a deep dive into the specific algorithms and components that power ConfigStream.

## 1. The Pareto Sort Algorithm

Most aggregators sort by Latency (Ping) alone. This is flawed because a proxy that pings 50ms but fails 50% of requests is useless. We use a multi-objective sorting algorithm.

### The Formula

```python
Score = (NormalizedLatency * 0.5) + (FailureRate * 0.3) + (Unstability * 0.2)
```

1.  **Normalized Latency (50% Weight)**:
    *   `RawLatency / 1000`. Capped at 1.0 (1 second).
    *   A 100ms proxy gets `0.1`. A 2000ms proxy gets `1.0`.

2.  **Failure Rate (30% Weight)**:
    *   Derived from `ProxyHistoryTracker`.
    *   `1.0 - (Successes / TotalChecks)`.
    *   A robust proxy (100% success) gets `0.0`. A flaky one (50% success) gets `0.5`.

3.  **Unstability / Jitter (20% Weight)**:
    *   Derived from `uptime_percentage` (as a proxy for stability over time).
    *   `1.0 - Uptime`.

**Result**: The sorting key minimizes the Score. A fast, reliable proxy appears at the top. A fast but broken proxy is pushed down.

## 2. Adaptive Timeout Logic

Fixed timeouts are inefficient.
*   **Too Short**: We drop valid but slow proxies (False Negatives).
*   **Too Long**: We waste minutes waiting for dead proxies.

### The `AdaptiveTimeout` Class
We track the average response time for every **Domain/IP**.

**Algorithm**:
1.  **Cold Start**: Default timeout is 10s.
2.  **Learning**: Every success records the latency.
3.  **Calculation**:
    ```python
    TargetTimeout = AvgLatency + (3 * StandardDeviation)
    ```
4.  **Bounds**: Min 3s, Max 20s.

**Effect**: If `us.server.com` usually responds in 200ms +/- 50ms, we set the timeout to ~350ms. If it hangs, we cut it instantly. This speeds up the pipeline by 40-60%.

## 3. The SingBoxTester

The `SingBoxTester` (`src/configstream/testers_core.py`) is the interface between Python and the testing engines.

*   **Logic Flow**:
    ```python
    if protocol in ["http", "socks"]:
        return self._test_direct(proxy)  # Uses aiohttp
    elif self.go_tester.available:
        return self.go_tester.test_batch(batch)  # Uses Go Sidecar
    else:
        return self._test_via_singbox(proxy)  # Uses Sing-box subprocess
    ```

### The Go Sidecar (Batch Tester)
*   **Path**: `src/go/tester/main.go`
*   **Concurrency**: Uses Go routines. Can handle 500 concurrent checks easily.
*   **Interface**: Reads JSON lines from STDIN, writes JSON lines to STDOUT.
*   **Honeypot Check**: Optionally performs a canary request using a `CANARY_URL` when `strict_security` is enabled.
    *   If `CANARY_URL` is **not** set, the tester logs a **warning** and disables honeypot detection while still measuring latency.
    *   This makes configuration drift visible without breaking the overall test pipeline.

## 4. Pipeline Orchestration & Backpressure

The `run_full_pipeline` function (`src/configstream/pipeline.py`) orchestrates producer/consumer stages, concurrency tuning, and output generation.

*   **Work Queue**: Uses an `asyncio.Queue` with a **max size of 500** to provide sufficient buffering between the fetcher and tester stages without risking deadlocks under high load.
*   **Timeouts**: The consumer side uses `asyncio.wait_for(..., timeout=300.0)` to avoid blocking indefinitely if the producer dies unexpectedly.
*   **Event Stream Lifecycle**: The `EventStream` is now closed in a `finally` block to guarantee that file handles and buffers are flushed even if the pipeline raises an exception.

## 4. Intelligence Layers

### Source Quality Tracker (`src/configstream/source_quality.py`)
Tracks the historical performance of every subscription source.

*   **Metrics**:
    *   **Reliability**: `working_proxies / fetched_proxies`
    *   **Consistency**: Variance in reliability over the last 10 runs.
    *   **Diversity**: How many unique ASNs (ISPs) does this source provide?
*   **Action**:
    *   **Gold**: High reliability + High diversity. Fetched first.
    *   **Silver**: Average. Fetched if capacity allows.
    *   **Garbage**: <1% reliability. Disabled automatically.

### Anomaly Detector (`src/configstream/anomaly.py`)
Detects "Pollution Attacks" or "Spam Batches."

1.  **Subnet Flood**:
    *   If a batch of 100 proxies contains 95 from `1.2.3.0/24`, it is suspicious.
    *   Action: Discard the whole batch.
2.  **Port Scanning**:
    *   If a batch contains sequential ports on the same IP (`1.2.3.4:1001`, `1.2.3.4:1002`...), we flag it.

## 5. Proxy Washing & Smart Chaining

### `ProxyWasher` (`src/configstream/intelligence/washer.py`)
*   **Problem**: Many IPs are "dirty" (blacklisted by Google/Cloudflare).
*   **Solution**: We wrap the proxy in a **Chain**.
    *   `Client -> DirtyProxy -> WARP (Clean IP) -> Target`
*   **Implementation**: We maintain a pool of valid Cloudflare WARP WireGuard keys. We generate a Sing-box "Chain" configuration that routes the outbound traffic of the dirty proxy into the WARP interface.
*   **Candidate Selection Update**: When a WARP pool is configured, we currently wash **all working proxies** (not just those tagged `dirty_ip`), providing a safer default in case tagging fails upstream.

### BoundedConcurrencyManager
To prevent "thundering herd" problems and OOM kills, we use a custom `BoundedConcurrencyManager`.
*   It uses an `asyncio.Condition` to manage a pool of permits.
*   It supports **Dynamic Resizing**: If the error rate spikes (indicating server overload or rate limiting), we dynamically reduce the concurrency limit. If errors drop, we increase it (AIMD - Additive Increase Multiplicative Decrease).

## 6. Static Vectors (Vector Search)

To enable "Natural Language Search" on a static site:
1.  **Vector Generation**: We convert proxy attributes (Country, City, ISP, Protocol, Speed Tag) into a simplistic low-dimensional vector, using SHA‑256–based feature hashing for consistency.
2.  **Pre-computation**: We generate `output/vectors.json` mapping `ProxyID -> [Vector]`.
3.  **Client-Side (Current)**: The frontend uses these vectors together with basic metadata to compute a simple keyword‑based relevance score (see `06-frontend.md`).
4.  **Client-Side (Planned)**: A future enhancement may use true cosine similarity over these vectors in a Web Worker to provide semantic search on large datasets.
