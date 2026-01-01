# Comprehensive Audit Roadmap for ConfigStream

This document outlines a deep, extensive, and end-to-end audit plan for the ConfigStream project. The goal is to identify bugs, logical inconsistencies, dead code, concurrency issues, security vulnerabilities, and technical debt across the entire codebase.

## Phase 1: Project Configuration & Architecture Validity

### 1.1. Dependency & Environment Analysis
- [ ] **Dependency Compatibility**: Analyze `pyproject.toml`, `requirements.txt`, and `package.json` for version conflicts or deprecated packages.
- [ ] **Docker Security**: Audit `Dockerfile` for best practices (non-root user, multi-stage builds, minimal base images, cached layers).
- [ ] **Env Var Handling**: Verify `src/configstream/config.py` correctly loads and validates all environment variables defined in `.env.example`.
- [ ] **Pre-commit Hooks**: Review `.pre-commit-config.yaml` to ensure lints and security checks (e.g., `gitleaks`) are comprehensive.

### 1.2. Architecture & Documentation Compliance
- [ ] **`AGENTS.md` Alignment**: Verify that the codebase strictly follows the directives in `AGENTS.md` (e.g., "No blocking I/O", "Sanitized Logging").
- [ ] **Module Boundaries**: Check for circular imports or violations of the clean architecture (e.g., core logic depending on CLI tools).
- [ ] **Dead Code Detection**: Identify unused files, classes, and functions (e.g., potential leftovers in `src/configstream/utils/` or root scripts).

## Phase 2: Core Pipeline Orchestration (`src/configstream/pipeline.py`)

### 2.1. Concurrency & Event Loop Management
- [ ] **Blocking Calls**: Scan `run_full_pipeline` and consumers for blocking calls (`subprocess.Popen`, `shutil.which`, file I/O) running directly on the event loop.
- [ ] **Task Management**: Specific checks for `asyncio.create_task` usage. Are references held to prevent garbage collection? Are exceptions retrieved?
- [ ] **Graceful Shutdown**: Simulate `SIGINT` and `SIGTERM`. Ensure `processing_consumer` and `source_producer` tasks cancel cleanly without orphaned resources (zombie Go processes).
- [ ] **Queue Bounding**: Verify `asyncio.Queue(maxsize=...)` usage to prevent OOM under backpressure.
- [ ] **Deduplication Logic**: Audit `filter_unique_endpoints` and `seen_keys` usage to ensure precise deduplication without false positives.

### 2.2. Error Handling & Resilience
- [ ] **Exception Swallowing**: Audit `try...except` blocks in `processing_consumer`. Ensure no critical errors are silently ignored.
- [ ] **Global Error Propagation**: If a critical component (e.g., `GeoIPResolver`) fails, does the pipeline fail safely or continue in a degraded state?

### 2.3. Resource Management
- [ ] **File Descriptors**: Check `EventStream` and `output_handler` for proper file closing patterns (e.g., `async with`, `aiofiles`).
- [ ] **Subprocess Leaks**: Deep review of `Vwarp` tunnel startup/shutdown logic. Can the process survive a parent crash?

## Phase 3: Data Ingestion & Parsing Layer

### 3.1. Fetcher Module (`src/configstream/fetcher*`)
- [ ] **Facade Integrity**: Verify `fetcher.py` correctly delegates to `fetcher_core/` without losing context or error details.
- [ ] **Streaming Safety**: Ensure `httpx` streaming response handling limits memory usage (`MAX_RESPONSE_SIZE` enforcement).
- [ ] **Encoding Handling**: Verify robust decoding (utf-8, latin-1 fallbacks) for random source content.

### 3.2. Parsers (`src/configstream/parsers/`)
- [ ] **Fuzzing Resistance**: Analyze parsers (VLESS, VMess, SS, etc.) for resilience against malformed inputs (DoS via RegEx, infinite loops).
- [ ] **Protocol Compliance**:
    - **VLESS**: Check UUID validation logic and "Reality" flow coverage.
    - **Shadowsocks**: Validate method and password extraction logic.
    - **Base64**: Verify handling of unpadded or corrupt Base64 strings.
- [ ] **Renaming & Remarks**: Audit logic for extracting and cleaning remarks (e.g., `unquote(parsed.fragment)`). Ensure "Renaming Remark" features don't introduce XSS or formatting breaks.
- [ ] **Magic Numbers**: Identify and document/refactor magic constants (e.g., `len(hostname) > 255`).

## Phase 4: Testing Engine (`src/configstream/testers/`)

