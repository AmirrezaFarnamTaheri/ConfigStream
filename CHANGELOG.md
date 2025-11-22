# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Initial implementation of Proxy Washing.
- Anomaly Detection with Isolation Forests.
- Adaptive Timeout Strategy.

### Changed
- Switched from `aiohttp` to `httpx` for fetching.
- Migrated to Pydantic v2.

## [1.0.0] - 2025-01-01

### Added
- Initial release.
- Basic fetching, parsing, testing pipeline.
- GitHub Actions integration.
