# Comprehensive Audit Roadmap for ConfigStream

This document outlines a deep, extensive, end-to-end audit plan for the ConfigStream project. The goal is to identify bugs, logical inconsistencies, dead code, concurrency issues, security vulnerabilities, and technical debt across the entire codebase.

## Phase 1: Project Configuration & Architecture Validity

### 1.1. Dependency & Environment Analysis
- [ ] **Dependency Compatibility**:
    - [ ] Analyze `pyproject.toml` for strict vs loose version pinning (e.g., `^` vs `~=`). Verify semantic versioning compliance.
    - [ ] Check `requirements.txt` for consistency with `pyproject.toml`. Ensure hash pinning for security.
    - [ ] Audit `package.json` (frontend) for deprecated npm packages and license compliance (MIT/BSD vs AGPL).
    - [ ] Verify `setup.py` (if exists) doesn't conflict with `pyproject.toml`. Check for `install_requires` duplication.
    - [ ] **Python 3.12 Readiness**: Check for removed stdlib modules (e.g., `distutils`, `imp`). Run `pylint --py3k`.
    - [ ] **Dev vs Prod**: Verify separation of `dev-dependencies` (e.g., `pytest`, `mypy`) from production requirements.
- [ ] **Docker Security**:
    - [ ] Audit `Dockerfile` for non-root user enforcement (`USER appuser`). Ensure UID/GID matches host expectations if volume mounted.
    - [ ] Verify multi-stage builds are used to reduce image size. Check `COPY --from=builder`.
    - [ ] Check for sensitive args/envs baked into layers (e.g., `ARG GITHUB_TOKEN`). Use `--secret` mount type instead.
    - [ ] Validate `docker-compose.yml` network isolation rules. Are containers strictly confined to internal networks?
    - [ ] Check `pip install --no-cache-dir` usage to reduce image size.
    - [ ] **Distroless**: Evaluate feasibility of using distroless base images for Python/Go.
- [ ] **Env Var Handling**:
    - [ ] Verify `src/configstream/config.py` uses `pydantic-settings` correctly. Check `extra="ignore"` vs `extra="forbid"`.
    - [ ] Check validation logic for all vars in `.env.example`. Are types enforced (int vs str)?
    - [ ] Ensure sensitive vars (keys, tokens) are marked `SecretStr` to prevent logging.
    - [ ] **Missing Vars**: Identify code accessing `os.getenv` directly instead of using the config object.
- [ ] **Pre-commit Hooks**:
    - [ ] Review `.pre-commit-config.yaml` for `gitleaks` (secret scanning). Is the regex pattern up to date?
    - [ ] Ensure `black`, `isort`, and `flake8` config matches project standards. Check for conflicting line lengths.
    - [ ] Verify `mypy` is running in strict mode (`no_implicit_optional`, `check_untyped_defs`, `disallow_any_generics`).
- [ ] **CI/CD Workflow**:
    - [ ] Audit `.github/workflows/` for secure secret injection. Avoid `env: ${{ secrets.ALL }}`.
    - [ ] Check for unlimited timeouts in jobs (cost risk). Set `timeout-minutes`.
    - [ ] Verify 3rd party actions are pinned by commit hash, not tag (immutable refs).
    - [ ] **Pip Audit**: Check `src/configstream/tools/pip_audit_wrapper.py`. Does it enforce failure (`check=True`) on vulnerabilities? Ensure it runs in CI.
- [ ] **Build Scripts**:
    - [ ] **`scripts/build_wasm.sh`**:
        - [ ] Verify strict Go version check (e.g., `1.21.0` vs `1.21`). Check `go.mod` compatibility.
        - [ ] Validate integrity of `wasm_exec.js` copy (checksum comparison with GOROOT).
        - [ ] Ensure `-trimpath` and `-ldflags "-w -s"` are used for reproducible and smaller builds.

### 1.2. Architecture & Documentation Compliance
- [ ] **`AGENTS.md` Alignment**:
    - [ ] Scan codebase for "Blocking I/O" violations (e.g., `requests.get`, `time.sleep` inside async functions).
    - [ ] Verify "Sanitized Logging" directive is respected in all new modules. Search for raw logging patterns.
- [ ] **Module Boundaries**:
    - [ ] Check for circular imports using `pylint --check-graph` or `import-linter`.
    - [ ] Verify core logic (`src/configstream/pipeline_core`) doesn't import CLI/UI layers (clean architecture).
    - [ ] **Public API**: Ensure `__all__` is defined in `__init__.py` to control exported symbols.
