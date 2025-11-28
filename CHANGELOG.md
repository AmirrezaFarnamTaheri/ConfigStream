# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.6] - 2025-11-29

### Critical Fixes (Architecture & Stability)
- **Local Resource DOS Prevention**: Capped pipeline max workers at 25 and Go tester workers at 20 to prevent OS socket exhaustion and "bind: address already in use" crashes.
- **Go Tester Race Condition**: Removed manual port binding/unbinding ("Port Dance") in `main.go` and implemented a jittered retry mechanism with random port selection (20000-60000) to resolve collision storms.
- **Go Tester Resilience**: Implemented standard `json.Unmarshal` usage and explicit panic recovery to prevent worker crashes on malformed configs.
- **WireGuard Concurrency**: Fixed routing conflicts during parallel testing by generating deterministic unique local IPs (172.16.x.y) for WireGuard configs.

### Data Hygiene & Protocol Fixes
- **VLESS Reality Sanitization**: Implemented aggressive cleaning in `parsers/vless.py` to strip invisible characters and enforce valid HEX format for `sid` (Short ID), preventing parser crashes.
- **uTLS Enforcement**: Updated `converters.py` to automatically inject `uTLS` fingerprint (defaulting to "chrome") for all Reality configurations, resolving "uTLS is required" errors.
- **Modern Protocol Stability**: Forced `insecure=True` for Hysteria2 and TUIC protocols during testing to bypass handshake failures on self-signed certificates common in free proxies.
- **Missing Protocols**: Added full conversion support for SSH, Hysteria (v1), and improved Trojan TLS handling.

### Features
- **Smart Washing**: Updated `washer.py` to generate unique local IPs for WireGuard chains, preventing collision when multiple chains are active.
- **WASM & BYOW**: Enhanced `wasm_main.go` to warn on non-WS protocols and updated `byow.js` to enforce uTLS for user-injected workers.
- **Documentation**: Updated architecture notes regarding worker limits and protocol support.

## [2.0.5] - 2025-11-29

### Critical Fixes
- **Go Tester Logic**: Fixed critical bug in `src/go/tester/main.go` where `UnmarshalJSONContext` was causing "missing inbound fields registry" error. Switched to `json.Unmarshal`.
- **Go Tester Performance**: Reduced instance-per-test overhead by optimizing config template and implementing flags for timeout and URLs.
- **Go Tester Rate Limiting**: Implemented random target selection in Go tester to prevent single-target rate limiting (Google 204).
- **CI/CD Reliability**: Fixed checkout failure in GitHub Actions by adding proper token permissions.
- **Infrastructure**: Added `setup_data` job to cache GeoIP databases, reducing redundant downloads and speeding up pipeline.
- **Configuration**: Synced Python and Go timeouts to prevent false negatives (Python now waits 15s, Go times out at 10s).
- **Testing**: Fixed `pytest-asyncio` version mismatch causing "RuntimeError: Runner is closed" in tests.

## [2.0.4] - 2025-11-29

### Critical Fixes (Go Tester & Pipeline Stability)
- **Go Import Registry**: Fixed a fatal error (`missing inbound fields registry`) where the Sing-box core library was not registering protocol modules. Added side-effect import `_ "github.com/sagernet/sing-box/include"` to `src/go/tester/main.go` to ensure VLESS, VMess, and other protocols are recognized.
- **Panic Recovery**: Implemented robust panic recovery in the Go tester's worker threads. Previously, a single malformed config could crash a worker silently; now, panics are caught, logged, and the worker survives.
- **Port Race Condition**: Fixed a TOCTOU (Time-of-Check to Time-of-Use) race condition in port binding by increasing retries and optimizing the bind-close-bind sequence in the Go tester.
- **Input Buffer Limit**: Switched from `bufio.Scanner` to `json.Decoder` in the Go tester to bypass the 64KB token limit, preventing silent drops of large proxy configurations.

### Logic Improvements
- **Shadowsocks Plugins**: Updated `src/configstream/converters.py` to correctly map `plugin` and `plugin_opts` fields. Obfuscated Shadowsocks proxies (obfs-local, v2ray-plugin) are no longer stripped to raw TCP.
- **TLS Insecure Mode**: Added mapping for `allowInsecure`, `insecure`, and `skip_cert_verify` flags in `converters.py`, preventing false negatives for proxies with self-signed certificates.

### Observability
- **Detailed Failure Logging**: Enhanced `src/configstream/testers_core.py` to categorize and log specific failure reasons (Panic, Honeypot, Dirty IP, Timeout, Bind Error) instead of generic error messages.

