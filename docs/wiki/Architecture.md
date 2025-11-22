# Architecture Guide

ConfigStream implements a **Hybrid Micro-Architecture** designed to process thousands of proxies concurrently within the constraints of GitHub Actions.

## High-Level Overview

The system operates as a pipeline with distinct stages.

```mermaid
graph TD
    A[Sources (Txt/Git)] -->|Fetch| B(Python Orchestrator)
    B -->|Parse & Dedupe| C{Intelligence Layer}
    C -->|Batch| D[Go Tester (Sidecar)]
    D -->|Results| E[Scoring & Filtering]
    E -->|Wash| F[Proxy Washer]
    F -->|Export| G[Artifacts (JSON/YAML)]
```

## 1. The Hybrid "Sidecar" Pattern

We use a mix of **Python** and **Go** to balance flexibility and performance.

### The Orchestrator (Python)
*   **Role:** The "Brain".
*   **Responsibilities:**
    *   Fetching URLs (AsyncIO).
    *   Parsing complex obfuscated configs (Regex/Base64).
    *   Decision making (Anomaly detection, Deduplication).
    *   Generating final JSON/YAML outputs.
*   **Location:** `src/configstream/pipeline.py`

### The Execution Engine (Go)
*   **Role:** The "Muscle".
*   **Responsibilities:**
    *   Raw socket connections.
    *   TLS handshakes.
    *   Real-world latency measurement (RTT).
*   **Mechanism:**
    *   The Python layer spawns a `configstream-tester` subprocess.
    *   It pipes a batch of 50-100 JSON configs via `stdin`.
    *   The Go binary spins up hundreds of goroutines to test them in parallel.
    *   Results are streamed back via `stdout`.
*   **Why?** Python's GIL limits network concurrency. Go's goroutines allow us to test 2,000+ proxies in seconds.

## 2. The CI/CD Sharding Strategy

To bypass the 6-hour timeout of GitHub Actions, we use **Matrix Sharding**.

1.  **Split:** The source list (`sources/`) is divided into 6 batches (`batch_1.txt` ... `batch_6.txt`).
2.  **Fan-Out:** 6 separate GitHub Action runners start simultaneously.
3.  **Process:** Each runner fetches, parses, and tests its assigned batch.
4.  **Fan-In:** A final `merge_results` job collects the 6 artifact chunks, merges the SQLite databases, removes duplicates across batches, and publishes the final release.

## 3. Ephemeral State Management

Since we have no persistent database (PostgreSQL/Redis), we use **GitHub Artifacts** as a state store.

*   **`data/source_quality.db`**: Tracks the historical reliability of every subscription URL.
*   **`data/history.json`**: Tracks the uptime of individual proxies (via Fingerprint).

These files are:
1.  Downloaded from the *previous* run's cache.
2.  Updated during the current run.
3.  Re-uploaded as artifacts for the *next* run.

This allows us to have "Memory" (e.g., "This source has failed 5 times, ignore it for 24 hours") without paying for a server.