- [ ] **Dead Code Detection**:
    - [ ] Run `vulture` or similar to find unused code.
    - [ ] Check `src/configstream/utils/` for orphaned helper functions.
    - [ ] Audit `src/configstream/plugins/` (e.g., `scoring.py`, `validation.py`): Are they loaded dynamically via `importlib` or unused?
    - [ ] Review `scripts/` for obsolete maintenance scripts that haven't been touched in >1 year.
- [ ] **Split Brain & Redundancies**:
    - [ ] **Protocol Parsing**: Compare `src/configstream/converters/singbox.py` vs Go sidecar. Are all protocols in Sync? Do they handle edge cases (empty fields) identically?
    - [ ] **Scoring Logic**: Compare `src/configstream/score.py` (if exists) vs `sort_proxies_pareto`. Consolidate logic.
    - [ ] **Vector Generation**: Compare `vectors.py` feature hashing vs any frontend logic. Ensure seed consistency.
- [ ] **Legacy Cleanups**:
    - [ ] Audit `src/configstream/adapters.py` vs `adapters_base.py`. Merge or deprecate.
    - [ ] Check for deprecated "v1" implementations in `parsers/`. Identify comment markers like `# TODO: Remove`.
- [ ] **Data Classes**:
    - [ ] Check `__slots__` usage in `Proxy` models to reduce memory footprint.
    - [ ] Verify immutability (`frozen=True`) where appropriate.

## Phase 2: Core Pipeline Orchestration (`src/configstream/pipeline.py`)

### 2.1. Concurrency & Event Loop Management
- [ ] **Blocking Calls**:
    - [ ] Scan `run_full_pipeline` for synchronous file I/O (`open()`, `shutil.copy`). Use `aiofiles` or `run_in_executor`.
    - [ ] Audit `processing_consumer` for CPU-bound tasks (encryption, parsing) not wrapped in `run_in_executor`.
    - [ ] Check `subprocess.Popen` usage: is it truly non-blocking? Use `asyncio.create_subprocess_exec`.
- [ ] **Task Management**:
    - [ ] Audit `asyncio.create_task` usage:
        - [ ] Are references held (`background_tasks` set) to prevent GC?
        - [ ] Are exceptions retrieved/handled via `add_done_callback` or `gather`?
    - [ ] Check for "fire-and-forget" tasks that might swallow errors. Use `TaskGroup` (Python 3.11+) or safe wrappers.
- [ ] **Graceful Shutdown**:
    - [ ] Simulate `SIGINT` (Ctrl+C) and `SIGTERM`.
    - [ ] Verify `processing_consumer` cancels immediately but allows current item to finish (cleanup).
    - [ ] Ensure `source_producer` stops fetching new data.
    - [ ] Verify `Vwarp` tunnel process receives `SIGTERM` and waits (`wait()`) to avoid zombies.
    - [ ] Check `EventStream` flush on exit. Ensure file handles are closed.
- [ ] **Queue Bounding**:
    - [ ] Verify `work_queue = asyncio.Queue(maxsize=...)`. Does it prevent OOM on slow consumers?
    - [ ] Test behavior when queue is full (does producer pause via `await queue.put`?).
- [ ] **Deduplication Logic**:
    - [ ] Audit `filter_unique_endpoints`:
        - [ ] Does it handle IP vs Domain duplicates correctly (DNS resolution or string comparison)?
        - [ ] Does it handle port differences?
    - [ ] Audit `seen_keys` usage:
        - [ ] Is it a `set` or `dict`? Does it track timestamp for TTL?
        - [ ] Is memory usage bounded (LRU)?
    - [ ] **Lock Safety**: Verify `seen_lock` is used consistently across all consumers to protect `seen_keys` and `PipelineStats`.
- [ ] **uvloop Integration**:
    - [ ] Check if `uvloop` is installed and activated (`uvloop.install()`) for performance boost.

### 2.2. Error Handling & Resilience
- [ ] **Exception Swallowing**:
    - [ ] Search for `except Exception:` (bare excepts). Use specific exceptions or log the error.
    - [ ] Ensure critical errors (OOM, Disk Full, PermissionError) are re-raised to stop the pipeline if necessary.
- [ ] **Global Error Propagation**:
    - [ ] If `GeoIPResolver` fails init (DB missing), does pipeline continue (fallback) or crash?
    - [ ] If `SourceQualityTracker` DB is locked, does pipeline stall or skip stats?
- [ ] **Timeout Management**:
    - [ ] Audit `AdaptiveTimeout` logic in `src/configstream/intelligence/adaptive_timeout.py`.
        - [ ] Can timeout drop below 0? Implement floor value (e.g., 1s).
        - [ ] Does it oscillate wildly? Implement smoothing (EMA).
    - [ ] Verify `httpx` timeouts are enforced on `connect`, `read`, and `write`.

