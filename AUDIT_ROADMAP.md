# Comprehensive Audit Roadmap for ConfigStream

This document outlines a deep, extensive, end-to-end audit plan for the ConfigStream project. The goal is to identify bugs, logical inconsistencies, dead code, concurrency issues, security vulnerabilities, and technical debt across the entire codebase.

## Phase 1: Project Configuration & Architecture Validity

### 1.1. Dependency & Environment Analysis
- [ ] **Dependency Compatibility**:
    - [ ] Analyze `pyproject.toml` for strict vs loose version pinning (e.g., `^` vs `~=`).
    - [ ] Check `requirements.txt` for consistency with `pyproject.toml`.
    - [ ] Audit `package.json` (frontend) for deprecated npm packages.
    - [ ] Verify `setup.py` (if exists) doesn't conflict with `pyproject.toml`.
- [ ] **Docker Security**:
    - [ ] Audit `Dockerfile` for non-root user enforcement (`USER appuser`).
    - [ ] Verify multi-stage builds are used to reduce image size.
    - [ ] Check for sensitive args/envs baked into layers (e.g., `ARG GITHUB_TOKEN`).
    - [ ] Validate `docker-compose.yml` network isolation rules.
- [ ] **Env Var Handling**:
    - [ ] Verify `src/configstream/config.py` uses `pydantic-settings` correctly.
    - [ ] Check validation logic for all vars in `.env.example`.
    - [ ] Ensure sensitive vars (keys, tokens) are marked `SecretStr`.
- [ ] **Pre-commit Hooks**:
    - [ ] Review `.pre-commit-config.yaml` for `gitleaks` (secret scanning).
    - [ ] Ensure `black`, `isort`, and `flake8` config matches project standards.
- [ ] **CI/CD Workflow**:
    - [ ] Audit `.github/workflows/` for secure secret injection.
    - [ ] Check for unlimited timeouts in jobs (cost risk).
    - [ ] Verify 3rd party actions are pinned by commit hash, not tag.
- [ ] **Build Scripts**:
    - [ ] **`scripts/build_wasm.sh`**:
        - [ ] Verify strict Go version check (e.g., `1.21.0` vs `1.21`).
        - [ ] Validate integrity of `wasm_exec.js` copy (checksum?).
        - [ ] Ensure `-trimpath` is used for reproducible builds.

### 1.2. Architecture & Documentation Compliance
- [ ] **`AGENTS.md` Alignment**:
    - [ ] Scan codebase for "Blocking I/O" violations (e.g., `requests.get` inside async).
    - [ ] Verify "Sanitized Logging" directive is respected in all new modules.
- [ ] **Module Boundaries**:
    - [ ] Check for circular imports using `pylint --check-graph`.
    - [ ] Verify core logic (`src/configstream/pipeline_core`) doesn't import CLI/UI layers.
- [ ] **Dead Code Detection**:
    - [ ] Run `vulture` or similar to find unused code.
    - [ ] Check `src/configstream/utils/` for orphaned helper functions.
    - [ ] Review `scripts/` for obsolete maintenance scripts.
- [ ] **Split Brain & Redundancies**:
    - [ ] **Protocol Parsing**: Compare `src/configstream/converters/singbox.py` vs Go sidecar. Are all protocols in Sync?
    - [ ] **Scoring Logic**: Compare `src/configstream/score.py` (if exists) vs `sort_proxies_pareto`.
    - [ ] **Vector Generation**: Compare `vectors.py` feature hashing vs any frontend logic.
- [ ] **Legacy Cleanups**:
    - [ ] Audit `src/configstream/adapters.py` vs `adapters_base.py`.
    - [ ] Check for deprecated "v1" implementations in `parsers/`.

## Phase 2: Core Pipeline Orchestration (`src/configstream/pipeline.py`)

### 2.1. Concurrency & Event Loop Management
- [ ] **Blocking Calls**:
    - [ ] Scan `run_full_pipeline` for synchronous file I/O.
    - [ ] Audit `processing_consumer` for CPU-bound tasks not wrapped in `run_in_executor`.
    - [ ] Check `subprocess.Popen` usage: is it truly non-blocking?
