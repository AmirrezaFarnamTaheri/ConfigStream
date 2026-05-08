# ConfigStream

ConfigStream is a sovereignty-grade, zero-budget anti-censorship platform. It continuously aggregates, validates, and distributes resilient proxy configurations under hostile network conditions.

> **Remediation status:** ConfigStream is currently being brought back into a verified production-ready state. The active source of truth is `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`; older production-ready claims are superseded until the P0/P1 audit items are closed.

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
Runs on a strict zero-budget design: GitHub Actions executes the pipeline every 4 hours, and GitHub Pages hosts the outputs. The pipeline is stateless between runs, uses adaptive timeouts, and prioritizes safe failure modes under hostile network conditions.

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
- Living roadmap process: `docs/ROADMAP_UPDATE_PROCESS.md`
- Release hardening and provenance controls: `docs/RELEASE_HARDENING_2026.md`
- Finalization status and phase matrix: `docs/FINALIZATION_REPORT_2026.md`
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
- **BYOW (Bring Your Own Worker)**: Users deploy their own Cloudflare Workers for unlimited, private, unblockable connections

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
All outputs are served from GitHub Pages in production. Each run writes outputs atomically and includes a `generated_at` timestamp in metadata to make freshness explicit.

Primary outputs:
- singbox.json: smart routing profile
- singbox-vpn.json: TUN or VPN profile
- clash.yaml: Clash-compatible
- base64.txt: universal subscription
- chosen/base64.txt: curated low-latency subset

