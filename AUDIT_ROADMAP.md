# Comprehensive Audit Roadmap for ConfigStream

This document outlines a deep, extensive, end-to-end audit plan for the ConfigStream project. The goal is to identify bugs, logical inconsistencies, dead code, concurrency issues, security vulnerabilities, and technical debt across the entire codebase.

> **Note**: This roadmap is structured into 8 Logical Groups comprising 25+ detailed Phases.

## Group A: Critical Assurance & Immediate Fixes

### Phase 0: Immediate Critical Fixes (High Priority)
- [ ] **Security Vulnerability: CI/CD Gaps**
    - [ ] **Target**: `src/configstream/tools/pip_audit_wrapper.py`
    - [ ] **Check**: Verify `subprocess.run(..., check=False)` usage.
    - [ ] **Action**: Change to `check=True` or explicitly handle return codes to fail the build on found vulnerabilities.
    - [ ] **Validation**: Create a test case with a known vulnerable package and ensure the script exits with non-zero code.
- [ ] **Log Sanitization Gap**
    - [ ] **Target**: `src/configstream/logging_config.py`
    - [ ] **Check**: File (`RotatingFileHandler`) and JSON (`JsonFormatter`) handlers currently bypass `SensitiveDataFilter`.
    - [ ] **Risk**: Secrets (UUIDs, Tokens) logged to disk in plain text.
    - [ ] **Action**: Apply `SensitiveDataFilter` to all handlers or implement a specific `RedactingFormatter` for file outputs.
- [ ] **Concurrency Testing Gap**
    - [ ] **Target**: `tests/unit/test_hedged_requests.py`
    - [ ] **Check**: Does the test actually run concurrent coroutines or just mock them sequentially?
    - [ ] **Action**: Verify usage of `asyncio.sleep` with random jitters to simulate real race conditions.

## Group B: Foundations & Infrastructure

### Phase 1: Environment & Dependency Architecture
- [ ] **Dependency Management (`pyproject.toml`, `requirements.txt`)**
    - [ ] **Version Pinning**: Analyze strict (`==`) vs loose (`^`, `~=`) pinning. Recommendation: Strict for app, loose for libs.
    - [ ] **Hash Integrity**: Ensure `requirements.txt` uses `--generate-hashes` to prevent supply chain attacks.
    - [ ] **Conflict Analysis**: Cross-check `setup.py` (if exists) vs `pyproject.toml` for `install_requires` drift.
    - [ ] **Frontend Deps**: Audit `package.json` for deprecated packages (`npm audit`). Check license compliance (AGPL compat).
    - [ ] **Python 3.12+**: Check for removed stdlib modules (`distutils`, `imp`, `cgi`). Run `pylint --py3k`.
- [ ] **Container Security (`Dockerfile`)**
    - [ ] **Privilege Escalation**: Verify `USER appuser` is enforced. Check for `sudo` usage.
    - [ ] **Attack Surface**: Verify multi-stage builds (`COPY --from=builder`). Are build tools (gcc, git) removed in final image?
    - [ ] **Secret Leaks**: Check `ARG` instructions for baked-in secrets. Use `RUN --mount=type=secret`.
    - [ ] **Network Isolation**: Validate `docker-compose.yml` networks. Is the database isolated from the public interface?
- [ ] **Build System (`scripts/build_wasm.sh`)**
    - [ ] **Reproducibility**: Ensure `-trimpath` and `-ldflags "-w -s"` are used.
    - [ ] **Integrity**: Compare `wasm_exec.js` checksum against the Go compiler version.
    - [ ] **Version Lock**: Verify script fails if Go version != `1.21.x` (strict check).

### Phase 2: Configuration & Constants
- [ ] **Configuration Logic (`src/configstream/config.py`)**
    - [ ] **Type Safety**: Verify `pydantic-settings` usage. Are `extra="forbid"` and `strict=True` enabled?
    - [ ] **Secret Handling**: Ensure `SecretStr` is used for all keys/tokens to prevent accidental `repr()` logging.
    - [ ] **Env Validation**: Check `.env.example` coverage. Are all required vars validated at startup?
- [ ] **Global Constants (`src/configstream/constants.py`)**
    - [ ] **Security Lists**: Verify `DANGEROUS_PORTS` completeness (add 27017 Mongo, 6379 Redis).
    - [ ] **Blocking Lists**: Check `SUSPICIOUS_DOMAINS` and `BLOCKED_DOMAINS` (GitHub raw links handling).
    - [ ] **Limits**: Audit `MAX_B64_INPUT_SIZE` (10MB). Is it sufficient for large subs? Is `MAX_CONFIG_LINE_LENGTH` (10k) safe against DoS?
    - [ ] **Protocol Colors**: Verify `PROTOCOL_COLORS` covers all 28+ supported protocols.

