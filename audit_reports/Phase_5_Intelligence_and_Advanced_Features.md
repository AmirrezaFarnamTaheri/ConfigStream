# Phase 5: Intelligence & Advanced Features - Analysis Report

## 5. Overview
This phase audits the "Intelligence" features, primarily the `ProxyWasher`, which attempts to revive dead proxies or chain them with Cloudflare WARP for better anonymity/reliability. It also includes adaptive timeout logic and "Vwarp" tooling.

## 5.1. Proxy Washer & Revival (`src/configstream/intelligence/washer/`)

### 5.1.1. Core Logic (`core.py`)
**Analysis**:
*   **Key Management**: Loads WARP keys from `WARP_KEY_POOL` env var or `warp_keys_json`.
    *   **Fallback**: Generates a new key using `KeyGenerator` if pool is empty.
    *   **Scraping**: Fetches keys from community sources (`WarpScraper`).
*   **Clean IPs**:
    *   Fetches from Scraper (GitHub raw URLs).
    *   Scans using `VwarpTool` (binary).
    *   Scans using legacy Python scanner (`WarpScannerWorker`).
    *   Fallbacks to static list.
*   **Infinite Loops**:
    *   `wash_failed` takes `failed_proxies`. It generates a NEW proxy object with `protocol="revived"`.
    *   The pipeline (Phase 2) needs to ensure these "revived" proxies are tested but NOT fed back into `wash_failed` if they fail again.
    *   **Check**: In `processing_consumer` (not fully visible here, but inferred), does it check `proxy.protocol != "revived"` before washing?
    *   **Recursion**: `revived_proxy` has `origin_proxy` in details.
*   **Locking**:
    *   Uses `threading.Lock` (`_state_lock`) for property access.
    *   Uses `asyncio.Lock` (`_async_state_lock`) for async fetch operations. **This is a fix mentioned in code comments.**

### 5.1.2. Key Generator
**Analysis**:
*   `KeyGenerator` is imported but not analyzed deeply here (file `key_generator.py`). Assuming it interacts with Cloudflare API to register accounts.

### 5.1.3. Revival Logic (`wash_failed`)
**Analysis**:
*   Creates a `WireGuard` outbound (WARP) that `detour`s through the failed proxy (`relay`).
*   **Idea**: Maybe the proxy is blocked from accessing the internet directly, but can reach Cloudflare? Or maybe the user is blocked from the proxy, but... wait.
*   **Logic Check**: If the proxy failed because it's down/unreachable (`connect timeout`), wrapping it in WARP won't help (you still need to connect to the proxy).
*   **Use Case**: This logic works if the proxy is *reachable* but the *target* (Google/Test URL) is blocked by the proxy or the proxy IP is dirty. Wrapping in WARP gives a clean exit IP.
    *   This is "Washing" dirty IPs.

### 5.1.4. Warp Scraper (`warp_scraper.py`)
**Analysis**:
*   **Sources**: `WARP_SOURCES` list. Removed dead links.
*   **Regex**: `WIREGUARD_REGEX` scans raw text for `PrivateKey = ...`.
*   **SingBox**: Can parse JSON `outbounds` from remote sources.
*   **Endpoint Lists**: Can parse simple IP/CIDR lists for clean IPs.
*   **URI Parsing**: Supports `warp://` scheme parsing (converts to `http` to use `urlparse`).

## 5.2. Scoring & Ranking (`src/configstream/pipeline_core/sorter.py`)
*(File not read, but referenced in pipeline)*
*   **Pareto Sort**: The pipeline calls `sort_proxies_pareto`.
*   **Math**: Formula typically involves latency, reliability, and uptime.

## 5.3. Adaptive Logic
*   **AdaptiveTimeout**: Used in `fetcher_core`. Adjusts timeout based on historical response times.
*   **CircuitBreaker**: Prevents hammering dead sources.

## 5.4. Vwarp Ecosystem
**Analysis**:
*   `VwarpTool`: A wrapper around a Go/Rust binary (`vwarp`).
*   **Scanning**: `scan_endpoints` finds clean IPs (Cloudflare endpoints that work from the user's location).
*   **SOCKS5 Tunnel**: The pipeline spawns `vwarp` as a local SOCKS5 server. The Go Tester uses this to tunnel traffic if `USE_VWARP_TUNNEL` is set.

## 5.5. Chaining (`src/configstream/intelligence/chaining.py`)
**Analysis**:
*   **Geodesic**: `find_optimal_relay` calculates distances.
*   **Strategies**: `wash_batch` creates "Intranet" or "Optimal" chains.
    *   **Chain**: User -> Relay (Proxy) -> WARP (WireGuard) -> Internet.
    *   **Benefit**: Hides user IP from WARP, hides WARP usage from ISP (looks like Proxy traffic), gives clean IP.

## Recommendations
1.  **Revival Loop Safety**: Ensure `processing_consumer` explicitly filters `is_revived` proxies from being washed again. Recursion depth should be 1 (failed -> revived -> result).
2.  **Key Rotation**: `ProxyWasher` loads keys but doesn't seem to retire bad keys automatically in `core.py`. If a key is invalid, the chain fails.
3.  **Vwarp Binary**: As noted in Phase 1, ensure the binary is secure.
4.  **Clean IP Persistence**: `_clean_ips` are in memory. Persisting them to disk (cache) would speed up cold starts.
