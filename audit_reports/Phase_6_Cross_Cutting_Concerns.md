# Phase 6: Cross-Cutting Concerns - Analysis Report (Deep Scan)

## 6. Overview
This phase audits cross-cutting concerns like security (blocklists, sanitization, rules), logging, stats tracking, and metrics.

## 6.1. Security (`src/configstream/security/`)

### 6.1.1. Log Sanitization (`logging_config.py`)
*   **Audit**: Analyzed in Phase 0. Found gap where file logs are not sanitized.
*   **Trace ID**: `logging_config.py` implements Trace ID injection via `ContextVar`. This is excellent for correlating async logs.
    *   **Implementation**: `_record_factory` ensures `trace_id` attribute exists on every record.
    *   **Filter**: `TraceIdFilter` is deprecated (comment says so) but still present. The logic moved to factory, which is robust.
    *   **Sensitive Data**: `SensitiveDataFilter` masks emails and UUIDs.
        *   **Gap**: It only applies to `console_handler`. `file_handler` and `json_file_handler` do NOT have this filter added.
        *   **Risk**: Secrets might be written to `configstream.log` or JSON logs.
        *   **Action**: Apply `SensitiveDataFilter` to file handlers too, or clearly document why they are exempt (e.g. for debugging in secure env).

### 6.1.6. Metrics (`src/configstream/metrics.py`)
*   **Analysis**: `PipelineMetrics` dataclass.
*   **Usage**: Tracks duration, rates, cache hits.
*   **Export**: `save_to_file` writes JSON.
*   **Performance**: `to_dict` is fast.
*   **Thread Safety**: It is a simple dataclass. If updated from multiple threads (e.g. `quality_tracker`), it needs locking. Currently `PipelineStats` (in `pipeline_core/stats.py`) is used for live stats, and `PipelineMetrics` seems to be a separate, simpler summary?
    *   **Confusion**: `PipelineStats` (Phase 2) vs `PipelineMetrics` (Phase 6). `PipelineStats` is the main one used in `pipeline.py`. `PipelineMetrics` seems unused or legacy?
    *   **Search**: `grep` shows `PipelineMetrics` is NOT used in `pipeline.py`. `pipeline.py` uses `PerformanceTracker` and `PipelineStats`.
    *   **Action**: Deprecate `metrics.py` if unused, or consolidate.

### 6.1.2. Blocklists (`blocklist.py`)
**Analysis**:
*   **Source**: Downloads `firehol_level1.netset` from GitHub raw.
*   **Indexing**: Implements bucket indexing (first octet for IPv4, first hextet for IPv6).
    *   **Efficiency**: This is much faster than iterating 50k+ CIDRs. `addr in net` is fast.
*   **Concurrency**: Uses `_lock` for singleton creation and `_data_lock` (AsyncLock) for data swapping.
    *   **Race Condition**: `is_blocked` reads `self._v4_index`. In Python, dictionary reads are atomic (GIL), but replacing `self._v4_index` in `load()` is also atomic (assignment). So `with_index = self._v4_index` is thread-safe without an explicit lock in the reader path, which is good for performance.
*   **Honeypot**: `is_honeypot` is deprecated. `is_suspicious_port` checks ports 23, 2323.

### 6.1.3. Honeypot Detection (`security/honeypot.py`)
**Analysis**:
*   **Active Scanning**: `check_common_honeypot_ports` is explicitly DISABLED ("Zero-Budget / No-Abuse policy"). This is excellent for compliance with Cloudflare/GitHub TOS.
*   **Passive Check**: `is_honeypot` calls `virus_total.check_ip_reputation`.
*   **Error Handling**: Fails OPEN (returns `False`) on API errors to avoid blocking good proxies.

### 6.1.4. VirusTotal Integration (`security/virus_total.py`)
**Analysis**:
*   **API Key**: Checks `VT_API_KEY`. Returns `api_key_missing` status if absent.
*   **Caching**: `_IP_CACHE` and `_URL_CACHE` (OrderedDict LRU).
    *   **Locking**: Uses `_CACHE_LOCK` (AsyncLock) for thread-safe access.
    *   **TTL**: 1 hour.
*   **Privacy**: Does NOT send the full URL for IP checks. Sends hash for URL checks (standard VT API usage).

### 6.1.5. Rules (`security/rules.py`)
**Analysis**:
*   **Port Check**: `validate_port` checks range 1-65535 and `DANGEROUS_PORTS`.
*   **Address Check**: `validate_address`
    *   **Normalization**: Uses `idna` and `unicodedata` to prevent homograph attacks.
    *   **DNS Rebinding**: checks for `0x` hex IPs or octal IPs.
    *   **Private IPs**: Checks `127.`, `10.`, `192.168.`, `169.254.`, `fc00:`, etc.
    *   **Bypass**: `ALLOW_PRIVATE_IPS` setting allows disabling this (e.g. for testing).
*   **Config Check**: `validate_config_string` checks for null bytes (`\x00`) and length limits.

## 6.2. Crypto Safety (`src/configstream/crypto/signer.py`)
**Analysis**:
*   **Algorithm**: `ed25519`.
*   **Library**: `cryptography` (standard, safe).
*   **Usage**: Signs subscription content.
*   **Key Handling**:
    *   `bytes.fromhex`.
    *   Checks length (64 bytes or 32 bytes).
    *   **Security**: Does not zero out memory (Python limitation), but key lifetime is short (per execution).

## 6.3. Background Workers (`src/configstream/workers/scanner.py`)
**Analysis**:
*   **CI Detection**: `is_ci = os.environ.get("CI") == "true"`.
    *   **Logic**: Disables scanner in CI unless `FORCE_SCANNER` is set.
    *   **Reason**: GitHub Actions blocks UDP and active scanning can be flagged as abuse. This is a critical safety feature.
*   **Binary Resolution**: Follows robust fallback chain (arg -> env -> path -> common locations).
*   **Execution**:
    *   `asyncio.create_subprocess_exec`.
    *   **Concurrency**: Passes `-workers 100` to binary.
    *   **Output Parsing**: Reads JSON lines from stdout.
    *   **Error Handling**: Catches `json.JSONDecodeError` and logs debug info. This makes it resilient to garbage output.

## Recommendations
1.  **Blocklist Security**: `BLOCKLIST_URL` is HTTPs. Verification of content (e.g., header check or minimal size check) is done in `load()` (via `ip_network` parsing).
2.  **Stats Safety**: Confirm no threads modify `PipelineStats` directly. `run_in_executor` calls should return values, and the main loop should update stats.
3.  **Key Rotation**: Document how `private_key_hex` is rotated in `signer.py` (via env var).
