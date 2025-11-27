# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Increased MAX_LINES_PER_SOURCE from 10,000 to 40,000 for large proxy lists

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
