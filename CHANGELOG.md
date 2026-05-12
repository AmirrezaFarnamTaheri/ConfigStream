
## [Unreleased]

### Documentation: Unified Source of Truth (2026-05-12)
- **Master audit consolidation**: Integrated the amendment, known issues, status context, changelog context, closure report, debt matrix, finalization report, release-hardening notes, roadmap, and roadmap update process into `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`.
- **Split-brain cleanup**: Removed superseded standalone amendment, known-issues, closure, finalization, release-hardening, roadmap, and roadmap-process files after preserving their content in the master report's evidence ledgers.
- **Status alignment**: Updated `STATUS.md` to point readers to the unified master report for integrated historical and current remediation context.

### Remediation: Laboratory Consistency & UX (2026-05-11)
- **Data-Driven Strategies**: Refactored the Laboratory to dynamically load strategy labels, hints, and UI panel visibility from `lab_strategies.json` at runtime.
- **UI/Manifest Parity**: Eliminated parallel literals in `lab.js` by centralizing strategy metadata, ensuring the UI stays in sync with the canonical manifest.
- **Export Integrity**: Added explicit export assertions and handling for Vwarp metadata in Sing-box, Clash, Xray, Python, and Bash outputs.
- **Offline QR Rendering**: Integrated a zero-dependency, fully-offline SVG QR code renderer to prevent configuration leakage to third-party services.
- **XSS Hardening**: Split the legacy `showResult()` templating function into strict `showResultText()` and `showResultHTML()` helpers to prevent DOM injection via user input.