### 2.3. Resource Management
- [ ] **File Descriptors**:
    - [ ] Check `EventStream` file handling. Are files closed in `finally` blocks?
    - [ ] Check `output_handler` file usage.
    - [ ] Ensure `ulimit` is respected or handled. Handle `EMFILE` errors gracefully.
- [ ] **Subprocess Leaks**:
    - [ ] Deep review of `Vwarp` tunnel lifecycle. Use `psutil` to verify child processes are killed.
    - [ ] Verify orphan cleanup if parent crashes (`atexit`, signal handlers).

## Phase 3: Data Ingestion & Parsing Layer

### 3.1. Fetcher Module (`src/configstream/fetcher*`)
- [ ] **Facade Integrity**:
    - [ ] Verify `fetcher.py` API matches `fetcher_core/` implementation.
    - [ ] Ensure deprecation warnings are present for old API usage.
- [ ] **Streaming Safety**:
    - [ ] Verify `httpx` streaming logic (`stream=True`).
    - [ ] Check `MAX_RESPONSE_SIZE` (prevent memory bomb). Abort download if Content-Length > limit.
    - [ ] Verify `iter_bytes` usage to process chunks incrementally.
- [ ] **Encoding Handling**:
    - [ ] Test with `utf-8`, `latin-1`, `gbk` (common in proxies).
    - [ ] Verify fallback strategy (`chardet` or simple try-except chain).
- [ ] **DNS Leaks**:
    - [ ] Audit `dns_batch_resolver.py`:
        - [ ] Does it leak DNS queries to system resolver?
        - [ ] Does it support DoH/DoT for privacy?
        - [ ] Is caching strictly respected (TTL)? Does it respect `hosts` file?
- [ ] **Advanced Protocols**:
    - [ ] Verify `HTTP/2` support enabled in `httpx` client.
    - [ ] Verify `IPv6` connectivity checks.

### 3.2. Parsers & Protocol Compliance (`src/configstream/parsers/`)
- [ ] **Fuzzing Resistance**:
    - [ ] Test parsers with random byte strings (fuzzing).
    - [ ] Test with "recursive" base64 strings or deeply nested JSON.
    - [ ] Check RegEx for ReDoS vulnerabilities (e.g. `(a+)+`). Use `re.compile` with timeouts if possible (3.11+ feature unavailable? Use careful patterns).
- [ ] **Specific Protocol Audits**:
    - [ ] **VLESS**:
        - [ ] Verify UUID validation (hex only, 32/36 chars).
        - [ ] Audit `Reality` flow: `pbk` and `sid` extraction. Validate hex/base64 format.
        - [ ] Check fallback for missing `flow`.
    - [ ] **VMess**:
        - [ ] Verify AEAD check (is `alterId` 0?).
        - [ ] Check `alterId` logic (force 0 if missing? Legacy support?).
        - [ ] Verify `scy` vs `cipher` priority.
    - [ ] **Trojan**:
        - [ ] Check TLS compulsion (Trojan is TLS-only).
        - [ ] Verify `sni` extraction from `peer` or `sni` field.
    - [ ] **Shadowsocks (SS/SIP002)**:
        - [ ] Validate Base64 padding for `user:pass`.
        - [ ] Check plugin param parsing (`obfs-local`, `v2ray-plugin`). Handle URL-encoding.
    - [ ] **Shadowsocks 2022**:
        - [ ] Verify `method` format (e.g., `2022-blake3-aes-128-gcm`).
        - [ ] Check key length validation (16/32 bytes base64).
    - [ ] **Hysteria / Hysteria2**:
        - [ ] Check `up_mbps`/`down_mbps` parsing (string vs int). Handle "100 Mbps" units.
        - [ ] Verify `obfs` vs `obfs-type` field handling.
    - [ ] **Tuic**:
        - [ ] Verify `uuid` requirement.
        - [ ] Check `congestion_control` mapping (standard `bbr` vs custom).
    - [ ] **WireGuard**:
        - [ ] Verify `private_key` length (Base64, 44 chars).
        - [ ] Check `reserved` bytes parsing (list of 3 ints, not strings).
        - [ ] Audit IP generation for WARP (collision risk in `to_singbox_outbound`). Use deterministic hashing.
    - [ ] **SSH**:
        - [ ] Check `private_key` vs `password` precedence.
        - [ ] Verify `host_key` validation. Parse known_hosts format?
    - [ ] **SOCKS5 / SOCKS4**:
        - [ ] Verify `version` field inference.
        - [ ] Check auth (user/pass) extraction.
    - [ ] **HTTP / HTTPS**:
        - [ ] Check `tls` flag logic.
        - [ ] Verify basic auth extraction from URL vs headers.
    - [ ] **NaiveProxy**:
        - [ ] Check `padding` support.
        - [ ] Verify `https` wrapping logic (Chrome probe resistance).
    - [ ] **Base64**:
        - [ ] Verify padding fix logic (`=` vs `==`).
        - [ ] Check handling of URL-safe (`-_`) vs standard (`+/`) base64.
