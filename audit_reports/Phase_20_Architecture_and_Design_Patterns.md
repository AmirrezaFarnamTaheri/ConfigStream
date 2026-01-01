# Phase 20: Architecture & Design Patterns - Analysis Report

## 20. Overview
This phase synthesizes the findings into an architectural review.

## 20.1. Hybrid Architecture
The system employs a **Hybrid Python-Go Architecture**.
*   **Python**: Orchestration, Fetching, Parsing, Intelligence (Washer/Chaining), API, Output.
    *   *Pros*: Flexible, rich ecosystem (FastAPI, httpx, pandas/numpy if needed).
    *   *Cons*: GIL limits CPU-bound concurrency (parsing 100k lines).
*   **Go**: High-performance Testing (`configstream-tester`), Vwarp Tunnel (`vwarp` binary).
    *   *Pros*: True parallelism, fast networking (net/http, quic-go).
    *   *Cons*: Binary dependency management.

## 20.2. Design Patterns
*   **Pipeline**: Producer-Consumer pattern (`asyncio.Queue`).
    *   *Producer*: `source_producer`.
    *   *Consumer*: `processing_consumer` (multiple instances).
*   **Singleton**: `GeoIPResolver`, `BlocklistManager`, `ProxyWasher` (shared instance).
*   **Facade**: `Fetcher` (wraps `fetcher_core`), `Output` (wraps `output_logic`).
*   **Strategy**: `parsers/` (different strategies for different protocols).
*   **Sidecar**: `GoBatchTester` runs as a daemon subprocess, communicating via NDJSON over Stdin/Stdout.

## 20.3. Strengths
*   **Resilience**: Hedged requests, adaptive timeouts, circuit breakers.
*   **Intelligence**: "Washing" dead proxies via WARP is a novel and powerful feature.
*   **Modularity**: Clear separation of `fetcher`, `parsers`, `testers`, `output`.

## 20.4. Weaknesses
*   **Split Brain**: Some logic (e.g., "is this a honeypot?") exists in both Python and Go.
*   **Deployment Complexity**: Requires Python 3.10+ AND specific Go binaries (`tester`, `vwarp`). Docker mitigates this, but bare-metal install is hard.
*   **State Management**: SQLite limits horizontal scaling.

## Recommendations
1.  **Architecture Doc**: Formalize the Hybrid Model in `ARCHITECTURE.md`.
2.  **Binary Management**: Create a `tools/download_binaries.py` script to fetch `vwarp` and `configstream-tester` (pre-built) for non-Docker users.
