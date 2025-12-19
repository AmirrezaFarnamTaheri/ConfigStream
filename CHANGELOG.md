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
