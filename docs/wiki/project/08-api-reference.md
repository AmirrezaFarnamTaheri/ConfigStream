# 08. API Reference

## CLI Reference

ConfigStream is primarily driven by its Command Line Interface (CLI).

### Global Options
*   `--help`: Show help message and exit.
*   `--version`: Show the version number.

### Commands

#### `run`
Executes the main aggregation pipeline.
```bash
configstream run --sources sources/batch_1.txt --output output/ --max-workers 50
```
**Options:**
*   `--sources`: Path to source file or URL (Required).
*   `--output`: Directory to save results (Default: `output/`).
*   `--max-workers`: Number of concurrent workers (Default: Auto).
*   `--timeout`: Connection timeout in seconds (Default: 10).
*   `--country`: Filter by country code (e.g., `IR`, `CN`).
*   `--strict`: Enable strict security checks (honeypot detection).

#### `serve`
Starts the API server.
```bash
configstream serve --host 0.0.0.0 --port 8000
```

#### `bot`
Starts the Telegram bot (polling mode).
```bash
configstream bot
```

#### `generate-warp`
Generates a Cloudflare WARP WireGuard configuration.
```bash
configstream generate-warp
```

## REST API (FastAPI)

The server exposes the following endpoints:

### Public Endpoints

#### `GET /api/stats`
Returns current pipeline statistics and last run status.
```json
{
  "last_updated": "2023-10-27T10:00:00Z",
  "total_proxies": 1500,
  "working_proxies": 1200,
  "sources_count": 50
}
```

#### `GET /api/convert`
Converts a subscription URL or content to a different format.
**Query Params:**
*   `url`: The subscription URL.
*   `target`: Target format (`clash`, `singbox`, `base64`).

#### `GET /health`
Health check endpoint for monitoring.
```json
{
  "status": "ok",
  "output_dir": "output/",
  "files_present": ["singbox.json", "clash.yaml"]
}
```

## Data Formats

### Metadata (`metadata.json`)
The `metadata.json` file contains summary data for the frontend.
```json
{
  "generated_at": "...",
  "stats": { ... },
  "proxies": [
    {
      "id": "...",
      "protocol": "vmess",
      "country": "US",
      "latency": 150,
      "reliability": 0.95
    }
  ]
}
```
