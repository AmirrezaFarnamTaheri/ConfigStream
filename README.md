# ConfigStream

ConfigStream is a sovereignty-grade, zero-budget anti-censorship platform. It continuously aggregates, validates, and distributes resilient proxy configurations under hostile network conditions.

## Principles
- **Zero Budget**: Free GitHub Actions/Pages, public APIs, and user-provided resources only.
- **Resilience**: Fail-open or fail-safe handling for timeouts, blocklists, and unreliable sources.
- **Security**: Strict validation, sanitized logging, and proactive scanning.

## Key Features
- **Multi-Protocol**: VLESS, VMess, Trojan, Shadowsocks, Hysteria2, TUIC, WireGuard, SSH, SOCKS.
- **Smart Chains**: Automatically builds multi-hop routing paths (Entry -> Relay -> Exit) to bypass severe censorship.
- **Vwarp Revival**: Resurrects dead or blocked proxies by wrapping them in clean Cloudflare WARP/Vwarp tunnels.
- **Active Scanning**: Optional active scanning for fresh, low-latency WARP endpoints using `dnsscanner_tui.py`.
- **Evasion**: TLS fingerprint rotation, ALPN shuffling, and multiplexing to evade DPI.
- **Rate Limiting**: Protects distribution endpoints from abuse.

## Quickstart

### Docker (Production)
```bash
docker compose up --build
```

### Local Development
```bash
pip install -e ".[dev]"
configstream merge --sources sources/batch_1.txt --output output
pytest
```

## Outputs (Updated Every 6 Hours)
Production artifacts are hosted on GitHub Pages:

| Output | Description | Clients |
|--------|-------------|---------|
| `singbox.json` | Smart routing profile (Sniper) | Sing-box |
| `singbox-vpn.json` | TUN/VPN profile (Tank) | Sing-box (VPN) |
| `clash.yaml` | Clash-compatible config | Clash, Meta, Verge |
| `base64.txt` | Universal subscription | V2Ray, v2rayNG, Streisand |
| `singbox-chains.json` | Washed & Smart Chains | Sing-box |
| `side_products.zip` | Native configs (OpenVPN, WireGuard) | OpenVPN, WireGuard |

**Note**: DNS-safe (`-dns-safe`) and DNS-hardened (`-dns-hardened`) variants are available for all major outputs.

## Architecture
ConfigStream uses a streaming producer-consumer pipeline:
1.  **Source Acquisition**: Fetches from remote URLs with adaptive timeouts.
2.  **Parsing & Normalization**: Extracts and standardizes configs.
3.  **Validation**: Enforces security policies (no private IPs, no missing credentials).
4.  **Testing**: Dual-engine testing (Go Sidecar + Python Fallback) for latency and reachability.
5.  **Intelligence**: Applies "Washing" (Vwarp) and "Chaining" to revive failed proxies.
6.  **Distribution**: Generates optimized subscriptions and deploys to GitHub Pages.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Security
- **Sanitization**: Logs are scrubbed of sensitive tokens.
- **Blocklists**: Known honeypots and malicious IPs are filtered.
- **Minification**: Frontend assets are minified for performance and security.

See [SECURITY.md](SECURITY.md) for our security policy.

## Roadmap & Status
See [docs/ROADMAP.md](docs/ROADMAP.md) for the latest progress. Recent completions include Vwarp integration, Smart Chains, and comprehensive test coverage.

## License
AGPL-3.0. See [LICENSE](LICENSE).

## Links
- **Dashboard**: [Live Analytics](https://amirrezafarnamtaheri.github.io/ConfigStream/)
- **Repository**: [GitHub](https://github.com/AmirrezaFarnamTaheri/ConfigStream)
- **Issues**: [Report Bugs](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
