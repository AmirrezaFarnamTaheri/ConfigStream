# 01. Introduction & Philosophy

## The Vision: Unstoppable Access

ConfigStream was born from a simple, unyielding necessity: **access to the free and open internet is a fundamental human right**, and it should not be complicated, expensive, or fragile. While there are many paid VPNs and complex self-hosted solutions (like Shadowsocks, V2Ray, or Xray), millions of users rely on free, public proxies.

The problem with public proxies is **reliability**. They are ephemeral, often slow, sometimes insecure, and frequently blocked.

**ConfigStream solves this by treating proxy aggregation as a high-velocity data engineering problem.**

We don't just "collect" links. We act as a refinery:
1.  **Aggregate** from hundreds of diverse sources (GitHub repos, Telegram channels, API endpoints).
2.  **Validate** structural integrity using strict parsing rules.
3.  **Test** connectivity and latency in real-time using actual protocol handshakes.
4.  **Secure** against honeypots and MITM attacks using active probing and fingerprinting.
5.  **Score** sources based on historical reliability, geo-diversity, and stability.
6.  **Distribute** via high-availability, censorship-resistant CDNs (GitHub Pages, Cloudflare, IPFS).

## The "Zero Budget" Architecture

A core constraint of ConfigStream is to run entirely on **free-tier** infrastructure. This ensures the project is sustainable indefinitely without financial backing, donations, or commercial interests. It effectively makes the project "uncancellable" as long as GitHub and free CI/CD exist.

### Key Components:
-   **Compute**: GitHub Actions (Standard Linux Runners). We leverage the parallel execution capabilities of the matrix strategy.
-   **Storage**: GitHub Repository (for code) & Artifacts (for ephemeral data passing).
-   **Hosting**: GitHub Pages (static hosting with CDN features) and decentralized mirrors (IPFS).
-   **Database**: SQLite (Ephemeral/Cached) & Flat Files (JSON/YAML/Protobuf). We treat the database as a cache, not a source of truth. The source of truth is the pipeline execution.
-   **Edge Logic**: Cloudflare Workers (Free Tier) for the Telegram Bot and stateless API endpoints.

This constraint forces us to be radically efficient. We cannot spin up a 24/7 heavy server. We must process everything in short bursts (GitHub Actions limits) and persist state smartly between runs using `actions/cache`.

## Design Principles

1.  **Fail Fast, Recover Faster**: If a source times out, we drop it immediately. We use adaptive timeouts to learn the behavior of each source.
2.  **Safety First**: We employ rigorous blocklists (FireHol Level 1), active honeypot detection, and structural validation to prevent malicious configs from reaching the user.
3.  **Client Agnostic**: We output universal formats (Base64, Clash, Sing-box, Surge, Loon) so users are not locked into a specific client.
4.  **Transparency**: Every step of the pipeline is logged and visible. Users can verify exactly where a proxy came from.
5.  **Decentralization**: By supporting IPFS and multiple mirrors, we ensure the subscription links remain accessible even if the main repository is blocked.

## Roadmap & Evolution

ConfigStream is constantly evolving.
*   **Phase 1 (Completed)**: Core pipeline, aggregation, basic testing.
*   **Phase 2 (Completed)**: Access & Localization (Mirrors, Bot).
*   **Phase 3 (In Progress)**: Distributed Scale (Worker Mesh).
*   **Phase 4 (Completed)**: Hardcore Security (uTLS, Honeypot).
*   **Phase 5 (Completed)**: Protocol Expansion (Rust FFI, Hysteria 2).