### Remediation: CI/CD Source-of-Truth Bootstrap (2026-05-03)
- **Workflow YAML parse repair**: Fixed malformed `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` indentation in `ci.yml`, `deploy-pages.yml`, `deploy_mirror.yml`, `main.yml`, and `retest.yml`; all workflow YAML files now parse locally.
- **Workflow validation gate**: Added `scripts/validate_workflows.py` and wired it into CI plus pre-commit so workflow syntax drift is caught before merge/deploy.
- **Workflow behavior guardrails**: Extended workflow validation to require concurrency on pipeline/retest/deploy workflows and to enforce source-reshard `paths-ignore` whenever a workflow can `git push`.
- **Mirror deploy race guard**: Added a top-level concurrency policy to `deploy_mirror.yml` so optional mirrors cannot overlap stale deployments on the same ref.
- **Pages artifact validation**: Added `scripts/validate_pages_artifact.py`, moved required Pages artifact checks out of shell arrays, and added tests for missing, empty, invalid JSON, and corrupt ZIP outputs.
- **Public artifact contract**: Output generation now writes `health.json` and `artifact_manifest.json`; deploy validation requires them and verifies manifest coverage plus health status.
- **Contract schemas**: Added `schema/artifact_manifest.schema.json` and `schema/health.schema.json` as the first canonical schemas for the public deploy control files.
- **Deploy contract enforcement**: Pages validation now checks manifest size/hash integrity, manifest totals, `metadata.json` required schema keys, `proxies.json` array shape, and `health.json` required fields before upload.
- **Exact deploy manifest refresh**: `deploy-pages.yml` now runs `scripts/validate_pages_artifact.py --refresh-contract output` after frontend copy, API alias creation, `.nojekyll`, cache-busting edits, and test-cache cleanup so `artifact_manifest.json` describes the exact Pages artifact being uploaded.
- **Cross-platform version validation**: Rewrote `scripts/validate_versions.py` to use explicit UTF-8 file reads and ASCII-safe output, fixing Windows console/encoding failures.
- **Audit source of truth**: Replaced the accumulated master audit/addendum document with a clean remediation report, claim-completion program, parity rules, cleanup policy, and production-readiness roadmap.
- **Status/docs parity**: Rewrote `STATUS.md`, updated the DevOps wiki, and added a README remediation notice so public docs no longer claim final production readiness while P0/P1 work remains open.
- **Package/readme claim cleanup**: Changed `pyproject.toml` from `Development Status :: 5 - Production/Stable` to `Development Status :: 4 - Beta` during remediation; corrected README TLS fragmentation language to state it is disabled in current sing-box outputs.
- **Documentation hygiene guard**: Extended `tests/unit/test_documentation_hygiene.py` to prevent reintroducing Production/Stable or active TLS-fragmentation claims while remediation remains open.
- **Metric trust correction**: `total_working` and `PipelineStats.total_proxies` no longer include untested shielded candidates; metadata now exposes `shielded_candidate_count` and `shielded_verified_count` while retaining `shielded_count` as the candidate count.
- **Frontend metric parity**: Updated analytics/statistics comments so frontend logic treats `total_working` as retested working proxies only and `shielded_count` as a candidate count.
- **Metric invariant tests**: Added regression coverage proving shielded candidates do not inflate `total_working`, `total_valid_proxies`, or `success_rate`.
- **Production admin auth fail-closed**: `/api/admin/notify-update` now rejects production calls when `ADMIN_API_KEY` is unset and rejects production calls without a matching payload key when configured; unauthenticated calls are allowed only for explicit `development`, `ci`, or `test` environments.
- **Admin endpoint rate limit**: Added a `10/minute` SlowAPI limit to `/api/admin/notify-update` and a regression test confirming limiter registration.
- **Admin startup validation**: Server startup now fails in production when `ADMIN_API_KEY` is unset, with tests for production no-key, production keyed, and development no-key modes.
- **Security docs parity**: Updated `SECURITY.md` to state `ADMIN_API_KEY` is required for production admin endpoints.
- **Admin auth tests**: Added server tests for production without configured key, production missing payload key, production valid key, and explicit development no-key behavior.
- **CORS production tightening**: Removed the broad default `https://.*\.github\.io` CORS regex, disabled credentialed CORS by default, and added production startup validation that rejects `ALLOWED_ORIGIN_REGEX`; production must use explicit `ALLOWED_ORIGINS`.
- **CORS docs/tests parity**: Updated `.env.example` and `SECURITY.md`; added server tests for default CORS settings, origin splitting, production regex rejection, and development regex allowance.
- **WebSocket lifecycle hardening**: Added configurable max connections, idle timeout, send timeout, stale-connection cleanup, and connection/drop stats for `/ws/updates`.
- **WebSocket tests/docs parity**: Added `.env.example` and `SECURITY.md` coverage for WebSocket lifecycle limits plus tests for over-capacity rejection, failed-send cleanup, and bounded defaults.
- **Lab live-test production guard**: `/api/lab/test-chain` is now disabled by default in production, requires explicit `LAB_LIVE_TEST_ENABLED=true`, requires `ADMIN_API_KEY` payload authentication when enabled, applies a `30/minute` rate limit, enforces `LAB_MAX_CONFIG_BYTES`, and uses configurable test timeout.
- **Lab live-test config safety**: Added route-level validation for submitted lab configs: non-empty `outbounds`, allowed outbound types only, valid host syntax, and blocking for localhost, internal hostnames, and private/non-global IP literals.
- **Lab live/manual mode labeling**: Step 4 now shows whether the page is in backend live-test mode or static-host manual-test mode; static GitHub Pages/file-style hosting relabels the action to manual instructions without removing the online live-test path for backend-capable deployments.
- **Lab live-test docs/tests parity**: Added `.env.example`, `SECURITY.md`, `STATUS.md`, and server-test coverage for disabled production mode, missing key, valid key, oversized config, invalid config shape, disallowed type, private destination, internal hostname, rate-limit registration, and nonproduction compatibility.
- **Fetcher SSRF/redirect guard**: Source fetching now rejects source URL credentials, localhost/internal hostnames, and private/non-global IP literals by default; redirects are no longer auto-followed by `httpx` and are instead validated target-by-target with `FETCH_MAX_REDIRECTS`.
- **Fetcher DNS-resolution guard**: Source hostnames and redirect targets are resolved immediately before fetch attempts when `FETCH_VALIDATE_DNS=true`, and private/non-global DNS answers are rejected before opening the HTTP stream.
- **Fetcher docs/tests parity**: Added `.env.example`, `SECURITY.md`, `STATUS.md`, and fetcher tests for private source URLs, safe redirects, private redirect targets, and redirect-depth limits.
- **Frontend runtime-config deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to generate `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, preserving checked-in source JS while failing upload on missing runtime keys or placeholder markers.
- **Pages artifact browser smoke**: Added a repeatable deploy-artifact smoke that assembles a temporary Pages-shaped artifact, generates runtime config, validates the public artifact contract, and runs same-origin browser, protocol render, Lab XSS, and no-JS degraded checks against that exact artifact.
- **Deployed Pages URL smoke**: Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, public artifact aliases, health metadata, base64/chosen subscription endpoints, manifest hash parity, run identity, and placeholder-key absence.
- **Data-release contract parity**: The scheduled data-release workflow now validates `output/` with the shared Pages artifact contract instead of hard-coded shell non-empty checks, so degraded empty subscription text/base64 files remain valid while control/client artifacts still fail closed.
- **Frontend verifier fail-closed path**: Signed frontend artifacts now reject when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.
- **Frontend trust labels**: Visible dashboard labels now separate unique candidates, retested working proxies, and shielded candidates so generated shielded chains are not presented as verified working.
- **Canonical Pages frontend path**: GitHub Pages deployment is now explicitly guarded as raw static `frontend/.` copied into `output/`; workflow validation rejects accidental `frontend-dist`/Vite deployment drift while keeping Vite as an optional/local build sanity check.
- **Frontend runtime-config tests/workflow parity**: Added tests for placeholder detection/runtime-config generation and extended workflow validation so `deploy-pages.yml` cannot drop the frontend runtime-config guard or secret env wiring silently.
- **Public artifact contract tightening**: Pages validation now rejects unknown top-level control schema keys and verifies `api/proxies` matches `proxies.json` and `api/stats` matches `metadata.json`.
- **Proxy snapshot identity**: Metadata now publishes current and previous proxy snapshot hashes, `/api/diff/proxies` rejects ambiguous base versions before returning deltas, and frontend proxy-array caching uses the metadata snapshot hash.
- **Nested public schema validation**: Pages validation now checks nested metadata objects and protocol-specific proxy `details` against the local schema subset, including refs, patterns, arrays, branch schemas, and additional-property closure.
- **Public schema docs parity**: README now documents `proxies.json` as the canonical proxy JSON array and `metadata.json` as the run-statistics object; documentation hygiene prevents reintroducing the old metadata-envelope wording.
- **Lab strategy parity**: Added `frontend/assets/data/lab_strategies.json` as the canonical 9-strategy list; README, wiki, Lab HTML options, and Lab JS hints now agree on the same strategy count and IDs.
- **Lab strategy browser proof**: The same-origin Playwright smoke now verifies that the rendered Lab strategy dropdown matches the canonical strategy manifest.
- **Vwarp Lab strategy handlers**: Implemented `vwarp-masque` and `vwarp-atomic` branches in the Lab chain builder with `_vwarp` metadata and CLI hints; unsupported strategy selections now fail loudly instead of advancing with stale config.
- **Lab QR privacy cleanup**: Removed the external QR image endpoint from `frontend/assets/js/lab.js`; QR export now stays in-browser as an offline copyable payload panel so proxy and chain material is not sent to a third party.
- **Lab manual clean-IP XSS cleanup**: Manual clean-IP rows now render through DOM text nodes instead of `tr.innerHTML`, and manual clean-IP entries are validated before being stored.
- **Lab result-message XSS cleanup**: Dynamic Lab status values from local proxy input, parsed proxy remarks, custom JSON errors, unsupported strategy names, live-test API responses, and export formats are now escaped before entering trusted helper markup.
- **Lab privacy/sanitization tests**: Extended `tests/unit/test_lab_strategy_parity.py` to assert no external QR service is referenced, guard the manual clean-IP table against `innerHTML` regression, and prove dynamic `showResult()` values are escaped.
- **Lab browser XSS/QR smoke**: Extended the same-origin Playwright smoke to inject Lab XSS payloads through local proxy input, parsed proxy remarks, custom JSON errors, live-test API errors/successes, and offline QR export while blocking non-same-origin requests.
- **Async route artifact reads**: `/api/stats` and `/api/diff/proxies` now read and parse JSON artifacts through `asyncio.to_thread()` instead of calling `Path.read_text()` directly inside route handlers.
- **Async route tests**: Added server regression tests proving both metadata and proxy-diff artifact reads dispatch through the off-event-loop JSON loader.
- **Test concurrency cleanup**: Removed the unused `test_budget` semaphore local/parameter wiring from `pipeline.py` and `consumer.py`; `ConcurrencyManager` remains the active Python fallback test limiter.
- **Concurrency contract tests**: Added `tests/unit/test_concurrency_contract.py` to prevent reintroducing the dead semaphore path and to assert that consumer test execution still uses the canonical concurrency manager.
- **Source-quality backpressure accounting**: Producer zero-queued backpressure paths now record `backpressure_drop` run metadata without calling `SourceQualityTracker.report_failure()`, so overloaded runner queues do not punish source trust.
- **Backpressure accounting tests**: Added `tests/unit/test_producer_quality_accounting.py` to verify queue pressure is recorded separately from source failure state.
- **Converter log sanitization**: Sanitized selected URI and Sing-box conversion logs that previously interpolated proxy endpoints, source URLs, source tokens, plugin names, or exception text directly.
- **DNS/Vwarp log sanitization**: Sanitized batch DNS failure logs and Vwarp process/tunnel diagnostics, including version checks, scan exceptions, stdout/stderr snippets, background process lines, and stored failure details, with bounded output lengths.
- **Security/cache log sanitization**: Sanitized security-rule address warnings, honeypot passive-intel host/error logs, and test-cache proxy hit/miss endpoint logs.
- **Parser log sanitization**: Sanitized parser drop/error logs for extraction, Shadowsocks, SSR, Generic/Naive/V2Ray JSON, OpenVPN, VMess, Trojan, Clash JSON, WireGuard-related parsers, and ALPN normalization; extraction now records generic dropped-line markers instead of raw config snippets.
- **High-risk logging policy guard**: Added AST/static checks for parsers, converters, DNS, Vwarp, security rules, honeypot, and test cache so sensitive f-string interpolation, `%`/`.format()` logger messages, and raw sensitive logger arguments fail tests unless approved sanitizer wrappers are used.
- **Security docs logging policy**: Documented sanitizer requirements, high-risk module coverage, parser dropped-line markers, and Vwarp subprocess-output bounds in `SECURITY.md`.
- **Logging sanitization tests**: Added `tests/unit/test_logging_sanitization_policy.py` to verify endpoint IPs and source query tokens are masked in representative converter drop logs, DNS failure logs, Vwarp subprocess output, security-rule logs, honeypot logs, test-cache logs, parser drop/error logs, and static high-risk logging policy checks.
- **Frontend local-first runtime cleanup**: Self-hosted critical frontend JS/CSS/fonts/globe/flag assets and Lab helper downloads, removed runtime dependencies on CDN/remote image hosts, preserved the original flag image experience with vendored 20px PNGs plus text fallback, and tightened page CSP to same-origin assets.
- **Frontend no-network guardrails**: Added static checks for banned runtime CDN hosts, vendor-manifest parity checks, plus Python and Node Playwright browser smokes that block every non-same-origin request while loading primary frontend pages.
- **P2-8 validation run**: `npm run build` passes; `npm run test:frontend:no-network` passes; frontend local-first, workflow, and documentation hygiene pytest checks pass; strict Python Playwright execution is covered by the `frontend-browser` profile.
- **Testing profile cleanup**: Added `scripts/run_test_profile.py` with explicit `unit`, `integration`, `frontend-browser`, and `production-smoke` profiles; `frontend-browser` requires Python Playwright browsers via `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` and CI now has a dedicated job for it.
- **Python frontend E2E proof**: Installed the Python Playwright Chromium payload locally, hardened the Windows browser-readiness probe for `PLAYWRIGHT_BROWSERS_PATH=0`, stabilized analytics E2E around headless WebGL, and verified the strict full suite with `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1`.
- **Frontend degraded browser coverage**: Extended the same-origin Node Playwright smoke to also load primary frontend pages with JavaScript disabled, and exposed it through `npm run test:frontend:degraded`.
- **Version validation Windows guard**: Added regression coverage that reads UTF-8 changelog content while writing through a strict cp1252-like stdout, keeping `scripts/validate_versions.py` safe for default Windows console semantics.
- **Optional Shadowsocks-Rust FFI boundary**: Made Rust SS validation explicitly optional: missing binaries or unset `SS_LIB_SHA256` skip the FFI path while Python validation remains authoritative, and configured hash mismatches fail closed.
- **WASM browser-check semantics**: Labeled frontend WASM checks as browser-limited reachability only, documented that sidecar/Python tests remain authoritative, and made unsupported schemes or invalid URLs fail explicitly before browser `WebSocket` construction.
- **STATUS remediation guard**: Added `scripts/validate_status.py` and wired it into the `production-smoke` profile so stale readiness claims, stale full-pytest counts, missing browser-skip visibility, and non-Beta remediation classifier drift fail locally/CI.
- **Encyclopedia docs mirror guard**: Chose `docs/wiki/encyclopedia` as canonical, synced `docs/encyclopedia` as a byte-identical mirror, and added `scripts/validate_docs_sync.py` plus tests to prevent duplicate-doc drift.
- **Portable debt matrix**: Regenerated debt artifacts with repo-relative paths, generated-artifact exclusions, category summaries that separate test debt from production/frontend/tooling/docs debt, and a `scripts/validate_debt_matrix.py` gate.
- **Static asset hygiene guard**: Removed unreferenced zero-byte `NL`, `US`, and `frontend/assets/images/header-bg.png`, dropped broken optional manifest screenshot references, and added `scripts/validate_assets.py` plus tests to enforce allowlisted zero-byte markers and concrete frontend image references.
- **Optional mirror claim cleanup**: Clarified that GitHub Pages is the core zero-budget publication target and IPFS/Pinata, Hugging Face, Google Drive, and Telegram are optional secret-gated mirrors; added `scripts/validate_optional_mirrors.py` plus tests to prevent core-capability claim drift.
- **Claim ledger bootstrap**: Added `docs/claim_ledger.json` and `scripts/validate_claim_ledger.py` so complete project-document claims must carry owner, tests, docs, changelog, frontend/output proof where applicable, and cleanup decisions.
- **Protocol matrix bootstrap**: Added `docs/protocol_matrix.json` and `scripts/validate_protocol_matrix.py` to make protocol claims explicit across schema enum coverage, parser exports, README claims, frontend display, aliases, schema-only markers, and export limitations.
- **Output matrix bootstrap**: Added `docs/output_matrix.json` and `scripts/validate_output_matrix.py` to make public output-family claims explicit across Pages-required artifact coverage, nonempty requirements, schema-validation flags, degraded validity, side-product required ZIP members, optional OpenVPN/WireGuard member patterns, and remaining semantic-validation work.
- **Side-product ZIP contract**: Pages artifact validation now requires side-product ZIPs to contain `proxies.txt` and rejects unsafe member paths, preserving existing online/offline bundles while tightening deploy-time checks.
- **Side-product deploy-secret scan**: Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers inside ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.
- **Sing-box/Clash artifact semantics**: Pages artifact validation now checks Sing-box selector/urltest references, outbound detours, route rule outbounds, DNS detours, duplicate tags, and Clash group/rule policy references before deployment.
- **Generated output docs**: Added `scripts/generate_output_docs.py` so README and API-reference output tables are rendered from `docs/output_matrix.json`; `production-smoke` now checks the generated blocks are current.
- **Optional native client artifact checks**: `scripts/validate_pages_artifact.py --native-client-check` now runs local `sing-box check` and `mihomo`/Clash config tests when those binaries are available; missing binaries skip cleanly so the zero-budget contract does not require native tools.
- **Deterministic public artifact fixture**: Added a unit fixture that builds a Pages-style artifact from the real output generator, adds deploy aliases and static placeholders, refreshes the public contract, and validates the result with `scripts/validate_pages_artifact.py`.
- **Per-protocol output golden fixtures**: Added matrix-driven fixtures for every public canonical protocol, checking actual Sing-box/Clash converter support and generated subscription output; corrected protocol export flags where the matrix overclaimed current generator support and added safe Clash export for `ss2022`.
- **Parser-to-frontend protocol fixtures**: Added parser samples for every public canonical protocol and a Node-backed frontend normalizer check so parsed `proxies.json` records preserve protocol labels through the real `processProxyData()` path.
- **Malformed parser fail-closed fixtures**: Extended the public protocol golden suite with representative malformed inputs for every public canonical parser, asserting bad data is dropped without widening accepted input behavior.
- **Credential-edge parser hardening**: Tightened TUIC, Snell, Brook, and SSH parsing so missing credential authorities fail closed; anonymous Hysteria/Hysteria2 and unauthenticated generic HTTP/SOCKS remain on their existing compatibility paths.
- **VLESS/VMess credential-boundary proof**: Aligned public protocol golden fixtures to UUIDv4, added VMess missing/empty ID malformed cases, proved VLESS UUID recovery from query parameters, and added validator regressions showing missing VMess/VLESS UUIDs are fatal even when insecure proxy retention is enabled.
- **Shadowsocks query credential recovery**: Moved host-side query parsing before the empty-password fallback decision so `ss://method:@host:port/?password=...` links use the intended password fallback without weakening method validation or missing-password drops.
- **Clash JSON import hardening**: Clash JSON parsing now rejects missing VMess/VLESS UUIDs, missing Trojan/Shadowsocks credentials, invalid Shadowsocks methods, invalid ports, empty WireGuard private keys, and unknown Clash `type` values while preserving valid supported imports.
- **Frontend failover proof**: Added local IPFS/IPNS failover tests for the same-origin connectivity probe, placeholder-key no-op, gateway URL normalization, page/query/hash preservation, and session loop prevention; production-smoke now runs this proof.
- **Browser-rendered protocol fixtures**: Extended the same-origin Chromium smoke with fixture `proxies.json`/`metadata.json` responses for every public canonical protocol, asserting rendered Proxies page protocol badges and filter options without external network access.
- **Validation run**: `scripts/validate_workflows.py` passes for 6 workflow files; `scripts/validate_versions.py` passes; production-smoke passes with workflow, version, status, docs-sync, debt-matrix, asset, optional-mirror, claim-ledger, protocol-matrix, output-matrix, build, same-origin browser, no-JS browser, and focused remediation tests.
- **Parity note**: This step restores workflow syntax trust and adds initial workflow/deploy guardrails. Artifact manifests, public schema contracts, deploy smoke tests, and public output freshness remain tracked in the master audit roadmap.