- [ ] **Task Management**:
    - [ ] Audit `asyncio.create_task` usage:
        - [ ] Are references held (`background_tasks` set)?
        - [ ] Are exceptions retrieved/handled via `add_done_callback` or `gather`?
    - [ ] Check for "fire-and-forget" tasks that might swallow errors.
- [ ] **Graceful Shutdown**:
    - [ ] Simulate `SIGINT` (Ctrl+C).
    - [ ] Verify `processing_consumer` cancels immediately.
    - [ ] Ensure `source_producer` stops fetching.
    - [ ] Verify `Vwarp` tunnel process receives `SIGTERM`.
    - [ ] Check `EventStream` flush on exit.
- [ ] **Queue Bounding**:
    - [ ] Verify `work_queue = asyncio.Queue(maxsize=...)`.
    - [ ] Test behavior when queue is full (does producer pause?).
- [ ] **Deduplication Logic**:
    - [ ] Audit `filter_unique_endpoints`:
        - [ ] Does it handle IP vs Domain duplicates correctly?
        - [ ] Does it handle port differences?
    - [ ] Audit `seen_keys` usage:
        - [ ] Is it a `set` or `dict`?
        - [ ] Is memory usage bounded (LRU)?

### 2.2. Error Handling & Resilience
- [ ] **Exception Swallowing**:
    - [ ] Search for `except Exception:` (bare excepts).
    - [ ] Ensure critical errors (OOM, Disk Full) are re-raised.
- [ ] **Global Error Propagation**:
    - [ ] If `GeoIPResolver` fails init, does pipeline continue?
    - [ ] If `SourceQualityTracker` DB is locked, does pipeline stall?
- [ ] **Timeout Management**:
    - [ ] Audit `AdaptiveTimeout` logic in `src/configstream/intelligence/adaptive_timeout.py`.
        - [ ] Can timeout drop below 0?
        - [ ] Does it oscillate wildly?
    - [ ] Verify `httpx` timeouts are enforced.

### 2.3. Resource Management
- [ ] **File Descriptors**:
    - [ ] Check `EventStream` file handling.
    - [ ] Check `output_handler` file usage.
    - [ ] Ensure `ulimit` is respected or handled.
- [ ] **Subprocess Leaks**:
    - [ ] Deep review of `Vwarp` tunnel lifecycle.
    - [ ] Verify orphan cleanup if parent crashes (`atexit`?).

## Phase 3: Data Ingestion & Parsing Layer

### 3.1. Fetcher Module (`src/configstream/fetcher*`)
- [ ] **Facade Integrity**:
    - [ ] Verify `fetcher.py` API matches `fetcher_core/` implementation.
    - [ ] Ensure deprecation warnings are present.
- [ ] **Streaming Safety**:
    - [ ] Verify `httpx` streaming logic.
    - [ ] Check `MAX_RESPONSE_SIZE` (prevent memory bomb).
    - [ ] Verify `iter_bytes` usage.
- [ ] **Encoding Handling**:
    - [ ] Test with `utf-8`, `latin-1`, `gbk` (common in proxies).
    - [ ] Verify fallback strategy.
- [ ] **DNS Leaks**:
    - [ ] Audit `dns_batch_resolver.py`:
        - [ ] Does it leak DNS queries to system resolver?
        - [ ] Does it support DoH/DoT?
        - [ ] Is caching strictly respected (TTL)?

### 3.2. Parsers & Protocol Compliance (`src/configstream/parsers/`)
- [ ] **Fuzzing Resistance**:
    - [ ] Test parsers with random byte strings.
    - [ ] Test with "recursive" base64 strings.
    - [ ] Check RegEx for ReDoS vulnerabilities.
