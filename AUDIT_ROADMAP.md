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
    - [ ] **Action**: Apply `SensitiveDataFilter` to all handlers or implement a specific `RedactingFormatter` for file outputs. Optionally restrict file permissions (`chmod 600`).
- [ ] **Concurrency Testing Gap**
    - [ ] **Target**: `tests/unit/test_hedged_requests.py`
    - [ ] **Check**: Does the test actually run concurrent coroutines or just mock them sequentially?
    - [ ] **Action**: Verify usage of `asyncio.sleep` with random jitters to simulate real race conditions.

## Group B: Foundations & Infrastructure

### Phase 1: Environment & Dependency Architecture
- [ ] **Dependency Management (`pyproject.toml`, `requirements.txt`)**
    - [ ] **Version Pinning**: Analyze strict (`==`) vs loose (`^`, `~=`) pinning. Recommendation: Strict for app, loose for libs. Verify semantic versioning compliance.
    - [ ] **Hash Integrity**: Ensure `requirements.txt` uses `--generate-hashes` to prevent supply chain attacks.
    - [ ] **Conflict Analysis**: Cross-check `setup.py` (if exists) vs `pyproject.toml` for `install_requires` drift.
    - [ ] **Frontend Deps**: Audit `package.json` for deprecated packages (`npm audit`). Check license compliance (AGPL compat).
    - [ ] **Python 3.12+**: Check for removed stdlib modules (`distutils`, `imp`, `cgi`). Run `pylint --py3k`.
    - [ ] **Dev vs Prod**: Verify separation of `dev-dependencies` (e.g., `pytest`, `mypy`) from production requirements.
- [ ] **Container Security (`Dockerfile`)**
    - [ ] **Privilege Escalation**: Verify `USER appuser` is enforced. Check for `sudo` usage.
    - [ ] **Attack Surface**: Verify multi-stage builds (`COPY --from=builder`). Are build tools (gcc, git) removed in final image? Use `pip install --no-cache-dir`.
    - [ ] **Secret Leaks**: Check `ARG` instructions for baked-in secrets. Use `RUN --mount=type=secret`.
    - [ ] **Network Isolation**: Validate `docker-compose.yml` networks. Is the database isolated from the public interface?
    - [ ] **Distroless**: Evaluate feasibility of using distroless base images for Python/Go.
- [ ] **Build System (`scripts/build_wasm.sh`)**
    - [ ] **Reproducibility**: Ensure `-trimpath` and `-ldflags "-w -s"` are used.
    - [ ] **Integrity**: Compare `wasm_exec.js` checksum against the Go compiler version.
    - [ ] **Version Lock**: Verify script fails if Go version != `1.21.x` (strict check).

### Phase 2: Configuration & Constants
- [ ] **Configuration Logic (`src/configstream/config.py`)**
    - [ ] **Type Safety**: Verify `pydantic-settings` usage. Are `extra="forbid"` and `strict=True` enabled?
    - [ ] **Secret Handling**: Ensure `SecretStr` is used for all keys/tokens to prevent accidental `repr()` logging.
    - [ ] **Env Validation**: Check `.env.example` coverage. Are all required vars validated at startup?
    - [ ] **Missing Vars**: Identify code accessing `os.getenv` directly instead of using the config object.
- [ ] **Global Constants (`src/configstream/constants.py`)**
    - [ ] **Security Lists**: Verify `DANGEROUS_PORTS` completeness (add 27017 Mongo, 6379 Redis).
    - [ ] **Blocking Lists**: Check `SUSPICIOUS_DOMAINS` (is `127.0.0.1` blocked?) and `BLOCKED_DOMAINS` (GitHub raw links handling).
    - [ ] **Limits**: Audit `MAX_B64_INPUT_SIZE` (10MB). Is it sufficient for large subs? Is `MAX_CONFIG_LINE_LENGTH` (10k) safe against DoS?
    - [ ] **Protocol Colors**: Verify `PROTOCOL_COLORS` covers all 28+ supported protocols.
