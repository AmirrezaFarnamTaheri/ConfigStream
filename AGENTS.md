# ConfigStream Agents & Contributors Guidelines

## 1. Project Philosophy & Directives
**Current Status**: `docs/readiness.json` is the canonical release checkpoint and `STATUS.md` is its generated human-readable view. Historical point-in-time audit reports are not active repository truth. Public Pages readiness remains gated on a fresh validated artifact deploy plus `scripts/verify_pages_deployment.py` passing against the live URL.

ConfigStream is a **sovereignty-grade, zero-budget anti-censorship platform**. Every line of code must align with these core tenets:
1.  **Zero Budget**: Do not introduce dependencies on paid APIs, databases, or infrastructure. We rely exclusively on free GitHub Actions/Pages, public APIs, and user-provided resources.
2.  **Resilience**: The system must assume hostile network conditions. It must handle timeouts, blocklists, and unreliable sources gracefully (Fail-Open or Fail-Safe).
3.  **Security**: We operate in a high-risk domain. Logs must be sanitized. Inputs must be validated. No project-operated active scanning of third-party infrastructure. Local scanner tools are opt-in, user-run diagnostics only, and scheduled CI/production must keep active scanning disabled via `ALLOW_ACTIVE_SCANNING=false` (default).

## 2. Architectural Overview
The system follows a **Streaming Pipeline Architecture** (`Producer-Consumer`):

### Canonical Matrices (Source of Truth)
*   **Protocol Matrix (`docs/protocol_matrix.json`)**: Definitive inventory of supported protocols, parser status, and export capabilities.
*   **Output Matrix (`docs/output_matrix.json`)**: Definitive inventory of generated artifacts, client config requirements, and Pages deploy rules.
*   **Claim Ledger (`docs/claim_ledger.json`)**: Tracking of implemented features and their proof (tests/docs/changelog).
*   **Debt Matrix (`docs/DEBT_MATRIX.md`)**: Tracking of technical debt, mocks, and placeholders.
*   **Module Ownership Map (`docs/module_ownership.json`)**: Canonical ownership/import-boundary map for major modules and removed-module replacements.

### Core Components
*   **Producer (`source_producer`)**: Fetches raw data from remote URLs or local files. It pushes raw content into a bounded `asyncio.Queue`.
    *   *Constraint*: Must not block on I/O. Uses `httpx` with adaptive timeouts.
*   **Consumer (`processing_consumer`)**: Pulls from the queue, parses, validates, tests, and aggregates proxies.
    *   *Parallelism*: Scalable via `num_consumers`.
    *   *Constraint*: CPU-intensive tasks (parsing, crypto) must run in `loop.run_in_executor`.
    *   *Revival Loop*: Automatically attempts to revive failed proxies by wrapping them in Cloudflare WARP/Vwarp and re-testing them.
*   **Intelligence Layer**:
    *   `AdaptiveTimeout`: Adjusts timeouts based on historical latency.
    *   `CircuitBreaker`: Fails fast for unstable hosts.
    *   `SecurityValidator`: Enforces protocol compliance and sanitization.
    *   `ProxyWasher` (`intelligence/washer/core.py`): Handles WARP key management and chain generation.

## 3. Coding Standards

### Python
*   **Version**: Python 3.10+ (strict typing required).
*   **Style**: PEP 8. Enforced via `black` and `flake8`.
*   **Concurrency**:
    *   Use `asyncio` for I/O-bound tasks.
    *   Use `ProcessPoolExecutor` or `ThreadPoolExecutor` for CPU-bound tasks (e.g., parsing 10k lines).
    *   **NEVER** use blocking I/O (e.g., `requests`, `time.sleep`) in async functions.
*   **Logging**:
    *   Use `logging.getLogger(__name__)`.
    *   **Sanitization IS MANDATORY**: Wrap URLs/Errors with `SecurityValidator.sanitize_log_message`.
    *   Avoid log spam: Use debouncing (e.g., `CircuitBreaker` warnings) or sampling (e.g., logging only the first 5 dropped lines).

