
## [3.0.2] - 2026-02-14

### Comprehensive Code Review & Simplification

**Logic Consolidation**
- `security/rules.py`: Replaced 14 duplicate regex patterns with import from `security_validator.LOCAL_IP_RANGES` — single source of truth
- `security_validator.py`: Inlined `validate_proxy` into `SecurityValidator.validate_proxy_config` — eliminated alias indirection
- `security_validator.py`: Collapsed 4 TLS protocol branches into single `in ("trojan", "hysteria2", "tuic", "https")` check
- `security_validator.py`: Simplified redundant UUID double-check into flat early-return pattern
- `filtering.py`: Extracted triplicated "prefer working > lower latency" comparison into shared `_is_better_proxy()` helper — replaced 3 call sites
- `pipeline_core/producer.py`: Extracted triplicated "report failure + record run" pattern into `_report_source_failure()` helper — eliminated ~70 lines of duplication
- `pipeline.py`: Replaced duplicated cancel logic in TimeoutError handler with existing `_cancel_all()` helper
- `adapters.py`: Replaced `get_adapter` if/elif chain with `_ADAPTER_MAP` dict lookup
- `testers/go.py`: Extracted 4x duplicated cancel/await/catch pattern into `_cancel_task()` static method
- `testers/go.py`: Extracted `_json_str()` helper for orjson bytes-vs-str decode — replaced 2 call sites
- `output_handler.py`: Extracted `_is_revived()` helper — replaced 3 identical filter expressions
- `output_handler.py`: Extracted `_collect_tags()` helper — simplified chain tag counting from 3 nested loops

**Dead Code & Redundancy Removal**
- `security_validator.py`: Removed dead `is_hex()` method — zero callers in entire codebase
- `security_validator.py`: Removed unreachable regex fallback in `is_local_ip()` — `ipaddress` handles all valid IPs; regex fallback would false-positive on hostnames like `10.example.com`
- `security_validator.py`: Removed dead `validate_proxy` module-level alias — zero importers in codebase
- `pipeline_core/consumer.py`: Removed redundant outer `try/except` in `_parse_chunk` and unnecessary `pass` after logging
- `pipeline_core/consumer.py`: Removed 7-line stale developer notes about proxy mutability
- `security/rules.py`: Simplified `validate_port` — collapsed 8-line if/else/pass block into 2-line debug log
- `virus_total.py`: Removed redundant `str()` wrapping in f-string
- `testers/go.py`: Removed dead `pass` + stale reentrancy comment in `_read_stderr_loop`
- `output_logic.py`: Removed dead `total_sources` metadata alias — unused by frontend or tests
- `parsers/shadowsocks.py`: Removed dead `pass` statement and redundant host validation

**Bug Fixes**
- `pipeline_core/consumer.py`: Fixed silent fingerprint save failure — `orjson.dumps()` doesn't accept `ensure_ascii` kwarg; switched to `write_bytes()` with orjson bytes output

**Over-Engineering Reduction**
- `security_validator.py`: Simplified `is_valid_uuid()` exception from `(ValueError, TypeError, AttributeError)` to just `ValueError`
- `security_validator.py`: Simplified `is_local_ip()` single-element tuple `in ("localhost",)` to direct `== "localhost"`
- `dns_batch_resolver.py`: Simplified over-broad `(DNSError, TimeoutError, Exception)` to just `Exception`
- `async_file_ops.py`: Removed redundant `isinstance(res, str)` check after exception filtering
- `serialize.py`: Simplified redundant `getattr`/`hasattr` chain for history injection
- `pipeline.py`: Collapsed 3 server-notification exception handlers into single `except Exception`
- `pipeline.py`: Removed unnecessary `"vwarp_tool" in locals()` defensive checks in finally block

**Stale Comment Cleanup**
- `parsers/base.py`: Removed 4-line stale developer notes about constants migration
- `tagging.py`: Removed redundant `# src/configstream/tagging.py` path comment
- `parsers/vless.py`: Removed 7-line stale rambling comments about UUID edge cases
- `merge_batches.py`: Updated to use canonical `total_configured_sources` key