- [ ] **Pre-commit Hooks**:
    - [ ] Review `.pre-commit-config.yaml` for `gitleaks`. Is the regex pattern up to date?
    - [ ] Ensure `black`, `isort`, and `flake8` config matches project standards.

### Phase 2b: Architecture & Codebase Health
- [ ] **`AGENTS.md` Alignment**:
    - [ ] Scan codebase for "Blocking I/O" violations (e.g., `requests.get` inside async).
    - [ ] Verify "Sanitized Logging" directive is respected in all new modules.
- [ ] **Module Boundaries**:
    - [ ] Check for circular imports (`pylint --check-graph`).
    - [ ] Verify core logic (`pipeline_core`) doesn't import CLI/UI layers.
    - [ ] **Public API**: Ensure `__all__` is defined in `__init__.py`.
- [ ] **Dead Code Detection**:
    - [ ] Run `vulture` to find unused code.
    - [ ] Audit `src/configstream/plugins/` for unused modules.
    - [ ] Review `scripts/` for obsolete maintenance scripts.
- [ ] **Data Classes**:
    - [ ] Check `__slots__` usage in `Proxy` models to reduce memory footprint.
    - [ ] Verify immutability (`frozen=True`) where appropriate.

## Group C: Core Data Plane (Ingestion & Parsing)

### Phase 3: Fetcher & Networking
- [ ] **Fetcher Module (`src/configstream/fetcher*`)**
    - [ ] **Facade Integrity**: Verify `fetcher.py` API parity with `fetcher_core/`. Ensure deprecation warnings.
    - [ ] **Streaming Safety**:
        - [ ] Verify `httpx.stream()` usage and `iter_bytes`.
        - [ ] **Memory Bomb**: Check `MAX_RESPONSE_SIZE` logic. Does it `raise` immediately if accumulated bytes > limit?
    - [ ] **Encoding Handling**:
        - [ ] Test with `utf-8`, `latin-1`, `gbk`. Verify fallback strategy (`chardet`).
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
    - [ ] **VLESS**: UUID (Hex, 32/36 chars). Reality (`pbk`, `sid`). Fallback for missing `flow`.
    - [ ] **VMess**: AEAD (`alterId=0`). `scy` vs `cipher`.
    - [ ] **Trojan**: TLS compulsion. `sni` extraction from `peer` or `sni`.
    - [ ] **Shadowsocks**: SIP002 (Base64 padding). Legacy (`ss://method:pass@host:port`). Plugins (`obfs-local`, `v2ray-plugin` decoding).
    - [ ] **Shadowsocks 2022**: Method (`2022-blake3...`). Key length validation.
    - [ ] **Hysteria / Hysteria2**: Bandwidth units ("Mbps"). `obfs` vs `obfs-type`.
    - [ ] **Tuic**: UUID check. Congestion control (`bbr` mapping).
    - [ ] **WireGuard**: Keys (Base64 44 chars). Reserved bytes (int list). MTU defaults.
    - [ ] **SSH**: `private_key` vs `password`. Host key validation.
    - [ ] **NaiveProxy**: Padding support. HTTPS wrapping logic.
    - [ ] **Base64**: Padding fix (`=` vs `==`). URL-safe vs standard characters.
- [ ] **Metadata Extraction (`src/configstream/tagging.py`, `country_inferrer.py`)**
    - [ ] **Tagging**: Audit `format_proxy_name` regex for catastrophic backtracking. Check `unquote` usage.
    - [ ] **Inference**: Verify `_EXCLUDED_CODES` list (e.g., "ID", "NO", "ON"). Check for false positives in complex remarks.

### Phase 4b: Transport & Internal Vectors
- [ ] **Steganography Transport (`src/configstream/transport/stego.py`)**
    - [ ] **Magic Marker**: Ensure `MAGIC_MARKER` bytes don't collide with PNG format.
    - [ ] **Image Validity**: Verify append-only logic preserves image structure.

