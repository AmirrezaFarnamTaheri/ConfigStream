# ConfigStream Roadmap

_Last updated: 2026-02-07_

This roadmap tracks the evolution of ConfigStream towards a fully autonomous, resilient anti-censorship platform.

---

## 1. Completed Items (v2.3.0) ✅

### Backend Resilience
- **Smart Chains**: Implemented multi-hop routing (Entry -> Relay -> Exit) for censorship bypass.
- **Vwarp Revival**: Integrated Vwarp to "wash" dirty IPs and revive dead proxies.
- **Active Scanning**: Added `dnsscanner_tui.py` for active endpoint discovery.
- **Rate Limiting**: Protected API endpoints against abuse.
- **Type Safety**: Achieved 100% MyPy compliance in core modules.

### Frontend & UX
- **Asset Minification**: Automated JS/CSS minification in CI pipeline.
- **Vwarp Statistics**: Added visibility into revival rates and chain performance.
- **Responsive Design**: Enhanced mobile experience for the dashboard.

### Testing & Quality
- **Test Coverage**: Expanded unit tests to >96% coverage for critical paths.
- **Go Tester Refactor**: Rewrote WASM integration for better stability.
- **SlowAPI Fixes**: Resolved conflicts between rate limiting and test clients.

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