## [2.0.3] - 2025-11-28

### Critical Fixes (Pipeline Reliability)
- **Base64 Validation**: Fixed strict validation that was rejecting URL-encoded characters (like `%2B`, `%2F`, `%3D`). Added automatic URL-decoding in `parsers/base.py` and `parsers/vmess.py`.
- **Shadowsocks Parsing**: Fixed a major log spam issue where plaintext credentials were incorrectly being attempted as Base64, raising thousands of warnings.
- **Tester Logging**: Implemented visibility for silent failures. Now logs specific error reasons (e.g., "I/O Timeout") when success rate is near zero, allowing for actual debugging.
- **Environment Compatibility**: Disabled "TCP Brutal" and "Multiplexing" injection by default in `converters.py` to ensure compatibility with standard CI environments (GitHub Actions) and Docker containers lacking specific kernel modules.

### Performance
- **Pipeline Throughput**: Increased Go tester batch size from 50 to 500, resolving a massive serialization bottleneck that was starving the worker process.
- **Fetcher Timeout**: Fixed aggressive timeout slicing. Fetcher now respects the full user-defined timeout per attempt instead of splitting it, preventing "Fetch Failed" on slow but valid sources.
- **Concurrency Logic**: Adjusted `ConcurrencyManager` to stop treating expected dead proxies as "system errors," preventing unnecessary self-throttling.

### Fixed
- **Statistics**: Removed double-counting of working proxies in the pipeline execution report.

## [2.0.2] - 2025-11-27

