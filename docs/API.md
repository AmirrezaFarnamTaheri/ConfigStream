# ConfigStream API Documentation

## Table of Contents
- [Overview](#overview)
- [Core Data Model](#core-data-model)
- [Pipeline Module](#pipeline-module)
- [Fetcher Module](#fetcher-module)
- [Testing Module](#testing-module)
- [CLI Entry Points](#cli-entry-points)
- [Logging Utilities](#logging-utilities)
- [Filtering Helpers](#filtering-helpers)
- [Statistics & Reporting](#statistics--reporting)
- [Scheduling & Monitoring](#scheduling--monitoring)
- [Examples](#examples)

## Overview

ConfigStream aggregates VPN proxy configurations, validates them, and produces
multiple output formats suitable for Clash, SingBox, and subscription feeds.
The Python API mirrors the command line workflow: fetch sources, parse
configurations, run connectivity tests, enrich with GeoIP data, and render
artifacts.

The package is fully type annotated (PEP 484) and lint-friendly. Key entry
points live under the `configstream` package.

## Core Data Model

```python
from configstream.models import Proxy

@dataclass
class Proxy:
    config: str
    protocol: str
    address: str
    port: int
    uuid: str = ""
    remarks: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    asn: str = ""
    latency: float | None = None
    is_working: bool = False
    is_secure: bool = True
    security_issues: list[str] = field(default_factory=list)
    tested_at: str = ""
    details: dict[str, Any] | None = field(default_factory=dict)
```

`Proxy` objects are produced by parser helpers and enriched by the pipeline
when connectivity tests finish.

## Pipeline Module

> Location: `src/configstream/pipeline.py`

### `run_full_pipeline`

```python
from configstream import pipeline
from rich.progress import Progress

result = await pipeline.run_full_pipeline(
    sources: Sequence[str],
    output_dir: str,
    progress: Progress | None = None,
    max_workers: int = 10,
    max_proxies: int | None = None,
    country_filter: str | None = None,
    min_latency: int | None = None,
    max_latency: int | None = None,
    timeout: int = 10,
    proxies: Sequence[Proxy] | None = None,
) -> dict[str, Any]
```

Runs the end-to-end workflow. When `proxies` are supplied the fetch/parse steps
are skipped, enabling retest flows. The result dictionary contains:

- `success`: `bool` indicating pipeline outcome
- `stats`: counters for fetched, tested, working, and filtered proxies
- `output_files`: mapping of artifact names to paths
- `error`: message when `success` is `False`

Helper functions exported in the module:

- `_prepare_sources(raw_sources: Sequence[str]) -> list[str]`
- `_fetch_source(session: aiohttp.ClientSession, source_url: str) -> tuple[list[str], int]`
- `_extract_config_lines(payload: str) -> list[str]`

These helpers are useful for fine-grained testing or custom ingestion flows.

The pipeline writes a suite of artifacts including `clash.yaml`, `singbox.json`, `shadowrocket.txt`, `quantumult.conf`, `surge.conf`, `proxies.json`, `statistics.json`, and `report.json`.

## Fetcher Module

> Location: `src/configstream/fetcher.py`

- `fetch_from_source(session, source, timeout=30, max_retries=3, retry_delay=1.0) -> FetchResult`
- `fetch_multiple_sources(sources, max_concurrent=10, timeout=30) -> dict[str, FetchResult]`
- `SourceFetcher.fetch_all(sources, max_proxies=None) -> list[str]`

`FetchResult` exposes:

```python
@dataclass
class FetchResult:
    source: str
    configs: list[str]
    success: bool
    error: str | None = None
    response_time: float | None = None
    status_code: int | None = None
```

## Testing Module

> Location: `src/configstream/testers.py`

- `class SingBoxTester:` wraps the SingBox sandbox to test proxies.
  - `test(self, proxy: Proxy) -> Proxy`: mutates latency, status, and security
    fields based on the test outcome.

The tester honours timeouts from `AppSettings` and masks sensitive data when
logging.

## CLI Entry Points

> Location: `src/configstream/cli.py`

The CLI is Click-based and mirrors API calls:

- `configstream merge` → `pipeline.run_full_pipeline` with parsed CLI options
- `configstream retest` → reuses pipeline with cached proxies
- `configstream geoip-download` (if enabled) → downloads GeoIP databases

Both `merge` and `retest` accept `--show-metrics`, surfacing the performance
snapshot gathered by the pipeline after each run.

All commands are wrapped by `@handle_cli_errors` for consistent error messaging.

## Logging Utilities

> Location: `src/configstream/logging_config.py`

```python
from configstream.logging_config import setup_logging

setup_logging(
    level: "INFO",
    mask_sensitive: True,
    log_file: "configstream.log",
    format_style: "detailed",
    use_color: None,
)
```

Features:
- Optional ANSI colour output when stdout is a TTY
- Sensitive data masking for UUID/password/email patterns
- Consolidated configuration of console and file handlers

## Filtering Helpers

> Location: `src/configstream/filtering.py`

```python
from configstream.filtering import ProxyFilter

filtered = (
    ProxyFilter(proxies)
    .by_country(["US", "GB"])
    .by_latency(max_ms=200)
    .sort_by_latency()
    .to_list()
)
```

`ProxyFilter` instances are immutable; each call returns a new filtered view that
can be combined with `chain()` or materialised via `to_list()`.

## Statistics & Reporting

> Location: `src/configstream/statistics.py`

```python
from configstream.statistics import StatisticsEngine

report = StatisticsEngine(proxies).generate_report()
print(report["success_rate"])
```

The engine produces the `report.json` artifact written by the pipeline and helps
drive dashboards or post-processing scripts.

## Scheduling & Monitoring

> Locations:
- `src/configstream/scheduler.py` — periodic retesting helper
- `src/configstream/monitor.py` — lightweight uptime tracker

```python
from datetime import timedelta
from configstream.scheduler import RetestScheduler

scheduler = RetestScheduler("output/proxies.json", interval=timedelta(hours=6))
scheduler.start()
```

The `HealthMonitor` class records historic test results and can report per-proxy
uptime ratios to feed alerting systems.

## Examples

### Run Pipeline from Python

```python
import asyncio
from configstream import pipeline

async def main() -> None:
    result = await pipeline.run_full_pipeline(
        sources=["https://example.com/proxies.txt"],
        output_dir="output",
        max_proxies=100,
        timeout=15,
    )
    if result["success"]:
        print(f"Generated {len(result['output_files'])} artifacts")
    else:
        print(f"Pipeline failed: {result['error']}")

asyncio.run(main())
```

### Retest Existing Results

```python
import asyncio
import json
from pathlib import Path

from configstream import pipeline
from configstream.models import Proxy

async def retest() -> None:
    data = json.loads(Path("output/proxies.json").read_text())
    proxies = [Proxy(**item) for item in data]

    result = await pipeline.run_full_pipeline(
        sources=[],
        output_dir="output",
        proxies=proxies,
        timeout=5,
    )
    print(result["stats"])

asyncio.run(retest())
```

### Custom Fetch Loop

```python
import asyncio
from configstream.fetcher import fetch_multiple_sources

async def fetch_only() -> None:
    results = await fetch_multiple_sources([
        "https://example.com/subscription.txt",
        "https://example.org/proxies.txt",
    ])
    for source, result in results.items():
        print(source, result.success, len(result.configs))

asyncio.run(fetch_only())
```

---

_Last updated: October 2025_