Derived outputs:
- singbox-chains.json: washed + revived + smart + shielded chains
- revived.json: revived-only dataset (proxies.json schema)
- proxies.json: full proxy dataset as a JSON array; metadata lives in metadata.json
- side_products.zip: native configs pack (OpenVPN .ovpn, WireGuard .conf, raw URIs)
- protocols/*.txt: per-protocol URI subscription files (e.g. vless.txt, trojan.txt)

Output notes:
- Base64 and plaintext subscriptions include both native and revived proxy URIs for maximum coverage.
- JSON datasets expose metadata and stats used by the frontend and external tooling.
- DNS-safe variants are available for all major outputs with the `-dns-safe` suffix (IP-only / pre-resolved endpoints). This is a strict subset — proxies that fail resolution are dropped.
- DNS-hardened variants are available for all major outputs with the `-dns-hardened` suffix. They embed DoH/DoT/DoQ resolvers and prefer IP when available while keeping unresolved entries intact.

## Compatibility Matrix
Use the output that matches your client or use case. This table is generated from `docs/output_matrix.json`, which is also checked by CI.

<!-- OUTPUT_MATRIX:START -->
<!-- Generated by scripts/generate_output_docs.py; edit docs/output_matrix.json instead. -->

| Output | Family | Format | Non-empty | Validation | Notes |
| --- | --- | --- | --- | --- | --- |
| `chains-dns-hardened.json` | chains | json | yes | json | DNS-hardened public chain metadata. |
| `chains-dns-safe.json` | chains | json | yes | json | DNS-safe public chain metadata. |
| `chains.json` | chains | json | yes | json | Public chain metadata; JSON syntax is validated. |
| `singbox-chains-dns-hardened.json` | chains | json | yes | json, references | DNS-hardened Sing-box chain outbounds; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-chains-dns-safe.json` | chains | json | yes | json, references | DNS-safe Sing-box chain outbounds; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-chains.json` | chains | json | yes | json, references | Sing-box chain outbounds; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `chosen/base64-dns-hardened.txt` | chosen | base64 | no | presence | Chosen DNS-hardened base64 output. |
| `chosen/base64-dns-safe.txt` | chosen | base64 | no | presence | Chosen DNS-safe base64 output. |
| `chosen/base64.txt` | chosen | base64 | no | presence | Chosen top-N base64 output; empty is valid when chosen lines are unavailable. |
| `clash-dns-hardened.yaml` | clash | yaml | yes | yaml, references | Clash DNS-hardened configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `clash-dns-safe.yaml` | clash | yaml | yes | yaml, references | Clash DNS-safe configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `clash.yaml` | clash | yaml | yes | yaml, references | Clash universal configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `base64-dns-hardened.txt` | dns-hardened | base64 | no | presence | DNS-hardened subset; empty is valid under degraded data. |
| `proxies-dns-hardened.txt` | dns-hardened | text | no | presence | DNS-hardened URI subscription lines. |
| `base64-dns-safe.txt` | dns-safe | base64 | no | presence | DNS-safe subset; empty is valid under degraded data. |
| `proxies-dns-safe.txt` | dns-safe | text | no | presence | DNS-safe URI subscription lines. |
| `singbox-dns-hardened.json` | singbox | json | yes | json, references | Sing-box DNS-hardened configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-dns-safe.json` | singbox | json | yes | json, references | Sing-box DNS-safe configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox.json` | singbox | json | yes | json, references | Sing-box universal configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn-dns-hardened.json` | singbox-vpn | json | yes | json, references | VPN-mode DNS-hardened Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn-dns-safe.json` | singbox-vpn | json | yes | json, references | VPN-mode DNS-safe Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn.json` | singbox-vpn | json | yes | json, references | VPN-mode Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `base64.txt` | universal | base64 | no | presence | May be empty when no usable subscription lines exist. |
| `proxies.json` | universal | json | yes | schema, json | Canonical public proxy JSON list. |
| `proxies.txt` | universal | text | no | presence | URI subscription lines. |
| `side_products-dns-hardened.zip` | side-products | zip | yes | zip, zip members | DNS-hardened side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `side_products-dns-safe.zip` | side-products | zip | yes | zip, zip members | DNS-safe side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `side_products.zip` | side-products | zip | yes | zip, zip members | Side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `artifact_manifest.json` | control | json | yes | schema, json | Generated file inventory with size and sha256 checks. |
| `health.json` | control | json | yes | schema, json | Freshness and degraded-state control artifact. |
| `metadata.json` | control | json | yes | schema, json | Canonical run metadata validated against metadata.schema.json. |
| `api/proxies` | api-alias | json | yes | schema, json | API alias that must match proxies.json. |
| `api/stats` | api-alias | json | yes | schema, json | API alias that must match metadata.json. |
| `data/active_proxy_trend.json` | analytics | json | yes | json | Active proxy trend data. |
| `data/clean_ips.json` | analytics | json | yes | json | Clean IP data consumed by frontend tools. |
| `data/evasion_trend.json` | analytics | json | yes | json | Evasion trend data. |
| `data/proxy_history_viz.json` | analytics | json | yes | json | Proxy history visualization data. |
| `index.html` | frontend | html | yes | presence | Published frontend entry point. |
| `docs/wiki/index.md` | docs | markdown | yes | presence | Published docs entry point. |

<!-- OUTPUT_MATRIX:END -->

DNS-safe variants:
- All primary outputs above have `-dns-safe` equivalents, for example `base64-dns-safe.txt`, `singbox-dns-safe.json`, `clash-dns-safe.yaml`, `shadowrocket-dns-safe.txt`, `proxies-dns-safe.txt`, `chains-dns-safe.json`, and `side_products-dns-safe.zip`.
- These files use IP-literal or pre-resolved endpoints and preserve SNI/Host where possible. They are useful when DNS is blocked or poisoned.
- DNS-safe outputs may be smaller if resolution fails or if a protocol cannot be safely rewritten.

DNS-hardened variants:
- All primary outputs have `-dns-hardened` equivalents: `singbox-dns-hardened.json`, `singbox-vpn-dns-hardened.json`, `clash-dns-hardened.yaml`, `base64-dns-hardened.txt`, `shadowrocket-dns-hardened.txt`, `surge-dns-hardened.conf`, `loon-dns-hardened.conf`, `quantumult-dns-hardened.conf`, `sip008-dns-hardened.json`, `chains-dns-hardened.json`, `side_products-dns-hardened.zip`.
- They keep hostnames but prefer IPs when available, which improves survivability under DNS poisoning without dropping unresolved entries.
- Sing-box and Clash variants embed DoH/DoT/DoQ resolver configs. Adapter variants (Surge, Loon, QX, Shadowrocket) include resolver comments.

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
- https://amirrezafarnamtaheri.github.io/ConfigStream/base64-dns-safe.txt
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox-dns-safe.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/clash-dns-safe.yaml
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox-dns-hardened.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/singbox-vpn-dns-hardened.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/clash-dns-hardened.yaml
- https://amirrezafarnamtaheri.github.io/ConfigStream/proxies-dns-safe.txt
- https://amirrezafarnamtaheri.github.io/ConfigStream/side_products-dns-safe.zip
- https://amirrezafarnamtaheri.github.io/ConfigStream/chains-dns-safe.json
- https://amirrezafarnamtaheri.github.io/ConfigStream/chains-dns-hardened.json

Self-hosting note: replace the base URL with your own GitHub Pages or server domain.

## Data Schema
ConfigStream produces separate canonical JSON artifacts for analytics and tooling:
`proxies.json` is always a JSON array of proxy objects, while `metadata.json`
contains run statistics and frontend analytics fields.

proxies.json (simplified example):
```json
[
  {
    "id": "proxy-uuid",
    "config": "vless://...",
    "protocol": "vless",
    "address": "example.com",
    "port": 443,
    "details": {},
    "country_code": "US",
    "latency": 210,
    "is_working": true,
    "process": "native",
    "tags": ["NATIVE"]
  }
]
```

metadata.json (simplified example):
```json
{
  "schema_version": "3.0.2",
  "generated_at": "2026-05-04T00:00:00Z",
  "total_proxies": 12345,
  "total_working": 4300,
  "revived_warp": 120,
  "revived_vwarp": 80,
  "smart_chain_count": 300,
  "shielded_candidate_count": 50,
  "shielded_verified_count": 0
}
```

revived.json uses the proxy array shape and contains only revived proxies.
singbox-chains.json contains chain-only outbounds for sing-box.

## Prerequisites

Before running the pipeline, ensure you have the following installed if you plan to use specific features:

*   **Python 3.10+**: Required for the core pipeline.
*   **Cloudflare WARP**: Required if `USE_VWARP_TUNNEL=true`. The `vwarp` binary must be available in your PATH or configured via environment variables.
*   **ConfigStream Tester (Go)**: Required for high-performance testing. The binary `configstream-tester` must be available in your PATH or configured via `CONFIGSTREAM_TESTER_BIN`.

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

Named validation profiles:
```bash
python scripts/run_test_profile.py unit
python scripts/run_test_profile.py integration
python scripts/run_test_profile.py frontend-browser
python scripts/run_test_profile.py production-smoke
```

`frontend-browser` requires installed Python Playwright browsers and fails
loudly when `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` is set. For local same-origin
frontend smoke coverage without relying on the Python browser bundle:
```bash
npm run test:frontend:no-network
npm run test:frontend:degraded
```

Frontend build (optional, Vite):
```bash
npm install
npm run build
```

## Environment Variables
Core:
- PYTHONPATH=/path/to/ConfigStream/src

Optional (enhanced features):
- WARP_KEY_POOL=[{"private_key":"...","reserved":[0,0,0],"peer_public_key":"..."}]
- USE_VWARP_TUNNEL=true (default: false)
- MAXMIND_LICENSE_KEY=your-key
- VT_API_KEY=your-virustotal-key
- CANARY_URL=https://example.com/health
- SS_LIB_SHA256=64-character-sha256-of-local-ss-checker-binary

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
- DNS_SAFE_OUTPUTS=true
- DNS_HARDENED_OUTPUTS=true
- DNS_SAFE_RESOLVE_TIMEOUT=4
- DNS_SAFE_RESOLVE_BATCH=500
- DNS_SAFE_RESOLVE_LIMIT=0
- EVASION_MODE=aggressive (options: standard, stealth, aggressive)

Optional Shadowsocks-Rust FFI validation is disabled unless both a local
`bin/ss_checker` library and matching `SS_LIB_SHA256` are configured. Without
that hash, ConfigStream skips the Rust FFI path and continues with the Python
validation path; a mismatched configured hash fails closed.

## Deployment
The reference deployment uses GitHub Actions to run the pipeline every 4 hours and GitHub Pages to host outputs. This keeps infrastructure free and globally accessible.

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
4. Frontend shows stale data: verify metadata timestamps in `metadata.json` and GitHub Pages cache refresh.
5. Local runs differ from CI: align environment variables, Python version, and dependencies.

## Chain Laboratory
The Laboratory page helps users build custom proxy chains step-by-step, even when starting from zero internet access.

Online: https://amirrezafarnamtaheri.github.io/ConfigStream/lab.html

Features:
- Network diagnosis to understand what your connection can reach
- Layer 1 support for local proxies (Psiphon, Lantern, V2RayN)
- 9 chain strategies: WARP, Vwarp MASQUE, Vwarp AtomicNoize, Double WARP, WARP+Psiphon, Relay Chain, TLS Fragment (legacy/manual), CDN Worker, Custom JSON
- Advanced evasion: uTLS fingerprint, ALPN, multiplex, padding
- 8 export formats: Sing-Box JSON, Clash YAML, Xray JSON, Nekobox, URI, offline QR payload, Python script, Bash script
- Full transport support in all exports: WebSocket, gRPC, HTTP/2, httpupgrade, Reality

Offline tools (no internet required):
- `tools/lab-scanner.py`: Python network diagnostic — clean IP scan, proxy discovery, DNS probe, interactive chain builder
- `tools/lab-runner.sh`: Bash chain runner — auto-installs sing-box, tests chains, scans IPs
- `frontend/lab-offline.html`: Self-contained offline chain builder in a single HTML file

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
