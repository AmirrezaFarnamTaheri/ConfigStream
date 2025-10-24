# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Planned
- Performance improvements for large proxy sets
- Additional output formats

## [1.0.0] - 2025-01-15
### Added
- Enhanced security validation with comprehensive test suite
- Performance tracking and metrics across all pipeline phases
- Async file operations for improved I/O performance
- Advanced error handling with custom CLI error types
- Event bus system for pub/sub patterns
- Health monitoring and uptime tracking
- Rate limiting with token bucket algorithm
- Fluent API for proxy filtering
- Multiple output formats (Base64, Clash, Sing-box, Shadowrocket, Quantumult, Surge)
- Interactive proxy viewer with filtering and export capabilities
- Statistics dashboard with charts and visualizations
- Service worker for offline support and caching
- Logo animations and modern UI design
- 281 comprehensive tests with 91% code coverage

### Changed
- Code formatting improvements with Black
- Removed unused imports and variables
- Improved code quality and consistency
- Updated documentation to reflect current architecture
- Enhanced security testing (content injection, SSL/TLS validation, header preservation)
- Optimized concurrent testing with configurable workers
- Enhanced geolocation data with MaxMind GeoIP integration
- Removed test file from production (test-state-manager.html)

### Removed
- Removed stale references to the retired About page

### Fixed
- Race condition in state manager
- Service worker cache import timing
- Workflow failures and code audit issues
- Fixed outdated navigation references
- Documentation inconsistencies
- Various bug fixes and stability improvements

### Security
- Comprehensive security validator for proxy configurations
- Malicious content detection and filtering
- Sensitive data masking in logs
- Port scanning prevention
- SSL/TLS certificate validation

## [0.4.0] - 2024-01-15
### Added
- Unit tests for configuration parsing and deduplication
- Improved Telegram configuration handling
- Better error messages for failed sources

### Fixed
- Race condition in state manager
- Service worker cache import timing

## [0.3.0] - 2024-01-10
### Added
- Continuous integration workflow on GitHub Actions
- Support for running without Telegram credentials
- Reconnection logic for Telegram scraping

### Changed
- Improved async pipeline performance

## [0.2.0] - 2024-01-05
### Added
- `aggregator_tool.py` for collecting VPN configs from URLs and Telegram
- Concurrency limits and hour-based history lookups
- GeoIP database integration

## [0.1.0] - 2023-12-30
### Added
- Initial release with basic merging features
- Core proxy testing functionality
- Multiple output format support
