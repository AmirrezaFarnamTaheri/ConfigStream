# Comprehensive Audit Roadmap for ConfigStream

This document outlines a deep, extensive, end-to-end audit plan for the ConfigStream project. The goal is to identify bugs, logical inconsistencies, dead code, concurrency issues, security vulnerabilities, and technical debt across the entire codebase.

## Phase 0: Immediate Critical Fixes (High Priority)

- [ ] **Security Vulnerability**: `src/configstream/tools/pip_audit_wrapper.py` sets `check=False`. This allows builds to pass even if vulnerabilities are found.
    - [ ] **Action**: Change to `check=True` or explicitly handle return codes to fail the build.
- [ ] **Log Sanitization Gap**: `src/configstream/logging_config.py` does not apply masking to file/JSON logs.
    - [ ] **Action**: Assess risk. If intended for debugging, restrict file permissions (`chmod 600`). If not, apply `SensitiveDataFilter`.
- [ ] **Testing Gap**: `test_hedged_requests.py` may not be testing actual concurrency race conditions.
    - [ ] **Action**: Verify tests use `asyncio.sleep` to simulate race conditions properly.

## Phase 1: Foundation & Configuration

### 1.1. Project Structure & Environment
- [ ] **Dependency Compatibility**:
    - [ ] Analyze `pyproject.toml` for strict vs loose version pinning (e.g., `^` vs `~=`). Verify semantic versioning compliance.
    - [ ] Check `requirements.txt` for consistency with `pyproject.toml`. Ensure hash pinning for security (`pip-compile --generate-hashes`).
    - [ ] **Python 3.12 Readiness**: Check for removed stdlib modules (e.g., `distutils`, `imp`). Run `pylint --py3k`.
- [ ] **Configuration Logic**:
    - [ ] Verify `src/configstream/config.py` uses `pydantic-settings` correctly. Check `extra="ignore"` vs `extra="forbid"`.
    - [ ] **Constants**: Audit `src/configstream/constants.py`. Are `DANGEROUS_PORTS` comprehensive? Is `MAX_B64_INPUT_SIZE` (10MB) sufficient?
    - [ ] **Secrets**: Ensure sensitive vars (keys, tokens) are marked `SecretStr` to prevent logging.

### 1.2. Architecture & Design Patterns
- [ ] **Singleton Pattern**:
    - [ ] Audit `GeoIPResolver`, `ProxyWasher`, `VwarpTool` usage. Are they truly singletons or instantiated multiple times? Use `functools.lru_cache` or module-level singletons.
- [ ] **Dependency Injection**:
    - [ ] Verify if `app_settings` is passed down or instantiated globally (tight coupling). Prefer passing instances.
- [ ] **Error Handling Strategy**:
    - [ ] Audit usage of custom exceptions in `cli_errors.py` vs standard `ValueError`. Ensure consistency.

## Phase 2: Core Ingestion & Parsing

### 2.1. Fetcher Module (`src/configstream/fetcher*`)
- [ ] **Facade Integrity**:
    - [ ] Verify `fetcher.py` API matches `fetcher_core/` implementation. Ensure deprecation warnings are present for old API usage.
- [ ] **Streaming Safety**:
    - [ ] Verify `httpx` streaming logic (`stream=True`).
    - [ ] Check `MAX_RESPONSE_SIZE` logic. Does it abort download *during* the stream if Content-Length > limit?
- [ ] **Advanced Protocols**:
    - [ ] Verify `HTTP/2` support enabled in `httpx` client.
    - [ ] Verify `IPv6` connectivity checks. Does `httpx` fallback gracefully?

### 2.2. Parsers & Protocol Compliance (`src/configstream/parsers/`)
- [ ] **Fuzzing Resistance**:
    - [ ] Test parsers with random byte strings (fuzzing).
    - [ ] Test with "recursive" base64 strings or deeply nested JSON.
    - [ ] **ReDoS**: Check RegEx for vulnerabilities (e.g. `(a+)+`). Use `re.compile` with timeouts if possible.
- [ ] **Specific Protocol Audits**:
    - [ ] **VLESS**: Verify UUID validation (hex only, 32/36 chars). Audit `Reality` flow: `pbk` and `sid` extraction.
    - [ ] **VMess**: Verify AEAD check (is `alterId` 0?). Check `scy` vs `cipher` priority.
    - [ ] **Trojan**: Check TLS compulsion (Trojan is TLS-only). Verify `sni` extraction.
    - [ ] **Shadowsocks**: Validate Base64 padding for `user:pass`. Check plugin param parsing (`obfs-local`).
    - [ ] **Hysteria2**: Check `up_mbps`/`down_mbps` parsing (string vs int). Verify `obfs` vs `obfs-type` field handling.
    - [ ] **Tuic**: Verify `uuid` requirement. Check `congestion_control` mapping (standard `bbr` vs custom).
    - [ ] **WireGuard**: Verify `private_key` length (Base64, 44 chars). Check `reserved` bytes parsing (list of 3 ints).
- [ ] **Country Inference**:
    - [ ] Verify `_EXCLUDED_CODES` in `country_inferrer.py` covers false positives (e.g., `ID`, `AI`, `NO`).

