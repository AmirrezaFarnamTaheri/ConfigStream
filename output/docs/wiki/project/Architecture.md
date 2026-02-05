# ConfigStream v2.0 Architecture

ConfigStream has evolved into a resilient, hybrid intelligence platform. This document outlines the key architectural components introduced in version 2.0.

## 1. Hybrid Engine (Python + Go)

The core processing pipeline is split between Python (Orchestration, Logic) and Go (Performance, Networking).

- **Python (The Brain):** Handles file parsing, database management, intelligence logic (washing, chaining), and output generation.
- **Go (The Muscle):** A custom binary (`configstream-tester`) performs high-concurrency latency testing and active network scanning.

### Why Go?
We integrated `shahradelahi/cloudflare-warp`'s scanning logic directly into our Go tester. This allows us to scan thousands of Cloudflare endpoints per second using raw UDP packets, bypassing the overhead of Python's `asyncio` loop for CPU-bound packet construction.

## 2. Intelligence Layer

ConfigStream is no longer just a "tester". It actively improves the proxies it finds.

### The Washer (Proxy Reviver)
Located in `src/configstream/intelligence/washer/`, this module "washes" dirty or insecure proxies by wrapping them in a Cloudflare WARP tunnel.

1.  **Scanner:** The Go binary scans for clean, low-latency Warp endpoints (Clean IPs).
2.  **Wrapper:** The Washer takes a working proxy (Relay) and chains it to a Clean IP (Exit) using WireGuard.
3.  **Result:** A "Washed Proxy" that has the reputation of Cloudflare and the accessibility of the original relay.

### Smart Chaining (Topology Aware Routing)
Located in `src/configstream/intelligence/washer/chaining.py`, this module builds complex proxy chains to solve specific problems:

-   **Intranet Bridge:** Connects a Domestic Relay (e.g., Iran) $\to$ Foreign Exit (e.g., Germany). Bypasses censorship while maintaining local network access.
-   **IPv6 Portal:** Connects an IPv4 Relay $\to$ IPv6 Exit. Unlocks IPv6-only VPS resources for legacy users.
-   **Streaming Accelerator:** Connects a UDP-optimized Relay (Hysteria2) $\to$ Streaming-friendly Exit (US/UK).

## 3. Worker System

We introduced a "Worker" concept in `src/configstream/workers/`.
-   **WarpScannerWorker:** Orchestrates the Go binary to perform background scans without blocking the main pipeline.

## 4. Pipeline Flow

1.  **Fetch & Parse:** Sources are fetched and parsed into `Proxy` objects.
2.  **Test:** The Go tester verifies connectivity and measures latency.
3.  **Optimize:** Dead proxies are discarded.
4.  **Intelligence Phase:**
    -   **Scan:** `WarpScannerWorker` finds clean IPs.
    -   **Wash:** `ProxyWasher` creates WARP wraps.
    -   **Chain:** `generate_smart_chains` builds topology chains.
5.  **Output:** Files (Sing-box, Clash, Sub) are generated with all original + intelligent proxies.

## 5. Frontend & Analytics

The frontend now consumes a richer `metadata.json` which includes:
-   **Protocol Distribution**
-   **Latency Histograms**
-   **Threat Analysis** (Dirty IPs, Honeypots)
-   **Intelligence Stats** (Revived Proxies, Smart Chains)

This architecture ensures ConfigStream remains "Zero Budget" while delivering enterprise-grade resilience.