### Added
- **WARP Key Validation System** - Comprehensive validation module for Cloudflare WARP credentials (Issue #22)
  - Format validation for Curve25519 keys (base64, 32-byte length)
  - Reserved bytes validation
  - Account activation checking via Cloudflare API
  - Endpoint reachability verification for known WARP ranges
- **Statistics & Observability** (Issues #17-18, #20-21)
  - `get_statistics()` method for AnomalyDetector monitoring
  - Export statistics logging in SurgeAdapter
  - `save_shard_metadata()` function for shard distribution tracking
  - Sorting statistics with latency metrics in Pareto sorter
- **Protocol Support** (Issue #26)
  - VLESS and Hysteria2 support in Surge adapter
- **Error Classification** (Issue #19)
  - WASM tester now reports structured error types (timeout, connection refused, dial failed)

### Fixed
- **Configuration Consolidation** (Issue #29)
  - Moved protocol colors to constants.py (18 protocols with aliases)
  - Eliminated duplication between config.py and output_transport.py
- **Reliability Improvements** (Issues #27-28)
  - Added geopy import fallback with haversine distance calculation
  - Added retry logic with exponential backoff (3 attempts, 2s/4s/8s delays) to `fetch_clean_ips()`

### Changed
- **Increased MAX_LINES_PER_SOURCE** from 10,000 to 40,000 for large proxy lists

## [2.0.1] - 2025-11-25

### Security
- **CRITICAL: Path Traversal Vulnerability Fixed** - Added regex validation and path resolution checks in server.py to prevent arbitrary file read
- **Race Condition Fixes** - Made RateLimiter and CircuitBreaker async-safe with proper asyncio.Lock() protection
- **Resource Leak Prevention** - Improved HTTP client exception handling to prevent resource leaks
- **DOS Protection** - Added LRU eviction (MAX_SOURCES=1000) to prevent unbounded memory growth in adaptive timeout tracker

### Fixed
- **Concurrency Issues**:
  - Fixed queue deadlock in pipeline_stages.py with 300s timeout protection
  - Fixed temp file cleanup race with threading.Lock in testers_core.py
  - Fixed AdaptiveTimeout race conditions by making methods async with asyncio.Lock
  - Fixed ProxyWasher seen_chains race with threading.Lock
- **Calculation Errors**:
  - Fixed off-by-one error in quantile calculation (n=20[18] → n=100[94] for 95th percentile)
- **Code Quality**:
  - Removed placeholder HONEYPOT_ASNS (empty set with proper type annotation)
  - Fixed import ordering in merge_batches.py
  - Removed unused imports in plugins/loader.py
  - Added missing threading import and lock declaration in testers_core.py
  - Fixed missing await for async AdaptiveTimeout methods in fetcher.py
- **Frontend**:
  - Replaced hardcoded UUID placeholder with dynamic UUID generation in byow.js

### Changed
- **Silent Exception Handling** - Added logging to all exception handlers for better production debugging
- **Test Coverage** - Increased from 85% to 89% with 307 new comprehensive tests
- **Code Quality** - All code now passes flake8 linting and black formatting (100% compliant)

### Testing
- **New Test Suites**:
  - transport/stego.py: 36% → 100% coverage (20 tests)
  - __init__.py: 28% → 96% coverage (22 tests)
  - parsers/shadowsocks.py: 69% → 87% coverage (40 tests)
  - security/virus_total.py: 70% → 100% coverage (23 tests)
  - proxy_history.py: 70% → 100% coverage (29 tests)
- **Test Infrastructure**: Fixed 9 test failures in comprehensive test suite
- **Total Tests**: Increased from 435 to 742 tests

## [2.0.0] - 2025-06-01

### Major Features (Sovereignty & Stealth)
- **Steganography with Key Rotation:** Implemented a robust transport layer that hides proxy configs inside PNG images. Includes a self-healing mechanism that rotates encryption keys every run and injects them into the frontend.
- **WASM Client-Side Tester:** Full implementation of the Go-based WebAssembly tester (`src/go/tester/wasm_main.go`), allowing users to verify proxies directly from their browser via WebSockets.
- **Bring Your Own Worker (BYOW):** Frontend feature enabling users to tunnel traffic through their own Cloudflare Workers.
- **Static Vector Search:** Zero-cost "Similar Proxy" search using feature hashing (`src/configstream/intelligence/vectors.py`).

### Architecture
- **Modular Pipeline:** Refactored monolithic pipeline into `src/configstream/pipeline_core/` with dedicated sorters and output handlers.
- **Plugin System:** Introduced `src/configstream/plugins/` for dynamic protocol support.
- **Zero Budget Compliance:** Removed all active scanning components; strictly passive verification to ensure GitHub Actions compliance.

### Fixed
- **WASM Build Target:** Corrected build script to target `wasm_main.go`.
- **Vector Generation Order:** Ensured vectors are generated before metadata for correct frontend indexing.
- **Output Stability:** Enforced atomic writes for all public artifacts.

## [1.3.2] - 2025-05-27

### Added
- **Go-Powered Batch Tester**: Native Go binary (`src/go/tester`) handling 500+ concurrent proxy tests with zero GIL overhead.
- **Smart Washing Intelligence**: Automated recycling of "Dirty" (Google-blocked) proxies via Cloudflare WARP WireGuard tunnels.
- **Double-Hop Chaining**: Logic to create "Intranet Bridge" (IR->EU) and "IPv6 Portal" routing chains.
- **Atomic Persistence**: New `AtomicFileWriter` ensures zero-corruption data storage for history and caches.
- **Split Outputs**: Generated dedicated configs for different user needs:
    - `singbox-vpn.json` (TUN/FakeIP "Tank" mode)
    - `singbox.json` (Lightweight "Sniper" mode with fragmentation)
    - `clash.yaml` (Legacy "Diplomat" compatibility)
- **Surge & Loon Adapter Enhancements**: Native support for WireGuard-over-Proxy chains in export formats.

### Changed
- **Parsers Refactoring**: Monolithic `parsers.py` split into modular `src/configstream/parsers/` package for better maintainability.
- **Concurrency Management**: Python tester now uses `BoundedConcurrencyManager` for safer scaling.
- **Documentation**: Updated Architecture, README, and Security docs to reflect v1.3 changes.

### Fixed
- **Race Condition**: Critical port binding race condition in Go tester fixed with retry loop.
- **Deadlock**: Fixed potential hang in Python `proc.communicate()` calls with `asyncio.wait_for`.
- **Split-Brain Logic**: Unified "Washing" logic so all adapters (Surge, Loon, Sing-box) receive the same high-quality chains.
- **Dirty Duplicates**: Prevented raw/dirty proxies from polluting the main selector list if a washed version exists.
- **Docker Caching**: Optimized Dockerfile to cache Go module downloads.

## [1.2.0] - 2025-04-15

### Added
- **Initial implementation of Proxy Washing.**
- **Anomaly Detection with Isolation Forests.**
- **Adaptive Timeout Strategy.**

### Changed
- **Switched from `aiohttp` to `httpx` for fetching.**
- **Migrated to Pydantic v2.**

## [1.0.0] - 2025-01-01

### Added
- **Initial release.**
- **Basic fetching, parsing, testing pipeline.**
- **GitHub Actions integration.**