- [ ] **Renaming & Remarks (`src/configstream/tagging.py`)**:
    - [ ] **Regex Safety**: Audit `format_proxy_name` cleanup regex. Ensure it doesn't strip essential chars.
    - [ ] **Unquote**: Check `unquote` usage for crash on invalid inputs (`%ZZ`).
    - [ ] **Template Injection**: Ensure `str.format` doesn't access internal attributes (`{__init__}`).
- [ ] **Country Inference (`src/configstream/country_inferrer.py`)**:
    - [ ] **Excluded Codes**: Verify `_EXCLUDED_CODES` list covers common false positives (e.g., `ID` (Indonesia vs ID), `AI` (Anguilla vs AI), `NO` (Norway vs No)).
    - [ ] **Regex Efficiency**: Check `_CODE_PATTERN` for ReDoS. Use `atomic grouping` simulation if needed.

## Phase 4: Testing Engine (`src/configstream/testers/`)

### 4.1. Go Sidecar Integration (`src/configstream/testers/go.py`)
- [ ] **Communication Protocol (NDJSON)**:
    - [ ] Audit stdin/stdout handling. Ensure UTF-8 encoding.
    - [ ] Check buffering: does it deadlock if buffer fills? (Pipe size limits).
    - [ ] Handle partial JSON lines or interspersed logs in stdout.
- [ ] **Process Lifecycle**:
    - [ ] Audit `_heartbeat_loop`: frequency vs load.
    - [ ] Audit `_ensure_process`: locking logic (avoid double spawn). Check PID validity.
- [ ] **Panic Handling**:
    - [ ] Check stderr reader logic. Capture Go panic stacks.
    - [ ] Verify auto-restart on panic code 2 or unexpected exit.
- [ ] **SingBox Integration**:
    - [ ] Verify generated config structure matches `sing-box` schema (version 1.8+ vs 1.9+).
    - [ ] Check `route` object generation (geo-site/ip rules).
- [ ] **Honeypot Detection**:
    - [ ] Verify `check_honeypot` logic in Go.
    - [ ] Is it checking strictly (port 80/443 vs any port)?
    - [ ] Are false positives minimized? (e.g., legitimate captive portals).

### 4.2. Python Fallback (`src/configstream/testers/python.py`)
- [ ] **TCPing**:
    - [ ] Is it `asyncio.open_connection` based?
    - [ ] Does it measure "Connect" or "Handshake" time?
    - [ ] Does it handle `ConnectionRefused` vs `Timeout` differently?
    - [ ] Check for timeout jitter implementation to prevent synchronized thundering herds.
- [ ] **Performance Bottlenecks**:
    - [ ] Check for heavy crypto loops (e.g., pure python AES).
    - [ ] Check for excessive object creation in loops.
- [ ] **Protocol Parity**:
    - [ ] Does Python tester verify VLESS/Reality? (Likely not, verify limitation). Document gaps.

### 4.3. Caching & State
- [ ] **TestResultCache**:
    - [ ] Audit `save()`: is it atomic (write temp + rename)?
    - [ ] Verify `get/set` thread safety (`threading.Lock` vs `asyncio.Lock`).
- [ ] **Cache Invalidation**:
    - [ ] Check `TTL` logic.
    - [ ] Does `retest_scheduler` respect "dead" (longer interval) vs "alive" (shorter interval) logic?

## Phase 5: Intelligence & Advanced Features

### 5.1. Proxy Washer & Revival (`src/configstream/intelligence/washer/`)
- [ ] **Infinite Loops**:
    - [ ] Analyze `ProxyWasher.wash_failed` in `core.py`.
    - [ ] Prevent: Dead -> Revive -> Fail -> Dead loop. Check recursion depth or retry counters.
- [ ] **Key Management**:
    - [ ] Check `key_generator.py`:
        - [ ] Algorithm correctness (`x25519` implementation).
        - [ ] Key rotation policy. Do keys expire?

