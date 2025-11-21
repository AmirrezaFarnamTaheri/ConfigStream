# Changelog

All notable changes to ConfigStream will be documented in this file.

## [1.3.0] - 2025-11-21

### Fixed - Critical Backend Robustness Improvements

- **C-1: Cache Logic** - Fixed silent proxy loss when cache entries expire. Proxies now properly retested instead of dropped.
- **C-2: Code Structure** - Corrected unreachable docstring in testers.py.
- **C-3: Latency Accuracy** - Removed artificial 0.3s delay in latency measurements, improving accuracy by 20-30% and test speed by 20%.
- **C-4: Security Visibility** - Added clear warning logging when optional security binaries (uTLS, SS-Rust) are unavailable, preventing silent feature degradation.
- **C-5: Data Integrity** - Implemented atomic file writes (temp + rename pattern) for all outputs, preventing data corruption on crashes.
- **C-6: Concurrency Safety** - Added asyncio.Lock protection to ConcurrencyManager statistics tracking, preventing race conditions.

### Fixed - Backend-Frontend Consistency

- **Workflow Configuration** - Removed undefined `--show-metrics` CLI flag from GitHub Actions workflow.
- **Server Endpoints** - Added missing subscription endpoints: `/subscribe/loon`, `/subscribe/sip008`, `/subscribe/quantumultx`.
- **Source Quality Tracking** - Eliminated duplicate quality_tracker updates per source.

### Fixed - High-Severity Issues

- **IP Validation** - Added format validation before GeoIP lookups to prevent crashes on malformed addresses.
- **Documentation** - Corrected map visualization library from "Leaflet.js" to "globe.gl".

### Added

- **Comprehensive Audit Report** - Added `docs/BACKEND_AUDIT_REPORT.md` documenting all findings and fixes from robustness audit.
- **Graceful Degradation** - Enhanced security modules to explicitly handle missing optional dependencies with clear user warnings.

### Changed

- **ConcurrencyManager** - `record()` method now async for proper lock handling.
- **Test Coverage** - Updated 107 unit tests to reflect async changes, all passing.
- **Code Quality** - Maintained Black and Flake8 compliance across all changes.

### Performance

- **20% Faster Testing** - Eliminated unnecessary delays in proxy latency measurements.
- **Atomic Writes** - More reliable file operations with no performance penalty.

## [1.2.0] - 2024-05-24

### Added
- **Smart Retest Scheduling**: New `scheduler.py` intelligently skips testing of healthy proxies based on historical reliability, reducing load by up to 40%.
- **Adaptive Timeout**: `adaptive_timeout.py` dynamically adjusts connection timeouts (3s-30s) based on network latency trends (p95).
- **Protocol Auto-Detection**: Enhanced `auto_detect.py` now automatically identifies 20+ protocols including Hysteria 2, TUIC v5, and Juicity without explicit headers.
- **Streaming Fetcher**: `fetcher.py` now streams sources asynchronously, improving concurrency and reducing memory usage.
- **Memory Optimization**: Implemented `__slots__` in `Proxy` models, reducing per-object memory overhead by approx. 40%.
- **New Frontend Pages**: Added `analytics.html` for insights and `about.html` for project info.
- **Map Visualization**: 3D Globe visualization using globe.gl for proxy distribution mapping.

### Changed
- **Pipeline Architecture**: Refactored `pipeline.py` to use a producer-consumer model with bounded queues for backpressure.
- **File Structure**: Consolidated `geoip.py` (was split into offline/online), removed redundant `core.py`.
- **Documentation**: Comprehensive rewrite of `README.md`, `ARCHITECTURE.md`, and added `DEPLOYMENT.md`.
- **Security**: Strengthened `testers.py` with active MITM detection (SSL issuer checks) and HTML injection heuristics.

### Fixed
- **Flake8/MyPy Issues**: Resolved indentation and type hint errors across the codebase.
- **Test Flakiness**: Stabilized async tests for fetcher logic.
- **Dependency Issues**: Pinned critical dependencies in `pyproject.toml`.

## [1.1.0] - 2024-04-15

### Added
- Initial PWA support with `manifest.json`.
- Service Worker for offline caching.

### Changed
- Switched to `sing-box` as the primary testing engine.

## [1.0.0] - 2024-01-01

- Initial Release.
