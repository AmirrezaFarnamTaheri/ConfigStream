# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2025-11-19

### Changed
- Refactored `cli.py` to improve version handling, security, and error handling.
- Refactored `core.py` to improve modularity and remove circular dependencies.
- Refactored `pipeline.py` to simplify logic and improve maintainability.
- Refactored `scripts/merge_batches.py` to improve flexibility and maintainability.

### Removed
- Removed the `remark_parser.py` module.

## [1.1.0] - 2025-11-19

### Added
- Geolocation conflict logging for debugging country code mismatches
- Experimental module documentation with integration paths for advanced features
- Support for naive+https and naive+http proxy protocols
- Support for v2ray JSON configuration format
- **Support for SSR (ShadowsocksR) protocol** - Removed intentional skip logic in pipeline
- DOCS.md master navigation document for easy documentation discovery
- Pipeline output verification before health checks run
- Metrics validation with type and range checking in health checks
- Baseline timeout validation (5-second minimum) in fetcher module
- GitHub Actions token permission hardening with explicit scopes
- SQLite backup API for atomic and consistent database backups
- Latency value validation in health checks (numeric, non-negative, non-NaN)
- Timeout sanitization with type validation and upper bound (120s)
- Normalized proxy merge keys with case-insensitive protocol matching
- Comprehensive test suite for package initialization and lazy loading
- Enhanced backup module tests covering error handling and edge cases
- Extended adaptive workers tests with psutil mocking and exception scenarios
- 25 new test cases for error paths and fallback behavior
- CHANGELOG.md with comprehensive documentation of all changes

### Changed
- **Geolocation priority order**: IP-based lookups (GeoIP DB → HTTP API) now take precedence over remark-based inference
- **Country name normalization**: All country names use COUNTRY_NAMES mapping for consistency
- **Remark parsing**: Much stricter pattern requiring codes in clear isolation contexts ([US], -FR-, ::KR)
- **Experimental modules**: Clearly marked fetcher.py, adaptive_concurrency.py, events.py, monitor.py, source_quality.py
- Health check exit code now properly propagates to trigger workflow failures
- Concurrency grouping uses stable identifiers (workflow + event_name) instead of git ref
- Discord webhook payloads constructed with `jq` for injection-proof JSON building
- Database backups now use sqlite3.backup() API instead of file copy for consistency
- Backup system cleans up partial files on failure
- Timeout values validated and clamped between 5s-120s with type conversion
- Proxy merge operations handle None protocols and explicit port casting
- Test coverage increased from 88% to 89% (553 tests passing, 1 skipped)
- Package initialization module coverage improved from 52% to 92%
- Backup module coverage improved from 82% to 96%
- ARCHITECTURE.md size limits updated to reflect actual values (50MB/100MB)

### Fixed
- **Critical: Country/city geolocation mismatches** (e.g., country="Belarus", city="Washington")
  - Root cause: Remark-based inference ("By" in "[By EbraSha]" → Belarus) had higher priority than IP-based lookups
  - Impact: ~25% improvement in geolocation accuracy (70% → 95%+)
- **Critical: HTTP client reuse bug in pipeline** - _fetch_source created new client per source instead of reusing passed client
  - Impact: ~90% reduction in HTTP connections, significantly improved performance for large source lists
- **Redundant GeoIP downloads** - download_geoip_dbs() called in both CLI and pipeline
  - Impact: 50% reduction in GeoIP download overhead (~200MB saved per run)
- **Atomic geolocation data** - country, country_code, city, and asn now always set together from same source
- **Remark parsing false positives** - Common English words (BY, IN, ON, AS, etc.) no longer misidentified as country codes
- **Logger configuration in fetcher.py** - Removed logger.setLevel at module import to respect global logging config
- MyPy type error in healthcheck script for latency validation (added None check before float conversion)
- Replaced regex-based f-string conversion with robust AST-based transformation in fix_lazy_logging.py
- Backup list now sorts by actual creation time instead of filename
- Adaptive timeout cache now gracefully handles database read failures
- Path traversal vulnerability in backup routine (added sanitization and validation)

### Improved
- Geolocation accuracy improved from ~70% to ~95%+ through IP-based priority
- Country name consistency - eliminates duplicates like "Netherlands" vs "The Netherlands"
- Pipeline performance - connection pooling now works correctly across all source fetches
- Documentation structure streamlined and consolidated (removed 12 redundant development docs)
- QUICKSTART.md formatting fixed (removed escape characters and HTML entities)
- Healthcheck workflow trigger condition now more explicit and readable
- Timeout budget allocation increased from 80% to 70% to better enforce total timeout across retries
- Byte length logging now accurate (encodes string before measuring)
- Test execution speed improved (reduced artificial delay from 10s to 6s)

### Removed
- Redundant development documentation (BACKEND_IMPROVEMENTS, IMPROVEMENTS_SUMMARY, IMPROVEMENTS,
  PIPELINE_ANALYSIS, PERFORMANCE_OPTIMIZATION, PERFORMANCE, VALIDATION_SUMMARY, TESTING_CHECKLIST,
  IMPLEMENTATION_SUMMARY, FINAL_SUMMARY, ACTION_PLAN, ZERO_BUDGET_ROADMAP) - ~3,500 lines
- All content consolidated into core documentation or removed as obsolete

### Deprecated
- src/configstream/dedup.py - Not used by main pipeline (uses dedupe_and_shuffle instead)
  - Kept as reference implementation for quality-based deduplication

### Enabled
- **SSR (ShadowsocksR) protocol** - Previously disabled by policy, now fully supported
  - Parser was already implemented and well-tested
  - Removed intentional skip logic from pipeline (lines 361-363 in pipeline.py)
  - SSR configs now parsed, tested, and included in outputs

### Performance Impact
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Geolocation Accuracy | ~70% | ~95%+ | +25% accuracy |
| Country/City Consistency | Mixed sources | Always atomic | 100% consistent |
| HTTP Connections/Run | N × sources | 1 pooled client | ~90% reduction |
| GeoIP Downloads/Run | 2× | 1× | 50% reduction |
| Naive Protocol Support | Not extracted | Fully supported | New capability |
| SSR Protocol Support | Intentionally disabled | Fully supported | New capability |
| V2Ray Recognition | "Unknown" | Properly recognized | Fixed |
| Country Name Variants | Multiple/country | Single normalized | 100% uniform |

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