### 4.1. Go Sidecar Integration (`src/configstream/testers/go.py`)
- [ ] **Communication Protocol**: Audit the NDJSON (Newline Delimited JSON) protocol over stdin/stdout. Check handling of partial writes or buffer overflows.
- [ ] **Process Lifecycle**: Review `_heartbeat_loop` and `_ensure_process`. Is there a race condition where multiple processes could be spawned?
- [ ] **Panic Handling**: Ensure the Python side detects Go panics via stderr and recovers cleanly.
- [ ] **SingBox Integration**: Verify that `singbox` configuration generation (in Go sidecar) correctly maps all protocol nuances.

### 4.2. Python Fallback (`src/configstream/testers/python.py`)
- [ ] **TCPing**: Audit the `tcping` implementation. Is it truly non-blocking? Does it handle timeout jitter correctly?
- [ ] **Performance Bottlenecks**: Check for CPU-bound operations in the Python tester (e.g., heavy crypto or SSL handshakes) blocking the loop.
- [ ] **Protocol Parity**: Ensure Python tester supports the same subset of protocols/checks as the Go tester where claimed.

### 4.3. Caching & State
- [ ] **TestResultCache**: Verify thread/async-safety of the cache. Is `save()` blocking?
- [ ] **Cache Invalidation**: Check logic for expiring old results.

## Phase 5: Intelligence & "Smart" Features

### 5.1. Proxy Washer & Revival
- [ ] **Infinite Loops**: Analyze `ProxyWasher` to ensure a proxy isn't indefinitely cycled between "dead" and "revival attempt".
- [ ] **WARP Integration**: Verify key management and `vwarp` binary dependencies.

### 5.2. Scoring & Ranking
- [ ] **Scorer Logic**: Audit `src/configstream/score.py` (if exists) or ranking functions. Are the weights for latency vs. stability balanced?
- [ ] **Ranker**: Review `sort_proxies_pareto` in `src/configstream/pipeline_core/sorter.py`. Ensure it handles edge cases (e.g., missing latency data) gracefully.

### 5.3. Adaptive Logic
- [ ] **AdaptiveTimeout**: Review the math behind timeout adjustments. Can it oscillate or grow unboundedly?
- [ ] **CircuitBreaker**: Ensure it opens/closes correctly and doesn't permanently block valid hosts due to transient errors.
- [ ] **Reshard Dynamic**: Analyze `src/configstream/sharding.py` (if applicable) for dynamic sharding logic correctness under load.

## Phase 6: Cross-Cutting Concerns

### 6.1. Security (`src/configstream/security*`)
- [ ] **Log Sanitization**: **CRITICAL**. Verify `SecurityValidator.sanitize_log_message` is applied to *every* log statement involving external data.
- [ ] **Injection Prevention**: Ensure proxy configs (often user-supplied strings) are not executed or evaluated unsafely.
- [ ] **Blocklists**: Verify `DEFAULT_BLOCKLIST` update mechanism and lookup performance.

### 6.2. Logging & Metrics
- [ ] **Log Noise**: Identify overly verbose logs in the critical path (e.g., per-proxy debug logs).
- [ ] **Stats & Tracking**: Check `PipelineStats` and `ProxyHistoryTracker` (`src/configstream/history/tracker.py`) for data consistency and concurrency safety.

### 6.3. Concurrency Safety
- [ ] **Race Conditions**: Audit `seen_keys` usage. Is the `seen_lock` used consistently?
- [ ] **Shared Singletons**: Verify `GeoIPResolver`, `AnomalyDetector`, `SourceQualityTracker` are strictly thread/async-safe.

## Phase 7: Frontend & Output Artifacts

### 7.1. Frontend (`frontend/`)
- [ ] **XSS Audit**: Check how `proxies.json` data is rendered. Are `remarks` or `details` HTML-escaped?
- [ ] **Performance**: Analyze `proxies.html` rendering performance with large datasets (10k+ proxies).

### 7.2. Output Generation (`src/configstream/output.py`)
- [ ] **Atomic Writes**: Ensure output files are written to a temp file and renamed to prevent partial reads by consumers.
- [ ] **Format Validity**: Verify JSON/YAML/Subscription formats align with standard client requirements (v2ray, SingBox, etc.).
- [ ] **Artifacts**: Check that no build artifacts (`__pycache__`, `.DS_Store`, temporary test files) are included in the final output or commit.

## Phase 8: Refactoring & Cleanup Targets

- [ ] **Split Brain**: Identify logic duplicated between Python and Go (e.g., scoring logic).
- [ ] **Code Duplication**: Merge `adapters.py` and `adapters_base.py` if redundant.
- [ ] **Type Hints**: Run `mypy` check to find missing or `Any` types in strict modules.