### Proxy JSON Format (2026-02)
- **output_transport.save_json**: Always outputs JSON array (list of proxies), never single object; coerce non-list input
- **output_handler._save_proxies_with_chains**: Validation that proxies.json root is array
- **output_logic**: country/protocol .list.json — ensure plist is list before building array

### Docs: TLS Fragmentation Status (2026-02)
- **ROADMAP, 01-introduction**: 3 evasion techniques (fragmentation disabled)
- **Lab_Page, 04-engineering, 06-frontend, Home, 10-troubleshooting**: TLS Fragment disabled; point to vwarp AtomicNoize
- **08-api-reference**: EVASION:FRAG tag removed
- **COMPLETE_AUDIT, OUTPUT_*, CENSORSHIP_EVASION, glossary, singbox_configuration_guide, warp**: Consistent fragmentation-disabled messaging

### Deprecated/Legacy Cleanup (2026-02)
- **dynamic_reshard.py**: Removed legacy `pipeline-output/consolidated_pipeline.log` from LOG_PATTERNS
- **evasion.py**: Removed `add_tls_fragmentation` no-op (sing-box removed tls_fragment); fragmentation no longer applied
- **output_handler.py**: `evasion_fragmentation_enabled` now 0 (accurate)
- **split.py**: Removed `has_fragmentation` from proxy details (fragmentation disabled)
- **tagging.py**: Removed EVASION:FRAG tag branch (dead code)
- **pipeline_stats.py**: Updated evasion_fragmentation_enabled comment
- **Frontend**: Consolidated to single `configstream:dataUpdated` event; removed `data-updated`, `dataUpdated` legacy handlers
- **Docs**: evasion_fragmentation_enabled examples 3800→0; audit field descriptions aligned
- **chaining.py**: Removed stray `# import os - removed` comment
- **vwarp.py**: Removed legacy test_url compatibility comment
- **test_washer.py**: Fixed stale output.py reference
- **server.py**: Clarified ValueError comment

