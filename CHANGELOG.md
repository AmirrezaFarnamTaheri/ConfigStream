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