## Group C: Core Data Plane (Ingestion & Parsing)

### Phase 3: Fetcher & Networking
- [ ] **Fetcher Module (`src/configstream/fetcher*`)**
    - [ ] **Facade Integrity**: Verify `fetcher.py` API parity with `fetcher_core/`.
    - [ ] **Streaming Safety**:
        - [ ] Verify `httpx.stream()` usage.
        - [ ] **Memory Bomb**: Check `MAX_RESPONSE_SIZE` logic. Does it `raise` immediately if accumulated bytes > limit?
    - [ ] **Protocol Support**:
        - [ ] **HTTP/2**: Verify `http2=True` in `httpx.AsyncClient`.
        - [ ] **IPv6**: Check connectivity fallback strategy (`Happy Eyeballs` equivalent).
- [ ] **DNS Batch Resolver (`src/configstream/dns_batch_resolver.py`)**
    - [ ] **Leakage**: Does it use system DNS or a custom DoH/DoT resolver?
    - [ ] **Privacy**: Verify it respects `hosts` file and doesn't leak internal domains.
    - [ ] **Caching**: Audit TTL respect. Is cache poisoning possible via malicious upstream?

### Phase 4: Parsers & Protocol Compliance
- [ ] **Parser Robustness (`src/configstream/parsers/`)**
    - [ ] **Fuzzing**: Test with random byte strings, recursive Base64, and huge JSONs.
    - [ ] **ReDoS**: Audit all Regex patterns (e.g., `(a+)+`). Use `re.compile` or `google-re2` wrapper.
- [ ] **Protocol-Specific Deep Dive**:
    - [ ] **VLESS**:
        - [ ] UUID: Hex-only, 32/36 chars. Fail on nil UUID.
        - [ ] Reality: Validate `pbk` (public key) format and `sid` (short id) hex.
    - [ ] **VMess**:
        - [ ] AEAD: Verify `alterId=0` enforcement.
        - [ ] Ciphers: Check `scy` vs `cipher` precedence logic.
    - [ ] **Trojan**:
        - [ ] TLS: Enforce `security='tls'`. Check `sni` field extraction.
    - [ ] **Shadowsocks**:
        - [ ] SIP002: Validate User/Pass Base64 padding.
        - [ ] Legacy: Check `ss://method:pass@host:port` parsing.
        - [ ] Plugins: Verify `obfs-local`, `v2ray-plugin` arg parsing (URL decoding).
    - [ ] **Shadowsocks 2022**:
        - [ ] Method: Validate `2022-blake3-aes-128-gcm`.
        - [ ] Key: Validate length (16/32 bytes) matches method.
    - [ ] **Hysteria / Hysteria2**:
        - [ ] Bandwidth: Parse `up_mbps`/`down_mbps` (handle units "Mbps", "Gbps").
        - [ ] Obfs: Check `obfs` vs `obfs-type` field usage.
    - [ ] **Tuic**:
        - [ ] UUID: Mandatory check.
        - [ ] Congestion: Map `bbr` to standard constants.
    - [ ] **WireGuard**:
        - [ ] Keys: Base64 length (44 chars) for `private_key` and `peer_public_key`.
        - [ ] Reserved: List of 3 integers [0-255]. Fail on strings.
        - [ ] MTU: Default vs Parsed.
    - [ ] **SSH**:
        - [ ] Auth: `private_key` vs `password` precedence.
        - [ ] Host Key: Validation logic.
    - [ ] **NaiveProxy**:
        - [ ] Padding: Verify support.
        - [ ] HTTPS: Check wrapping logic.
- [ ] **Metadata Extraction (`src/configstream/tagging.py`, `country_inferrer.py`)**
    - [ ] **Tagging**: Audit `format_proxy_name` regex for catastrophic backtracking.
    - [ ] **Inference**: Verify `_EXCLUDED_CODES` list (e.g., "ID", "NO", "ON"). Check for false positives in complex remarks.

## Group D: Core Control Plane (Orchestration)

### Phase 5: Pipeline Orchestration & Concurrency
- [ ] **Orchestrator (`src/configstream/pipeline.py`)**
    - [ ] **Blocking Calls**: Scan for `shutil.copy`, `open()`, `time.sleep`.
    - [ ] **Subprocess**: Check `subprocess.Popen` (blocking) vs `asyncio.create_subprocess_exec`.
- [ ] **Task Lifecycle**:
    - [ ] **Reference Holding**: Verify `asyncio.create_task` references are stored (`background_tasks`) to prevent GC.
    - [ ] **Exception Retrieval**: Ensure all tasks have `add_done_callback` or are `await`ed in `gather`.
