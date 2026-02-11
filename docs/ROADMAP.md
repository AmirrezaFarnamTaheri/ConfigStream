# ConfigStream Roadmap

_Last updated: 2026-02-09_

This roadmap tracks the current state and future direction of ConfigStream.

---

## Current State (v3.0)

### Pipeline & Backend
- **26+ Protocols**: VLESS, VMess, Trojan, Shadowsocks, SS2022, Hysteria2, TUIC, WireGuard, SSH, SOCKS5, HTTP, OpenVPN, SSR, Juicity, and more.
- **14-Shard Parallel Pipeline**: GitHub Actions matrix strategy with merge job.
- **Hybrid Python + Go Engine**: Python orchestration, Go sidecar for mass testing.
- **9 Smart Chain Types**: Intranet, Washed, IPv6, Streaming, Censorship-Resistant, Low-Latency, High-Anonymity, Load-Balanced, Experimental.
- **4 Evasion Techniques**: uTLS fingerprinting, TLS fragmentation, multiplexing with padding, ALPN rotation.
- **3 DNS Profiles**: Standard, DNS-Safe (IP-only), DNS-Hardened (DoH/DoT/DoQ).
- **Proxy Washing & Shielding**: WARP and Vwarp revival, Copper-to-Gold shielding.
- **Intelligence Layer**: AdaptiveTimeout, CircuitBreaker, Source Quality Tracker, Anomaly Detector.
- **60+ Output Files**: Sing-box, Clash, Surge, Loon, Quantumult X, Shadowrocket, SIP008, Base64, plaintext — each in Standard, DNS-Safe, and DNS-Hardened variants.

### Frontend & UX
- **Progressive Web App**: Vanilla JS, no build step, Service Worker caching.
- **Chain Laboratory**: 5-step browser-based chain builder with 6 strategies and 8 export formats.
- **Offline Tools**: `lab-scanner.py` (Python), `lab-runner.sh` (Bash), `lab-offline.html` (self-contained HTML).
- **Analytics Dashboard**: Globe visualization, protocol/country/latency charts, evasion trend time-series.
- **Internationalization**: i18n support with language switcher.

### Testing & Quality
- **800+ Tests**: Unit, E2E (Playwright), fuzz testing.
- **>96% Coverage** on critical paths (parsers, testers, generators).
- **0 flake8 errors**, 100% black-formatted, MyPy-compliant core.

---

## In Progress 🚧

### Passive Honeypot Heuristics
- **Goal**: Detect honeypot proxies via passive header inspection (no active probing).
- **Status**: Research phase. Prototype inspects HTTP response headers for known honeypot signatures.

### Operational Observability
- **Goal**: Webhook notifications for pipeline failures (Telegram, Discord).
- **Status**: Telegram upload exists; expanding to failure alerts.

---

## Future Directions 🔮

### Decentralized Distribution
Publish subscriptions to IPFS/IPNS for censorship-resistant fallback. The `failover.js` frontend module already detects GitHub Pages outages — IPFS gateway redirect is the next step.

### AI-Driven Routing
Use historical latency and success-rate data to predict optimal relay selection dynamically, replacing static protocol scoring with learned weights.

### Adaptive Chain Length
Adjust the number of hops based on real-time threat level detection (e.g., 2-hop during normal conditions, 3-hop during active censorship events).

### Bandwidth Estimation
Prefer high-bandwidth relays for streaming chains by measuring throughput during testing (not just latency).

---

## Maintenance
- Regular blocklist updates (FireHol, VirusTotal).
- Dependency security patches (Pip Audit, Dependabot).
- Source list curation and deduplication.
- GeoIP database refresh (MaxMind, SagerNet).
