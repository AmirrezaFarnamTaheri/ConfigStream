# 08. API Reference

## CLI Reference

ConfigStream is driven by the `configstream` CLI.

### `merge`
Fetch, test, and merge proxies from sources.
```bash
configstream merge --sources sources/batch_1.txt --output output/ --max-workers 50
```
**Options**
- `--sources`: Path to source list (required).
- `--output`: Output directory (default: `output/`).
- `--max-workers`: Concurrency limit (0 = auto-scale).
- `--timeout`: Test timeout in seconds (defaults to `TEST_TIMEOUT`).
- `--country`: ISO country code filter (e.g., `US`).
- `--max-latency`: Max acceptable latency in ms.
- `--leniency/--strict`: Allow insecure proxies (default: strict).
- `--dry-run`: Skip network tests.
- `--verbose`: Debug logging.
- `--max-proxies`: Deprecated (ignored).

### `retest`
Retest proxies from an existing `proxies.json`.
```bash
configstream retest --input output/proxies.json --output output/ --max-workers 50
```

### `update-databases`
Download GeoIP databases.
```bash
configstream update-databases
```

### `generate-warp`
Generate WARP templates.
```bash
configstream generate-warp --count 1
```

### `bot`
Start the Telegram bot (polling).
```bash
configstream bot --token $TELEGRAM_BOT_TOKEN
```

### `backup`
Backup pipeline databases.
```bash
configstream backup --days 7 --dir data
```

## REST API (FastAPI)

### Public Endpoints

#### `GET /api/stats`
Returns the latest pipeline metadata (`metadata.json`).

#### `GET /api/proxies`
Optional filters:
- `country=US`
- `protocol=vless`

#### `GET /api/diff/proxies?base_version=...`
Returns a delta against the previous `proxies.json` snapshot (if available).

#### `GET /subscribe/{format}`
Supported formats:
`base64`, `clash`, `singbox`, `singbox-vpn`, `singbox-chains`,
`shadowrocket`, `quantumult`, `surge`, `loon`, `sip008`, `revived`

#### `GET /chosen/base64.txt`
Top picks per protocol (small curated Base64 subscription).

#### `GET /health`
Basic health information.

#### `WS /ws/updates`
WebSocket stream for pipeline update notifications.

### Admin Endpoint

#### `POST /api/admin/notify-update`
Broadcast update events to connected clients. Requires `ADMIN_API_KEY` in production.

## Data Formats

### `metadata.json`
Summary statistics for the frontend and downstream clients.
```json
{
  "schema_version": "2.3.0",
  "total_proxies": 5000,
  "total_working": 4300,
  "total_revived": 650,
  "total_smart_chains": 120,
  "sources_count": 800,
  "update_interval_hours": 5,
  "generated_at": "2026-01-25T12:00:00Z"
}
```
