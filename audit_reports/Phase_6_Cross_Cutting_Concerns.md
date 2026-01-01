# Phase 6: Cross-Cutting Concerns - Analysis Report

## 6. Overview
This phase audits cross-cutting concerns like security (blocklists, sanitization), logging, stats tracking, and metrics.

## 6.1. Security (`src/configstream/security/`)

### 6.1.1. Log Sanitization (`logging_config.py`)
*   **Audit**: Analyzed in Phase 0. Found gap where file logs are not sanitized.

### 6.1.2. Blocklists (`blocklist.py`)
**Analysis**:
*   **Source**: Downloads `firehol_level1.netset` from GitHub raw.
*   **Indexing**: Implements bucket indexing (first octet for IPv4, first hextet for IPv6).
    *   **Efficiency**: This is much faster than iterating 50k+ CIDRs. `addr in net` is fast.
*   **Concurrency**: Uses `_lock` for singleton creation and `_data_lock` (AsyncLock) for data swapping.
    *   **Race Condition**: `is_blocked` reads `self._v4_index`. In Python, dictionary reads are atomic (GIL), but replacing `self._v4_index` in `load()` is also atomic (assignment). So `with_index = self._v4_index` is thread-safe without an explicit lock in the reader path, which is good for performance.
*   **Honeypot**: `is_honeypot` is deprecated. `is_suspicious_port` checks ports 23, 2323.

### 6.1.3. Injection Prevention
*   **Configs**: Parsers use regex/struct parsing, not `eval`. `json.loads` is safe.
*   **YAML**: Need to check where `yaml` is used (Roadmap mentions `yaml.safe_load`). `requirements.txt` has `PyYAML`.
    *   **Search**: I haven't seen YAML usage in parsed code yet, but `output.py` likely uses it.

## 6.2. Logging & Metrics

### 6.2.1. Log Noise
**Analysis**:
*   `fetcher_core` uses `logger.debug` for repetitive tasks.
*   `pipeline.py` logs start/stop.
*   **Recommendation**: Ensure `logging_config.py` default level is INFO in prod.

### 6.2.2. Stats & Tracking (`pipeline_core/stats.py`)
**Analysis**:
*   `PipelineStats` is a dataclass.
*   **Concurrency**: It is passed to `processing_consumer`.
    *   **Risk**: Updates like `stats.working += 1` are NOT atomic in `asyncio` if `await` happens in between (not the case for simple `+=`), but multiple consumers running in *parallel threads* (if `run_in_executor`) would race.
    *   **Check**: `processing_consumer` is an `async def`. In `asyncio`, only one task runs at a time on the loop. So `stats.working += 1` is safe *unless* there are threads.
    *   **Pipeline**: The pipeline uses `asyncio.gather`. Everything is single-threaded (mostly). The `GoTester` is a subprocess. `PythonTester` (singbox fallback) uses `run_in_executor`.
    *   **However**: `processing_consumer` updates stats *after* awaiting results. Since `processing_consumer` runs on the main loop, incrementing an integer is safe.

### 6.2.3. Metric Cardinality (`metrics.py`)
**Analysis**:
*   `protocol_counts: Dict[str, int]`.
*   **Risk**: If `proxy.protocol` is user-controlled (it comes from the parser), can a malicious source send random protocols?
    *   Parsers (VMess, VLESS, etc.) hardcode the protocol string (e.g., `protocol="vmess"`).
    *   Generic parsers (if any) might extract scheme. `urlparse(config).scheme`.
    *   **Check**: `trojan.py` checks `scheme` against whitelist. `vmess` is hardcoded. `shadowsocks` is hardcoded.
    *   **Conclusion**: Protocol cardinality is bounded by the parsers.

## 6.3. Concurrency Safety

### 6.3.1. Race Conditions
*   **Seen Keys**: `seen_lock` is used in `pipeline.py` (passed to consumer).
*   **Stats**: Discussed above. Safe in single-threaded event loop.

### 6.3.2. Shared Singletons
*   `BlocklistManager`: Singleton. Thread-safe updates.
*   `GeoIPResolver`: Shared. `maxminddb` reader is usually thread-safe (file read).

## Recommendations
1.  **Blocklist Security**: `BLOCKLIST_URL` is HTTPs. Verification of content (e.g., header check or minimal size check) is done in `load()` (via `ip_network` parsing).
2.  **Stats Safety**: Confirm no threads modify `PipelineStats` directly. `run_in_executor` calls should return values, and the main loop should update stats.