- [ ] **Specific Protocol Audits**:
    - [ ] **VLESS**:
        - [ ] Verify UUID validation (hex only).
        - [ ] Audit `Reality` flow: `pbk` and `sid` extraction.
        - [ ] Check fallback for missing `flow`.
    - [ ] **VMess**:
        - [ ] Verify AEAD check.
        - [ ] Check `alterId` logic (force 0?).
        - [ ] Verify `scy` vs `cipher` priority.
    - [ ] **Trojan**:
        - [ ] Check TLS compulsion.
        - [ ] Verify `sni` extraction.
    - [ ] **Shadowsocks (SS/SIP002)**:
        - [ ] Validate Base64 padding for `user:pass`.
        - [ ] Check plugin param parsing (`obfs-local`, `v2ray-plugin`).
    - [ ] **Shadowsocks 2022**:
        - [ ] Verify `method` format (e.g., `2022-blake3-aes-128-gcm`).
        - [ ] Check key length validation.
    - [ ] **Hysteria / Hysteria2**:
        - [ ] Check `up_mbps`/`down_mbps` parsing (string vs int).
        - [ ] Verify `obfs` vs `obfs-type` field handling.
    - [ ] **Tuic**:
        - [ ] Verify `uuid` requirement.
        - [ ] Check `congestion_control` mapping (standard vs custom).
    - [ ] **WireGuard**:
        - [ ] Verify `private_key` length (Base64).
        - [ ] Check `reserved` bytes parsing (list of 3 ints).
        - [ ] Audit IP generation for WARP (collision risk in `to_singbox_outbound`).
    - [ ] **SSH**:
        - [ ] Check `private_key` vs `password` precedence.
        - [ ] Verify `host_key` validation.
    - [ ] **SOCKS5 / SOCKS4**:
        - [ ] Verify `version` field inference.
        - [ ] Check auth (user/pass) extraction.
    - [ ] **HTTP / HTTPS**:
        - [ ] Check `tls` flag logic.
        - [ ] Verify basic auth extraction.
    - [ ] **NaiveProxy**:
        - [ ] Check `padding` support.
        - [ ] Verify `https` wrapping logic.
    - [ ] **Base64**:
        - [ ] Verify padding fix logic.
        - [ ] Check handling of URL-safe vs standard base64.
- [ ] **Renaming & Remarks (`src/configstream/tagging.py`)**:
    - [ ] **Regex Safety**: Audit `format_proxy_name` cleanup regex.
    - [ ] **Unquote**: Check `unquote` usage for crash on invalid inputs.
    - [ ] **Template Injection**: Ensure `str.format` doesn't access internal attributes.
- [ ] **Magic Numbers**:
    - [ ] Identify `len(hostname) > 255`.
    - [ ] Identify port `1-65535` checks.

## Phase 4: Testing Engine (`src/configstream/testers/`)

### 4.1. Go Sidecar Integration (`src/configstream/testers/go.py`)
- [ ] **Communication Protocol (NDJSON)**:
    - [ ] Audit stdin/stdout handling.
    - [ ] Check buffering: does it deadlock if buffer fills?
    - [ ] Handle partial JSON lines.
- [ ] **Process Lifecycle**:
    - [ ] Audit `_heartbeat_loop`: frequency vs load.
    - [ ] Audit `_ensure_process`: locking logic (avoid double spawn).
- [ ] **Panic Handling**:
    - [ ] Check stderr reader logic.
    - [ ] Verify auto-restart on panic code 2.
- [ ] **SingBox Integration**:
    - [ ] Verify generated config structure matches `sing-box` schema.
    - [ ] Check `route` object generation (geo-site/ip rules).
- [ ] **Honeypot Detection**:
    - [ ] Verify `check_honeypot` logic in Go.
    - [ ] Is it checking strictly (port 80/443 vs any port)?
    - [ ] Are false positives minimized?

### 4.2. Python Fallback (`src/configstream/testers/python.py`)
- [ ] **TCPing**:
    - [ ] Is it `asyncio.open_connection` based?
    - [ ] Does it measure "Connect" or "Handshake" time?
    - [ ] Does it handle `ConnectionRefused` vs `Timeout` differently?
    - [ ] Check for timeout jitter implementation.
- [ ] **Performance Bottlenecks**:
    - [ ] Check for heavy crypto loops.
    - [ ] Check for excessive object creation.
- [ ] **Protocol Parity**:
    - [ ] Does Python tester verify VLESS/Reality? (Likely not, verify limitation).

### 4.3. Caching & State
- [ ] **TestResultCache**:
    - [ ] Audit `save()`: is it atomic?
    - [ ] Verify `get/set` thread safety.
- [ ] **Cache Invalidation**:
    - [ ] Check `TTL` logic.
    - [ ] Does `retest_scheduler` respect "dead" vs "alive" intervals?

## Phase 5: Intelligence & "Smart" Features

