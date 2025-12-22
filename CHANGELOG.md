## [2.0.10] - 2025-12-22

### Complete Protocol Implementation & Final Bug Fixes

**New Protocol Converters (Sing-box)**
- **Shadowsocks 2022 (SS2022)**: Full converter implementation using `2022-blake3-aes-128-gcm` as default cipher. Previously parsed but dropped during conversion. (singbox.py:95-126)
- **SOCKS4**: Added support via sing-box's socks type with `version: "4"` parameter. (singbox.py:195-201)
- **NaiveProxy**: Full converter with TLS support and credential validation. (singbox.py:203-224)

**Critical Pipeline Fix**
- **history.save() Restored**: Fixed commented-out `history.save()` call in pipeline.py - history data now properly persists to disk after each pipeline run. The comment incorrectly stated the method didn't exist, but it was always available at proxy_history.py:75-77. (pipeline.py:253)

**Protocol Support Summary**
- **Fully Supported (14 protocols)**: VLESS, VMess, Trojan, Shadowsocks, SS2022, Hysteria v1, Hysteria2, TUIC, WireGuard, SOCKS5, SOCKS4, HTTP/HTTPS, SSH, NaiveProxy
- **Parse-Only (7 protocols)**: SSR, Snell, Brook, Juicity, OpenVPN, XRay, V2Ray JSON (not supported by sing-box natively)

**Quality Checks**
- All 733 unit tests passing
- All modified files pass mypy, black, and flake8

---

## [2.0.9] - 2025-12-22

### Comprehensive Technical Debt Resolution & Protocol Fixes

**CRITICAL Protocol Fixes**
- **VLESS Flow Bug**: Fixed `str(proxy.details.get("flow", ""))` which converted `None` to literal `"None"` string instead of empty string. (singbox.py:90)
- **Hysteria2 Obfuscation**: Fixed field name mismatch - parser stored `obfs`, converter looked for `obfs-type`. Now checks both fields. (singbox.py:254-257)
- **Hysteria v1 Insecure TLS**: Removed hardcoded `insecure: True` - now respects `allowInsecure` and `skip_cert_verify` flags from config. (singbox.py:167-174)
- **Hysteria v1 Speed Config**: Now parses `up_mbps`/`down_mbps` from config instead of hardcoding 100 Mbps. (singbox.py:157-165)

**Pipeline & Stats Fixes**
- **Missing get_warp_config()**: Added method to ProxyWasher class required by chaining.py for washed chain generation. (washer/core.py:220-245)
- **stats.end_time**: Now properly set at pipeline completion for accurate duration tracking. (pipeline.py:243-244)
- **Stats Export**: Added `vwarp_attempts`, `vwarp_success`, and `drop_reasons` to PipelineStats.to_dict() for complete CLI/API export. (stats.py:68-72)
- **Metadata Export**: All PipelineStats metrics now exported to metadata.json including revived_warp, revived_vwarp, duration_seconds, geo_resolved, cache_misses. (output_logic.py)
- **Sing-box _process Field**: Added `_strip_internal_metadata()` to remove internal `_` prefixed fields before JSON serialization, fixing mobile client parse errors.

**Quality Checks**
- All 720 unit tests passing
- All modified files pass mypy, black, and flake8

---

## [2.0.8] - 2025-12-21

### Critical Fixes: Log Rotation, Metadata Standardization, and Frontend Consistency

**Log Management**
- **Log Rotation System**: Replaced `FileHandler` with `RotatingFileHandler` to prevent unbounded log growth (60MB+ issue fixed).
  - Max file size: 10MB per log
  - Backup count: 5 files (maintains last 50MB of logs)
  - Applies to both regular and JSON log handlers
  - Files: `src/configstream/logging_config.py:192-218`

**Metadata & Data Consistency**
- **Standardized Backend Fields**: Added canonical metadata fields with single source of truth principle:
  - `sources_count`: Actual number of sources (no hardcoded 668 fallback)
  - `update_interval_hours`: Dynamic update frequency from env (default: 6)
  - All frontend metrics now use canonical field names from `metadata.json`
  - Files: `src/configstream/output_logic.py:245-279`

- **Frontend Variable Standardization**: Eliminated redundant fallback chains across all frontend files:
  - Removed 50+ lines of confusing multi-level fallbacks
  - Established 1:1 mapping between frontend and backend variables
  - Standardized canonical field names: `total_lines_sourced`, `total_unique_candidates`, `total_valid_proxies`, `total_revived`, `total_dirty`, `total_smart_chains`
  - Files: `frontend/assets/js/main.js`, `analytics.js`, `statistics.js`

**Performance & UX**
- **Globe Visualization Optimization**: Implemented lazy loading for globe to improve initial page load time:
  - Added loading indicator during initialization
  - Deferred globe render with setTimeout(100ms)
  - Added error handling for missing Globe.gl library
  - File: `frontend/assets/js/analytics.js:104-125`

**Verification & Quality**
- **Data Flow Verification**: Confirmed warp/vwarp/chain outputs correctly included in final configs
- **Binary Files**: Verified dynamic binary resolution working correctly
- **Code Quality**: All Python code formatted with Black, passes Flake8 and Mypy checks
- **Documentation**: Updated CHANGELOG with comprehensive technical details

### Breaking Changes
None - All changes are backward compatible.

---

## [2.0.7] - 2025-12-20

