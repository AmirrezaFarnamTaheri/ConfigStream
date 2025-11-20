# 04. Engineering Tricks

To achieve high reliability on zero budget, we employ several advanced engineering techniques usually found in high-scale distributed systems.

## 1. Adaptive Timeouts (TCP-like)

A fixed timeout (e.g., 30s) is inefficient. Some sources are fast (CDN-backed), others are slow (residential).

-   **Algorithm**: **AIMD** (Additive Increase, Multiplicative Decrease), inspired by TCP Congestion Control.
    -   **History**: We track the average response time of each source in `adaptive_timeout.py`.
    -   **Success**: If a fetch succeeds in 2s, we decrease the timeout for the next run: `new_timeout = max(min_t, old_timeout * 0.9)`.
    -   **Failure**: If it times out, we aggressively increase it: `new_timeout = min(max_t, old_timeout + 5)`.
-   **Benefit**: The pipeline "learns" which sources are fast and stops wasting minutes waiting for dead ones.

## 2. Hedged Requests

Borrowing from Google's *The Tail at Scale* paper.

-   **Concept**: Tail latency (the slowest 1% of requests) ruins batch performance.
-   **Implementation**: When fetching a source:
    1.  Send Request A.
    2.  Wait for a short delay (e.g., 500ms or the p95 historical latency).
    3.  If Request A hasn't returned, send Request B.
    4.  The first to return wins. The loser is cancelled.
-   **Why?**: Network packet loss or momentary server hiccups are common. A second request often bypasses the glitch.

## 3. Circuit Breakers

If a source is consistently failing (e.g., 404 or 500 errors), continuously retrying it wastes resources.

-   **Logic**: `src/configstream/circuit_breaker.py`.
-   **State**: `CLOSED` (Normal) -> `OPEN` (Blocked) -> `HALF-OPEN` (Testing).
-   **Threshold**: 5 consecutive failures trip the breaker for 1 hour.
-   **Impact**: Reduces pipeline duration by ~40% by skipping known-bad sources.

## 4. Memory Management in Python

Python's Garbage Collector (GC) is not optimized for millions of small, short-lived objects (like parsed proxy lines).

### Strategies
1.  **`__slots__`**: The `Proxy` class uses `__slots__` instead of `__dict__`. This reduces memory usage per object by ~40-50%.
2.  **Generators (`yield`)**: The fetcher and parser yield results lazily. We never hold the entire dataset in memory as a list until the final deduplication step.
3.  **Explicit `del`**: We manually delete large raw content strings immediately after parsing.

## 5. Database as a Cache

We use SQLite (`source_quality.db`) but we treat it as **ephemeral**.
-   **WAL Mode**: Write-Ahead Logging is enabled for concurrency.
-   **Persistence**: The DB is uploaded/downloaded as a GitHub Actions Artifact. If it's lost, the system degrades gracefully (re-learns scores from scratch) rather than breaking.
-   **Zero-Copy**: We pass data between jobs via artifacts, not by querying a remote SQL server (which violates the Zero Budget rule).
