# 01. Introduction & Philosophy

## The Vision: Unstoppable Access

ConfigStream represents a paradigm shift in how we approach internet freedom tools. It was born from a simple, unyielding necessity: **access to the free and open internet is a fundamental human right**, and it should not be complicated, expensive, or fragile.

In a world of increasing digital borders, state-sponsored censorship, and fragmented networks, the "standard" solutions often fail:
*   **Commercial VPNs**: Easy to block, require payment (identity trail), and rely on central trust.
*   **Self-Hosted Servers**: Require technical expertise, credit cards, and maintenance.
*   **Public Proxies**: Historically unreliable, ephemeral, dangerous, and often broken.

**ConfigStream solves this by treating proxy aggregation not as a "collection" task, but as a high-velocity data engineering problem.**

We act as a global refinery for the open internet:
1.  **Ingest**: We consume thousands of potential access points from hundreds of chaotic sources (GitHub repositories, Telegram channels, Pastebins, APIs).
2.  **Refine**: We parse, normalize, and structurally validate these configurations, discarding the malformed and the dangerous.
3.  **Verify**: We test connectivity, latency, and protocol handshake validity in real-time using a hybrid Python/Go engine.
4.  **Secure**: We actively probe for honeypots, strip tracking metadata, and "wash" dirty IPs using Cloudflare WARP.
5.  **Enrich**: We add geolocation, ISP data, and historical reliability scores.
6.  **Distribute**: We publish the "refined fuel" (clean, working proxies) via high-availability, censorship-resistant CDNs (GitHub Pages, Cloudflare, IPFS, Hugging Face).

## The "Zero Budget" Manifesto

A core constraint of ConfigStream is to run **entirely on free-tier infrastructure**. This is not just about saving money; it is a design philosophy that ensures resilience and sustainability.

**If it costs money, it can be cancelled.**
**If it relies on a credit card, it can be traced.**

By strictly adhering to "Zero Budget," ConfigStream becomes:
*   **Uncancellable**: As long as GitHub and free CI/CD providers exist, ConfigStream exists.
*   **Sustainable**: No server bills mean the project can run indefinitely without donations or commercial models.
*   **Scalable**: We leverage the massive, distributed compute power of public CI runners rather than a single limited VPS.

### The Stack

| Component | Solution | Role |
| :--- | :--- | :--- |
| **Compute** | **GitHub Actions** (Linux Runners) | The engine. We use parallel matrix jobs to get 20+ vCPUs of concurrent processing power for free. |
| **Storage** | **GitHub Repository** | Source code and configuration. |
| **Persistence** | **GitHub Artifacts & Cache** | Ephemeral state passing. Databases (`sqlite`) are cached between runs. |
| **Hosting** | **GitHub Pages** | Static file hosting for subscriptions and the frontend. |
| **CDN** | **Fastly / Cloudflare** | GitHub Pages uses Fastly; we also deploy mirrors to Cloudflare Pages. |
| **Database** | **SQLite (Serverless)** | We treat the DB as a file. It is downloaded at the start of a job and uploaded at the end. |
| **Intelligence** | **VirusTotal (Free API)** | Passive IP reputation scanning. |
| **Edge Logic** | **Cloudflare Workers** | Stateless API endpoints and Telegram bot hosting. |
| **Mirrors** | **Hugging Face / IPFS** | Immutable, redundant storage for outputs. |

## Digital Sovereignty & The User

ConfigStream empowers the user to be their own ISP. By aggregating thousands of scattered, weak signals (individual proxies), we create a strong, unified signal (a robust network).

*   **No Login**: We never ask for email or credentials.
*   **No Logs**: We run on ephemeral runners that are wiped after execution. We cannot log user activity even if we wanted to.
*   **Client Control**: We do not force a specific client app. We output standard formats (Clash, Sing-box) that work with open-source tools users already trust.

## Design Principles

### 1. Fail Fast, Recover Faster
The internet is messy. Sources die. Proxies rot. Our pipeline is designed to be ruthless.
*   **Adaptive Timeouts**: We learn the speed of a source. If it usually responds in 1s but takes 5s today, we cut it.
*   **Circuit Breakers**: If a source fails 3 times in a row, we stop checking it for the rest of the run to save resources.