### Type Safety
*   All function signatures must have type hints.
*   Use `Optional`, `List`, `Dict`, `Union` from `typing`.
*   Check your work with `mypy`.

## 4. Specific Component Instructions

### Parsers (`src/configstream/parsers/`)
*   **Robustness**: Inputs are untrusted and often malformed.
    *   Handle trailing garbage in Base64 strings.
    *   Gracefully skip invalid lines without crashing the pipeline.
    *   Log drop rates/reasons at `DEBUG` level (or `WARNING` if failure rate > 50%).
    *   Return type: `extract_config_lines` returns `(List[str], Dict[str, int])` containing configs and drop statistics.
*   **Robust Parsing**:
    *   **Credential Recovery**: For VLESS, Trojan, and Shadowsocks, if the primary credential field (e.g., username for UUID) is empty, the parser **MUST** check query parameters or other fields as a fallback before dropping the proxy.
    *   **Mandatory Fields**: If credentials are still missing after fallback attempts, parser MUST return `None` (drop).
    *   **Method Check**: Shadowsocks method must be valid (not "ss", "shadowsocks").
*   **Protocols**: Support for 20+ protocols (VLESS, VMess, Trojan, SS, SSR, Hysteria, Hysteria2, Tuic, WireGuard, SSH, SOCKS, HTTP, etc.) is required. Ensure correct mapping to the `Proxy` model.
*   **Normalization**:
    *   `https://` -> `http` protocol with `tls=True`.
    *   `socks://` -> `socks5`.
    *   `socks4://` -> `socks4` (supported).

### Fetcher (`src/configstream/pipeline/fetcher.py`)
*   **Resilience**:
    *   Use `AdaptiveTimeout` to prevent stalling.
    *   Respect `CircuitBreaker` states to avoid hammering dead hosts.
    *   **Do not use ETag caching** (ConfigStream is stateless in CI).
    *   Binary Safety: Use `aiter_bytes()` and decode safely with fallbacks.

### Security (`src/configstream/security_validator.py`)
*   **UUIDs**: For VMess/VLESS, a missing UUID is a fatal error. Drop the proxy.
*   **Sanitization**: Ensure tokens, passwords, and UUIDs are masked in logs.
*   **Blocklists**: Ensure `DEFAULT_BLOCKLIST` is updated before processing begins.
*   **Singletons**: Both `BlocklistManager` and `GeoIPResolver` use `threading.Lock` in `__new__` for thread-safe instantiation. Any new singleton **MUST** follow this pattern.

### Testing (`src/configstream/testers/`)
*   **Dual Engine**:
    *   **Go Sidecar**: Preferred for performance/compatibility. It supports testing single proxies and **Chains** (lists of outbounds).
        *   **Payload Format**: The Go tester expects a valid JSON array of config objects for batch or custom testing. Do NOT send concatenated JSON strings.
        *   **Timeout Resilience**: `GoBatchTester` tracks `_consecutive_timeouts`. After **5** consecutive batch timeouts, the daemon is **disabled** (`available = False`) to preserve the pipeline's time budget. The counter resets to 0 on any successful batch. Daemon restarts are **awaited** (30s timeout) before the next batch (not fire-and-forget).
    *   **Python Fallback**: Minimal implementation for environments without the binary.
    *   **WASM Tester**: Browser-based verification component (`src/go/tester/wasm_main.go`). Must communicate via JS interop (`syscall/js`) and not use native networking.
*   **Washer & Revival**:
    *   **Revival Loop**: The Washer attempts to "revive" failed proxies by wrapping them in both **Standard Warp** and **Vwarp** chains.
    *   **Vwarp Fallback**: Prioritizes `WarpScraper` if the `vwarp` binary is missing.
    *   **Retesting**: Washed chains (Relay -> WARP) are re-tested immediately. Successful revivals are tagged as `revived-warp` or `revived-vwarp`. **Even if re-testing fails**, revived candidates are kept in the output with `is_working=False` so users can try them in their own network.
