
## [2.5.1] - 2026-02-08

### Final Deep Audit

**Fixes**
- **Version**: Updated `pyproject.toml` version from 2.2.0 to 2.5.0
- **Dependencies**: Removed unused `scikit-learn`, `numpy`, `scipy` from `pyproject.toml` (anomaly detection uses stdlib `statistics`)
- **Mypy**: Fixed missing `Optional` import in `security/censorship.py`
- **Mypy**: Added `type: ignore` for optional `crypto` assignment in `utils/cert.py`
- **Duplicate Code**: Removed duplicate comment block in `score.py` `_latency_points`
- **Duplicate Line**: Removed duplicate `EVASION_MODE` line in `README.md`

**Documentation**
- Updated `STATUS.md` version from v2.2.0 to v2.5.0, audit file count 400→900+
- Updated `SECURITY.md` supported versions (added 2.5.x), audit date and score
- Updated `README.md` with Chain Laboratory section

**QA Results**
- **pytest**: 800 passed, 0 failed, 3 skipped
- **mypy**: 0 errors
- **black**: 135/135 files formatted
- **flake8**: 0 errors

---

## [2.5.0] - 2026-02-08

### Deep Audit & Laboratory Page

**Code Quality Fixes**
- **Security**: Replaced MD5 with SHA256 for source URL fingerprinting in `consumer.py`
- **Dead Code Removal**: Deleted `tools/vwarp_tool.py` stub, consolidated `validate_warp_key` into canonical `VwarpTool`
- **Dead Code Removal**: Removed unused `vwarp_proc` variable and cleanup path in `pipeline.py`
- **Dead Code Removal**: Removed duplicate standalone `validate_proxy_config` in `security_validator.py`
- **Dead Code Removal**: Removed unused `subprocess` import from `pipeline.py`
- **Dead Code Removal**: Removed unused `socket` import from `security/censorship.py`
- **Bug Fix**: Fixed `dnsscanner_tui.py` shebang position, unused variables, and comment style
- **Bug Fix**: Renamed `format` parameter to `fmt` in `server.py` to avoid shadowing Python builtin
- **Bug Fix**: Fixed SPDX license header ordering in `output_handler.py` and `testers/python.py`
- **Bug Fix**: Fixed Go tester `main.go` import indentation (`crypto/tls`)
- **Refactor**: Created shared `utils/net.py` with `normalize_host`, `is_ip_literal`, `is_global_ip`
- **Refactor**: Updated `output_logic.py` and `output_handler.py` to use shared `utils.net` module
- **DNS Profiles**: Re-exported `IRAN_INFRASTRUCTURE_DNS` from `dns_profiles.py` for test compatibility

**Frontend**
- **Laboratory Page** (`frontend/lab.html` + `assets/js/lab.js`): 5-step chain builder walkthrough
  1. Parse proxy URI (VLESS, VMess, Trojan, SS, Hysteria2, TUIC, WireGuard)
  2. Discover clean Cloudflare IPs (auto, manual, or local scan)
  3. Build chain — 5 strategies: WARP, Double WARP, TLS Fragment, CDN Worker, Custom JSON
     - Advanced evasion: uTLS fingerprint, ALPN, multiplex (h2mux/smux/yamux), padding
  4. Test chain (live API or manual fallback with sing-box CLI instructions)
  5. Export: Sing-Box JSON, Clash YAML, Xray JSON, Nekobox link, URI, QR, Python script, Bash script
- **Nav Consistency**: Added "Lab" link to all 6 HTML pages (index, proxies, analytics, wiki, about, lab)

**Test Fixes**
- Fixed 3 test files asserting removed `output_dir` field in `/health` endpoint (now checks `output_available`)
- Fixed `test_cloudflare_optimized_ips` to not hardcode a specific IP that rotated out of curated list
- Updated `test_vwarp_tool.py` to import from canonical `VwarpTool` in `tools/vwarp.py`
- **800 tests passing**, 0 failures, 3 skipped

**Offline Tools & Scripts**
- **`tools/lab-scanner.py`**: Zero-dependency Python network diagnostic tool
  - 4-phase scan: basic connectivity, local proxy discovery, clean Cloudflare IP scan, DNS server probe
  - Interactive multi-layer chain builder with JSON config export
  - Tests through existing proxies, finds SOCKS5/HTTP proxies on localhost and LAN
  - Scans 17 Cloudflare IPs x 17 ports with concurrent UDP/TCP probes
- **`tools/lab-runner.sh`**: Bash chain runner for Linux/Mac
  - Auto-downloads sing-box binary, runs chain configs, tests connectivity end-to-end
  - Layer-by-layer testing (TCP, SOCKS5, HTTP, TLS)
  - Clean IP scanning with proxy passthrough support
- **`frontend/lab-offline.html`**: Self-contained offline Lab page
  - Full multi-layer chain builder in a single HTML file (no server needed)
  - Dynamic layer add/remove with visual chain diagram
  - Sing-Box JSON, Clash YAML, Xray JSON export

**Documentation**
- Updated `AGENTS.md` with Shared Utilities section, VwarpTool canonical location, and Laboratory page docs
- Updated `STATUS.md` with current test count (800+) and v2.5.0 roadmap items
- Updated `CHANGELOG.md` with comprehensive v2.5.0 release notes

