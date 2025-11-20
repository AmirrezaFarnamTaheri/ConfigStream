# API Reference

ConfigStream provides a modular Python API for proxy aggregation, testing, and management. While primarily used via the CLI, its internal components are designed for reusability in custom applications.

## Core Modules

### `configstream.pipeline`

The central orchestrator that manages the entire lifecycle of proxy aggregation.

#### `run_full_pipeline`
```python
async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    max_workers: int = 0,
    max_proxies: Optional[int] = None,
    timeout: int = 10,
    country_filter: Optional[str] = None,
    min_latency: Optional[int] = None,
    leniency: bool = False,
    strict_security: bool = False,
    progress: Optional[Progress] = None,
    proxies: Optional[List[Proxy]] = None,
    dry_run: bool = False,
) -> PipelineResult
```
**Parameters:**
- `sources`: A list of URLs (http/https) or local file paths containing proxy configurations.
- `output_dir`: Directory to save generated files.
- `max_workers`: Concurrency limit for testing. Set to 0 for auto-detection based on CPU/Memory.
- `timeout`: Base timeout in seconds for network operations.
- `strict_security`: If True, enables rigorous checks like MITM detection and IP blocklisting.

**Returns:**
- `PipelineResult`: An object containing `success` status, `stats` dictionary, and `output_files` paths.

### `configstream.fetcher`

Handles the retrieval of proxy configurations from remote sources.

#### `fetch_multiple_sources`
```python
async def fetch_multiple_sources(
    sources: list[str],
    max_concurrent: int = 10,
    timeout: int = 30,
    per_host_limit: int = 4,
    client: Optional[httpx.AsyncClient] = None,
    use_adaptive_timeout: bool = True,
) -> dict[str, FetchResult]
```
Fetches multiple sources concurrently with adaptive timeouts and rate limiting.

### `configstream.testers`

#### `SingBoxTester`
The primary testing engine wrapping the `sing-box` binary.

```python
class SingBoxTester:
    def __init__(self, timeout: float = 10.0, strict_security: bool = False): ...

    async def test(self, proxy: Proxy) -> Proxy: ...
```
- **test**: Connects to the proxy, measures latency, performs security checks (MITM, Injection), and returns the updated `Proxy` object.

### `configstream.models`

#### `Proxy`
Data class representing a single proxy configuration. Optimized with `__slots__` for memory efficiency.

**Attributes:**
- `protocol` (str): vmess, vless, trojan, etc.
- `address` (str): Server IP or hostname.
- `port` (int): Server port.
- `latency` (float | None): Round-trip time in ms.
- `is_working` (bool): Result of the connectivity test.
- `security_issues` (dict): List of detected security problems (e.g., `{"mitm": ["Suspicious Issuer"]}`).
- `country_code` (str): ISO 3166-1 alpha-2 country code.
- `config` (str): The raw configuration string/URL.

## CLI Reference

The `configstream` command-line interface exposes the pipeline functionality.

### `merge`
Runs the full aggregation and testing pipeline.

```bash
configstream merge [OPTIONS]
```

**Options:**
- `--sources FILE`: Path to the text file containing source URLs (Required).
- `--output DIR`: Output directory (Default: `output/`).
- `--max-workers INT`: Number of concurrent testing threads.
- `--timeout INT`: Timeout for socket connections in seconds.
- `--country CODE`: Filter results by country (e.g., `US`, `DE`).
- `--strict`: Enable strict security validation.

### `fetch`
Debug command to test fetching from a source without running the full pipeline.

```bash
configstream fetch [URL]
```

### `generate-warp`
Generates a Cloudflare WARP WireGuard configuration.

```bash
configstream generate-warp
```

## Web API

When running the optional FastAPI server (`configstream serve` or `server.py`), the following endpoints are available:

### `GET /api/proxies`
Returns a JSON list of currently active, working proxies.
- **Query Params:**
  - `country`: Filter by country code.
  - `protocol`: Filter by protocol.
  - `sort`: Sort by `latency` or `score`.

### `GET /api/stats`
Returns current pipeline statistics (total count, working count, country distribution).

### `POST /api/convert`
Converts a proxy configuration string or subscription to a different format.
- **Body:** `{"config": "vmess://...", "target": "clash"}`

## Extension Points

- **Parsers**: Add new protocol support in `src/configstream/parsers.py`.
- **Adapters**: Add new client export formats in `src/configstream/adapters.py`.
- **Scoring**: Modify ranking algorithms in `src/configstream/source_quality.py`.