- [ ] **Queue Management**:
    - [ ] **Backpressure**: Verify `asyncio.Queue(maxsize=...)` usage. Does producer pause?
    - [ ] **Deadlocks**: Check for circular dependencies in queue consumers.
- [ ] **Graceful Shutdown**:
    - [ ] **Signals**: Verify `SIGINT`/`SIGTERM` handling.
    - [ ] **Cancellation**: Ensure `processing_consumer` cleans up (closes files) on `CancelledError`.
    - [ ] **Zombies**: Verify Vwarp tunnel process is explicitly killed (`proc.kill()`).

### Phase 6: Resilience & State
- [ ] **Error Handling**:
    - [ ] **Swallowing**: Grep for `except Exception: pass`.
    - [ ] **Critical Failures**: Ensure DB locks or Disk Full trigger a hard stop or alert.
- [ ] **Timeout Logic (`src/configstream/intelligence/adaptive_timeout.py`)**:
    - [ ] **Bounds**: Ensure timeout cannot go `< 1s` or `> 60s`.
    - [ ] **Smoothing**: Check EMA (Exponential Moving Average) implementation stability.
- [ ] **Deduplication**:
    - [ ] **Logic**: Audit `filter_unique_endpoints` (IP vs Domain).
    - [ ] **State**: Check `seen_keys` size management (LRU or bloom filter?).
    - [ ] **Locking**: Verify `seen_lock` usage in `processing_consumer`.

## Group E: Intelligence & Advanced Features

### Phase 7: The Vwarp Ecosystem (Feature A)
- [ ] **Vwarp Controller (`src/configstream/tools/vwarp.py`)**
    - [ ] **Binary Resolution**: Verify `shutil.which` vs fallback paths (`/usr/local/bin`).
    - [ ] **Output Parsing**: Audit `scan_endpoints` stdout parsing. Does it handle IPv6 `[brackets]`?
    - [ ] **Timeout**: Is scan timeout (30s) sufficient?
- [ ] **Warp Key Generator (`src/configstream/tools/warp.py`)**
    - [ ] **Crypto**: Verify `x25519` key generation uses `cryptography` properly.
    - [ ] **Concurrency**: Ensure CPU-bound key gen runs in `loop.run_in_executor`.
    - [ ] **API**: Verify Cloudflare API endpoints (`v0a2404`) and headers (`okhttp`).
- [ ] **Validator (`src/configstream/tools/warp_validator.py`)**
    - [ ] **Endpoints**: Audit hardcoded IP list (`162.159...`). Is it current?
    - [ ] **Account**: Verify API checks (`/reg/{id}`).

### Phase 8: Advanced Routing & Chaining (Feature B)
- [ ] **Chaining Logic (`src/configstream/intelligence/chaining.py`)**
    - [ ] **Geodesic**: Verify `haversine` formula accuracy vs `geopy`.
    - [ ] **Database**: Check `COUNTRIES` lat/lon accuracy (80+ entries).
    - [ ] **Strategies**:
        - [ ] **Intranet**: IR -> Relay -> Exit. Verify relay reachability.
        - [ ] **IPv6**: Dual-stack Relay -> IPv6 Exit.
        - [ ] **Anonymity**: 3-hop construction.
- [ ] **Scoring System**:
    - [ ] **Weights**: Review `PROTOCOL_SCORES` (Stealth vs Speed).
    - [ ] **Censorship Map**: Is `CENSORSHIP_LEVELS` map current?

### Phase 9: Washer & Revival Logic
- [ ] **Washer Core (`src/configstream/intelligence/washer/core.py`)**
    - [ ] **Loop Prevention**: Check for infinite revival cycles (Dead -> Revive -> Fail -> Dead).
    - [ ] **Scanner Integration**: Does `fetch_clean_ips` block the main loop?
- [ ] **Circuit Breaker (`src/configstream/intelligence/circuit_breaker.py`)**
    - [ ] **State Machine**: Verify Open -> Half-Open -> Closed transitions.
    - [ ] **Leakage**: How many requests pass in Half-Open state?

## Group F: Operations, Security, & Tools

### Phase 10: Security & Cryptography
- [ ] **Log Sanitization**:
    - [ ] **Verification**: Ensure `SecurityValidator.sanitize_log_message` runs on every log call involving external data.
- [ ] **Injection Defense**:
    - [ ] **Config**: Verify `yaml.safe_load`.
    - [ ] **Shell**: Ensure no `shell=True` in subprocess calls involving user input.
- [ ] **Crypto Module (`src/configstream/crypto/`)**:
    - [ ] **Signer**: Audit `ed25519` signature implementation.
    - [ ] **Stego**: Audit `Fernet` (AES-128-CBC) usage. Is the key rotated?
    - [ ] **HMAC**: Verify integrity checks on steganography payloads.