### 5.2. Scoring & Ranking
- [ ] **Scorer Logic**:
    - [ ] Audit `src/configstream/pipeline_core/sorter.py`.
    - [ ] Check Pareto scoring math: `(norm_latency * 0.5) + ((1.0 - reliability) * 0.3) + ((1.0 - uptime) * 0.2)`.
    - [ ] Is pre-calculation of stats efficient (bulk fetch)? Avoid N+1 queries.
- [ ] **Ranker**:
    - [ ] Verify sorting stability (Python `sort` is stable, but are keys unique?).
    - [ ] Handle proxies with `latency=None` (assigned 9999).

### 5.3. Adaptive Logic
- [ ] **AdaptiveTimeout**:
    - [ ] Review AIMD algorithm (Additive Increase/Multiplicative Decrease).
    - [ ] Check boundaries (Min/Max timeout).
- [ ] **CircuitBreaker**:
    - [ ] Verify "Open" state logic in `src/configstream/intelligence/circuit_breaker.py`.
    - [ ] Check "Half-Open" probe logic. How many requests pass through?
- [ ] **Reshard Dynamic**:
    - [ ] Analyze `src/configstream/sharding.py`.
    - [ ] Verify `blake2b` bucketing determinism (`buckets=256`).
    - [ ] Check `save_shard_metadata` logic. Is it atomic?

### 5.4. Vwarp Ecosystem (Feature 1: `src/configstream/tools/vwarp.py`, `warp.py`, `warp_validator.py`)
- [ ] **VwarpTool Controller**:
    - [ ] **Binary Path**: Verify fallback logic if `vwarp` is not in PATH. Check `/usr/local/bin` and CWD.
    - [ ] **Timeout Handling**: Check `scan_endpoints` timeout (default 30s) - is it sufficient for global scans?
    - [ ] **Parsing**: Audit stdout parsing logic for `scan_endpoints` (IPv4 vs [IPv6]).
- [ ] **Warp Key Generator**:
    - [ ] **Cryptography**: Verify `_generate_keys` uses `cryptography.hazmat` correctly.
    - [ ] **Blocking Calls**: Ensure `_generate_keys` runs in `loop.run_in_executor` to avoid blocking main loop.
    - [ ] **Registration**: Audit `register_warp_account` HTTP request structure against current Cloudflare API.
- [ ] **Warp Key Validator**:
    - [ ] **Key Length**: Audit `validate_key_format` (32 bytes).
    - [ ] **Endpoint Check**: Review `validate_endpoint_reachable` - is hardcoded IP list (`162.159...`) up to date?
- [ ] **Scanner Integration**:
    - [ ] Check integration of `VwarpTool.scan_endpoints` with `ProxyWasher`. Does it persist results?

### 5.5. Advanced Chaining & Routing (Feature 2: `src/configstream/intelligence/chaining.py`)
- [ ] **Geodesic Logic**:
    - [ ] Audit `haversine` implementation vs `geopy`. Ensure fallback works.
    - [ ] Check `COUNTRIES` coordinate accuracy (80+ entries). Are centers accurate?
- [ ] **Chain Strategies**:
    - [ ] **Intranet**: Verify "IR -> Relay -> Exit" logic. Ensure Relays are actually reachable from IR.
    - [ ] **IPv6**: Audit "Dual Stack -> IPv6 Only" selection. Verify Relay supports IPv6.
    - [ ] **Streamer**: Check "Fast Protocol -> Streaming Region" selection.
    - [ ] **Censorship Resistant**: Verify multi-hop stealth routing logic (TLS in TLS?).
    - [ ] **High Anonymity**: Audit 3-hop chain construction (Continent hopping).
- [ ] **Protocol Scoring**:
    - [ ] Review `PROTOCOL_SCORES` weights (Stealth vs Speed).
    - [ ] Is `CENSORSHIP_LEVELS` map up-to-date with recent events?

## Phase 6: Cross-Cutting Concerns

### 6.1. Security (`src/configstream/security*`)
- [ ] **Log Sanitization (`src/configstream/logging_config.py`)**:
    - [ ] **CRITICAL**: Verify `SecurityValidator.sanitize_log_message` applied to all console outputs.
    - [ ] **Audit Findings**: File/JSON handlers are currently **UNMASKED**. Verify if this is intended behavior for debuggability vs security risk. Add warning in docs.
- [ ] **Injection Prevention**:
    - [ ] Ensure configs are treated as data, not code.
    - [ ] Check `yaml.safe_load` vs `yaml.load`.
- [ ] **Blocklists**:
    - [ ] Verify `DEFAULT_BLOCKLIST` update source (FireHol?). Is HTTPS enforced?
    - [ ] Check IP range lookup efficiency (Trie vs List). `ipaddress` module can be slow for lists.
