# Architecture Guide

This document details the "Zero to Hero" architecture of ConfigStream.

## Overview

ConfigStream is designed to be **Unstoppable**, **Fast**, and **Secure**. It moves away from simple script execution to a containerized, compiled, and distributed system.

### 1. The Pipeline (GitHub Actions)

The pipeline runs on a schedule (every 6 hours) and performs the following steps:

1.  **Build/Cache Container:** A Docker image containing the Python runtime and the compiled Go Tester is built/pulled from GHCR.
2.  **Sharding:** The job is split into 6 parallel shards. Each shard processes a `batch_X.txt` source file.
3.  **Go Batch Testing:** The Python script streams 10,000+ proxies to the Go binary via `stdin`. The Go binary uses 50+ concurrent goroutines to verify TCP connectivity and honeypot status.
4.  **Merge:** Results from all shards are aggregated.
5.  **Output Generation:**
    *   **Standard:** `singbox.json`, `clash.yaml`
    *   **Washing:** Insecure proxies are wrapped in WARP tunnels.
    *   **Chaining:** Protocol chains are generated.
6.  **Fan-Out Distribution:** Artifacts are uploaded to GitHub Releases, Telegram, and Hugging Face in parallel.

### 2. The High-Performance Engine (Go)

Located in `src/go/tester`, this binary replaces the overhead of spawning thousands of `sing-box` processes.

*   **Worker Pool:** Uses a fixed pool of goroutines (default 50) to prevent resource exhaustion.
*   **Honeypot Check:** Verifies cryptographic signatures from the Canary Worker to detect MITM.

### 3. Smart Output Logic

*   **The Recycling Plant:** We do not discard "Working but Insecure" proxies. We wrap them in WireGuard (WARP) to make them secure and usable.
*   **VPN vs. Proxy Mode:** We generate distinct configs for different user needs (Tun/VPN for mobile, Mixed Port for desktop).

### 4. Zero Budget Infrastructure

*   **Compute:** GitHub Actions (Free Tier).
*   **Storage:** GitHub Releases / Hugging Face Datasets.
*   **Hosting:** GitHub Pages / Telegram.
*   **Database:** SQLite (Artifact passing between jobs).