### 2. Safety First (The "No Abuse" Pledge)
We are guests on the internet infrastructure. We must behave responsibly.
*   **Passive Only**: We never port scan random ranges. We only verify IPs that have been publicly shared.
*   **Rate Limiting**: We respect source server limits.
*   **Blocklists**: We integrate FireHol Level 1 to strictly block known malicious IPs (botnets, spam sources) from ever reaching the user.

### 3. Client Agnostic
We do not believe in "one app to rule them all." Users have preferences.
*   **Native Configs**: We output tailored configurations for **Clash**, **Sing-box**, **Surge**, **Loon**, **Quantumult X**.
*   **Universal Formats**: We provide **SIP008** and **Base64** subscriptions for maximum compatibility.
*   **Field Mapping**: We handle complex mapping of protocol fields (e.g., converting VLESS flow settings to Clash's specific format).

### 4. Transparency & Verifiability
Trust is earned.
*   **Open Source**: Every line of code is visible.
*   **Traceability**: Every proxy in the final list includes metadata about its origin (`_source` field).
*   **Reproducibility**: Anyone can fork the repo and run their own private instance of ConfigStream.

### 5. Decentralization
A central point of failure is a censorship target.
*   **Multiple Mirrors**: If GitHub is blocked, we have mirrors on GitLab, Hugging Face, and IPFS.
*   **Distributed Testing**: Our WASM client allows users to verify proxies from *their* network perspective, not just ours.

## Current Capabilities (v3.0)

ConfigStream today is a fully autonomous platform that runs every 4 hours without human intervention:

*   **26+ Protocols**: VLESS, VMess, Trojan, Shadowsocks, SS2022, Hysteria2, TUIC, WireGuard, SSH, SOCKS5, HTTP, OpenVPN, ShadowsocksR, Juicity, and more.
*   **17-Shard Parallel Pipeline**: 17 GitHub Actions VMs process sources concurrently, then merge results.
*   **Hybrid Python + Go Engine**: Python orchestrates; Go tests 10,000+ proxies in minutes.
*   **9 Smart Chain Types**: Intranet, Washed, IPv6, Streaming, Censorship-Resistant, Low-Latency, High-Anonymity, Load-Balanced, Experimental.
*   **3 Evasion Techniques**: uTLS fingerprinting, multiplexing with padding, ALPN rotation. (TLS fragmentation disabled — sing-box removed tls_fragment; use vwarp AtomicNoize for fragmentation-based evasion.)
*   **3 DNS Profiles**: Standard, DNS-Safe (IP-only), DNS-Hardened (DoH/DoT/DoQ).
*   **Proxy Washing & Shielding**: Resurrect dead proxies via WARP/Vwarp tunnels.
*   **Chain Laboratory**: Browser-based 5-step chain builder with 6 strategies and 8 export formats.
*   **Offline Tools**: `tools/lab-scanner.py` (Python), `tools/lab-runner.sh` (Bash), `frontend/lab-offline.html` (self-contained HTML).
*   **Full Client Support**: Sing-box, Clash, Surge, Loon, Quantumult X, Shadowrocket, SIP008, Base64, plain text.
*   **800+ Tests**: Unit, E2E, fuzz testing with >96% coverage on critical paths.

ConfigStream is a demonstration of how powerful software can be built without a budget, relying on architectural ingenuity rather than capital.

## Related Documentation

*   **[Architecture Deep Dive](02-architecture.md)** — How the pipeline, hybrid engine, and intelligence layer work together.
*   **[Protocols & Parsing](03-protocols.md)** — The 26+ protocols listed above, explained in depth.
*   **[Getting Started](getting_started.md)** — Clone, install, and run your first pipeline in 5 minutes.
*   **[Networking Terms](../encyclopedia/glossary/networking_terms.md)** — ISP, TCP/UDP, TLS, SNI, DPI, QUIC — the building blocks referenced throughout this wiki.
*   **[Firewalls & Honeypots](../encyclopedia/security/firewall_honeypot.md)** — The adversaries ConfigStream is designed to defeat.