## Group D: Core Control Plane (Orchestration)

### Phase 5: Pipeline Orchestration & Concurrency
- [ ] **Orchestrator (`src/configstream/pipeline.py`)**
    - [ ] **Blocking Calls**: Scan for `shutil.copy`, `open()`, `time.sleep` in async paths.
    - [ ] **Subprocess**: Check `subprocess.Popen` (blocking) vs `asyncio.create_subprocess_exec`.
- [ ] **Task Lifecycle**:
    - [ ] **Reference Holding**: Verify `asyncio.create_task` references are stored (`background_tasks`) to prevent GC.
    - [ ] **Exception Retrieval**: Ensure all tasks have `add_done_callback` or are `await`ed. Check for fire-and-forget swallowing errors.
- [ ] **Queue Management**:
    - [ ] **Backpressure**: Verify `asyncio.Queue(maxsize=...)` usage. Does producer pause?
    - [ ] **Deadlocks**: Check for circular dependencies in queue consumers.
- [ ] **Graceful Shutdown**:
    - [ ] **Signals**: Verify `SIGINT`/`SIGTERM` handling.
    - [ ] **Cancellation**: Ensure `processing_consumer` cleans up (closes files) on `CancelledError`.
    - [ ] **Zombies**: Verify Vwarp tunnel process is explicitly killed (`proc.kill()` and `wait()`).
- [ ] **Concurrency Safety**:
    - [ ] **Race Conditions**: Audit `seen_keys` and `stats` updates.
    - [ ] **Shared Singletons**: Verify `GeoIPResolver` and `AnomalyDetector` instance sharing and thread-safety.

### Phase 6: Resilience & State
- [ ] **Error Handling**:
    - [ ] **Swallowing**: Grep for `except Exception: pass`.
    - [ ] **Critical Failures**: Ensure DB locks or Disk Full trigger a hard stop or alert.
    - [ ] **Global Propagation**: If `GeoIPResolver` fails init, does pipeline crash or fallback?
- [ ] **Timeout Logic (`src/configstream/intelligence/adaptive_timeout.py`)**:
    - [ ] **Bounds**: Ensure timeout cannot go `< 1s` or `> 60s`.
    - [ ] **Smoothing**: Check EMA (Exponential Moving Average) implementation stability.
- [ ] **Deduplication**:
    - [ ] **Logic**: Audit `filter_unique_endpoints` (IP vs Domain).
    - [ ] **State**: Check `seen_keys` size management (LRU or bloom filter?).
    - [ ] **Locking**: Verify `seen_lock` usage in `processing_consumer`.
- [ ] **Logging & Metrics**:
    - [ ] **Log Noise**: Debounce repetitive logs.
    - [ ] **Stats**: Verify `PipelineStats` atomic updates.
    - [ ] **Metric Cardinality**: Check `protocol_counts` for DoS via infinite keys.

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
- [ ] **Scanner Integration**:
    - [ ] Check `VwarpTool.scan_endpoints` integration with `ProxyWasher`.

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
    - [ ] **Pareto Math**: Check formula `(norm_latency * 0.5) + ...`.
    - [ ] **Censorship Map**: Is `CENSORSHIP_LEVELS` map current?
- [ ] **Vector Intelligence (`src/configstream/intelligence/vectors.py`)**
    - [ ] **Feature Hashing**: Audit `_compute_vector` logic and hash collisions. Verify dimensions capture variance.

### Phase 9: Washer & Revival Logic
- [ ] **Washer Core (`src/configstream/intelligence/washer/core.py`)**
    - [ ] **Loop Prevention**: Check for infinite revival cycles (Dead -> Revive -> Fail -> Dead).
    - [ ] **Scanner Integration**: Does `fetch_clean_ips` block the main loop?
- [ ] **Circuit Breaker (`src/configstream/intelligence/circuit_breaker.py`)**
    - [ ] **State Machine**: Verify Open -> Half-Open -> Closed transitions.
    - [ ] **Leakage**: How many requests pass in Half-Open state?
