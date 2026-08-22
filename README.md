# ConfigStream

[![Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml)
[![CI](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml)
[![Pages Deploy & Smoke Test](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml)

**[English](README.md) • [فارسی](README_FA.md) • [简体中文](README_ZH.md) • [Русский](README_RU.md)**

ConfigStream is a sovereignty-grade, zero-budget anti-censorship platform. It continuously aggregates, validates, and distributes resilient proxy configurations under hostile network conditions.

> **Release status:** v3.2.0 is a conditional release candidate, not a verified production release. `docs/readiness.json` is the machine-readable authority and `STATUS.md` is generated from it. Production readiness requires passing exact-head CI, a sealed pipeline artifact, historical secret review, and a live GitHub Pages digest/smoke check for the same commit.

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Docker** (Recommended for production)
- **Node.js 24+** (Optional, for frontend development)
- **Go 1.24+** (Optional, for high-performance tester builds)

### 🚀 Quick Start (Docker)
```bash
docker compose up --build
```
Access the dashboard at `http://localhost:8000`.

### 🐍 Local Pipeline (Development)
```bash
# Install pinned dependencies and then the editable project
pip install -r requirements-dev.txt
pip install -e . --no-deps

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
- Canonical release checkpoint: `docs/readiness.json`
- Generated human-readable status: `STATUS.md`
- Chronological implementation history: `CHANGELOG.md`
- Technical debt registry: `docs/debt_matrix.json` and `docs/DEBT_MATRIX.md`
- Module boundaries and ownership: `docs/module_ownership.json` and `docs/MODULE_OWNERSHIP.md`

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

## Outputs and Freshness
GitHub Pages is the primary publication target. The intended schedule is every four hours, but users must treat `health.json`, `metadata.json`, and `artifact_manifest.json` as the authority for current health, freshness, source commit, and artifact identity. The frontend disables copy/download controls when those checks fail.

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

Stable capability claims are tracked in `docs/capability_registry.json`; core/client compatibility truth is tracked in `docs/core_compatibility_report.json`. CI validates both so Sing-box, Clash, and future Xray claims cannot drift from implemented outputs.

<!-- OUTPUT_MATRIX:START -->
<!-- Generated by scripts/generate_output_docs.py; edit docs/output_matrix.json instead. -->

| Output | Family | Format | Non-empty | Validation | Notes |
| --- | --- | --- | --- | --- | --- |
| `chains-dns-hardened.json` | chains | json | yes | json, references | Compatibility alias for singbox-chains-dns-hardened.json. |
| `chains-dns-safe.json` | chains | json | yes | json, references | Compatibility alias for singbox-chains-dns-safe.json. |
| `chains.json` | chains | json | yes | json, references | Compatibility alias for singbox-chains.json; JSON syntax is validated. |
| `singbox-chains-dns-hardened.json` | chains | json | yes | json, references | DNS-hardened Sing-box chain outbounds; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-chains-dns-safe.json` | chains | json | yes | json, references | DNS-safe Sing-box chain outbounds; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-chains.json` | chains | json | yes | json, references | Sing-box chain outbounds; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `chosen/base64-dns-hardened.txt` | chosen | base64 | no | presence | Chosen DNS-hardened base64 output. |
| `chosen/base64-dns-safe.txt` | chosen | base64 | no | presence | Chosen DNS-safe base64 output. |
| `chosen/base64.txt` | chosen | base64 | no | presence | Chosen top-N base64 output; empty is valid when chosen lines are unavailable. |
| `chosen/proxies.txt` | chosen | text | no | presence | Chosen top-N newline-delimited share-link subscription; empty is valid when no proxies are selected. |
| `chosen/clash.yaml` | clash | yaml | yes | yaml, references | Chosen top-N complete Mihomo/Clash configuration; repaired and validated with the same contract as root Clash artifacts. |
| `clash-dns-hardened.yaml` | clash | yaml | yes | yaml, references | Clash DNS-hardened configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `clash-dns-safe.yaml` | clash | yaml | yes | yaml, references | Clash DNS-safe configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `clash.yaml` | clash | yaml | yes | yaml, references | Clash universal configuration; YAML syntax, proxy/group list shape, unique names, group references, and rule policy references are validated. |
| `base64-dns-hardened.txt` | dns-hardened | base64 | no | presence | DNS-hardened subset; empty is valid under degraded data. |
| `proxies-dns-hardened.txt` | dns-hardened | text | no | presence | DNS-hardened URI subscription lines. |
| `base64-dns-safe.txt` | dns-safe | base64 | no | presence | DNS-safe subset; empty is valid under degraded data. |
| `proxies-dns-safe.txt` | dns-safe | text | no | presence | DNS-safe URI subscription lines. |
| `chosen/singbox.json` | singbox | json | yes | json, references | Chosen top-N complete sing-box configuration; finalized and validated with the same contract as root sing-box artifacts. |
| `countries/*.json` | singbox | json | no | json, references | Country-specific complete sing-box configurations; excludes the sibling *.list.json ConfigStream API arrays. |
| `protocols/*.json` | singbox | json | no | json, references | Protocol-specific complete sing-box configurations; excludes the sibling *.list.json ConfigStream API arrays. |
| `singbox-dns-hardened.json` | singbox | json | yes | json, references | Sing-box DNS-hardened configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-dns-safe.json` | singbox | json | yes | json, references | Sing-box DNS-safe configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox.json` | singbox | json | yes | json, references | Sing-box universal configuration; JSON syntax, outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn-dns-hardened.json` | singbox-vpn | json | yes | json, references | VPN-mode DNS-hardened Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn-dns-safe.json` | singbox-vpn | json | yes | json, references | VPN-mode DNS-safe Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `singbox-vpn.json` | singbox-vpn | json | yes | json, references | VPN-mode Sing-box configuration; outbound list shape, unique tags, selector/urltest references, detours, route outbounds, and DNS detours are validated. |
| `base64.txt` | universal | base64 | no | presence | May be empty when no usable subscription lines exist. |
| `proxies.txt` | universal | text | no | presence | URI subscription lines. |
| `xray.json` | xray | json | yes | json, references | Xray full configuration with modern VMess/VLESS settings, structural reference validation, and pinned native release checks. |
| `side_products-dns-hardened.zip` | side-products | zip | yes | zip, zip members | DNS-hardened side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `side_products-dns-safe.zip` | side-products | zip | yes | zip, zip members | DNS-safe side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `side_products.zip` | side-products | zip | yes | zip, zip members | Side-product bundle; ZIP integrity, safe member paths, required proxies.txt, optional OpenVPN/WireGuard member patterns, and deploy-secret markers are validated. |
| `artifact_manifest.json` | control | json | yes | schema, json | Generated file inventory with size and sha256 checks. |
| `health.json` | control | json | yes | schema, json | Freshness and degraded-state control artifact. |
| `metadata.json` | control | json | yes | schema, json | Canonical run metadata validated against metadata.schema.json. |
| `pipeline_events.jsonl` | control | jsonl | yes | jsonl | Sanitized append-only pipeline event telemetry; JSONL structure and secret-marker absence are validated. |
| `api/proxies` | api-alias | json | yes | schema, json | API alias that must exactly match the proxies.json ConfigStream record array; it is not a native client configuration. |
| `api/stats` | api-alias | json | yes | schema, json | API alias that must match metadata.json. |
| `countries/*.list.json` | categorized-api | json | no | schema, json | Country-specific ConfigStream proxy record array validated by proxy-list.schema.json. This is API/filtering data, not a native client configuration. |
| `protocols/*.list.json` | categorized-api | json | no | schema, json | Protocol-specific ConfigStream proxy record array validated by proxy-list.schema.json. This is API/filtering data, not a native client configuration. |
| `proxies.json` | universal | json | yes | schema, json | Canonical ConfigStream API dataset validated by proxy-list.schema.json: a JSON array whose items follow proxy.schema.json, not a directly importable sing-box, Xray, or Mihomo configuration. |
| `data/active_proxy_trend.json` | analytics | json | yes | json | Active proxy trend data. |
| `data/clean_ips.json` | analytics | json | yes | json | Clean IP data consumed by frontend tools. |
| `data/evasion_trend.json` | analytics | json | yes | json | Evasion trend data. |
| `data/proxy_history_viz.json` | analytics | json | yes | json | Proxy history visualization data. |
| `assets/js/runtime-config.js` | frontend | text | yes | presence | Generated deploy-time frontend runtime config carrying public verification and stego keys. |
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

## Deployment
ConfigStream uses GitHub Actions to schedule the pipeline and GitHub Pages to host verified outputs. A schedule trigger does not prove freshness; publication and the live smoke gate must both pass. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for setup.

## Generated operational evidence

- Runtime/toolchain source of truth: [`config/runtime-versions.json`](config/runtime-versions.json)
- Environment catalog: [`docs/generated/environment-variables.md`](docs/generated/environment-variables.md)
- CycloneDX SBOM: [`docs/generated/sbom.cdx.json`](docs/generated/sbom.cdx.json)
- Dependency license evidence: [`docs/generated/dependency-licenses.md`](docs/generated/dependency-licenses.md)
- Unified verification: `python scripts/verify_repository.py --profile release`

The license report only records declarations present in checked-in manifests and lock files. `unknown` means the license still requires external resolution; it is not treated as evidence of a license.

## Security
Security is mandatory. Logs are sanitized, inputs validated, and active scanning disabled by default. See [SECURITY.md](SECURITY.md) for details.

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

Offline diagnostic tools (local, opt-in, user-responsible):
> **Security Contract:** ConfigStream pipeline automation keeps active scanning out of CI/default runs. These scanner tools are strictly local, opt-in diagnostics requiring explicit user execution. They are never run automatically in CI.

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

## Maturity tiers

ConfigStream labels runtime surfaces by operational maturity. The canonical,
machine-readable inventory is [`docs/maturity_tiers.json`](docs/maturity_tiers.json).

| Tier | Meaning | Current surfaces |
|---|---|---|
| Stable | Required release path with blocking verification | Python core, native Go tester, GitHub Pages publication |
| Beta | Supported demonstration surface without production durability guarantees | HTTP demo server and Render deployment |
| Experimental | Optional research path; never substitutes for native validation | Browser reachability WASM and Rust Shadowsocks checker |

Browser WASM results are reachability signals only. They cannot prove native
TCP/UDP proxy behavior and are never promoted into the stable release gate.