**Code Flattening**
- `parsers/vless.py`: Merged 4 duplicate transport blocks (ws/http/h2/httpupgrade) into single conditional; flattened pbk/sid alias chains using `next()` generator
- `parsers/shadowsocks.py`: Merged duplicate query-param parsing blocks into loop
- `converters/singbox.py`: Replaced protocol alias if/elif chain with `_PROTOCOL_ALIASES` dict lookup
- `quality/storage.py`: Collapsed 3x triplicated exception handlers in `_init_db`, `get_source_state`, and `get_trust_score` into single `except Exception` each
- `testers/go.py`: Simplified 2 redundant exception tuples `(TimeoutError, CancelledError, Exception)` → `Exception`

**Bug Fixes (continued)**
- `parsers/extraction.py`: Dead HTML detection block (`if html_tags: pass`) now actually drops large pure-HTML payloads (>100KB without proxy URIs) and logs for smaller ones

**Additional Stale Comment Cleanup**
- `converters/singbox.py`: Removed stale F841 comment about removed variable
- `tests/e2e/test_failure_scenarios.py`: Cleaned 7-line stale developer notes

**QA Results**
- **pytest**: 785 passed, 3 skipped, 0 failed
- **pyflakes**: 5 findings, all with valid `# noqa` markers (feature detection, re-exports, conditional imports)
- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts

---

## [3.0.1] - 2026-02-14

### Codebase Refactoring & Consolidation

**Module Consolidation (12 files removed, 3 directories flattened)**
- Consolidated `pipeline_stages.py` into `pipeline_core/` submodules
- Consolidated `dns_prewarm.py` into `dns_cache.py`
- Consolidated `fetcher_core/constants.py` into `fetcher_core/models.py`
- Consolidated `pipeline_core/models.py` into `pipeline_core/stats.py`
- Removed duplicate `quality/geo.py` (already in `intelligence/chaining.py`)
- Consolidated `intelligence/washer.py` into `intelligence/washer/core.py`
- Consolidated `fetcher.py` into `fetcher_core/orchestrator.py` and `fetcher_core/batch.py`
- Consolidated `output.py` into `output_logic.py` and `output_transport.py`
- Flattened `crypto/signer.py` → `signer.py`
- Flattened `transport/stego.py` → `stego.py`
- Flattened `workers/scanner.py` → `warp_scanner.py`

**Parser Cleanup**
- Removed all 20 `_parse_*` / `_extract_config_lines` aliases from `parsers/__init__.py`
- Added explicit `__all__` to `parsers/__init__.py`
- Updated 13 consumer files to use canonical function names

**Dead Code Removal**
- `constants.py`: Removed unused `MAX_SOURCE_URL_LENGTH`, `WARP_PREFIXES`, `MIN_SAFE_PORT`, `SECURITY_CATEGORIES` list
- `output_logic.py`: Extracted `_prune_dangling_detours` helper to eliminate ~40 lines of duplication
- `pipeline.py`: Consolidated 3 identical except blocks into `_cancel_all` helper
- `output_transport.py`: Merged 3 gzip except blocks into 1
- `serialize.py`: Removed dead `hasattr(json_lib, 'dumps')` branch
- `security/honeypot.py`: Removed dead functions
- `logging_config.py`: Removed dead no-op `TraceIdFilter` class
- `dns_profiles.py`: Removed unused `ZEUS_DNS` re-export
- `testers/__init__.py`: Removed unused `_cleanup_temp_files` from public API
- `warp_scraper.py`: Replaced indirect usage with direct `httpx.AsyncClient`

**Structural Cleanup**
- Deleted duplicate `frontend/assets/js/lib/purify.min.js` (canonical copy in `assets/libs/`)
- Updated stale path references in `docs/wiki/project/02-architecture.md` and `07-security.md`
- All production code now imports from canonical module paths
- 20+ test files updated to canonical imports

