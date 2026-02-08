# ConfigStream Wiki

Welcome to the **ConfigStream** documentation. ConfigStream is an automated, high-performance VPN configuration aggregator and anti-censorship platform designed to provide reliable, free access to the open internet.

## Core Concepts

*   **Zero Budget Architecture:** The system runs entirely on free, resilient cloud infrastructure (GitHub Actions, Pages, Cloudflare), ensuring long-term sustainability and censorship resistance. No paid APIs, no server bills, no identity trail.
*   **Hybrid Engine:** We combine the flexibility of **Python** for data processing and intelligence with the raw performance of **Go** for massive-scale network testing. The pipeline processes thousands of proxies in minutes.
*   **Multi-Strategy Circumvention:** WARP tunnels are just one tool. ConfigStream supports **proxy cascading** (chaining multiple proxies), **intranet relay discovery** (finding LAN hosts with internet access), **TLS fragmentation**, **CDN Worker relays**, and **domain fronting** — adapting to whatever works on your network.
*   **Smart Routing ("The Sniper"):** Configurations are optimized with geographic intelligence, protocol scoring, and censorship-awareness to route traffic through the fastest, stealthiest path available.
*   **Proxy Washing & Shielding:** Blocked IPs are automatically "washed" through Cloudflare WARP to restore connectivity. "Shielding" inverts the topology — wrapping your proxy *inside* a WARP tunnel so your ISP never sees the proxy IP.

## Getting Started

### For End Users
1.  **Download:** Visit the [Home Page](../index.html) to get the latest subscription links.
2.  **Import:** Use a compatible client like **V2RayNG**, **Hiddify**, **Shadowrocket**, **Streisand**, or **Sing-box**.
3.  **Connect:** Select a proxy and connect. Use the "Auto" group for automatic best-node selection.

### For Users Behind Heavy Censorship
1.  **Use the Lab:** Visit the [Chain Laboratory](../lab.html) to build a custom multi-layer chain.
2.  **Run the Scanner:** Download `lab-scanner.py` and run `python lab-scanner.py --auto-chain` to automatically discover the best path (tries 6 strategies).
3.  **Try Pre-Tested Proxies:** The Lab page offers working proxies from ConfigStream's pipeline output — use them directly or as building blocks in your chain.

### For Developers
1.  Fork the repository and run `pytest` to verify the test suite (800+ tests).
2.  Read the [Architecture](Architecture_v2.md) doc for a deep dive.
3.  See [Contributing](09-contributing.md) for the development workflow.

## Documentation Index

### Project Documentation
*   **[Introduction](01-introduction.md):** Philosophy, design principles, and the Zero Budget manifesto.
*   **[Architecture](Architecture_v2.md):** Deep dive into the streaming pipeline, producer-consumer model, and intelligence layers.
*   **[Protocols](03-protocols.md):** Parsing logic, validation rules, and client compatibility for 26+ protocols.
*   **[Engineering](04-engineering.md):** Concurrency patterns, async I/O, and performance optimization.
*   **[DevOps](05-devops.md):** CI/CD pipeline, GitHub Actions matrix strategy, and deployment.
*   **[Frontend](06-frontend.md):** PWA architecture, WASM testing, virtual scrolling, and the Chain Laboratory.
*   **[Security](07-security.md):** Blocklists, honeypot detection, log sanitization, and threat model.
*   **[API Reference](08-api-reference.md):** Data structures, output formats, and endpoint specifications.
*   **[Contributing](09-contributing.md):** How developers can help improve the project.
*   **[Troubleshooting](10-troubleshooting.md):** Solutions for common connection issues and client-specific guides.

### Encyclopedia (Deep Knowledge)
*   **[Networking Terms](../encyclopedia/glossary/networking_terms.md):** ISP, routing, TCP/UDP, TLS, SNI, DPI, and obfuscation techniques.
*   **[Security Concepts](../encyclopedia/glossary/security_concepts.md):** Steganography, honeypots, active probing, traffic analysis, and circuit breakers.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md):** How Cloudflare WARP works, clean IP scanning, shielding, and WARP chains.
*   **[Network Topology](../encyclopedia/networking/topology.md):** ASNs, peering, proxy chaining strategies, and intranet relay patterns.
*   **[Trojan Protocol](../encyclopedia/protocols/trojan.md):** How Trojan mimics HTTPS, fallback mechanisms, and detection resistance.
*   **[Firewalls & Honeypots](../encyclopedia/security/firewall_honeypot.md):** GFW techniques, Iran/Russia-specific blocking, and ConfigStream's defenses.
*   **[Sing-box Configuration](../encyclopedia/tools/singbox_configuration_guide.md):** Inbounds, outbounds, routing rules, DNS, and chain configuration examples.

### Feature Documentation
*   **[Censorship Evasion](../../CENSORSHIP_EVASION.md):** DNS hardening, shielding, TLS fingerprinting, fragmentation, multiplexing, BYOW.
*   **[Evasion User Guide](../../USER_GUIDE_EVASION.md):** How to select evasion modes (Standard, Stealth, Aggressive) and DNS profiles.
*   **[Smart Chains](../../SMART_CHAINS_ENHANCEMENT.md):** 9 chain types, multi-criteria relay scoring, censorship-aware routing.
*   **[Output Formats](../../OUTPUT_VARIATIONS.md):** All subscription formats (Sing-box, Clash, Surge, Loon, QX, SIP008, Base64).

## Legal & Security

These configurations are aggregated from public sources. While we perform rigorous automated security checks (filtering malware, honeypots, and invalid certs), usage is at your own risk. We recommend avoiding sensitive transactions (banking) over public proxies. All proxy testing is passive — we never port-scan or probe infrastructure that hasn't been publicly shared.
