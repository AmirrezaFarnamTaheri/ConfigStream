# Implementation: Zero to Hero Roadmap

This document details the technical implementation of the "Zero to Hero" roadmap for ConfigStream, transforming it into a "Sanction-Proof Anti-Censorship Factory".

## 1. Architecture Overview

*   **Core Logic:** Python (Orchestrator, Parsing, Output).
*   **Engine:** Go (Batch Testing, Honeypot Verification).
*   **Environment:** Docker (Multi-stage build).
*   **Distribution:** GitHub Releases, Telegram, Hugging Face (Fan-Out).

## 2. High-Performance Engine (Go)

Located in `src/go/tester/`, the Go binary replaces the legacy `sing-box` CLI subprocess spawning.
*   **Batch Processing:** Reads a stream of JSON configurations from `stdin`.
*   **Concurrency:** Uses a worker pool (default 50) to test proxies in parallel with minimal memory overhead (Goroutines vs Threads/Processes).
*   **Honeypot Verification:** Implements HMAC-SHA256 signature verification against a Cloudflare Worker to detect MITM proxies.

## 3. Intelligent Topology & Proxy Washing

The "Brain" of the system, located in `src/configstream/output.py`.

### Proxy Washing (Recycling)
We no longer discard "dirty" (Google-blocked) or "insecure" (HTTP/SOCKS) proxies.
*   **Consistent Hashing:** Maps a relay proxy to a specific Cloudflare WARP key deterministically.
*   **Tunneling:** Wraps the dirty/insecure proxy in a WireGuard tunnel (WARP).
*   **Result:** `User -> Insecure Relay -> Encrypted WARP Tunnel -> Internet`.

### Smart Chains
We generate exotic chains to bypass specific network conditions:
1.  **Intranet Bridge:** `User -> Domestic Relay (IR) -> Foreign Exit`. Bypasses throttling.
2.  **IPv6 Portal:** `User (IPv4) -> Dual-Stack Relay -> IPv6 Exit`. Unlocks IPv6-only resources.
3.  **Streamer:** `User -> Hysteria2 (UDP Speed) -> US/DE Exit (Geo-location)`.

## 4. Distribution & Resilience

*   **Parallel Uploads:** GitHub Actions trigger Telegram and Hugging Face uploads simultaneously.
*   **Date-Based Versioning:** Releases are tagged `vYYYY.MM.DD-HHMM` to prevent overwrites.
*   **Mirrors:**
    *   **Telegram:** Direct file delivery for users in restricted zones.
    *   **Hugging Face:** "S3-like" storage that is rarely blocked.

## 5. Output Formats

*   **singbox-vpn.json:** "The Tank" - Full TUN mode, GVisor stack, auto-route.
*   **singbox.json:** "The Sniper" - Mixed port, includes "Smart Selector" groups for Intelligent Routing.
*   **clash.yaml:** "The Diplomat" - Conservative, widely compatible configuration.

## 6. Security

*   **Signed Honeypot:** Cloudflare Worker (`tools/bot/worker.js`) verifies request integrity.
*   **Blocklist:** IPs are checked against FireHol Level 1.
*   **Secrets:** All sensitive keys (WARP pool, Honeypot secret) are stored in GitHub Secrets.
