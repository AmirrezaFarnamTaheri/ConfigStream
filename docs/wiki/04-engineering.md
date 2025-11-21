# 04. Engineering Tricks

To achieve high reliability on zero budget, we employ several advanced engineering techniques usually found in high-scale distributed systems.

## 1. Foreign Function Interface (FFI) Integration

Python is great for orchestration, but slow for crypto and low-level networking. We bridge this gap using FFI.

### Rust FFI (Shadowsocks)
-   **Why**: Validating Shadowsocks credentials requires key derivation (PBKDF2/EVP_BytesToKey) and cipher initialization. Doing this for 1000s of proxies in Python is too slow.
-   **How**: We build a shared library (`.so`/`.dll`) from Rust.
-   **Code**: `src/rust/ss_checker/src/lib.rs` exposes a C-compatible `verify_shadowsocks` function.
-   **Python**: `ctypes` loads the library and calls it with zero overhead.

### Go Sidecar (uTLS)
-   **Why**: Python's `ssl` module cannot modify the Client Hello packet to mimic Chrome/Firefox. Go's `uTLS` library can.
-   **How**: We compile a standalone Go binary (`bin/utls-client`).
-   **Interaction**: Python calls the binary via `subprocess`. While not "pure" FFI, it provides the necessary isolation and capabilities.

## 2. Active Security Probing (Honeypots)

We treat proxies as "guilty until proven innocent".

-   **Async Port Scanning**: `src/configstream/security/honeypot.py` uses `asyncio.open_connection` to rapidly check ports.
-   **Concurrency**: These checks run in parallel with the main fetch/parse pipeline, adding minimal latency (only for working proxies).
-   **Heuristics**: We check not just connectivity, but also service banners (if possible) to distinguish a honeypot from a legitimate server.

## 3. Adaptive Timeouts (AIMD)

A fixed timeout (e.g., 30s) is inefficient. Some sources are fast (CDN-backed), others are slow (residential).

-   **Algorithm**: **AIMD** (Additive Increase, Multiplicative Decrease).
    -   **History**: We track the average response time of each source.
    -   **Success**: `new_timeout = max(min_t, old_timeout * 0.9)`.
    -   **Failure**: `new_timeout = min(max_t, old_timeout + 5)`.
-   **Benefit**: The pipeline "learns" which sources are fast and stops wasting minutes waiting for dead ones.

## 4. Hedged Requests

Borrowing from Google's *The Tail at Scale* paper.

-   **Implementation**: When fetching a source:
    1.  Send Request A.
    2.  Wait for `hedge_delay` (e.g., 500ms).
    3.  If Request A hasn't returned, send Request B.
    4.  The first to return wins.
-   **Why?**: Network packet loss is common. A second request often bypasses the glitch.

## 5. Circuit Breakers

If a source is consistently failing, we stop calling it.

-   **Logic**: `src/configstream/circuit_breaker.py`.
-   **Threshold**: 5 consecutive failures trip the breaker for 1 hour.
-   **Impact**: Reduces pipeline duration by ~40%.

## 6. Memory Management

Python's GC is not optimized for millions of small objects.

-   **`__slots__`**: The `Proxy` class uses `__slots__` to reduce memory footprint by ~50%.
-   **Generators**: We process streams lazily.
-   **Explicit Cleanup**: `gc.collect()` is called strategically between batches.