- [ ] **Dynamic Resharding**:
    - [ ] Analyze `src/configstream/sharding.py`. Verify `blake2b` bucketing determinism and atomic metadata saves.

## Group F: Operations, Security, & Tools

### Phase 10: Security & Cryptography
- [ ] **Log Sanitization**:
    - [ ] **Verification**: Ensure `SecurityValidator.sanitize_log_message` runs on every log call involving external data.
- [ ] **Injection Defense**:
    - [ ] **Config**: Verify `yaml.safe_load`.
    - [ ] **Shell**: Ensure no `shell=True` in subprocess calls involving user input.
- [ ] **Crypto Module (`src/configstream/crypto/`)**:
    - [ ] **Signer**: Audit `ed25519` signature implementation. Deterministic signatures?
    - [ ] **Stego**: Audit `Fernet` (AES-128-CBC) usage. Is the key rotated?
    - [ ] **HMAC**: Verify integrity checks on steganography payloads.
- [ ] **Blocklists & Secrets**:
    - [ ] **Blocklists**: Verify update source (FireHol?) and HTTPS enforcement. IP range lookup efficiency.
    - [ ] **Secret Rotation**: Check how `WARP_KEY_POOL` handles stale keys.

### Phase 11: Operational Tools & CLI
- [ ] **Bot CLI (`src/configstream/bot_cli.py`)**
    - [ ] **Token**: Verify `TELEGRAM_BOT_TOKEN` isn't logged.
    - [ ] **Reliability**: Check network error handling (don't crash main process).
- [ ] **Maintenance Scripts**:
    - [ ] `clean_security_issues.py`: Logic check (safe deletion?).
    - [ ] `publish_ipfs.py`: API Secret handling.
    - [ ] `pip_audit_wrapper.py`: **Fix the `check=False` bug**.
- [ ] **Tools Audit**:
    - [ ] `blocklist_manager/`: Source validation.
    - [ ] `latency_tester/`: Concurrency conflicts.
- [ ] **Policy & Schema**:
    - [ ] Verify `schema/proxy_schema.json` covers all protocols.
    - [ ] Check `policy/` directory usage.

## Group G: Verification & Artifacts

### Phase 12: Testing Engine
- [ ] **Go Sidecar (`src/configstream/testers/go.py`)**
    - [ ] **IPC**: Audit NDJSON stream handling (buffering, encoding, partial lines).
    - [ ] **Process**: Verify `_ensure_process` locking logic (avoid double spawn).
    - [ ] **Panic**: Ensure Python handles Go panics gracefully (restart).
    - [ ] **Honeypot**: Verify `check_honeypot` logic and false positives.
- [ ] **Python Fallback (`src/configstream/testers/python.py`)**
    - [ ] **TCPing**: Audit `asyncio.open_connection` usage. Handle `ConnectionRefused` vs `Timeout`.
    - [ ] **Jitter**: Verify randomization to prevent thundering herds.
    - [ ] **Protocol Parity**: Document gaps compared to Go tester (e.g., VLESS Reality).
- [ ] **Caching & State**:
    - [ ] **TestResultCache**: Audit `save()` atomicity and thread-safety.
    - [ ] **Invalidation**: Check TTL logic and "dead" vs "alive" retest intervals.

### Phase 13: Output & Converters
- [ ] **File Operations (`src/configstream/async_file_ops.py`)**
    - [ ] **Atomicity**: Verify `write -> flush -> sync -> rename` pattern.
- [ ] **Converters (`src/configstream/converters/`)**:
    - [ ] **SingBox**: Audit `to_singbox_outbound`. Check `singbox_utils` for string corruption (`str(None)`). Check WireGuard IP generation collisions.
    - [ ] **Clash**: Verify `to_clash_proxy` mappings and Reality support.
- [ ] **Artifacts & Data Integrity**:
    - [ ] **Cleanup**: Verify `output/` pruning logic.
    - [ ] **Versioning**: Check `proxies.json` vs `proxies.old.json` rotation.
    - [ ] **DB Integrity**: Check `history.db` integrity checks.
    - [ ] **Format Validity**: Validate generated JSON/YAML against schema.
    - [ ] **Performance**: Evaluate `orjson` vs standard `json`.

### Phase 14: Frontend & API
- [ ] **Frontend (`frontend/`)**:
    - [ ] **XSS**: Check `proxies.json` rendering (`textContent` vs `innerHTML`). Escape remarks.
    - [ ] **CSP**: Verify `Content-Security-Policy` and SRI headers.
    - [ ] **Performance**: Test with 10k items (Virtual Scrolling?).
    - [ ] **Accessibility**: Check ARIA labels and keyboard navigation.
- [ ] **API (`src/configstream/server.py`)**:
    - [ ] **Input Validation**: Validate `country` (2-char), `protocol`.
    - [ ] **Path Traversal**: Audit `SAFE_PATH_PATTERN` (`^[a-zA-Z0-9_-]+$`).
    - [ ] **Rate Limiting**: Is middleware configured? Check `admin/notify-update` auth.
    - [ ] **CORS**: Check `ALLOWED_ORIGIN_REGEX`. Is it too permissive?
    - [ ] **WebSocket**: Check max message size and connection limits.

## Group H: Maintenance & Future Proofing

### Phase 15: Edge Case Handling
- [ ] **Hedged Requests**: Audit `src/configstream/hedged_requests.py` for zombie tasks.
- [ ] **DNS Prewarming**: Verify `src/configstream/dns_prewarm.py` error masking (`return_exceptions=True`) and cache poisoning risks.
- [ ] **Freshness**: Audit `src/configstream/freshness.py` timezone logic (`replace("Z", ...)`). Check integer overflow.

### Phase 16: Scalability & Compliance
- [ ] **Horizontal Scaling**: Can multiple instances share `history.db`? (SQLite Locking).
- [ ] **Migration**: Plan for PostgreSQL.
- [ ] **Legal**: Verify License Headers (AGPLv3).
- [ ] **GDPR**: Verify `history.db` anonymizes user IPs.

### Phase 17: Disaster Recovery
- [ ] **Backup**: Audit `src/configstream/backup.py`.
    - [ ] **Locking**: Uses `immutable=1`?
    - [ ] **Restoration**: Test `restore_database` against corrupt files. Verify pre-restore backups.

### Phase 18: Refactoring Strategy
- [ ] **Split Brain**: Map Python vs Go logic divergence. Consolidate scoring/parsing.
- [ ] **Code Duplication**: Merge `adapters.py` / `adapters_base.py`.
- [ ] **Type Hints**: Enforce `mypy --strict`.
- [ ] **Utility Audit**: Review `src/configstream/utils/`. Deprecate `bool_parser` if standard exists.

### Phase 19: Toolchain & Utilities Deep Dive
- [ ] **Wrapper Audits**:
    - [ ] `pip_audit_wrapper.py`: **Critical Fix** needed.
    - [ ] `warp_validator.py`: Review hardcoded IPs. Add check for WARP+ License Key.

### Phase 20: Architecture & Patterns
- [ ] **Singleton**: Audit `GeoIPResolver` instantiation.
- [ ] **DI**: Review `app_settings` passing.
- [ ] **Error Handling**: Audit usage of custom exceptions vs standard ones.

## Phase 21: Final Verification & QA Strategy
- [ ] **Profiling**: `scripts/profile_performance.py`. Use `yappi`.
- [ ] **Regression**: `tests/test_converters.py`. `tests/test_pipeline_resilience.py`.
- [ ] **Linting**: `flake8`, `black`.
- [ ] **Documentation**:
    - [ ] Update `README.md` and `AGENTS.md`.
    - [ ] Document Split Brain map.
    - [ ] Ensure `KNOWN_ISSUES.md` is current.