- [ ] **Crypto (`src/configstream/crypto/`)**:
    - [ ] Audit `signer.py`:
        - [ ] Is `ed25519` implementation standard?
        - [ ] Is private key loaded from secure Env/File?
        - [ ] Are signatures deterministic?
- [ ] **Secret Rotation**:
    - [ ] Check how `WARP_KEY_POOL` handles stale keys.
    - [ ] Verify `FERNET_KEY` rotation in `stego.py`.

### 6.2. Logging & Metrics
- [ ] **Log Noise**:
    - [ ] Check `DEBUG` vs `INFO` levels.
    - [ ] Debounce repetitive logs (e.g., "Connection refused" x1000).
- [ ] **Stats & Tracking (`src/configstream/pipeline_core/stats.py`)**:
    - [ ] **Concurrency**: Verify `PipelineStats` updates are guarded by `seen_lock` in `consumer.py`.
    - [ ] **Atomic Operations**: Check if integer increments are thread-safe (GIL usually handles this, but `asyncio` context switch matters).
    - [ ] **Serialization**: Audit `to_dict` for unserializable types (`datetime`).
- [ ] **Metric Cardinality (`src/configstream/metrics.py`)**:
    - [ ] Check `protocol_counts`: can user input create infinite keys? (DoS vector).
    - [ ] Verify `save_to_file` atomic write.

### 6.3. Concurrency Safety
- [ ] **Race Conditions**:
    - [ ] Audit `seen_keys` access.
    - [ ] Audit `stats` updates.
- [ ] **Shared Singletons**:
    - [ ] Verify `GeoIPResolver` instance sharing. Is internal cache thread-safe?
    - [ ] Verify `AnomalyDetector` internal state lock.

## Phase 7: Frontend & Output Artifacts

### 7.1. Frontend (`frontend/`)
- [ ] **XSS Audit**:
    - [ ] Check `proxies.json` rendering in JS. Use `textContent` instead of `innerHTML`.
    - [ ] Escaping of `remarks` field.
    - [ ] Escaping of `details` object keys/values.
- [ ] **Performance**:
    - [ ] Test `proxies.html` with 10k items (Virtual Scrolling?).
    - [ ] Check load time with large `vectors.json`.
- [ ] **Accessibility (a11y)**:
    - [ ] Check ARIA labels on dynamic elements.
    - [ ] Verify keyboard navigation in tables.
- [ ] **Security Headers**:
    - [ ] Verify `Content-Security-Policy`.
    - [ ] Check `Subresource Integrity` (SRI) for external scripts (if any).
- [ ] **Artifacts**:
    - [ ] Check `.gitignore` for `output/`.
    - [ ] Verify `clean` step before build.
    - [ ] Audit `generate_favicons.py` logic.

### 7.2. Output Generation (`src/configstream/output.py`)
- [ ] **Atomic Writes**:
    - [ ] Ensure `write -> flush -> fsync -> rename` pattern (see `async_file_ops.py`).
- [ ] **Format Validity**:
    - [ ] Validate generated JSON against schema.
    - [ ] Validate YAML syntax.
- [ ] **Converters (`src/configstream/converters/`)**:
    - [ ] **SingBox**:
        - [ ] Audit `to_singbox_outbound` in `singbox.py`.
        - [ ] Check `WireGuard` IP generation (collision risk?).
        - [ ] **Transport Mapping**: Audit `singbox_utils.add_transport_sb`.
            - [ ] Verify `ws`, `grpc`, `http` type mapping.
            - [ ] Check for `str(None) -> "None"` string corruption.
        - [ ] **Stealth Profile**: Audit `singbox_utils.apply_stealth_profile`.
            - [ ] Does User-Agent injection break WAFs?
    - [ ] **Clash**:
        - [ ] Audit `to_clash_proxy` in `clash.py`.
        - [ ] Verify `Reality` support (Clash Meta).
- [ ] **Generators (`src/configstream/generators/`)**:
    - [ ] Check `generate_split_outputs` logic.
    - [ ] Verify "Subscription" base64 padding.

## Phase 8: Server & API (`src/configstream/server.py`)

### 8.1. API Security
- [ ] **Input Validation**:
    - [ ] Validate `country` param (2 chars, alpha).
    - [ ] Validate `protocol` param (alphanumeric).
- [ ] **Path Traversal**:
    - [ ] Check `SAFE_PATH_PATTERN` regex (`^[a-zA-Z0-9_-]+$`).
    - [ ] Verify `os.path.commonpath` checks are robust.