### Backend-Frontend-Docs Consistency (2026-02)
- **Frontend fetchers**: All data fetches now use `ROOT_PATH` for subpath deployment (analytics.js, statistics.js, proxy-history-chart.js, lab.js, byow.js, loadCountryData)
- **network.js**: `fetchStatistics()` now has `/api/stats` fallback (aligned with fetchMetadata/fetchProxies)
- **common-ui.js**: Replaced legacy `files/chosen/base64.txt` with explicit chosen paths
- **08-api-reference.md**: Fixed malformed GET /api/proxies section; documented fetchStatistics fallback; corrected module references

### Polish & Consistency (2026-02)
- **CHANGELOG**: Corrected flattened paths (producer.py, consumer.py); deduplicated lab test-chain entries
- **README**: Added Xray, Snell, Brook, Juicity to protocols list
- **testers/manager.py**: Removed redundant pass; simplified gather comment

### Implementations Completed (2026-02)
- **Lab test-chain API**: Full implementation when singbox2proxy/sing-box available — tests chain config, returns latency and exit IP; 503 when unavailable
- **Vectors stability/reliability**: Integrated `ProxyHistoryTracker.get_bulk_stats()` into `generate_vectors()` — dimensions 6–7 now use real success-rate data instead of default 5
- **auto_detect parsers**: Xray, Snell, Brook, Juicity added to `auto_detect_and_parse()` for pipeline format support

