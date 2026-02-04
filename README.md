# ConfigStream

ConfigStream is a sovereignty-grade, zero-budget anti-censorship platform. It continuously aggregates, validates, and distributes resilient proxy configurations under hostile network conditions.

## Principles
- Zero budget: free GitHub Actions/Pages, public APIs, and user-provided resources only
- Resilience: fail-open or fail-safe handling for timeouts, blocklists, and unreliable sources
- Security: strict validation and sanitized logging

## What It Does
- Ingests sources (remote URLs or local files) and extracts proxy configs across 20+ protocols
- Tests and ranks proxies using a dual engine (Go sidecar + Python fallback)
- Revives failed proxies by wrapping them in WARP or Vwarp chains when possible
- Builds smart chains for resilient routing
- Publishes multiple subscription formats and a metadata-rich JSON dataset

## Who It Is For
- End users who want stable, frequently updated subscriptions
- Operators who need a free, resilient pipeline with zero paid infrastructure
- Developers who want structured datasets for analytics or custom tooling

## Operating Model
Runs on a strict zero-budget design: GitHub Actions executes the pipeline every 6 hours, and GitHub Pages hosts the outputs. The pipeline is stateless between runs, uses adaptive timeouts, and prioritizes safe failure modes under hostile network conditions.

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

See docs/ARCHITECTURE.md for the full pipeline design and data flow.

## Protocols and Formats
Supported protocols include VLESS, VMess, Trojan, Shadowsocks, SSR, Hysteria, Hysteria2, TUIC, WireGuard, OpenVPN, HTTP, SOCKS, and SSH. Parsing is resilient against malformed inputs and includes credential recovery for common edge cases.

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

## Outputs (Updated Every 6 Hours)
All outputs are served from GitHub Pages in production. Each run writes outputs atomically and includes a `generated_at` timestamp in metadata to make freshness explicit.

Primary outputs:
- singbox.json: smart routing profile
- singbox-vpn.json: TUN or VPN profile
- clash.yaml: Clash-compatible
- base64.txt: universal subscription
- chosen/base64.txt: curated low-latency subset

Derived outputs:
- singbox-chains.json: washed + smart chains only
- revived.json: revived-only dataset (proxies.json schema)
- proxies.json: full dataset with metadata
- side_products.zip: native configs pack (OpenVPN .ovpn, WireGuard .conf, raw URIs)

Output notes:
- Base64 subscriptions contain raw proxy URIs for maximum client compatibility.
- JSON datasets expose metadata and stats used by the frontend and external tooling.

## Compatibility Matrix
Use the output that matches your client or use case. This matrix lists every output and its compatible client family.

| Output | Compatible Clients | Notes |
| --- | --- | --- |
| `singbox.json` | sing-box (desktop, mobile, server) | Smart routing profile |
| `singbox-vpn.json` | sing-box (TUN/VPN mode) | System-wide VPN profile |
| `singbox-chains.json` | sing-box | Washed + smart chains only |
| `clash.yaml` | Clash family (Clash, Meta, Verge, etc.) | Clash-compatible format |
| `base64.txt` | Clients that accept base64/URI subscriptions (e.g., common iOS/macOS clients) | Universal base64 subscription |
| `chosen/base64.txt` | Lightweight clients or quick start setups | Smaller curated list |
| `side_products.zip` | OpenVPN and WireGuard clients | `.ovpn` and `.conf` files |
| `proxies.json` | Developers and tooling | Full dataset with metadata |
| `revived.json` | Developers and tooling | Revived-only subset |

Production subscription links:
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox-vpn.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/clash.yaml
- https://amirrezafarnamtaheri.github.io/ConfigStream/base64.txt
- https://amirrezafarnamtaheri.github.io/ConfigStream/chosen/base64.txt
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox-chains.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/revived.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/proxies.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/side_products.zip

Self-hosting note: replace the base URL with your own GitHub Pages or server domain.

## Data Schema
ConfigStream produces a structured JSON dataset for analytics and tooling.