**Documentation**
- `AGENTS.md`: Section 9 expanded with all module locations
- `STATUS.md`: Updated test count, added v3.0.1 roadmap section
- `CHANGELOG.md`: Comprehensive v3.0.1 release notes

**QA Results**
- **pytest**: 785 passed, 0 failed (full suite including fuzz, tools, warp_scraper)
- Zero dangling imports to any deleted file or directory

---

## [3.0.2] - 2026-02-09

### Frontend Redesign & Analytics Completion
- **Unified Stats Card**: Merged primary (4 hero metrics) and secondary (9 compact metrics) into a single card with two rows
- **Layout Overhaul**: Downloads 40% / Info 60% two-column grid; BYOW moved to full-width below
- **Config Selectors**: Redesigned DNS Profile and Evasion Level dropdowns with labels, icons, and consistent styling
- **Evasion Labels**: Replaced variable names with human-readable labels (Standard/Stealth/Maximum)
- **Info Cards Finalized**: Clean, proper language — no "new" or "now supporting" phrasing
- **About Page**: Updated protocols (11) and clients (10) lists, copyright 2024–2026
- **Analytics Page**: Added Shielded, uTLS, DNS-Hardened, TLS Fragment, Multiplexed stats
- **Evasion Trend Chart**: All 7 metrics visualized (added TLS Fragment + Multiplexed datasets)
- **Metadata Schema**: Complete rewrite of `metadata.schema.json` to match actual `save_metadata` output
- **i18n**: Synchronized all English translations with finalized frontend content
- **Version**: Bumped to 3.0.0 across pyproject.toml, frontend build config, STATUS.md

## [2.6.0] - 2026-02-09

### Artifact Consistency & Multi-Core Export Audit

**Core Export Fixes**
- **lab.js Xray/V2Ray export**: Full rewrite — now supports WebSocket, gRPC, HTTP/2, httpupgrade transports, Reality, uTLS fingerprint, ALPN, VLESS flow. WireGuard uses native Xray `secretKey` + `peers[]` format (was incorrectly falling back to `freedom`).
- **lab.js Clash/Mihomo export**: Full rewrite — now supports transports (ws/grpc/h2/httpupgrade), Reality (`reality-opts`), uTLS (`client-fingerprint`), ALPN, VLESS flow, Hysteria2 and TUIC native types. WireGuard adds `reserved`, `udp: true`, dynamic `local_address`.
- **Pipeline Clash converter**: Added Trojan WebSocket/gRPC transport support (was missing).
- **Pipeline Sing-box/Clash converters**: WireGuard outbounds now default to `mtu: 1280` when not explicitly set.
- **WireGuard .conf export**: Added `MTU = 1280` to `[Interface]` section.
- **Surge/Loon adapters**: Chain export broadened from `🛡️ Secure` prefix to **all** WireGuard outbounds with `detour` (catches VWARP-REVIVE, WARP-REVIVE, GOLD, Optimal chains).
- **adapters_base.py**: Added vless, trojan, hysteria2, http, socks5 relay support to Surge/Loon chain formatters. Added `mtu` field.

**New Output Artifacts**
- **Per-protocol URI subscriptions** (`protocols/*.txt`): Plaintext URI lists per protocol (e.g. `vless.txt`, `trojan.txt`) for clients that only accept subscription links.
- **Revived proxy URIs in subscriptions**: `base64.txt` and `proxies.txt` now include revived/washed proxy URIs (reconstructed from origin proxy with `[Revived]` or `[Revived-VWARP]` tag).
- **Frontend download selector**: Added "Chains (Gold/Shielded)" and "Side Products (.conf/.ovpn)" options.

**Documentation Fixes**
- Fixed outdated claim that Xray doesn't support WireGuard natively (it does: `secretKey` + `peers[]` format).
- Fixed claim that Clash cannot chain WireGuard (Mihomo supports `dialer-proxy`).
- Updated client compatibility tables in `wireguard.md`, `singbox_configuration_guide.md`, `06-frontend.md`, `CENSORSHIP_EVASION.md`.
- Updated Lab strategy count to 7 (added WARP+Psiphon, Relay Chain).