*   **Cache**: Use `TestResultCache` to skip re-testing recently verified proxies. Ensure path persistence.

### Shared Utilities (`src/configstream/utils/`)
*   **`net.py`**: Shared network helpers (`normalize_host`, `is_ip_literal`, `is_global_ip`). Used by `output_logic.py` and `output_handler.py`. Do NOT duplicate these — always import from `utils.net`.
*   **`__init__.py`**: `AtomicFileWriter`, `BoundedConcurrencyManager`, `_FileLock`.

### Output Generation (`src/configstream/output/`)
*   **Modular Architecture**: Logic is split across specialized modules in the `src/configstream/output/` package. `output_logic.py` acts as a thin orchestrator.
    *   `metadata.py`: Handles `metadata.json`, `health.json`, and artifact manifest generation.
    *   `public_lists.py`: Generates protocol and country-specific URI lists.
    *   `native_configs.py`: Builds profiles for Sing-box, Clash, and third-party adapters (Shadowrocket, QuantumultX, Surge, Loon).
    *   `subscriptions.py`: Manages Base64/plaintext formatting and `side_products.zip` packaging.
*   **DNS Cache Passthrough**: `output_handler.py` pre-computes `_build_dns_safe_proxies` and `_build_dns_hardened_proxies` results and passes them via `dns_safe_cache` / `dns_hardened_cache` params.
*   **Always Generate**: The pipeline **never** exits early on zero working proxies. Outputs are always produced to prevent frontend/client 404s.

### Split Generator (`src/configstream/generators/split.py`)
*   **Outbound Cache**: `to_singbox_outbound()` is called **once** per proxy and cached in `_base_outbound_cache`. Both Sniper (with evasion) and Tank (clean) use `copy.deepcopy()` of the cached result. Do NOT call `to_singbox_outbound()` twice per proxy.

### VwarpTool (`src/configstream/tools/vwarp.py`)
*   The **canonical** Vwarp tool class is `VwarpTool` in `tools/vwarp.py`.
*   `validate_warp_key()` is a static method on this class.
*   **Structured Logging**: Scan and tunnel operations log timing (`%.1fs`), PID, and command used. Failure classification (`_classify_failure`) routes to `config`, `dns`, `connectivity`, or `other` for targeted retry logic.
*   **Config Generation**: `build_vwarp_config()` produces configs aligned with the official vwarp CONFIG_FORGE.md format. Supports MASQUE noize presets (`light`, `moderate`, `heavy`, `gfw`), AtomicNoize presets (`light`, `moderate`, `heavy`), Psiphon country codes (`PSIPHON_COUNTRY_CODES`), and SOCKS5 proxy chaining.
*   **Scan Timeout**: Vwarp IP scan timeout is **60s** (increased from 30s for CI environments).
*   **Presets**: `MASQUE_NOIZE_PRESETS` and `ATOMICNOIZE_PRESETS` dicts are module-level constants sourced from official vwarp documentation. Do NOT hardcode preset values elsewhere — always import from `tools/vwarp.py`.
*   **WARP Outbounds**: All WireGuard outbounds generated by the washer (`get_warp_config`, `wash_failed`, `wash_batch`, `shield_batch`) **MUST** include `"mtu": 1280` per the standard vwarp/WireGuard configuration.

### AnomalyDetector (`src/configstream/anomaly.py`)
*   Uses a persistent SQLite connection with `threading.Lock` and WAL mode.
*   **MUST** call `.close()` during pipeline shutdown to release the DB connection.
*   Implements fail-open behaviour: transient DB errors allow sources through rather than blocking the pipeline.