**Files Modified**
- `src/configstream/pipeline_core/consumer.py` - SHA256 hashing
- `src/configstream/pipeline_core/output_handler.py` - SPDX + shared utils import
- `src/configstream/output_logic.py` - shared utils import
- `src/configstream/pipeline.py` - dead code removal
- `src/configstream/server.py` - parameter rename
- `src/configstream/security_validator.py` - dead code removal
- `src/configstream/security/censorship.py` - unused import removal
- `src/configstream/tools/vwarp.py` - consolidated validate_warp_key
- `src/configstream/testers/python.py` - SPDX fix
- `src/configstream/dns_profiles.py` - re-export fix
- `src/configstream/utils/net.py` - new shared utility module
- `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` - shebang/variable fixes
- `src/go/tester/main.go` - import indentation fix
- `frontend/lab.html` - new Laboratory page
- `frontend/assets/js/lab.js` - new Laboratory page logic
- `frontend/{index,proxies,analytics,wiki,about}.html` - added Lab nav link
- `tests/unit/coverage_boost/test_server_coverage.py` - health endpoint fix
- `tests/unit/test_server.py` - health endpoint fix
- `tests/unit/test_server_new.py` - health endpoint fix
- `tests/unit/test_dns_profiles.py` - IP list fix
- `tests/unit/tools/test_vwarp_tool.py` - import fix

## [2.4.0] - 2026-02-05

### BYOW (Bring Your Own Worker) - Platinum Tier

**Decentralized Infrastructure Strategy**
- **BYOW Feature**: Users can deploy their own Cloudflare Workers for unlimited, private, unblockable connections
  - One-click deploy via Cloudflare Deploy Button
  - Frontend injection logic to personalize Gold configs with user's Worker URL
  - "Hydra Strategy" - thousands of unique worker domains are unblockable
- **Worker Enhancements**: Updated `tools/worker.js` with Platinum version
  - Enhanced masquerading (fake website mode for active probes)
  - Dynamic routing support (IP:PORT via path)
  - WebSocket tunneling with proper error handling
- **Frontend Integration**:
  - Added BYOW section to `frontend/index.html` with deploy button and URL input
  - Created `frontend/assets/js/byow.js` for config injection logic
  - Enhanced Gold Connection warning (V2RayNG incompatibility notice)
- **Deployment Configuration**: Created `tools/wrangler.toml` for one-click Cloudflare deployment

**Test Fixes**
- Fixed `test_save_metadata_analytics_structure`: Set `stats.working` explicitly in test
- Fixed `test_metadata_generation`: Set `stats.working` explicitly in test
- Fixed `test_create_html_smuggled_config`: Updated regex to match `csrf-token` meta tag specifically
- Fixed `output_logic.py`: Only use `stats.working` if non-zero (avoids overriding correct loop count)

**Documentation Updates**
- Updated `README.md`: Added BYOW to evasion features list
- Updated `docs/CENSORSHIP_EVASION.md`: Added comprehensive BYOW section with "Hydra Strategy" explanation
- Updated `docs/USER_GUIDE_EVASION.md`: Added BYOW usage instructions and benefits

**Files Modified**
- `tools/worker.js` - Platinum version with masquerading and dynamic routing
- `tools/wrangler.toml` - Cloudflare deployment configuration (new)
- `frontend/index.html` - Added BYOW section and enhanced Gold warning
- `frontend/assets/js/byow.js` - Worker URL injection logic (new)
- `src/configstream/output_logic.py` - Fixed stats.working handling
- `tests/unit/test_analytics_output.py` - Fixed test assertions
- `tests/unit/test_output.py` - Fixed test assertions
- `tests/unit/test_html_smuggler.py` - Fixed regex pattern

## [2.3.0] - 2026-02-05

### Time-Series Analytics & Evasion Metrics

**Analytics Enhancements**
- **Time-Series Charts**: Added comprehensive evasion metrics tracking over 7-day rolling window
  - Shielded (Gold) proxies count over time
  - Revived (WARP/VWARP) proxies count over time
  - uTLS enabled proxies count over time
  - DNS-Hardened proxies count over time
  - Visualized in both statistics and analytics pages
- **Evasion Trend Export**: Automatic export of evasion metrics to `data/evasion_trend.json` on each pipeline run
- **Historical Tracking**: Rolling window maintains last 7 days of evasion metrics for trend analysis

**Documentation Updates**
- Updated `docs/EVASION_IMPLEMENTATION.md` with time-series charts implementation details
- Merged `docs/COMPLETE_FEATURE_COVERAGE.md` into `docs/OUTPUT_VARIATIONS.md` (redundancy cleanup)
- Marked `docs/SMART_CHAINS_ENHANCEMENT.md` as historical reference document
- Updated `docs/ARCHITECTURE.md` with metrics and analytics section
- Updated `README.md` with analytics and monitoring section
- Removed temporary `IMPLEMENTATION_SUMMARY.md` (information merged into core docs)

**Files Modified**
- `src/configstream/history/export.py` - Added `export_evasion_trend()` function
- `src/configstream/history/tracker.py` - Added `export_evasion_trend()` method
- `src/configstream/pipeline_core/output_handler.py` - Integrated evasion trend export
- `frontend/assets/js/statistics.js` - Added evasion trend chart rendering
- `frontend/assets/js/analytics.js` - Added evasion trend chart rendering
- `frontend/analytics.html` - Added evasion trend chart container

## [2.2.0] - 2026-02-01

### Load Balancing & Vwarp Activation

**Infrastructure Improvements**
- **Load Balancing**: Redistributed sources from heavy batches (6, 10, 11, 12) into a new `batch_15` and lighter existing batches (3, 4, 5, 13) to reduce pipeline runtime.
- **Pipeline Optimization**: Enabled `FORCE_SCANNER` and `ALLOW_ACTIVE_SCANNING` in CI pipeline to activate Vwarp binary usage.
- **Vwarp Fix**: Resolved issue where vwarp binary was not being utilized, ensuring "chains" and "revived" proxies are now correctly generated.
