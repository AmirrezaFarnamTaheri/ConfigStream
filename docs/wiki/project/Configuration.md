# Configuration Reference

ConfigStream is configured via Environment Variables.

## Core Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAX_WORKERS` | `0` | Override max workers (0 = auto-scale). |
| `TEST_TIMEOUT` | `10` | Timeout in seconds for proxy testing. |
| `FETCH_TIMEOUT` | `15` | Timeout in seconds for source fetching. |
| `CANARY_URL` | `""` | Optional override target used during strict security checks. |
| `MAX_LINES_PER_SOURCE` | `40000` | Max lines processed per source payload. |
| `MAX_CONFIG_LINE_LENGTH` | `10000` | Max length of a single config line. |
| `MAX_B64_INPUT_SIZE` | `10485760` | Max input size (bytes) before Base64 decode. |
| `MAX_B64_OUTPUT_SIZE` | `52428800` | Max decoded size (bytes) before parsing. |
| `MAX_SOURCE_URL_LENGTH` | `2048` | Max source URL length. |

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

## Security Controls

| Variable | Default | Description |
| :--- | :--- | :--- |
| `STRICT_SECURITY` | `false` | Enable honeypot probing + stricter tester checks. |
| `STEGO_KEY` | *None* | Fernet key used for stego asset generation and frontend injection. |
| `ALLOW_PRIVATE_IPS` | `false` | Allow private/loopback IPs through validation. |
| `TLS_TESTS_ENABLED` | `true` | Require TLS-capable configs when TLS validation is enabled. |
| `DEDUP_IGNORE_PROTOCOL` | `false` | Ignore protocol when endpoint-deduplicating (more aggressive). |
| `ENABLE_ENDPOINT_FILTERING` | `true` | Enable endpoint-level deduplication after testing. |

## External Services

| Variable | Default | Description |
| :--- | :--- | :--- |
| `VT_API_KEY` | *None* | VirusTotal API key for IP reputation checks. |
| `TELEGRAM_BOT_TOKEN` | *None* | Bot token for uploading results to Telegram. |
| `TELEGRAM_CHAT_ID` | *None* | Chat ID for Telegram upload. |

## File Paths

*   `sources/batch_*.txt`: Input proxy sources (URLs or direct proxy URIs).
*   `output/`: Generated artifacts (JSON, YAML, HTML).
*   `data/`: Persistent caches/DBs (GeoIP, source quality, history, test cache).