### Documentation & Test Fixes (2026-02)
- **CENSORSHIP_EVASION.md**: Fixed test references — use `test_evasion.py`, `test_censorship.py` (removed non-existent `test_censorship_lab.py`, `test_html_smuggler.py`)
- **HTML smuggling**: Updated docs to reference `stego.py` (no `html_smuggler.py` module)
- **countries.py**: Documented as optional; added `__all__`
- **test_output_transport.py**: Merged into `test_converters.py` (tests converter transport options)
- **09-contributing.md**: Updated batch count to 17; tools list (VwarpTool, CensorshipLab, DNS scanner)
- **08-api-reference.md**: Documented `POST /api/lab/test-chain`
- **security_concepts.md**: HTML smuggling now references stego delivery
- **test_output_full.py**: Updated split output assertion (proxy + washed = 2 selector tags)
- **security/honeypot.py**: Docstring clarified (pipeline uses Go tester; is_honeypot for tests/standalone)
- **Note**: test_html_smuggler.py (referenced in 2.7.0) no longer exists; stego tests cover delivery

---

## [3.0.2] - 2026-02-14

### Comprehensive Code Review & Simplification

**Logic Consolidation**
- `security/rules.py`: Replaced 14 duplicate regex patterns with import from `security_validator.LOCAL_IP_RANGES` — single source of truth
- `security_validator.py`: Inlined `validate_proxy` into `SecurityValidator.validate_proxy_config` — eliminated alias indirection
- `security_validator.py`: Collapsed 4 TLS protocol branches into single `in ("trojan", "hysteria2", "tuic", "https")` check
- `security_validator.py`: Simplified redundant UUID double-check into flat early-return pattern
- `filtering.py`: Extracted triplicated "prefer working > lower latency" comparison into shared `_is_better_proxy()` helper — replaced 3 call sites
- `producer.py`: Extracted triplicated "report failure + record run" pattern into `_report_source_failure()` helper — eliminated ~70 lines of duplication
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
- `consumer.py`: Removed redundant outer `try/except` in `_parse_chunk` and unnecessary `pass` after logging
- `consumer.py`: Removed 7-line stale developer notes about proxy mutability
- `security/rules.py`: Simplified `validate_port` — collapsed 8-line if/else/pass block into 2-line debug log
- `virus_total.py`: Removed redundant `str()` wrapping in f-string
- `testers/go.py`: Removed dead `pass` + stale reentrancy comment in `_read_stderr_loop`
- `output_logic.py`: Removed dead `total_sources` metadata alias — unused by frontend or tests
- `parsers/shadowsocks.py`: Removed dead `pass` statement and redundant host validation

**Bug Fixes**
- `consumer.py`: Fixed silent fingerprint save failure — `orjson.dumps()` doesn't accept `ensure_ascii` kwarg; switched to `write_bytes()` with orjson bytes output

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