- [ ] **Rate Limiting**:
    - [ ] Is there middleware for rate limiting?
    - [ ] Check `admin/notify-update` auth (API Key check).
- [ ] **WebSocket Security**:
    - [ ] Check max message size (DoS).
    - [ ] Check open connection limits.

### 8.2. Operational Safety
- [ ] **CORS Policy**:
    - [ ] Review `ALLOWED_ORIGIN_REGEX`.
    - [ ] Is it allowing `*` implicitly?
- [ ] **Error Leakage**:
    - [ ] Check `HTTPException` details.
    - [ ] Ensure 500 errors don't expose stack trace in production.

## Phase 9: Tools & Operational Scripts

### 9.1. Maintenance Scripts
- [ ] **Scripts Audit**:
    - [ ] `clean_security_issues.py`: Logic check. Does it delete files?
    - [ ] `publish_ipfs.py`: Secret handling.
    - [ ] `upload_*.py`: Token permissions scope.
- [ ] **Tools Audit**:
    - [ ] `blocklist_manager/`: Source validation.
    - [ ] `latency_tester/`: Concurrency conflicts.
- [ ] **Bot CLI (`src/configstream/bot_cli.py`)**:
    - [ ] **Token Security**: Verify `TELEGRAM_BOT_TOKEN` is not logged.
    - [ ] **Error Handling**: Check if bot crashes pipeline on network error. Use try-except.

### 9.2. Policy & Schema
- [ ] **Schema Validation**:
    - [ ] Verify `schema/proxy_schema.json` covers all protocols.
    - [ ] Verify `schema/source_schema.json`.
- [ ] **Policy Enforcement**:
    - [ ] Check `policy/` directory usage.

## Phase 10: Refactoring & Cleanup Targets

- [ ] **Split Brain**:
    - [ ] Map all Python-Go duplications.
    - [ ] Plan consolidation (move more to Go?).
- [ ] **Code Duplication**:
    - [ ] Merge `adapters.py` / `adapters_base.py`.
    - [ ] Refactor `converters` common logic (TLS struct).
- [ ] **Type Hints**:
    - [ ] Enforce `mypy --strict`.
    - [ ] Eliminate `type: ignore`.
- [ ] **Utility Audit**:
    - [ ] Review `src/configstream/utils/`.
    - [ ] **`bool_parser.py`**: Check edge cases ("on", "off", "yes", "no").
    - [ ] **`async_file_ops.py`**: Verify `aiofiles` usage.
    - [ ] Deprecate `bool_parser` if standard exists.
- [ ] **JSON Performance**:
    - [ ] Evaluate `orjson` vs standard `json` for high-throughput serialization.

## Phase 11: Transport & Vectors (Deep Internals)

### 11.1. Steganography Transport (`src/configstream/transport/stego.py`)
- [ ] **Magic Marker Safety**:
    - [ ] Ensure `MAGIC_MARKER` bytes don't collide with PNG format.
    - [ ] Verify image validity is preserved (append-only).
- [ ] **Encryption**:
    - [ ] Audit `Fernet` usage. Is key rotation possible?
    - [ ] Verify `HMAC` implementation.

### 11.2. Vector Intelligence (`src/configstream/intelligence/vectors.py`)
- [ ] **Feature Hashing**:
    - [ ] Audit `_compute_vector` logic.
    - [ ] Check for hash collisions reducing vector utility.
    - [ ] Verify dimensions (0-7) capture meaningful variance.

## Phase 12: Data Integrity & Artifacts

- [ ] **Artifact Management**:
    - [ ] Audit cleanup of `output/` directory.
    - [ ] Verify versioning of `proxies.json` (`proxies.old.json`).
    - [ ] Check `history` DB integrity checks (`PRAGMA integrity_check`).
- [ ] **Reshard Dynamic**:
    - [ ] Verify `sharding.py` logic under load.
    - [ ] Check `buckets` configuration (default 256).

## Phase 13: Documentation & Knowledge Base

- [ ] **Documentation Audit**:
    - [ ] Review `docs/` folder for outdated info.
    - [ ] Ensure `KNOWN_ISSUES.md` is current.
    - [ ] Verify `CONTRIBUTING.md` matches `AGENTS.md`.
- [ ] **Knowledge Preservation**:
    - [ ] Document "Split Brain" map in `docs/architecture.md`.
    - [ ] Create decision log for Protocol choices.

## Phase 14: Continuous Improvement & Final Polish

- [ ] **Profiling**:
    - [ ] Review `scripts/profile_performance.py`.
    - [ ] Add `yappi` for async profiling.