## 5. Metrics & Analytics
*   **Stats Tracking**:
    *   `PipelineStats` tracks granular metrics: `revived_warp`, `revived_vwarp`, `smart_chain_count`, `shielded_count`, `shielded_candidate_count`, `shielded_verified_count`, evasion metrics, etc.
    *   `total_proxies` in metadata includes Native + Revived + Smart Chains.
    *   **Shielded Accounting**: Untested shielded chains are candidates, not working proxies. They must be exposed with `is_working=False`, candidate tags/details, and must not inflate `total_working`. Only retested chains may count toward `shielded_verified_count`.
    *   **Metadata Completeness**: `save_metadata` in `output_logic.py` **MUST** export every field that `PipelineStats.to_dict()` produces and that the frontend reads. Key fields: `shielded_count`, `shielded_candidate_count`, `shielded_verified_count`, `evasion_utls_enabled`, `evasion_alpn_enabled`, `evasion_fragmentation_enabled`, `evasion_multiplexing_enabled`, `evasion_dns_safe_count`, `evasion_dns_hardened_count`.
### Frontend & Laboratory (`frontend/assets/js/lab/`)
*   **Modular Lab**: The Laboratory logic is a modern ES6 package in `assets/js/lab/`.
    *   `state.js`: Centralized state management for the chain builder.
    *   `ui.js`: Programmatic DOM construction. **Strictly forbidden to use `innerHTML`**; use `textContent` and `appendChild`.
    *   `exporters.js`: Export format builders (Clash YAML, Xray JSON, etc.).
    *   `index.js`: Main entry point and event wiring.
*   **Security Mandate**: All frontend components must avoid `innerHTML` where variable data or metadata is involved. Use the `ui.js` helper `showResultHTML` only for trusted internal strings.
*   **Frontend Deploy Reality**: GitHub Pages deploys the raw static `frontend/.` tree copied into `output/`. `frontend-dist/` is a local build artifact.

## 6. Git & Version Control
*   **Diffs**: When generating patches, ensure context is accurate.
*   **Commit Messages**: Descriptive and git-agnostic.
*   **Artifacts**: Do not commit `output/`, `data/`, or `__pycache__` to the repo.

## 7. Checklist for Agents
Before submitting ANY code:
1.  [ ] Did you run `pytest`?
2.  [ ] Did you sanitize new log statements?
3.  [ ] Did you verify async compatibility (no blocking calls)?
4.  [ ] Did you update relevant documentation?
5.  [ ] If modifying `AGENTS.md`, does it reflect the new reality?

## 8. Common Pitfalls to Avoid
*   **Blocking the Event Loop**: E.g., large `base64.b64decode` on the main thread. -> Use `run_in_executor`.
*   **Unbounded Queues**: Can lead to OOM. -> Use `maxsize` for `asyncio.Queue`.
*   **Log Leaks**: Logging a raw URL with a token. -> Use `sanitize_log_message`.
*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.
*   **Invalid URL Escapes**: Malformed percent-encoding in proxy paths (e.g., `%2` instead of `%20`) crashes sing-box. -> `singbox_utils.add_transport_sb` now sanitizes paths via `_BAD_PERCENT_RE`.
*   **Pipeline Early Exit**: Never return early from the pipeline on zero working proxies. Always generate outputs.

## 9. Module Layout & Canonical Locations
*   **Pipeline Stats**: `PipelineStats` and `PipelineResult` live in `pipeline_stats.py`.
*   **Producer / Consumer**: `source_producer` in `src/configstream/pipeline/producer.py` and `processing_consumer` in `src/configstream/pipeline/consumer.py`. Root `src/configstream/producer.py` and `src/configstream/consumer.py` remain thin compatibility shims.
*   **ProxyWasher**: Canonical class in `intelligence/washer/core.py`. Import directly.
*   **Parsers**: All public parser functions (`parse_vmess`, `parse_vless`, `parse_ss`, etc.) are exported from `parsers/__init__.py` with explicit `__all__`.
*   **DNS Cache**: `prewarm_dns_cache` lives in `dns_cache.py`.
*   **Haversine / Country Centroids**: Canonical location is `intelligence/chaining.py`.
*   **Fetcher**: network fetching lives in `src/configstream/pipeline/fetcher.py`; legacy fetch result helpers remain in `fetcher_worker.py`.
*   **Signer**: `Signer` class lives in `signer.py`.
*   **Steganography**: `StegoPacker` and `generate_stego_assets` live in `stego.py`.
*   **WARP Scanner**: `WarpScannerWorker` lives in `warp_scanner.py`.
*   **Source Quality**: `SourceQualityTracker` in `source_quality.py` extends `quality/storage.py`.
*   **Security Validation**: `SecurityValidator` in `security_validator.py` is the canonical validator. `security/rules.py` imports `LOCAL_IP_RANGES` from it — do NOT duplicate IP patterns.
*   **Generators**: Public API in `generators/__init__.py` with `__all__`.
*   **Converters**: Public API in `converters/__init__.py` with `__all__`.