### Critical Security & Performance Audit
- **Deep Audit**: Comprehensive audit of Parsers, Testers, Washer, and Stats modules.
- **Base64 Optimization**: Implemented a highly optimized, single-pass Base64 decoder in `src/configstream/parsers/decoders.py` with strict rejection of non-Base64 content (e.g., URLs containing `:`) to prevent garbage decoding and log spam.
- **Stats Accuracy**: Fixed `metadata.json` generation in `scripts/merge/generators.py` to correctly calculate `total_smart_chains` and added `smart_chains_breakdown`.
- **Go Tester Robustness**: Updated `src/configstream/testers/go.py` to use full UUIDs for request IDs to guarantee collision-free tracking and clamp worker count to safer limits (1-1000).
- **Extraction Logic**: Refactored `src/configstream/parsers/extraction.py` to use a centralized `BLOCKED_DOMAINS` list from `constants.py`.

### Code Quality
- **Linter Fixes**: Resolved all `flake8`, `black`, and `mypy` issues across the codebase.
- **Refactoring**: Removed redundant code and optimized import statements in core scripts.
- **Test Coverage**: Verified system integrity with full test suite passing (736 tests).

## [2.0.6] - 2025-12-19

### Major Improvements
- **Process Tracking**: Added explicit `process` field to Proxy model and Frontend to distinguish between Native, Washed, Revived, and Chained proxies.
- **Frontend Upgrades**: Replaced sparkline history chart in proxies table with a clear "Process" badge indicating the proxy source/type.
- **Source Expansion**: Added new high-quality proxy sources (Pawdroid, ErMaozi) for expanded coverage.

### Code Quality & Security
- **Strict Typing**: Resolved Mypy type errors in security rules (`re.match` handling).
- **Log Hygiene**: Significantly reduced log spam in the pipeline consumer by moving high-frequency logs to DEBUG level.
- **Serialization**: Updated serialization logic to support the new `process` field.

## [2.0.5] - 2025-12-15

### Critical Fixes (Backend & Concurrency)
- **GeoIP Race Condition Fix**: Fixed singleton pattern race condition in `geoip.py` by always acquiring lock before checking instance. Added lazy initialization for asyncio.Lock to prevent "no running event loop" errors.
- **TYPE_CHECKING Guard Fix**: Replaced `if False:` with proper `if TYPE_CHECKING:` in `consumer.py` and `producer.py` for correct type checking behavior.
- **Stego Key Injection Security**: Added proper JSON escaping for secret key injection in `output_transport.py` to prevent JavaScript syntax errors from special characters.
- **Deprecated Method Warning**: Added deprecation warning to `BlocklistManager.is_honeypot()` with proper `warnings.warn()` call.

### Frontend Fixes
- **Mobile UX Improvements**:
    - Reduced filter controls whitespace by ~60% for compact mobile experience
    - Fixed "Get Your Configs" card with proper rounded corners and text containment
    - Improved BYOW panel mobile layout with reduced padding
    - Restored rounded corners on mobile cards
- **Globe Widget Enhancements**: Added proper centering, dark mode gradient background, and mobile responsiveness for globe visualization.
- **Stats Card Consistency**: Unified stats field mappings between `main.js` and `analytics.js` with comprehensive fallback handling.
- **Alert to Notification**: Replaced intrusive `alert()` with state manager notification system for data updates.
- **Analytics Robustness**: Added fallback data loading and empty state handling for analytics page.

### i18n Enhancements
- Added missing translation keys (`footer.lastupdated`, `footer.checking`, `stats.update.value`) to Chinese, Persian, Russian, and Arabic languages.

### Code Quality
- Consistent TYPE_CHECKING imports across pipeline modules
- Improved error handling patterns in analytics.js

---

## [2.0.4] - 2025-12-07

### Critical Fixes (Frontend & Reliability)
- **Frontend Architecture Standardization**: Unified the frontend structure to a "flat" model, resolving 404 errors caused by conflicting path strategies (flat vs. subdirectory) in `generators.py`.
- **Navigation Fixes**: Corrected broken links and asset paths across `index.html`, `about.html`, `proxies.html`, `analytics.html`, and `wiki.html` by ensuring consistent use of `window.ROOT_PATH`.
- **Go Tester Stability**:
    - Implemented a heartbeat mechanism in the Go tester (`src/go/tester/main.go`) to prevent silent freezes during long batches.
    - Added smart batch splitting in the Python wrapper (`src/configstream/testers/go.py`) to process large inputs in manageable chunks (default 25), preventing memory exhaustion and timeouts.
- **WARP Integration**: Added a dedicated `WARP Configuration Scraper` (`src/configstream/intelligence/washer/warp_scraper.py`) as a primary fallback for fetching WireGuard keys/endpoints when active scanning fails.
- **Service Worker Caching**: Incremented cache version to v6 to force clients to update and receive critical JS fixes.

### Improvements
- **UI/UX Enhancements**:
    - Renamed "Hybrid" download option to "Sing-box (Universal)" for clarity.
    - Added lazy loading for heavy components (Globe, Charts) to improve page load speed.
    - Fixed truncated code in `wiki.js` causing documentation load failures.
    - Resolved async syntax error in `statistics.js`.
- **Documentation**: Updated `wiki.js` to support multiple fallback sources for fetching documentation, improving resilience against GitHub raw content blocks.

### Code Quality
- **Refactoring**: Cleaned up `frontend/assets/js/utils.js` to ensure proper `window.api` exports.
- **Linting**: Applied formatting (Black) and fixed imports in new scraper modules.