### 5.1. Proxy Washer & Revival (`src/configstream/intelligence/washer/`)
- [ ] **Infinite Loops**:
    - [ ] Analyze `ProxyWasher.wash_failed` in `core.py`.
    - [ ] Prevent: Dead -> Revive -> Fail -> Dead loop.
- [ ] **WARP Integration**:
    - [ ] Audit `warp_scraper.py`:
        - [ ] Is it using legitimate endpoints (`ircfspace/warpendpoint`)?
        - [ ] Rate limit compliance.
    - [ ] Check `key_generator.py`:
        - [ ] Algorithm correctness.
- [ ] **Scanner Logic**:
    - [ ] Audit `fetch_clean_ips`: does it block?
    - [ ] Verify integration with `vwarp` official project (e.g., MASQUE support).
- [ ] **Vwarp Chaining**:
    - [ ] Verify chain construction in `chaining.py`: `Client -> WARP -> Proxy`.
    - [ ] Check handling of chain failure (blame WARP or Proxy?).

### 5.2. Scoring & Ranking
- [ ] **Scorer Logic**:
    - [ ] Audit `src/configstream/pipeline_core/sorter.py`.
    - [ ] Check Pareto scoring math: `(norm_latency * 0.5) + ((1.0 - reliability) * 0.3) + ((1.0 - uptime) * 0.2)`.
    - [ ] Is pre-calculation of stats efficient (bulk fetch)?
- [ ] **Ranker**:
    - [ ] Verify sorting stability (Python `sort` is stable, but are keys unique?).
    - [ ] Handle proxies with `latency=None` (assigned 9999).

### 5.3. Adaptive Logic
- [ ] **AdaptiveTimeout**:
    - [ ] Review AIMD algorithm (Additive Increase/Multiplicative Decrease).
    - [ ] Check boundaries (Min/Max timeout).
- [ ] **CircuitBreaker**:
    - [ ] Verify "Open" state logic in `src/configstream/intelligence/circuit_breaker.py`.
    - [ ] Check "Half-Open" probe logic.
- [ ] **Reshard Dynamic**:
    - [ ] Analyze `src/configstream/sharding.py`.
    - [ ] Verify `blake2b` bucketing determinism (`buckets=256`).
    - [ ] Check `save_shard_metadata` logic.

### 5.4. Advanced Chaining & Routing (`src/configstream/intelligence/chaining.py`)
- [ ] **Geodesic Logic**:
    - [ ] Audit `haversine` implementation vs `geopy`.
    - [ ] Check `COUNTRIES` coordinate accuracy (80+ entries).
- [ ] **Chain Strategies**:
    - [ ] **Intranet**: Verify "IR -> Relay -> Exit" logic.
    - [ ] **IPv6**: Audit "Dual Stack -> IPv6 Only" selection.
    - [ ] **Streamer**: Check "Fast Protocol -> Streaming Region" selection.
    - [ ] **Censorship Resistant**: Verify multi-hop stealth routing logic.
    - [ ] **High Anonymity**: Audit 3-hop chain construction.
- [ ] **Protocol Scoring**:
    - [ ] Review `PROTOCOL_SCORES` weights (Stealth vs Speed).
    - [ ] Is `CENSORSHIP_LEVELS` map up-to-date?

### 5.5. Scanner & Vwarp (Upstream Alignment)
- [ ] **Upstream Compatibility**:
    - [ ] Check if `src/go/tester` implements MASQUE tunneling (Vwarp feature).
    - [ ] Verify `Psiphon` integration points (if any).
    - [ ] Audit `Warp-in-Warp` chaining logic against official Vwarp specs.
- [ ] **Endpoint Scraper**:
    - [ ] Verify `WIREGUARD_REGEX` robustness.
    - [ ] Check `warp://` URI parsing compliance.

## Phase 6: Cross-Cutting Concerns

### 6.1. Security (`src/configstream/security*`)
- [ ] **Log Sanitization**:
    - [ ] **CRITICAL**: Verify `SecurityValidator.sanitize_log_message` applied to:
        - [ ] Source URLs.
        - [ ] Proxy Config strings.
        - [ ] Error messages containing configs.
- [ ] **Injection Prevention**:
    - [ ] Ensure configs are treated as data, not code.
    - [ ] Check `yaml.safe_load` vs `yaml.load`.
- [ ] **Blocklists**:
    - [ ] Verify `DEFAULT_BLOCKLIST` update source (FireHol?).
    - [ ] Check IP range lookup efficiency (Trie vs List).
