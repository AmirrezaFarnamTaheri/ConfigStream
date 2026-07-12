# ConfigStream

[![Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml)
[![CI](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml)
[![Pages Deploy & Smoke Test](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml)

ConfigStream is a sovereignty-grade, zero-budget anti-censorship platform. It continuously aggregates, validates, and distributes resilient proxy configurations under hostile network conditions.

> **Production status:** ConfigStream is **not production-ready** while the machine-verifiable release gate remains blocked. Older production-ready claims are superseded by [`STATUS.md`](STATUS.md) and [`docs/readiness.json`](docs/readiness.json), which track exact-commit CI, artifact, provenance, deployment, and live-smoke evidence. Historical source-of-truth ledgers were absorbed into the master report and removed from active repository documentation.

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Docker** (Recommended for production)
- **Node.js 20+** (Optional, for frontend development)
- **Go 1.21+** (Optional, for high-performance tester builds)

### 🚀 Quick Start (Docker)
```bash
docker compose up --build
```
Access the dashboard at `http://localhost:8000`.

### 🐍 Local Pipeline (Development)
```bash
# Install dependencies
pip install -e ".[dev]"

# Run the aggregation pipeline
configstream merge --sources sources/batch_1.txt --output output/

# Run tests
pytest
```

### 🛠 CLI Tools
- **WARP Configs**: `configstream generate-warp --count 3`
- **DB Update**: `configstream update-databases`
- **Backups**: `configstream backup`

## Architecture Overview
ConfigStream uses a streaming producer-consumer pipeline.

1. Source acquisition
   Fetch remote URLs or local files with adaptive timeouts and circuit breakers. Decode safely and enqueue raw content.
2. Parsing and normalization
   Extract valid config lines from untrusted inputs. Normalize protocol aliases and enforce mandatory fields.
3. Validation and security
   Drop malformed or unsafe configs. Sanitize logs and enforce blocklists.
4. Testing and scoring
   Test proxies with the Go sidecar or Python fallback. Rank proxies by latency and reliability.
5. Washing and smart chains
   Wrap failed proxies with WARP or Vwarp to attempt revival. Generate topology-aware chains for resilient routing.
6. Output generation
   Export multiple formats with metadata and stats. Split outputs by format and category.
7. Publish and cache
   Write outputs atomically and publish via GitHub Pages.

See `docs/wiki/project/02-architecture.md` for the full pipeline design and data flow.

## Operational Governance
- Unified source of truth, integrated roadmap history, release-hardening notes, and historical finalization/closure evidence: `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`
- Current remediation checkpoint: `STATUS.md`
- Chronological implementation history: `CHANGELOG.md`
- Technical debt registry: `docs/DEBT_MATRIX.md`

## Evasion Features
ConfigStream includes advanced censorship evasion capabilities:

- **TLS Fingerprint Rotation**: Mimics browser TLS handshakes (Chrome, Firefox, Safari, iOS)
- **TLS Fragmentation**: Disabled in current sing-box outputs; retained only as historical documentation and future research context.
- **Multiplexing with Padding**: HTTP/2 multiplexing with random padding to hide traffic patterns
- **ALPN Rotation**: Varies protocol negotiation to prevent fingerprinting
- **DNS Hardening**: DoH/DoT/DoQ resolvers with prefer-IP strategy
- **Shielding (Copper to Gold)**: Wraps blocked proxies in WARP tunnels
- **Revival**: Resurrects failed proxies using WARP or Vwarp chains
- **BYOW (Bring Your Own Worker)**: Users can deploy their own Cloudflare Worker bridge to avoid shared quota pressure and improve availability without adding project-operated infrastructure.

See `docs/CENSORSHIP_EVASION.md` for technical details, evasion modes, DNS profiles, and user instructions.

## Protocols and Formats
Supported protocols include VLESS, VMess, Trojan, Shadowsocks, SSR, Hysteria, Hysteria2, TUIC, WireGuard, OpenVPN, HTTP, SOCKS, SSH, Xray, Snell, Brook, and Juicity. Parsing is resilient against malformed inputs and includes credential recovery for common edge cases.

Export formats include:
- Sing-box configs
- Clash YAML
- Base64 subscriptions
- Native client packs (OpenVPN and WireGuard)
- Structured JSON datasets for analytics and tooling

## Testing and Ranking
ConfigStream validates reachability and quality with a dual engine and ranks proxies using latency and reliability signals.
- Go sidecar tester for high-concurrency checks
- Python fallback tester when the binary is unavailable
- Cache-aware retesting to avoid redundant checks
- Evasion-aware testing to identify proxies requiring advanced features

Browser WASM checks are deliberately weaker than sidecar testing. They provide
browser-limited reachability for compatible WebSocket endpoints and local
integrity signals only; browsers cannot perform native proxy handshakes or raw
TCP/UDP testing from WASM.

## Smart Chains Explained
Smart chains are multi-hop routing paths assembled automatically to improve resilience and bypass DPI or hostile networks. A chain is built from multiple outbounds (for example: entry -> relay -> exit), and the system selects relays using latency, reliability, and geography signals to reduce failure rates and improve stability.

Key points:
- Built only from proxies that pass validation and testing
- Prioritizes diverse routes to avoid single points of failure
- Works alongside WARP or Vwarp washing
- Exported in singbox-chains.json and tracked in metadata

## Terminology
- Native proxies: validated and tested direct proxies from sources
- Washed proxies: proxies wrapped through WARP or Vwarp tunnels
- Revived proxies: previously failing proxies that became usable after washing
- Smart chains: multi-hop paths built from tested proxies to improve resilience

## Outputs (Updated Every 4 Hours)

`proxies.json` is always a JSON array. Aggregate statistics, freshness, provenance, and release identity metadata lives in `metadata.json`.

The frontend reads `metadata.json` to determine whether its displayed data is stale. Frontend shows stale data only when the metadata freshness contract is exceeded.

For production-compatible local runs, keep `USE_VWARP_TUNNEL=true` and satisfy every required security setting documented in `docs/wiki/project/Configuration.md`.