**Tests**
- Added `test_artifact_consistency.py`: 31 new tests covering mtu defaults, relay protocols, chain broadening, Trojan transport.

**QA Results**
- **pytest**: 784 passed, 3 skipped
- **flake8**: 0 errors
- **black**: Clean
- **mypy**: 0 errors

---

## [2.5.2] - 2026-02-09

### Lab Scanner v2.1.0 & Documentation Enrichment

**Lab Scanner (`tools/lab-scanner.py`)**
- **New Phase: Intranet Relay Discovery** (`--scan-lan`): Probes 5 LAN subnets × 8 ports for SOCKS5/HTTP/HTTPS hosts with internet access
- **Multi-Strategy Auto-Chain** (`--auto-chain`): Rewritten with 6 strategies — direct proxy, proxy cascade, intranet relay, WARP tunnel, local proxy + WARP, LAN relay + WARP
- **New CLI Options**: `--scan-lan`, `--custom-ips`, `--custom-proxy` for user-supplied resources
- **Enhanced Interactive Builder**: Paste proxy URIs, import clean IPs from file, remove last layer
- **Updated Recommendations**: All diagnostic summaries now suggest multi-strategy approaches (not just WARP)

**Frontend Lab (`lab.html` + `lab.js`)**
- **Pipeline Proxy Integration**: "Load Pre-Tested Proxies" button fetches working proxies from pipeline output (`output/base64.txt`), grouped by protocol in a dropdown
- **2 New Chain Strategies**: Proxy Cascade (1-2 hop SOCKS/HTTP chain) and Intranet/LAN Relay
- **New Builder Functions**: `buildProxyCascadeChain()`, `buildIntranetRelayChain()` generate sing-box configs
- **Multi-Strategy Advice**: All 6 diagnosis tiers updated with strategy-agnostic recommendations
- **Quick Start Commands**: Updated to v2.1.0 with all new CLI options

**Documentation Enrichment**
- **Wiki Home** (`Home.md`): Complete documentation index, getting started for 3 user types, multi-strategy concepts
- **Encyclopedia — Networking Terms**: Added DPI (stateless/stateful/ML), CDN/domain fronting, QUIC, HTTP CONNECT, SOCKS5, Reality protocol, uTLS, BGP, RST injection, ECH, TLS fragmentation
- **Encyclopedia — Security Concepts**: Added active probing (replay attacks, GFW), traffic analysis, circuit breaker pattern, adaptive timeout, FireHol integration
- **Encyclopedia — WARP**: Added how WARP works, 50+ ports, scanner details, 3 chain topologies, alternatives to WARP, key management, WireGuard config fields
- **Encyclopedia — Topology**: Added 6 chaining strategies with diagrams, 9 smart chain types, intranet vs internet explanation
- **Encyclopedia — Trojan**: Added fallback deep dive, Trojan-Go/Xray variants, parsing logic, validation rules, CDN-compatible config, client compatibility matrix
- **Encyclopedia — Firewalls**: Added Iran/Russia-specific censorship details, honeypot detection signs, expanded defense categories
- **Encyclopedia — Sing-box Guide**: Added detour chaining explanation, 4 chain config examples, evasion options, DNS profiles, Lab integration
- **Wiki 06-Frontend**: Full Chain Laboratory documentation (5 steps, 7 strategies, pipeline proxies, offline tools)
- **Wiki 10-Troubleshooting**: Lab Scanner troubleshooting, multi-strategy decision flowchart

**QA Results**
- **flake8**: 0 errors
- **black**: Clean
- **mypy**: 0 errors (notes only)
- **node -c**: lab.js syntax OK

---

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
- **Dead Code Removal**: Consolidated `validate_warp_key` into `VwarpTool`
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
