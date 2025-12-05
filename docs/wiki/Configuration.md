# Configuration Reference

ConfigStream is configured via Environment Variables.

## Core Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAX_WORKERS` | `50` | Concurrency for Python fetchers/parsers. |
| `TEST_TIMEOUT` | `10` | Timeout in seconds for proxy testing. |
| `CANARY_URL` | *None* | URL to check for Honeypot detection (e.g., a signed endpoint). |

## Intelligence Layer (v2.0)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WARP_KEY_POOL` | `[]` | JSON array of Cloudflare WARP credentials. **Required for Washing.** |
| `WARP_PORT` | `2408` | Target port for WARP endpoints (usually 2408 or 500-1000 range). |
| `RELAY_COUNTRY_CODE` | `IR` | Origin country for "Intranet Bridge" chains. |

## External Services

| Variable | Default | Description |
| :--- | :--- | :--- |
| `VT_API_KEY` | *None* | VirusTotal API key for IP reputation checks. |
| `TELEGRAM_BOT_TOKEN` | *None* | Bot token for uploading results to Telegram. |
| `TELEGRAM_CHAT_ID` | *None* | Chat ID for Telegram upload. |

## File Paths

*   `sources/batch_*.txt`: Input proxy sources.
*   `output/`: Generated artifacts (JSON, YAML, HTML).
*   `data/`: Persistent DBs (GeoIP, Quality Score).