- [ ] **Regression Testing**:
    - [ ] Add `tests/test_converters.py` (round-trip tests).
    - [ ] Add `tests/test_pipeline_resilience.py`.
    - [ ] **Test Gaps**: Verify `test_hedged_requests.py` actually tests concurrency (not just mocks).
- [ ] **Linting**:
    - [ ] Enforce `flake8` max-complexity.
    - [ ] Enforce `black` formatting.
- [ ] **Documentation**:
    - [ ] Update `README.md` architecture diagram.
    - [ ] Update `AGENTS.md` with new findings.

## Phase 15: Edge Case & Anomaly Handling

- [ ] **Hedged Requests (`src/configstream/hedged_requests.py`)**:
    - [ ] **Zombie Tasks**: Verify that canceled tasks in `queue` are properly awaited/cleaned up.
    - [ ] **Race Conditions**: Check logic when `hedge_after` is very small.
- [ ] **DNS Prewarming (`src/configstream/dns_prewarm.py`)**:
    - [ ] **Cache Poisoning**: Verify that `top_hosts` cannot be manipulated by malicious sources.
    - [ ] **Exception Silencing**: Ensure `return_exceptions=True` doesn't mask systemic DNS failures.
- [ ] **Freshness Logic (`src/configstream/freshness.py`)**:
    - [ ] **Timezone Safety**: Audit `replace("Z", "+00:00")` for robustness against non-ISO formats. Use `dateutil`?
    - [ ] **Integer Overflow**: Check `age_seconds` calculation for very old proxies.

## Phase 16: Future Proofing & Scalability

- [ ] **Horizontal Scaling**:
    - [ ] Can multiple pipeline instances write to the same `history` DB? (Locking issue?).
    - [ ] Is `output/` directory shared or local?
- [ ] **Database Migration**:
    - [ ] Is there a schema version in `ProxyHistoryTracker`?
    - [ ] Plan for migration to PostgreSQL if SQLite hits limits.

## Phase 17: Legal & Compliance

- [ ] **License Headers**:
    - [ ] Verify all source files contain AGPLv3 header.
- [ ] **GDPR/Privacy**:
    - [ ] Verify `history.db` doesn't log user IPs accessing the API.
    - [ ] Check if `GeoIPResolver` uses a local DB (privacy safe) or external API (leaks source IP).

## Phase 18: Disaster Recovery (`src/configstream/backup.py`)

- [ ] **Backup Logic**:
    - [ ] Audit `backup_databases` for `sqlite3` locking (use `immutable=1`?).
    - [ ] Verify `cleanup_old_backups` sorts correctly by date.
- [ ] **Restoration**:
    - [ ] Test `restore_database` function. Does it handle corrupt gzip files?
    - [ ] Verify `pre_restore_backup` creation prevents data loss on failed restore.

## Phase 19: Configuration & Constants (`src/configstream/constants.py`)

- [ ] **Security Constants**:
    - [ ] Verify `DANGEROUS_PORTS` list completeness (missing MongoDB 27017?).
    - [ ] Check `SUSPICIOUS_DOMAINS` (is `127.0.0.1` blocked?).
- [ ] **Limits & Thresholds**:
    - [ ] Audit `MAX_B64_INPUT_SIZE` (10MB sufficient?).
    - [ ] Check `MAX_CONFIG_LINE_LENGTH` (10k chars).
- [ ] **Protocol Support**:
    - [ ] Ensure `VALID_PROTOCOLS` matches `parsers/` capabilities.
    - [ ] Verify `PROTOCOL_COLORS` covers all supported protocols (for UI).

## Phase 20: Architecture & Design Patterns

- [ ] **Singleton Pattern**:
    - [ ] Audit `GeoIPResolver`, `ProxyWasher`, `VwarpTool` usage. Are they truly singletons or instantiated multiple times?
- [ ] **Dependency Injection**:
    - [ ] Verify if `app_settings` is passed down or instantiated globally (tight coupling).
- [ ] **Error Handling Strategy**:
    - [ ] Audit usage of custom exceptions in `cli_errors.py` vs standard `ValueError`.

## Phase 21: Toolchain & Utilities Deep Dive

- [ ] **Pip Audit Wrapper (`src/configstream/tools/pip_audit_wrapper.py`)**:
    - [ ] **Security Flaw**: Verify `subprocess.run(..., check=False)` usage. This allows build to pass even if vulnerabilities are found.
- [ ] **Warp Validator (`src/configstream/tools/warp_validator.py`)**:
    - [ ] **Fragility**: Audit `validate_endpoint_reachable` reliance on hardcoded IPs (`162.159...`).
    - [ ] **Coverage**: Add check for WARP+ License Key validation (currently missing).