## Phase 3: Core Pipeline Orchestration

### 3.1. Concurrency & Event Loop Management
- [ ] **Blocking Calls**:
    - [ ] Scan `run_full_pipeline` for synchronous file I/O (`open()`, `shutil.copy`). Use `aiofiles` or `run_in_executor`.
    - [ ] Check `subprocess.Popen` usage: is it truly non-blocking? Use `asyncio.create_subprocess_exec`.
- [ ] **Task Management**:
    - [ ] Audit `asyncio.create_task` usage. Are references held (`background_tasks` set) to prevent GC?
    - [ ] **uvloop Integration**: Check if `uvloop` is installed and activated (`uvloop.install()`) for performance boost.
- [ ] **Queue Bounding**:
    - [ ] Verify `work_queue = asyncio.Queue(maxsize=...)`. Does it prevent OOM on slow consumers?
    - [ ] Test behavior when queue is full (does producer pause via `await queue.put`?).

### 3.2. Resilience & Error Handling
- [ ] **Exception Swallowing**:
    - [ ] Search for `except Exception:` (bare excepts). Use specific exceptions or log the error.
- [ ] **Timeout Management**:
    - [ ] Audit `AdaptiveTimeout` logic. Can timeout drop below 0? Implement floor value (e.g., 1s).
- [ ] **Resource Management**:
    - [ ] Check `EventStream` file handling. Are files closed in `finally` blocks?
    - [ ] Ensure `ulimit` is respected. Handle `EMFILE` errors gracefully.

## Phase 4: Intelligence & Routing

### 4.1. Vwarp Ecosystem (Feature 1)
- [ ] **VwarpTool Controller**:
    - [ ] **Binary Path**: Verify fallback logic if `vwarp` is not in PATH. Check `/usr/local/bin` and CWD.
    - [ ] **Timeout Handling**: Check `scan_endpoints` timeout (default 30s) - is it sufficient?
- [ ] **Warp Key Generator**:
    - [ ] **Cryptography**: Verify `_generate_keys` uses `cryptography.hazmat` correctly.
    - [ ] **Blocking Calls**: Ensure `_generate_keys` runs in `loop.run_in_executor` to avoid blocking main loop.
- [ ] **Warp Key Validator**:
    - [ ] **Endpoint Check**: Review `validate_endpoint_reachable` - is hardcoded IP list (`162.159...`) up to date?

### 4.2. Advanced Chaining & Routing (Feature 2)
- [ ] **Geodesic Logic**:
    - [ ] Audit `haversine` implementation vs `geopy`. Ensure fallback works correctly.
    - [ ] Check `COUNTRIES` coordinate accuracy (80+ entries). Are centers accurate?
- [ ] **Chain Strategies**:
    - [ ] **Intranet**: Verify "IR -> Relay -> Exit" logic. Ensure Relays are actually reachable from IR.
    - [ ] **IPv6**: Audit "Dual Stack -> IPv6 Only" selection. Verify Relay supports IPv6.
    - [ ] **Censorship Resistant**: Verify multi-hop stealth routing logic (TLS in TLS?).

### 4.3. Washer & Revival
- [ ] **Infinite Loops**:
    - [ ] Analyze `ProxyWasher.wash_failed` in `core.py`. Prevent: Dead -> Revive -> Fail -> Dead loop.
- [ ] **Key Management**:
    - [ ] Check `key_generator.py`: Key rotation policy. Do keys expire?

## Phase 5: Testing & Verification

### 5.1. Testing Engine
- [ ] **Go Sidecar Integration**:
    - [ ] **Communication**: Audit stdin/stdout handling. Ensure UTF-8 encoding. Check pipe buffering deadlocks.
    - [ ] **Panic Handling**: Check stderr reader logic. Capture Go panic stacks.
- [ ] **Python Fallback**:
    - [ ] **TCPing**: Is it `asyncio.open_connection` based? Does it handle `ConnectionRefused` vs `Timeout` differently?
    - [ ] **Jitter**: Check for timeout jitter implementation to prevent synchronized thundering herds.

### 5.2. Caching & State
- [ ] **TestResultCache**:
    - [ ] Audit `save()`: is it atomic (write temp + rename)?
    - [ ] **Concurrency**: Verify `get/set` thread safety (`threading.Lock` vs `asyncio.Lock`).
- [ ] **Cache Invalidation**:
    - [ ] Check `TTL` logic. Does `retest_scheduler` respect "dead" vs "alive" intervals?

## Phase 6: Data Persistence & Integrity

### 6.1. Artifacts & History
- [ ] **Artifact Management**:
    - [ ] Audit cleanup of `output/` directory.
    - [ ] Verify versioning of `proxies.json` (`proxies.old.json`).
- [ ] **Reshard Dynamic**:
    - [ ] Verify `sharding.py` logic. Check `blake2b` bucketing determinism (`buckets=256`).
- [ ] **Database Integrity**:
    - [ ] Check `history` DB integrity checks (`PRAGMA integrity_check`).