proxies.json (simplified example):
```json
{
  "metadata": {
    "generated_at": "2026-02-05T00:00:00Z",
    "update_interval_hours": 6,
    "total_proxies": 12345,
    "total_configured_sources": 220,
    "revived_warp": 120,
    "revived_vwarp": 80,
    "smart_chain_count": 300,
    "chain_outbounds_count": 500,
    "country_stats": {
      "US": { "count": 1200, "median_latency_ms": 210 }
    },
    "latency_by_country": {
      "US": { "p50": 210, "p90": 480 }
    },
    "latency_by_protocol": {
      "vless": { "p50": 190, "p90": 420 }
    }
  },
  "proxies": [
    {
      "id": "proxy-uuid",
      "protocol": "vless",
      "address": "example.com",
      "port": 443,
      "country": "US",
      "latency_ms": 210,
      "tags": ["revived-warp"]
    }
  ]
}
```

revived.json uses the same schema and contains only revived proxies.
singbox-chains.json contains chain-only outbounds for sing-box.

## Quickstart

Docker (recommended for production):
```bash
docker compose up --build
```

Local (development):
```bash
pip install -e ".[dev]"
configstream merge --sources sources/batch_1.txt --output output
pytest
```

## Environment Variables
Core:
- PYTHONPATH=/path/to/ConfigStream/src

Optional (enhanced features):
- WARP_KEY_POOL=[{"private_key":"...","reserved":[0,0,0],"peer_public_key":"..."}]
- USE_VWARP_TUNNEL=true
- MAXMIND_LICENSE_KEY=your-key
- VT_API_KEY=your-virustotal-key
- CANARY_URL=https://example.com/health

Optional (Vwarp tuning):
- VWARP_TEST_URL=http://1.1.1.1/cdn-cgi/trace
- VWARP_DNS=1.1.1.1
- VWARP_ENDPOINT=162.159.192.1:2408
- VWARP_CONFIG_PATH=/path/to/vwarp.json
- VWARP_CONFIG_JSON={"version":"1.0","bind":"127.0.0.1:10808"}
- VWARP_FORCE_MASQUE=true

Optional (production hardening):
- ADMIN_API_KEY=your-secret-key
- ALLOWED_ORIGINS=https://yourdomain.com
- STEGO_KEY=your-base64-fernet-key (rotate every 6 hours)

## Deployment
The reference deployment uses GitHub Actions to run the pipeline every 6 hours and GitHub Pages to host outputs. This keeps infrastructure free and globally accessible.

For local deployment, Docker Compose is the simplest path. For CI, see docs/DEPLOYMENT.md.

## Quality Controls
- Adaptive timeouts and circuit breakers to prevent stalls
- Strict validation and blocklist enforcement on untrusted inputs
- Test-result caching to avoid redundant checks
- Atomic output writes to prevent partial datasets

## Security
Security is mandatory, not optional.
- Logs are sanitized and sensitive tokens are masked
- Inputs are validated and blocklisted hosts are filtered
- No active scanning of third-party infrastructure

See SECURITY.md for policies, threat model, and disclosure process.

## Operational FAQ
1. Outputs look empty or very small: check source availability, blocklists, and tester binary presence in logs.
2. Revived counts are zero: ensure `WARP_KEY_POOL` is configured and WARP or Vwarp tooling is available.
3. Vwarp not being used: set `USE_VWARP_TUNNEL=true`, install the binary, and check probe logs.
4. Frontend shows stale data: verify metadata timestamps in `proxies.json` and GitHub Pages cache refresh.
5. Local runs differ from CI: align environment variables, Python version, and dependencies.

## Documentation
- README.md: you are here
- docs/: architecture, deployment, frontend, API reference
- CHANGELOG.md: release notes
- SECURITY.md: security policies and audit process
- STATUS.md: operational posture
- CONTRIBUTING.md: contribution rules
- AGENTS.md: contributor constraints and guardrails

## Contributing
We enforce a strict zero-budget, high-resilience policy. Please read CONTRIBUTING.md and AGENTS.md before making changes.

## License
AGPL-3.0. See LICENSE.

## Links
- Repository: https://github.com/AmirrezaFarnamTaheri/ConfigStream
- Live dashboard: https://amirrezafarnamtaheri.github.io/ConfigStream/
- Issues: https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues
- Discussions: https://github.com/AmirrezaFarnamTaheri/ConfigStream/discussions