- [ ] **Crypto (`src/configstream/crypto/`)**:
    - [ ] Audit `signer.py`:
        - [ ] Is `ed25519` implementation standard?
        - [ ] Is private key loaded from secure Env/File?
        - [ ] Are signatures deterministic?

### 6.2. Logging & Metrics
- [ ] **Log Noise**:
    - [ ] Check `DEBUG` vs `INFO` levels.
    - [ ] Debounce repetitive logs (e.g., "Connection refused").
- [ ] **Stats & Tracking**:
    - [ ] Audit `PipelineStats` counters (atomic increments?).
    - [ ] Check `ProxyHistoryTracker`:
        - [ ] Data retention policy (prune old records).
        - [ ] Concurrency safety (sqlite lock?).
- [ ] **Metric Cardinality (`src/configstream/metrics.py`)**:
    - [ ] Check `protocol_counts`: can user input create infinite keys?
    - [ ] Verify `save_to_file` atomic write.

### 6.3. Concurrency Safety
- [ ] **Race Conditions**:
    - [ ] Audit `seen_keys` access.
    - [ ] Audit `stats` updates.
- [ ] **Shared Singletons**:
    - [ ] Verify `GeoIPResolver` instance sharing.
    - [ ] Verify `AnomalyDetector` internal state lock.

## Phase 7: Frontend & Output Artifacts

### 7.1. Frontend (`frontend/`)
- [ ] **XSS Audit**:
    - [ ] Check `proxies.json` rendering in JS.
    - [ ] Escaping of `remarks` field.
    - [ ] Escaping of `details` object keys/values.
- [ ] **Performance**:
    - [ ] Test `proxies.html` with 10k items (Virtual Scrolling?).
- [ ] **Artifacts**:
    - [ ] Check `.gitignore` for `output/`.
    - [ ] Verify `clean` step before build.
    - [ ] Audit `generate_favicons.py` logic.

### 7.2. Output Generation (`src/configstream/output.py`)
- [ ] **Atomic Writes**:
    - [ ] Ensure `write -> flush -> fsync -> rename` pattern.
- [ ] **Format Validity**:
    - [ ] Validate generated JSON against schema.
    - [ ] Validate YAML syntax.
- [ ] **Converters (`src/configstream/converters/`)**:
    - [ ] **SingBox**:
        - [ ] Audit `to_singbox_outbound` in `singbox.py`.
        - [ ] Check `WireGuard` IP generation (collision risk?).
        - [ ] Check `Hysteria2` obsoleted fields.
        - [ ] Verify "Stealth Profile" application.
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
    - [ ] Check `SAFE_PATH_PATTERN` regex.
    - [ ] Verify `os.path.commonpath` checks are robust.
- [ ] **Rate Limiting**:
    - [ ] Is there middleware for rate limiting?
    - [ ] Check `admin/notify-update` auth.
- [ ] **WebSocket Security**:
    - [ ] Check max message size (DoS).
    - [ ] Check open connection limits.

### 8.2. Operational Safety
- [ ] **CORS Policy**:
    - [ ] Review `ALLOWED_ORIGIN_REGEX`.
    - [ ] Is it allowing `*` implicitly?
- [ ] **Error Leakage**:
    - [ ] Check `HTTPException` details.
    - [ ] Ensure 500 errors don't expose stack trace.

## Phase 9: Tools & Operational Scripts

### 9.1. Maintenance Scripts
- [ ] **Scripts Audit**:
    - [ ] `clean_security_issues.py`: Logic check.
    - [ ] `publish_ipfs.py`: Secret handling.
    - [ ] `upload_*.py`: Token permissions scope.
- [ ] **Tools Audit**:
    - [ ] `blocklist_manager/`: Source validation.
    - [ ] `latency_tester/`: Concurrency conflicts.

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
    - [ ] Deprecate `bool_parser` if standard exists.

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
    - [ ] Check `history` DB integrity checks.
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
- [ ] **Linting**:
    - [ ] Enforce `flake8` max-complexity.
    - [ ] Enforce `black` formatting.
- [ ] **Documentation**:
    - [ ] Update `README.md` architecture diagram.
    - [ ] Update `AGENTS.md` with new findings.