### 6.2. Disaster Recovery (`src/configstream/backup.py`)
- [ ] **Backup Logic**:
    - [ ] Audit `backup_databases` for `sqlite3` locking (use `immutable=1`?).
    - [ ] Verify `cleanup_old_backups` sorts correctly by date.
- [ ] **Restoration**:
    - [ ] Test `restore_database` function. Does it handle corrupt gzip files?

## Phase 7: Output & Transport

### 7.1. Output Generation
- [ ] **Atomic Writes**:
    - [ ] Ensure `write -> flush -> fsync -> rename` pattern (see `async_file_ops.py`).
- [ ] **Converters (`src/configstream/converters/`)**:
    - [ ] **SingBox**: Audit `to_singbox_outbound`. Check `WireGuard` IP generation (collision risk?).
    - [ ] **Stealth Profile**: Audit `singbox_utils.apply_stealth_profile`. Does User-Agent injection break WAFs?
    - [ ] **Clash**: Verify `Reality` support (Clash Meta).

### 7.2. Transport & Vectors
- [ ] **Steganography (`src/configstream/transport/stego.py`)**:
    - [ ] **Magic Marker**: Ensure `MAGIC_MARKER` bytes don't collide with PNG format.
    - [ ] **Encryption**: Verify `Fernet` usage and key rotation.
- [ ] **Vector Intelligence (`src/configstream/intelligence/vectors.py`)**:
    - [ ] **Feature Hashing**: Check for hash collisions reducing vector utility.

## Phase 8: Server & API (`src/configstream/server.py`)

- [ ] **API Security**:
    - [ ] **Path Traversal**: Check `SAFE_PATH_PATTERN` regex (`^[a-zA-Z0-9_-]+$`). Verify `os.path.commonpath` checks.
    - [ ] **Rate Limiting**: Is there middleware for rate limiting?
    - [ ] **WebSocket Security**: Check max message size (DoS).
- [ ] **Operational Safety**:
    - [ ] **CORS Policy**: Review `ALLOWED_ORIGIN_REGEX`. Is it allowing `*` implicitly?
    - [ ] **Error Leakage**: Ensure 500 errors don't expose stack trace in production.

## Phase 9: Tooling & Operations

### 9.1. Maintenance Scripts
- [ ] **Scripts Audit**:
    - [ ] `clean_security_issues.py`: Logic check. Does it delete files?
    - [ ] `publish_ipfs.py`: Secret handling.
- [ ] **Bot CLI (`src/configstream/bot_cli.py`)**:
    - [ ] **Token Security**: Verify `TELEGRAM_BOT_TOKEN` is not logged.
    - [ ] **Error Handling**: Check if bot crashes pipeline on network error. Use try-except.

### 9.2. Toolchain Deep Dive
- [ ] **Pip Audit Wrapper**: Verify `src/configstream/tools/pip_audit_wrapper.py`. Fix security flaw (`check=False`).
- [ ] **Warp Validator**: Audit `validate_endpoint_reachable` reliance on hardcoded IPs.

## Phase 10: Cross-Cutting Concerns

### 10.1. Security
- [ ] **Log Sanitization**:
    - [ ] **CRITICAL**: Verify `SecurityValidator.sanitize_log_message` applied to all console outputs.
    - [ ] **Unmasked Logs**: Address unmasked File/JSON logs.
- [ ] **Injection Prevention**:
    - [ ] Check `yaml.safe_load` vs `yaml.load`.
- [ ] **Secret Rotation**:
    - [ ] Check how `WARP_KEY_POOL` handles stale keys.

### 10.2. Logging & Metrics
- [ ] **Log Noise**:
    - [ ] Debounce repetitive logs (e.g., "Connection refused").
- [ ] **Stats & Tracking**:
    - [ ] **Concurrency**: Verify `PipelineStats` updates are guarded by `seen_lock` in `consumer.py`.
- [ ] **Metric Cardinality**:
    - [ ] Check `protocol_counts`: can user input create infinite keys? (DoS vector).

## Phase 11: Maintenance & Future

- [ ] **Refactoring**:
    - [ ] **Split Brain**: Map Python-Go logic duplications. Plan consolidation.
    - [ ] **Code Duplication**: Merge `adapters.py` / `adapters_base.py`.
- [ ] **Scalability**:
    - [ ] **Horizontal Scaling**: Can multiple pipeline instances write to the same `history` DB? (Locking issue?).
    - [ ] **Database Migration**: Plan for migration to PostgreSQL if SQLite hits limits.
- [ ] **Legal & Compliance**:
    - [ ] **License Headers**: Verify all source files contain AGPLv3 header.
    - [ ] **GDPR**: Verify `history.db` doesn't log user IPs.

## Phase 12: Continuous Assurance

- [ ] **Profiling**:
    - [ ] Review `scripts/profile_performance.py`. Add `yappi` for async profiling.
- [ ] **Regression Testing**:
    - [ ] Add `tests/test_converters.py` (round-trip tests).
    - [ ] **Test Gaps**: Verify `test_hedged_requests.py` tests concurrency properly.
- [ ] **Documentation**:
    - [ ] Update `README.md` and `AGENTS.md` with new findings.
    - [ ] Document "Split Brain" map in `docs/architecture.md`.
