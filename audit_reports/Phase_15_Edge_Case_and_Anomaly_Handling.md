# Phase 15: Edge Case & Anomaly Handling - Analysis Report

## 15. Overview
This phase audits mechanisms for handling edge cases: slow requests (hedging), DNS issues, and stale data.

## 15.1. Hedged Requests (`src/configstream/hedged_requests.py`)

### 15.1.1. Logic
**Analysis**:
*   **Race Strategy**:
    *   Starts T1.
    *   Waits `hedge_after` (e.g. 500ms).
    *   If T1 is done: return result (if success), or start T2 immediately (if fail).
    *   If T1 is not done: start T2 (latency hedge).
    *   Then race both.
*   **Concurrency**: Uses `asyncio.Queue` to collect results.
*   **Cleanup**: `finally` block cancels pending tasks.
    *   `await asyncio.gather(*active_tasks, return_exceptions=True)`. This ensures clean task teardown.
    *   **Zombie Check**: The tasks are collected in `active_tasks` set.
*   **Bug/Edge Case**:
    *   If T1 fails *immediately* (e.g., DNS error), `queue.put` happens.
    *   The `wait(timeout=hedge_after)` returns T1 in `done`.
    *   It checks queue: `success=False`.
    *   It starts T2.
    *   This logic works perfectly for failover.

## 15.2. DNS Prewarming (`src/configstream/dns_prewarm.py`)
**Analysis**:
*   **Logic**: Parses hostnames from source list, counts frequency, picks Top N.
*   **Safety**: `return_exceptions=True` prevents a single DNS failure from crashing the batch.
*   **Cache Poisoning**: `sources` come from configuration. If an attacker controls the source URLs (e.g., via PR), they can make the system resolve malicious domains. But resolving a domain is generally low risk unless there's a vulnerability in `aiodns`/`c-ares`.

## 15.3. Freshness Logic (`src/configstream/freshness.py`)
**Analysis**:
*   **Timezone**: `replace("Z", "+00:00")` is a classic Python < 3.11 fix for ISO strings.
    *   **Risk**: If string uses other offsets (e.g. `+0500`), this replace does nothing (which is fine). If it uses `Z`, it fixes it.
    *   **Validation**: `try-except ValueError` falls back to "fresh".
    *   **Issue**: Falling back to "fresh" (`age_seconds=0`) for invalid dates might keep invalid/old proxies alive forever if their date format is corrupted.
    *   **Recommendation**: Fall back to "stale" or "drop" for invalid dates? Or just log warning.

## 15.4. DNS Caching Limitations (`src/configstream/http_client.py`)
**Analysis**:
*   **Mechanism**: `CachedDNS_AsyncHTTPTransport` intercepts requests and replaces the hostname with a cached IP.
*   **Limitation**: The code explicitly checks `if request.url.scheme == "http"`. It does **NOT** apply to HTTPS.
    *   **Reasoning**: "Forcing an IP connection with HTTPS requires manual Host header manipulation and a custom SSLContext... which adds significant complexity and security risk (MITM)."
    *   **Impact**: Since 99% of proxy sources use HTTPS, `DNS_CACHE_ENABLED` is effectively a no-op for the majority of traffic. The custom DNS resolver is unused for secure fetching.
    *   **Recommendation**: Document this limitation clearly. If DNS resolution is a bottleneck for HTTPS, `httpx` allows passing a custom `resolver` in newer versions, or one must use the `Host` header + `verify=False` (insecure) or a custom SSLContext (complex). Given "Zero-Budget" constraints, sticking to standard HTTPS resolution is safer, but the "DNS Cache" feature is misleadingly named if it only affects HTTP.

## Recommendations
1.  **Freshness Default**: If date parsing fails, assume STALE (`age_seconds = 999999`) rather than FRESH (`0`). It forces a re-test, which is safer. The current implementation in `src/configstream/freshness.py` defaults to `age=0` (fresh), which is unsafe.
2.  **DNS Cache Documentation**: Clarify in `AGENTS.md` and docs that DNS Caching only applies to plain HTTP sources.
