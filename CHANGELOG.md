# Changelog

All notable changes to ConfigStream will be documented in this file.

## [1.2.0] - 2024-05-24

### Added
- **Smart Retest Scheduling**: New `scheduler.py` intelligently skips testing of healthy proxies based on historical reliability, reducing load by up to 40%.
- **Adaptive Timeout**: `adaptive_timeout.py` dynamically adjusts connection timeouts (3s-30s) based on network latency trends (p95).
- **Protocol Auto-Detection**: Enhanced `auto_detect.py` now automatically identifies 20+ protocols including Hysteria 2, TUIC v5, and Juicity without explicit headers.
- **Streaming Fetcher**: `fetcher.py` now streams sources asynchronously, improving concurrency and reducing memory usage.
- **Memory Optimization**: Implemented `__slots__` in `Proxy` models, reducing per-object memory overhead by approx. 40%.
- **New Frontend Pages**: Added `analytics.html` for insights and `about.html` for project info.
- **Map Visualization**: Placeholder for Leaflet.js based proxy distribution map.

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
