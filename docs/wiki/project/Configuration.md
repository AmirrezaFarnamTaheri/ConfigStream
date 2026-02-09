# Configuration Reference

ConfigStream is configured via Environment Variables.

## Core Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAX_WORKERS` | `0` | Override max workers (0 = auto-scale). |
| `TEST_TIMEOUT` | `10` | Timeout in seconds for proxy testing. |
| `FETCH_TIMEOUT` | `15` | Timeout in seconds for source fetching. |
| `CANARY_URL` | `""` | Optional override target used during strict security checks. |
| `MAX_LINES_PER_SOURCE` | `0` | Max lines processed per source payload (0 = unlimited). |
| `MAX_CONFIG_LINE_LENGTH` | `0` | Max length of a single config line (0 = unlimited). |
| `MAX_B64_INPUT_SIZE` | `0` | Max input size (bytes) before Base64 decode (0 = unlimited). |
| `MAX_B64_OUTPUT_SIZE` | `0` | Max decoded size (bytes) before parsing (0 = unlimited). |
| `MAX_SOURCE_URL_LENGTH` | `2048` | Max source URL length. |
| `MAX_SEEN_KEYS` | `0` | Max dedup keys retained in memory (0 = unlimited). |
| `MAX_OPENVPN_CONFIG_SIZE` | `0` | Max OpenVPN config size (bytes) (0 = unlimited). |
| `MAX_RESPONSE_SIZE` | `0` | Max fetch response size (bytes) (0 = unlimited). |
| `GO_TESTER_BATCH_SIZE` | `0` | Go tester batch size (0 = no chunking). |
| `PY_TESTER_BATCH_SIZE` | `0` | Python tester batch size (0 = no chunking). |
| `SOURCE_PROBATION_FAILURES` | `3` | Consecutive failures before a source enters probation (cooldown) status. |
| `SOURCE_DEAD_FAILURES` | `10` | Consecutive failures before a source is marked dead (skipped). |

## Intelligence Layer (v2.0)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WARP_KEY_POOL` | `[]` | JSON array of Cloudflare WARP credentials (or comma-separated private keys). **Required for Washing.** |
| `INTRANET_ORIGIN` | `IR` | Origin country for "Intranet Bridge" chains. |
| `OPTIMAL_RELAY_ORIGIN` | `IR` | Preferred origin for relay chains. |
| `USE_VWARP_TUNNEL` | `true` | Route Go tester traffic through the Vwarp tunnel if available. |
| `VWARP_SOCKS5_PORT` | `10808` | Local SOCKS5 port for the Vwarp tunnel. |
| `ALLOW_ACTIVE_SCANNING` | `false` | Opt-in flag to allow WARP endpoint scanning. |
| `FORCE_SCANNER` | `false` | Override CI safety guard (requires `ALLOW_ACTIVE_SCANNING=true`). |
| `ENABLE_ANOMALY_DETECTION` | `true` | Enable anomaly detection on source volume. |
| `ENABLE_SMART_CHAINING` | `true` | Enable smart chain generation. |
| `ENABLE_CACHE_WARMING` | `true` | Prioritize testing of historically reliable proxies. |
| `EVASION_MODE` | `aggressive` | Evasion feature level: `standard` (none), `stealth` (uTLS + frag), `aggressive` (all). |
| `VWARP_VERSION` | *latest* | Pin a specific Vwarp binary version (e.g., `2.1.0`). |
| `UPDATE_INTERVAL_HOURS` | `6` | Publish interval reported in `metadata.json` for frontend freshness display. |

## Security Controls

| Variable | Default | Description |
| :--- | :--- | :--- |
| `STRICT_SECURITY` | `false` | Enable honeypot probing + stricter tester checks. |
| `STEGO_KEY` | *None* | Fernet key used for stego asset generation and frontend injection. |
| `ALLOW_PRIVATE_IPS` | `true` | Allow private/loopback IPs through validation. |
| `TLS_TESTS_ENABLED` | `true` | Require TLS-capable configs when TLS validation is enabled. |
| `DEDUP_IGNORE_PROTOCOL` | `false` | Ignore protocol when endpoint-deduplicating (more aggressive). |
| `ENABLE_ENDPOINT_FILTERING` | `true` | Enable endpoint-level deduplication after testing. |

## External Services

| Variable | Default | Description |
| :--- | :--- | :--- |
| `VT_API_KEY` | *None* | VirusTotal API key for IP reputation checks. |
| `TELEGRAM_BOT_TOKEN` | *None* | Bot token for uploading results to Telegram. |
| `TELEGRAM_CHAT_ID` | *None* | Chat ID for Telegram upload. |
| `ADMIN_API_KEY` | *None* | API key for admin endpoints (e.g., `POST /api/admin/notify-update`). |

## GitHub Actions Secrets

These are set in the repository's Settings → Secrets → Actions:

| Secret | Purpose |
| :--- | :--- |
| `WARP_KEY_POOL` | JSON array of WARP credentials for washing/shielding. |
| `VT_API_KEY` | VirusTotal API key for IP reputation checks. |
| `VWARP_VERSION` | Vwarp binary version to download in CI. |
| `TELEGRAM_BOT_TOKEN` | Bot token for Telegram result uploads. |
| `TELEGRAM_CHAT_ID` | Chat ID for Telegram uploads. |

## File Paths

| Path | Purpose |
| :--- | :--- |
| `sources/batch_*.txt` | Input proxy sources (URLs or direct proxy URIs). Split into 14 shards for parallel CI. |
| `output/` | Generated artifacts (JSON, YAML, TXT, CONF, PNG). Deployed to GitHub Pages. |
| `output/data/` | Time-series trend data (`active_proxy_trend.json`, `evasion_trend.json`). |
| `output/countries/` | Per-country proxy JSON files (e.g., `US.json`, `DE.json`). |
| `output/protocols/` | Per-protocol proxy JSON files (e.g., `vless.json`, `trojan.json`). |
| `output/chosen/` | Curated "top picks" subset (`base64.txt`). |
| `data/` | Persistent caches/DBs — GeoIP (`.mmdb`), source quality (`.db`), history, test cache. |
| `frontend/` | Static frontend assets. Merged with `output/` during Pages deployment. |