### Phase 11: Operational Tools & CLI
- [ ] **Bot CLI (`src/configstream/bot_cli.py`)**
    - [ ] **Token**: Verify `TELEGRAM_BOT_TOKEN` isn't logged.
    - [ ] **Reliability**: Check network error handling (don't crash main process).
- [ ] **Maintenance Scripts**:
    - [ ] `clean_security_issues.py`: Logic check (safe deletion?).
    - [ ] `publish_ipfs.py`: API Secret handling.
    - [ ] `pip_audit_wrapper.py`: **Fix the `check=False` bug**.

## Group G: Verification & Artifacts

### Phase 12: Testing Engine
- [ ] **Go Sidecar (`src/configstream/testers/go.py`)**
    - [ ] **IPC**: Audit NDJSON stream handling (buffering, encoding).
    - [ ] **Process**: Verify `_ensure_process` locking logic (avoid double spawn).
    - [ ] **Panic**: Ensure Python handles Go panics gracefully (restart).
- [ ] **Python Fallback (`src/configstream/testers/python.py`)**
    - [ ] **TCPing**: Audit `asyncio.open_connection` usage. Handle `ConnectionRefused` vs `Timeout`.
    - [ ] **Jitter**: Verify randomization to prevent thundering herds.

### Phase 13: Output & Converters
- [ ] **File Operations (`src/configstream/async_file_ops.py`)**
    - [ ] **Atomicity**: Verify `write -> flush -> sync -> rename` pattern.
- [ ] **Converters (`src/configstream/converters/`)**:
    - [ ] **SingBox**: Audit `to_singbox_outbound`. Check `singbox_utils` for string corruption (`str(None)` -> `"None"`).
    - [ ] **Clash**: Verify `to_clash_proxy` mappings.
- [ ] **Artifacts**:
    - [ ] **Cleanup**: Verify `output/` pruning logic.
    - [ ] **Versioning**: Check `proxies.json` vs `proxies.old.json` rotation.

### Phase 14: Frontend & API
- [ ] **Frontend (`frontend/`)**:
    - [ ] **XSS**: Check `proxies.json` rendering (`textContent` vs `innerHTML`).
    - [ ] **CSP**: Verify `Content-Security-Policy` headers.
- [ ] **API (`src/configstream/server.py`)**:
    - [ ] **Input Validation**: Validate `country` (2-char), `protocol`.
    - [ ] **Path Traversal**: Audit `SAFE_PATH_PATTERN` (`^[a-zA-Z0-9_-]+$`).
    - [ ] **Rate Limiting**: Is middleware configured?
    - [ ] **CORS**: Check `ALLOWED_ORIGIN_REGEX`. Is it too permissive?

## Group H: Maintenance & Future Proofing

### Phase 15: Edge Case Handling
- [ ] **Hedged Requests**: Audit `src/configstream/hedged_requests.py` for zombie tasks.
- [ ] **DNS Prewarming**: Verify `src/configstream/dns_prewarm.py` error masking (`return_exceptions=True`).
- [ ] **Freshness**: Audit `src/configstream/freshness.py` timezone logic (`replace("Z", ...)`).

### Phase 16: Scalability & Compliance
- [ ] **Horizontal Scaling**: Can multiple instances share `history.db`? (SQLite Locking).
- [ ] **Migration**: Plan for PostgreSQL.
- [ ] **Legal**: Verify License Headers (AGPLv3).
- [ ] **GDPR**: Verify `history.db` anonymizes user IPs.

### Phase 17: Disaster Recovery
- [ ] **Backup**: Audit `src/configstream/backup.py`.
    - [ ] **Locking**: Uses `immutable=1`?
    - [ ] **Restoration**: Test `restore_database` against corrupt files.

### Phase 18: Refactoring Strategy
- [ ] **Split Brain**: Map Python vs Go logic divergence.
- [ ] **Code Duplication**: Merge `adapters.py` / `adapters_base.py`.
- [ ] **Type Hints**: Enforce `mypy --strict`.

### Phase 19: Toolchain & Utilities Deep Dive
- [ ] **Wrapper Audits**:
    - [ ] `pip_audit_wrapper.py`: **Critical Fix** needed.
    - [ ] `warp_validator.py`: Review hardcoded IPs.

### Phase 20: Architecture & Patterns
- [ ] **Singleton**: Audit `GeoIPResolver` instantiation.
- [ ] **DI**: Review `app_settings` passing.

## Phase 21: Final Verification & QA Strategy
- [ ] **Profiling**: `scripts/profile_performance.py`.
- [ ] **Regression**: `tests/test_converters.py`.
- [ ] **Linting**: `flake8`, `black`.
