# ConfigStream Roadmap

_Last updated: 2026-02-08_

This roadmap tracks the evolution of ConfigStream towards a fully autonomous, resilient anti-censorship platform.

---

## 1. Completed Items (v2.3.0) ✅

### Backend Resilience
- **Smart Chains**: Implemented multi-hop routing (Entry -> Relay -> Exit) for censorship bypass.
- **Vwarp Revival**: Integrated Vwarp to "wash" dirty IPs and revive dead proxies.
- **Active Scanning**: Added `dnsscanner_tui.py` for active endpoint discovery.
- **Rate Limiting**: Protected API endpoints against abuse.
- **Type Safety**: Achieved 100% MyPy compliance in core modules.
- **Censorship Check**: Integrated active checks for sensitive site reachability.
- **Deprecation Cleanup**: Removed legacy tools and consolidated validation logic.

### Frontend & UX
- **Asset Minification**: Automated JS/CSS minification in CI pipeline.
- **Vwarp Statistics**: Added visibility into revival rates and chain performance.
- **Responsive Design**: Enhanced mobile experience for the dashboard.

### Testing & Quality
- **Test Coverage**: Expanded unit tests to >96% coverage for critical paths.
- **Go Tester Refactor**: Rewrote WASM integration for better stability.
- **SlowAPI Fixes**: Resolved conflicts between rate limiting and test clients.

---

## 1b. Completed Items (v2.5.0) ✅

### Laboratory Page
- **Chain Builder**: 5-step walkthrough with network diagnosis, clean IP discovery, multi-strategy chain building, live testing, and export.
- **5 Chain Strategies**: WARP, Double WARP, TLS Fragment, CDN Worker, Custom JSON.
- **8 Export Formats**: Sing-Box JSON, Clash YAML, Xray JSON, Nekobox Link, URI, QR, Python script, Bash script.
- **Advanced Evasion**: uTLS fingerprint, ALPN, multiplex (h2mux/smux/yamux), padding.
- **Layer 1 Support**: Users with local proxies (Psiphon, Lantern, V2RayN) can stack them as the base of the chain.
- **Network Diagnosis**: Browser-based connectivity tests with tailored strategy advice.

### Offline Tools
- **`tools/lab-scanner.py`**: Zero-dependency Python tool — network diagnosis, clean IP scan, proxy discovery, DNS probe, interactive chain builder.
- **`tools/lab-runner.sh`**: Bash chain runner — auto-installs sing-box, tests chains, scans IPs through proxies.
- **`frontend/lab-offline.html`**: Self-contained offline Lab page — full multi-layer chain builder in a single HTML file.

### Code Quality (v2.5.0)
- **800 tests passing**, 0 failures, 3 skipped.
- **flake8**: 0 errors across 135 source files.
- **black**: 100% formatted.
- Shared utility consolidation (`utils/net.py`), dead code removal, SHA256 hashing fix.

---

## 2. In Progress 🚧

### 2.1 Advanced Evasion
- **Goal**: Implement passive honeypot heuristics.
- **Status**: Research phase. Passive headers inspection prototypes exist.

### 2.2 Operational Observability
- **Goal**: Add webhook notifications for pipeline failures.
- **Status**: Planned.

---

## 3. Future Directions 🔮

### 3.1 Decentralized Distribution
- **Concept**: Publish subscriptions to IPFS or other decentralized storage to avoid GitHub Pages censorship.

### 3.2 AI-Driven Routing
- **Concept**: Use historical latency data to predict best routes dynamically.

---

## 4. Maintenance
- Regular blocklist updates.
- Dependency security patches (via Pip Audit).
- Source list curation.