### Removed Files (do NOT recreate)
*   `output_logic.py` — internals decomposed into `src/configstream/output/` package; root file remains as a thin re-export shim.
*   `lab.js` — fully modularized into `frontend/assets/js/lab/` ES6 package.
*   `pipeline_stages.py` — consolidated into `producer.py` and `consumer.py`.

### Source & Ingestion Contract
*   **Canonical Source**: `sources/batch_*.txt` are the authored operational source lists. No root-level mirror is maintained.
*   **Token Safety**: Tracked source lists MUST NOT contain live-looking user tokens, subscription credentials, or private query strings.
*   **Fetch Safety**: Remote source fetches must enforce source admission and pinned-IP/Host/SNI protection in `src/configstream/pipeline/fetcher.py` and `src/configstream/security/transport.py`.

### Verification Contract
*   Run `python scripts/verify_repository.py --profile static` for repository contracts.
*   Run `python scripts/verify_repository.py --profile full` before claiming release readiness; unavailable toolchains must be reported, not treated as passing.

### Completion Doctrine
A feature is NOT complete because code exists. It is complete only when:
1.  Implementation is modular and documented.
2.  Tests (unit/scenario) pass.
3.  Schemas and machine-readable matrices (`docs/*.json`) are updated.
4.  Generated artifacts validate against the `output_matrix.json`.
5.  CI/Deploy workflows are updated and green.
*   `dns_prewarm.py` — consolidated into `dns_cache.py`.
*   `quality/geo.py` — duplicate of `intelligence/chaining.py`; deleted.
*   `intelligence/washer.py` — consolidated into `intelligence/washer/core.py`.
*   `tools/vwarp_tool.py` — consolidated into `tools/vwarp.py`.
*   `fetcher_core/` — flattened into `fetcher.py` and `fetcher_worker.py`.
*   `pipeline_core/` — flattened into `producer.py`, `consumer.py`, `pipeline_stats.py`, `output_handler.py`.
*   `output.py` — consolidated into `output_logic.py` and `output_transport.py`.
*   `crypto/` — flattened to `signer.py`.
*   `transport/` — flattened to `stego.py`.
*   `workers/` — flattened to `warp_scanner.py`.

### Superseded Documentation
Do NOT recreate standalone point-in-time source-of-truth ledgers. Durable status belongs in generated `STATUS.md`, `CHANGELOG.md`, or canonical machine-readable matrices under `docs/`. Detailed audits belong outside the active source tree or under a dated `docs/audits/` directory when they remain operationally relevant.
*   `KNOWN_ISSUES.md`
*   `CLOSURE_REPORT.md`
*   `docs/FINALIZATION_REPORT_2026.md`
*   `docs/RELEASE_HARDENING_2026.md`
*   `docs/ROADMAP.md`
*   `docs/ROADMAP_UPDATE_PROCESS.md`

## 10. CI / Batch Configuration
*   **Batch Count**: 17 shards (batch_1.txt through batch_17.txt). `dynamic_reshard.py` manages distribution.
*   **MAX_BATCHES**: Set to 17 in `dynamic_reshard.py`. Empty batch files are allowed — reshard fills them.
*   **Time Limits**: `BATCH_TIME_LIMIT_SECONDS = 14400` (4h00m fetch/parse/test) + `BATCH_TIME_LIMIT_GRACE_SECONDS = 2700` (45m for consumers to finish revival, then output generation runs after gather).
*   **TARGET_BATCH_SECONDS**: 14400s (4h) target per batch in reshard.
