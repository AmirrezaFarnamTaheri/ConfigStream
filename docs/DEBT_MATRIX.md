# Debt Matrix

Generated: `2026-05-07T06:50:24.531406+00:00`

## Summary

- Total markers: **1402**
- `ASSUMING`: **9**
- `FIXME`: **1**
- `MOCK`: **1248**
- `PLACEHOLDER`: **126**
- `TODO`: **13**
- `XXX`: **5**

## Categories

- `ci`: **1**
- `docs`: **10**
- `frontend`: **51**
- `other`: **39**
- `production`: **28**
- `test`: **1252**
- `tooling`: **21**

## Triage Rules

- `FIXME` / `XXX`: fix inline before release freeze.
- `TODO`: create issue with owner + milestone.
- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.
- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.

## Findings

| File | Marker Count | Markers |
| --- | ---: | --- |
| `.github/workflows/deploy-pages.yml` | 1 | PLACEHOLDER |
| `AGENTS.md` | 1 | ASSUMING |
| `CHANGELOG.md` | 4 | PLACEHOLDER, TODO |
| `CLOSURE_REPORT.md` | 1 | PLACEHOLDER |
| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 34 | MOCK, PLACEHOLDER, TODO |
| `SECURITY.md` | 2 | PLACEHOLDER |
| `STATUS.md` | 3 | PLACEHOLDER |
| `docs/wiki/encyclopedia/glossary/networking_terms.md` | 1 | ASSUMING |
| `docs/wiki/encyclopedia/glossary/security_concepts.md` | 1 | XXX |
| `docs/wiki/encyclopedia/networking/warp.md` | 1 | XXX |
| `frontend/assets/js/analytics.js` | 3 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/charts.js` | 1 | MOCK |
| `frontend/assets/js/constants.js` | 3 | PLACEHOLDER |
| `frontend/assets/js/i18n.js` | 12 | PLACEHOLDER |
| `frontend/assets/js/lab.js` | 1 | XXX |
| `frontend/assets/js/main.js` | 2 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/stego.js` | 2 | PLACEHOLDER |
| `frontend/assets/js/verifier.js` | 3 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/washer_client.js` | 1 | MOCK |
| `frontend/index.html` | 1 | PLACEHOLDER |
| `frontend/lab-offline.html` | 1 | PLACEHOLDER |
| `frontend/lab.html` | 15 | PLACEHOLDER, XXX |
| `frontend/proxies.html` | 5 | PLACEHOLDER |
| `frontend/service-worker.js` | 1 | ASSUMING |
| `scripts/generate_debt_matrix.py` | 6 | FIXME, MOCK, PLACEHOLDER, TODO |
| `scripts/run_test_profile.py` | 1 | PLACEHOLDER |
| `scripts/validate_frontend_placeholders.py` | 10 | PLACEHOLDER |
| `scripts/validate_workflows.py` | 4 | PLACEHOLDER |
| `sources/manual_warp.txt` | 1 | XXX |
| `src/configstream/anomaly.py` | 2 | MOCK |
| `src/configstream/constants.py` | 1 | PLACEHOLDER |
| `src/configstream/generators/base64.py` | 1 | PLACEHOLDER |
| `src/configstream/history/tracker.py` | 1 | MOCK |
| `src/configstream/intelligence/chaining.py` | 1 | MOCK |
| `src/configstream/quality/storage.py` | 7 | PLACEHOLDER |
| `src/configstream/security_validator.py` | 4 | MOCK |
| `src/configstream/tools/censorship_lab.py` | 1 | MOCK |
| `src/configstream/tools/dns_scanner/bash/dnsScanner.sh` | 7 | TODO |
| `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` | 3 | PLACEHOLDER |
| `tests/e2e/test_failure_scenarios.py` | 4 | MOCK |
| `tests/e2e/test_frontend.py` | 10 | MOCK |
| `tests/e2e/test_mixed_protocols.py` | 10 | MOCK |
| `tests/scenarios/test_failure_modes.py` | 9 | MOCK |
| `tests/test_manager.py` | 19 | MOCK |
| `tests/test_output_transport.py` | 7 | MOCK |
| `tests/test_python_tester.py` | 18 | MOCK |
| `tests/test_scanner.py` | 17 | MOCK |
| `tests/test_warp_scraper.py` | 17 | MOCK |
| `tests/test_washer_utils.py` | 1 | MOCK |
| `tests/unit/converters/test_singbox_converters.py` | 1 | MOCK |
| `tests/unit/coverage_boost/test_adaptive_workers_coverage.py` | 13 | MOCK |
| `tests/unit/coverage_boost/test_blocklist_coverage.py` | 2 | MOCK |
| `tests/unit/coverage_boost/test_cli_coverage.py` | 27 | MOCK |
| `tests/unit/coverage_boost/test_server_coverage.py` | 1 | MOCK |
| `tests/unit/coverage_boost/test_washer_coverage.py` | 7 | MOCK |
| `tests/unit/fetcher/test_fetcher_core.py` | 2 | MOCK |
| `tests/unit/generators/test_singbox_comprehensive.py` | 1 | MOCK |
| `tests/unit/geoip/test_geoip_resolver.py` | 17 | MOCK |
| `tests/unit/history/test_history_components.py` | 8 | MOCK |
| `tests/unit/intelligence/test_chaining_extended.py` | 2 | MOCK |
| `tests/unit/intelligence/test_vectors.py` | 1 | MOCK |
| `tests/unit/quality/test_quality_components.py` | 2 | MOCK |
| `tests/unit/security/test_censorship.py` | 5 | MOCK |
| `tests/unit/security/test_rules.py` | 8 | MOCK |
| `tests/unit/security/test_utls_wrapper.py` | 14 | MOCK |
| `tests/unit/security/test_virus_total_comprehensive.py` | 75 | MOCK |
| `tests/unit/test_adapters_comprehensive.py` | 6 | MOCK |
| `tests/unit/test_adaptive_timeout_extra.py` | 4 | MOCK |
| `tests/unit/test_adaptive_workers.py` | 3 | MOCK |
| `tests/unit/test_analytics_output.py` | 7 | MOCK |
| `tests/unit/test_anomaly_extended.py` | 9 | MOCK |
| `tests/unit/test_backup.py` | 1 | MOCK |
| `tests/unit/test_backup_extended.py` | 8 | MOCK |
| `tests/unit/test_bot_cli.py` | 38 | MOCK |
| `tests/unit/test_cache_warming.py` | 15 | ASSUMING, MOCK |
| `tests/unit/test_cli_extended.py` | 23 | MOCK |
| `tests/unit/test_cli_full.py` | 1 | MOCK |
| `tests/unit/test_concurrency_extended.py` | 3 | MOCK |
| `tests/unit/test_consumer.py` | 23 | MOCK |
| `tests/unit/test_dns_batch_resolver.py` | 12 | MOCK |
| `tests/unit/test_event_stream.py` | 65 | MOCK |
| `tests/unit/test_fetcher.py` | 85 | MOCK |
| `tests/unit/test_fetcher_advanced.py` | 18 | MOCK |
| `tests/unit/test_fetcher_config.py` | 13 | MOCK |
| `tests/unit/test_fetcher_resilience.py` | 8 | MOCK |
| `tests/unit/test_fetcher_retries.py` | 12 | MOCK |
| `tests/unit/test_filtering_extended.py` | 8 | MOCK |
| `tests/unit/test_geoip_extended.py` | 3 | MOCK |
| `tests/unit/test_go_tester_streaming.py` | 20 | MOCK |
| `tests/unit/test_honeypot.py` | 71 | MOCK |
| `tests/unit/test_init_module.py` | 2 | MOCK |
| `tests/unit/test_output.py` | 4 | MOCK |
| `tests/unit/test_output_advanced.py` | 1 | MOCK |
| `tests/unit/test_output_full.py` | 13 | MOCK |
| `tests/unit/test_output_logic.py` | 1 | PLACEHOLDER |
| `tests/unit/test_parsers_robustness.py` | 1 | MOCK |
| `tests/unit/test_pipeline_coverage.py` | 38 | MOCK |
| `tests/unit/test_pipeline_deep.py` | 38 | MOCK |
| `tests/unit/test_pipeline_extended.py` | 64 | MOCK |
| `tests/unit/test_pipeline_orchestration.py` | 29 | MOCK |
| `tests/unit/test_pipeline_stages.py` | 125 | MOCK |
| `tests/unit/test_producer_quality_accounting.py` | 2 | MOCK |
| `tests/unit/test_proxy_history_extended.py` | 6 | MOCK |
| `tests/unit/test_scheduler.py` | 4 | MOCK |
| `tests/unit/test_security.py` | 26 | MOCK |
| `tests/unit/test_security_validator.py` | 1 | ASSUMING |
| `tests/unit/test_security_validator_extra.py` | 5 | MOCK |
| `tests/unit/test_security_validator_full.py` | 1 | ASSUMING |
| `tests/unit/test_server.py` | 34 | MOCK |
| `tests/unit/test_server_new.py` | 1 | MOCK |
| `tests/unit/test_singbox_binary_resolution.py` | 1 | MOCK |
| `tests/unit/test_sorter.py` | 20 | MOCK |
| `tests/unit/test_ss_ffi.py` | 47 | MOCK |
| `tests/unit/test_utils.py` | 1 | MOCK |
| `tests/unit/test_utils_extended.py` | 3 | MOCK |
| `tests/unit/test_validate_frontend_placeholders.py` | 12 | PLACEHOLDER |
| `tests/unit/test_validate_workflows.py` | 1 | PLACEHOLDER |
| `tests/unit/test_washer.py` | 6 | MOCK |
| `tests/unit/tools/test_dns_scanner.py` | 3 | MOCK |
| `tests/unit/utils/test_cert.py` | 8 | MOCK |

## Raw Entries

### `.github/workflows/deploy-pages.yml`
- L136 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output`

### `AGENTS.md`
- L148 [`ASSUMING`] `*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.`

### `CHANGELOG.md`
- L36 [`PLACEHOLDER`] `- **Frontend placeholder deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to inject `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets before upload.`
- L37 [`PLACEHOLDER`] `- **Frontend placeholder tests/workflow parity**: Added tests for placeholder detection/injection and extended workflow validation so `deploy-pages.yml` cannot drop the frontend placeholder guard or secret env wiring silently.`
- L68 [`PLACEHOLDER`] `- **Validation run**: `scripts/validate_workflows.py` passes for 6 workflow files; `scripts/validate_versions.py` passes; focused remediation tests pass with 127 tests across server, fetcher, output, deploy-contract, analytics, merge, docs hygiene, frontend-placeholder, lab-strategy, concurrency-contract, producer-quality, logging-sanitization, workflow, and version validation.`
- L191 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts`

### `CLOSURE_REPORT.md`
- L11 [`PLACEHOLDER`] `**Resolution:** Updated `main.yml` to set `continue-on-error: true` for the `frontend-wasm` download step in the merge job. Ensure `scripts/build_wasm.sh` creates the necessary directories and placeholder dummy files gracefully if compilation fails.`

### `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`
- L20 [`PLACEHOLDER`] `5. The deployed frontend path bypasses the Vite build output and serves raw static files with placeholder key material.`
- L57 [`PLACEHOLDER`] `- frontend external dependencies, placeholders, and `innerHTML``
- L378 [`PLACEHOLDER`] `- The frontend renders the degraded state without placeholders.`
- L679 [`PLACEHOLDER`] `Status: partially remediated on 2026-05-04. Pages deploy now injects and validates frontend placeholders; the larger Vite-vs-raw-frontend production-build decision remains open.`
- L683 [`PLACEHOLDER`] `- `frontend/assets/js/constants.js` contains placeholder `PUBLIC_KEY`.`
- L684 [`PLACEHOLDER`] `- `frontend/assets/js/stego.js` contains `PLACEHOLDER_KEY_INJECTED_BY_CI`.`
- L693 [`PLACEHOLDER`] `- Production Pages likely serves placeholder key material.`
- L700 [`PLACEHOLDER`] `- Added `scripts/validate_frontend_placeholders.py`.`
- L701 [`PLACEHOLDER`] `- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.`
- L702 [`PLACEHOLDER`] `- Pages deploy now passes `CS_PUBLIC_KEY` and `STEGO_KEY` into the frontend placeholder guard step from GitHub secrets.`
- L705 [`PLACEHOLDER`] `- The validator fails if the public key placeholder marker or stego placeholder remains in the Pages artifact.`
- L706 [`PLACEHOLDER`] `- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.`
- L707 [`PLACEHOLDER`] `- Tests cover placeholder detection, env injection, optional non-strict stego handling, and workflow guard retention.`
- L714 [`PLACEHOLDER`] `4. Fail production build if required public key/stego key placeholders remain.`
- L716 [`PLACEHOLDER`] `6. Add placeholder leak tests.`
- L727 [`PLACEHOLDER`] `- Deployed frontend contains no placeholder key strings.`
- L731 [`PLACEHOLDER`] `- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.`
- L1183 [`PLACEHOLDER`] `- If the library is present but does not match the placeholder hash, validation fails.`
- L1258 [`TODO`] `- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.`
- L1336 [`MOCK`] `3. Separate test-only mocks from production TODOs.`
- L1341 [`PLACEHOLDER`] `### P3-4. Zero-byte and placeholder assets remain`
- L1554 [`PLACEHOLDER`] `- Placeholder key material remains.`
- L1560 [`PLACEHOLDER`] `- Make frontend local-first, build-driven, no-placeholder, and no-network smoke-tested.`
- L1813 [`PLACEHOLDER`] `3. Public pages must never show unresolved placeholders.`
- L1823 [`PLACEHOLDER`] `- placeholder leak tests`
- L1895 [`TODO`] `- zero TODO/FIXME`
- L1936 [`PLACEHOLDER`] `4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.`
- L2112 [`PLACEHOLDER`] `5. Fail build on placeholder keys.`
- L2125 [`PLACEHOLDER`] `- Delete unused build path, unused scripts, and placeholder config files.`
- L2194 [`PLACEHOLDER`] `6. Add no-placeholder, no-network frontend, public contract, and security posture tests.`
- L2239 [`PLACEHOLDER`] `- frontend has no unresolved placeholders.`
- L2240 [`PLACEHOLDER`] `- no placeholder key material is deployed.`
- L2279 [`PLACEHOLDER`] `- No placeholder keys.`
- L2339 [`PLACEHOLDER`] `10. Frontend has no placeholder keys or unresolved template tokens.`

### `SECURITY.md`
- L46 [`PLACEHOLDER`] `- Deploy fails if the public-key placeholder or stego placeholder remains in the Pages artifact.`
- L47 [`PLACEHOLDER`] `- Workflow validation enforces the frontend placeholder guard so it cannot be removed from deploy without breaking validation.`

### `STATUS.md`
- L40 [`PLACEHOLDER`] `- Pages deploy now injects `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets and fails before upload if frontend public-key or stego placeholders remain; workflow validation enforces this guard.`
- L85 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed`
- L92 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed`

### `docs/wiki/encyclopedia/glossary/networking_terms.md`
- L114 [`ASSUMING`] `*   **ConfigStream Usage:** Some parsers reject input if the "Noise Ratio" (non-printable characters) is too high, assuming it's garbage. Conversely, obfuscation protocols add noise to look like static.`

### `docs/wiki/encyclopedia/glossary/security_concepts.md`
- L73 [`XXX`] `*   **Format:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (36 characters with hyphens).`

### `docs/wiki/encyclopedia/networking/warp.md`
- L96 [`XXX`] `*   **WARP+ Key:** Format `xxxxxxxx-xxxxxxxx-xxxxxxxx`. Provides optimized routing (Argo Smart Routing). Optional — free tier is sufficient for circumvention.`

### `frontend/assets/js/analytics.js`
- L40 [`PLACEHOLDER`] `// Show empty state or placeholder`
- L161 [`PLACEHOLDER`] `container.innerHTML = '<div class="error-placeholder">Visualization Unavailable (Network Error)</div>';`
- L776 [`ASSUMING`] `// Assuming all rejection reasons are worth showing if present`

### `frontend/assets/js/charts.js`
- L106 [`MOCK`] `// Audit: Removed random mock data to prevent misleading users.`

### `frontend/assets/js/constants.js`
- L29 [`PLACEHOLDER`] `// Validation: Detect placeholder values in production`
- L43 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder PUBLIC_KEY!");`
- L48 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder IPNS_KEY!");`

### `frontend/assets/js/i18n.js`
- L135 [`PLACEHOLDER`] `"byow.url.placeholder": "Paste your Cloudflare Worker URL...",`
- L136 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Optional: UUID",`
- L362 [`PLACEHOLDER`] `"byow.url.placeholder": "在此输入 Cloudflare Worker 地址...",`
- L363 [`PLACEHOLDER`] `"byow.uuid.placeholder": "可选: UUID",`
- L582 [`PLACEHOLDER`] `"byow.url.placeholder": "آدرس Cloudflare Worker خود را وارد کنید...",`
- L583 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختیاری: UUID",`
- L802 [`PLACEHOLDER`] `"byow.url.placeholder": "Вставьте ссылку на ваш Cloudflare Worker...",`
- L803 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Опционально: UUID",`
- L1022 [`PLACEHOLDER`] `"byow.url.placeholder": "رابط Cloudflare Worker...",`
- L1023 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختياري: UUID",`
- L1187 [`PLACEHOLDER`] `if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {`
- L1188 [`PLACEHOLDER`] `el.setAttribute('placeholder', translation);`

### `frontend/assets/js/lab.js`
- L1425 [`XXX`] `CFG=$(mktemp /tmp/cs-chain-XXXX.json)`

### `frontend/assets/js/main.js`
- L102 [`ASSUMING`] `// Assuming proxies have 'id'`
- L183 [`PLACEHOLDER`] `// Initialize immediately with defaults to avoid "--" flash or placeholders`

### `frontend/assets/js/stego.js`
- L9 [`PLACEHOLDER`] `const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";`
- L13 [`PLACEHOLDER`] `SECRET_KEY === "PLACEHOLDER_KEY_INJECTED_BY_CI" ||`

### `frontend/assets/js/verifier.js`
- L42 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {`
- L49 [`ASSUMING`] `// Assuming Base64 SPKI from constants.js example`
- L96 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {`

### `frontend/assets/js/washer_client.js`
- L9 [`MOCK`] `// Mock status check`

### `frontend/index.html`
- L515 [`PLACEHOLDER`] `placeholder="your-worker.username.workers.dev"`

### `frontend/lab-offline.html`
- L129 [`PLACEHOLDER`] `warp:'<div class="row"><div><label>Clean IP</label><input data-f="ip" value="162.159.192.1"></div><div><label>Port</label><input data-f="port" type="number" value="2408"></div></div><div><label>WARP+ Key (optional)</label><input data-f="key" placeholder="Leave blank for free"></div>',`

### `frontend/lab.html`
- L573 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="localProxyAddr" placeholder="127.0.0.1:1080">`
- L584 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="proxyUri" placeholder="vless://uuid@server:443?type=ws&security=tls&sni=example.com#MyProxy"></textarea>`
- L628 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="manualCleanIps" placeholder="162.159.192.1:2408&#10;188.114.98.224:854"></textarea>`
- L710 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warpKeyInput" placeholder="Leave blank for free tier">`
- L711 [`XXX`] `<div class="hint">WARP+ key for better speed. Format: xxxxxxxx-xxxxxxxx-xxxxxxxx</div>`
- L717 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2CleanIp" placeholder="162.159.192.1:2408">`
- L722 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2Key" placeholder="Leave blank for free tier">`
- L732 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragSize" value="10-30" placeholder="10-30">`
- L737 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragDelay" value="5-10" placeholder="5-10">`
- L789 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="workerUrl" placeholder="https://my-worker.username.workers.dev">`
- L814 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="1" placeholder="127.0.0.1:1080 or vless://...">`
- L836 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="2" placeholder="10.0.0.50:3128 or trojan://...">`
- L857 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="3" placeholder="162.159.192.1:2408 or vmess://...">`
- L878 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="4" placeholder="ss://... or socks5://...">`
- L892 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="customOutboundsJson" placeholder='[{"type":"wireguard","tag":"warp-out","server":"162.159.192.1",...}]' style="min-height:160px;"></textarea>`

### `frontend/proxies.html`
- L140 [`PLACEHOLDER`] `<input type="text" id="worker-url" data-i18n="byow.url.placeholder" placeholder="Paste Worker URL..." class="input-modern">`
- L141 [`PLACEHOLDER`] `<input type="text" id="worker-uuid" data-i18n="byow.uuid.placeholder" placeholder="UUID (Optional)" class="input-modern input-short">`
- L154 [`PLACEHOLDER`] `<input type="text" id="searchInput" data-i18n="filters.search" placeholder="e.g., fastest US vmess, or Germany < 100ms" aria-label="Search proxies">`
- L188 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMin" placeholder="Min" aria-label="Minimum latency">`
- L190 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMax" placeholder="Max" aria-label="Maximum latency">`

### `frontend/service-worker.js`
- L42 [`ASSUMING`] `// Assuming prefix "configstream-v" from cache-config.js logic`

### `scripts/generate_debt_matrix.py`
- L3 [`TODO`] `"""Generate a repository debt matrix from TODO/FIXME-style markers."""`
- L16 [`TODO`] `PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"`
- L160 [`FIXME`] `"- `FIXME` / `XXX`: fix inline before release freeze.",`
- L161 [`TODO`] `"- `TODO`: create issue with owner + milestone.",`
- L162 [`MOCK`] `"- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.",`
- L163 [`PLACEHOLDER`] `"- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.",`

### `scripts/run_test_profile.py`
- L94 [`PLACEHOLDER`] `"tests/unit/test_validate_frontend_placeholders.py",`

### `scripts/validate_frontend_placeholders.py`
- L4 [`PLACEHOLDER`] `This guard keeps deploy artifacts from silently shipping placeholder verification`
- L18 [`PLACEHOLDER`] `PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")`
- L19 [`PLACEHOLDER`] `STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"`
- L68 [`PLACEHOLDER`] `def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:`
- L77 [`PLACEHOLDER`] `if any(marker in constants for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):`
- L79 [`PLACEHOLDER`] `"Frontend PUBLIC_KEY placeholder remains in assets/js/constants.js"`
- L87 [`PLACEHOLDER`] `if STEGO_KEY_PLACEHOLDER in stego:`
- L89 [`PLACEHOLDER`] `"Frontend STEGO_KEY placeholder remains in assets/js/stego.js"`
- L120 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(root, strict=bool(args.strict))`
- L126 [`PLACEHOLDER`] `print("OK: frontend production placeholders validated.")`

### `scripts/validate_workflows.py`
- L46 [`PLACEHOLDER`] `def _deploy_pages_has_frontend_placeholder_guard(path: Path) -> bool:`
- L52 [`PLACEHOLDER`] `"scripts/validate_frontend_placeholders.py --inject-env --strict output"`
- L108 [`PLACEHOLDER`] `and not _deploy_pages_has_frontend_placeholder_guard(path)`
- L111 [`PLACEHOLDER`] `f"{path}: missing frontend placeholder injection/validation guard"`

### `sources/manual_warp.txt`
- L10 [`XXX`] `wireguard://UJckB8h6r2P6xxx8UEspxw8r3YkpzBEbjxol3jeoqEw%3D@188.114.97.82:5956?address=172.16.0.2/32, 2606:4700:110:846c:e510:bfa1:ea9f:5247/128&publickey=bmXOC%2BF1FxEMF9dyiK2H5%2F1SUtzH0JuVo51h2wPfgyo%3D&reserved=61%2C41%2C250#Tel= @arshiacomplus wire`

### `src/configstream/anomaly.py`
- L193 [`MOCK`] `# However, the test 'test_failure_mode_anomaly_db_crash' explicitly mocks this method`
- L194 [`MOCK`] `# to raise RuntimeError. If the real method catches it, the test mock is bypassed if we use spy.`

### `src/configstream/constants.py`
- L128 [`PLACEHOLDER`] `"ws",  # Test fixtures / transport placeholders`

### `src/configstream/generators/base64.py`
- L12 [`PLACEHOLDER`] `a minimal placeholder is encoded so output files are always ≥ 1 byte.`

### `src/configstream/history/tracker.py`
- L97 [`MOCK`] `# Fallback for mock storage`

### `src/configstream/intelligence/chaining.py`
- L187 [`MOCK`] `)  # Fallback if library returns raw float (unlikely for geopy but good for mocks)`

### `src/configstream/quality/storage.py`
- L354 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns_to_use))`
- L376 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec`
- L384 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec`
- L396 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(cols_no_id))`
- L403 [`PLACEHOLDER`] `f"INSERT INTO source_runs ({','.join(cols_no_id)}) VALUES ({placeholders})",  # nosec`
- L419 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns))`
- L422 [`PLACEHOLDER`] `f"INSERT INTO proxy_history VALUES ({placeholders})",  # nosec`

### `src/configstream/security_validator.py`
- L6 [`MOCK`] `# Import urlparse directly to allow mocking in tests`
- L153 [`MOCK`] `Internal check for address safety. Used by tests to mock safety checks.`
- L177 [`MOCK`] `# Use internal check (to allow mocking by tests)`
- L279 [`MOCK`] `# Use SecurityValidator.validate_proxy_config to allow mocking on the class`

### `src/configstream/tools/censorship_lab.py`
- L63 [`MOCK`] `"""Mock IP blocklist for testing."""`

### `src/configstream/tools/dns_scanner/bash/dnsScanner.sh`
- L130 [`TODO`] `barCharTodo=" "`
- L140 [`TODO`] `# The number of done and todo characters`
- L142 [`TODO`] `todo=$(bc <<< "scale=0; $barSize - $done")`
- L143 [`TODO`] `# build the done and todo sub-bars`
- L145 [`TODO`] `todoSubBar=$(printf "%${todo}s" | tr " " "${barCharTodo} - 1") # 1 for barSplitter`
- L146 [`TODO`] `spacesSubBar=$(printf "%${todo}s" | tr " " " ")`
- L149 [`TODO`] `progressBar="| Progress bar of main IPs: [${doneSubBar}${barSplitter}${todoSubBar}] ${percent}%${spacesSubBar}" # Some end space for pretty formatting`

### `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py`
- L722 [`PLACEHOLDER`] `placeholder="Enter path or click Browse",`
- L734 [`PLACEHOLDER`] `placeholder="e.g., google.com",`
- L758 [`PLACEHOLDER`] `placeholder="100",`

### `tests/e2e/test_failure_scenarios.py`
- L12 [`MOCK`] `# Mock quality tracker to reject everything`
- L37 [`MOCK`] `# Mock AnomalyDetector to fail on is_safe`
- L43 [`MOCK`] `# Mock fetcher to return something`
- L58 [`MOCK`] `# Mock GeoIP`

### `tests/e2e/test_frontend.py`
- L45 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing`
- L107 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing`
- L145 [`MOCK`] `# Mock the metadata request data (using canonical field names from v2.0.8)`
- L146 [`MOCK`] `mock_data = {`
- L161 [`MOCK`] `mock_json = json.dumps(mock_data)`
- L163 [`MOCK`] `# Inject a mock fetch function that returns our data for statistics endpoints`
- L169 [`MOCK`] `// Mock metadata.json (unified stats) and api/stats endpoints`
- L174 [`MOCK`] `json: async () => ({mock_json})`
- L180 [`MOCK`] `// Mock window.api.fetchStatistics directly if needed`
- L182 [`MOCK`] `window.api.fetchStatistics = async () => ({mock_json});`

### `tests/e2e/test_mixed_protocols.py`
- L28 [`MOCK`] `# 2. Mock external dependencies that might block or fail without network`
- L30 [`MOCK`] `# Mock GeoIP to return deterministic data`
- L34 [`MOCK`] `# We need self because we are mocking the instance method or class method?`
- L35 [`MOCK`] `# Actually standard mock usually mocks the function on the class.`
- L49 [`MOCK`] `# Mock Blocklist update`
- L55 [`MOCK`] `# Mock Output Generation to avoid filesystem overhead but verify data presence`
- L60 [`MOCK`] `# The roadmap says: "assert that parsing, validation, dedup, washing, and GeoIP enrichment all execute without mocks."`
- L62 [`MOCK`] `# So we MOCKED GeoIP above. The roadmap allows mocks for things that strictly require network.`
- L64 [`MOCK`] `# However, we need to mock `generate_stego_assets` since it requires assets/images which might not exist in tmp env.`
- L66 [`MOCK`] `# So we remove the mock that causes AttributeError.`

### `tests/scenarios/test_failure_modes.py`
- L16 [`MOCK`] `# Mock SourceQualityTracker to always return False for should_fetch`
- L27 [`MOCK`] `# Mock Blocklist update to avoid network`
- L64 [`MOCK`] `# Mock SourceQualityTracker to allow fetch`
- L70 [`MOCK`] `# Mock network fetch`
- L85 [`MOCK`] `# Mock Blocklist`
- L91 [`MOCK`] `# Mock GeoIP`
- L94 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData`
- L126 [`MOCK`] `# Mock fetch/geoip/blocklist as usual`
- L148 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData`

### `tests/test_manager.py`
- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch`
- L8 [`MOCK`] `def mock_settings():`
- L9 [`MOCK`] `with patch("configstream.testers.manager.AppSettings") as MockSettings:`
- L10 [`MOCK`] `settings = MockSettings.return_value`
- L16 [`MOCK`] `async def test_singbox_tester_dry_run(mock_settings):`
- L29 [`MOCK`] `async def test_singbox_tester_batch_dry_run(mock_settings):`
- L47 [`MOCK`] `async def test_singbox_tester_cache_hit(mock_settings):`
- L48 [`MOCK`] `cache = MagicMock()`
- L72 [`MOCK`] `async def test_singbox_tester_python_direct(mock_settings):`
- L74 [`MOCK`] `tester.python_tester.test_direct = AsyncMock(`
- L75 [`MOCK`] `return_value=MagicMock(is_working=True)`
- L90 [`MOCK`] `async def test_singbox_tester_go_fallback(mock_settings):`
- L92 [`MOCK`] `# Mock Go tester as unavailable`
- L94 [`MOCK`] `tester.python_tester.test_via_singbox = AsyncMock(`
- L95 [`MOCK`] `return_value=MagicMock(is_working=True)`
- L103 [`MOCK`] `# Should call python tester via semaphore wrapper (internal details hard to mock perfectly, but we check if result populated)`
- L104 [`MOCK`] `# Actually we mocked the method, so let's verify call.`
- L111 [`MOCK`] `async def test_singbox_tester_close(mock_settings):`
- L113 [`MOCK`] `tester.go_tester.close = AsyncMock()`

### `tests/test_output_transport.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L9 [`MOCK`] `def mock_history():`
- L10 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:`
- L11 [`MOCK`] `hist = MockHistory.return_value`
- L16 [`MOCK`] `def test_save_json(tmp_path, mock_history):`
- L35 [`MOCK`] `def test_save_json_outputs_array_not_single_object(tmp_path, mock_history):`
- L50 [`MOCK`] `def test_save_json_compress(tmp_path, mock_history):`

### `tests/test_python_tester.py`
- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch`
- L8 [`MOCK`] `def mock_settings():`
- L9 [`MOCK`] `settings = MagicMock()`
- L16 [`MOCK`] `async def test_python_tester_direct_http(mock_settings):`
- L17 [`MOCK`] `tester = PythonTester(mock_settings)`
- L22 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:`
- L23 [`MOCK`] `session = MockSession.return_value`
- L26 [`MOCK`] `# Mock successful response`
- L27 [`MOCK`] `resp = MagicMock()`
- L38 [`MOCK`] `async def test_python_tester_direct_fail(mock_settings):`
- L39 [`MOCK`] `tester = PythonTester(mock_settings)`
- L47 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:`
- L48 [`MOCK`] `session = MockSession.return_value`
- L51 [`MOCK`] `# Mock exception for get()`
- L75 [`MOCK`] `async def test_python_tester_singbox_missing_factory(mock_settings):`
- L77 [`MOCK`] `tester = PythonTester(mock_settings)`
- L91 [`MOCK`] `async def test_python_tester_no_config(mock_settings):`
- L92 [`MOCK`] `tester = PythonTester(mock_settings)`

### `tests/test_scanner.py`
- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch`
- L8 [`MOCK`] `# Mock settings to NOT force scanner`
- L9 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:`
- L10 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False`
- L18 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:`
- L19 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = True`
- L20 [`MOCK`] `MockSettings.return_value.CONFIGSTREAM_TESTER_BIN = "/bin/ls"  # Dummy path`
- L30 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:`
- L31 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = False`
- L32 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False`
- L43 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:`
- L44 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True`
- L46 [`MOCK`] `# Mock subprocess`
- L47 [`MOCK`] `proc = AsyncMock()`
- L66 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:`
- L67 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True`
- L69 [`MOCK`] `proc = AsyncMock()`

### `tests/test_warp_scraper.py`
- L3 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch`
- L7 [`MOCK`] `def _mock_httpx_response(text: str):`
- L9 [`MOCK`] `mock_resp = MagicMock(spec=httpx.Response)`
- L10 [`MOCK`] `mock_resp.text = text`
- L11 [`MOCK`] `mock_resp.status_code = 200`
- L12 [`MOCK`] `mock_resp.raise_for_status = MagicMock()`
- L14 [`MOCK`] `mock_client = AsyncMock(spec=httpx.AsyncClient)`
- L15 [`MOCK`] `mock_client.get = AsyncMock(return_value=mock_resp)`
- L16 [`MOCK`] `mock_client.__aenter__ = AsyncMock(return_value=mock_client)`
- L17 [`MOCK`] `mock_client.__aexit__ = AsyncMock(return_value=False)`
- L18 [`MOCK`] `return mock_client`
- L24 [`MOCK`] `mock_client = _mock_httpx_response("162.159.192.1:2408\ninvalid\n1.1.1.1")`
- L33 [`MOCK`] `return_value=mock_client,`
- L48 [`MOCK`] `mock_client = _mock_httpx_response(warp_uri)`
- L57 [`MOCK`] `return_value=mock_client,`
- L87 [`MOCK`] `mock_client = _mock_httpx_response(json_content)`
- L96 [`MOCK`] `return_value=mock_client,`

### `tests/test_washer_utils.py`
- L6 [`MOCK`] `key = "a" * 44  # Mock key`

### `tests/unit/converters/test_singbox_converters.py`
- L22 [`MOCK`] `# Mocking logger is tricky in unit test without fixtures, but we can check return None`

### `tests/unit/coverage_boost/test_adaptive_workers_coverage.py`
- L3 [`MOCK`] `from unittest.mock import patch, MagicMock`
- L12 [`MOCK`] `# Mock psutil not present (fallback to CPU logic)`
- L15 [`MOCK`] `# Mock CI detection to False for deterministic test`
- L35 [`MOCK`] `mock_psutil = MagicMock()`
- L36 [`MOCK`] `mock_mem = MagicMock()`
- L38 [`MOCK`] `mock_mem.available = 1024 * 1024 * 1024`
- L39 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem`
- L41 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):`
- L51 [`MOCK`] `mock_psutil = MagicMock()`
- L52 [`MOCK`] `mock_mem = MagicMock()`
- L53 [`MOCK`] `mock_mem.available = 64 * 1024 * 1024 * 1024  # Huge RAM`
- L54 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem`
- L56 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):`

### `tests/unit/coverage_boost/test_blocklist_coverage.py`
- L5 [`MOCK`] `from unittest.mock import patch`
- L27 [`MOCK`] `# Mock cache file`

### `tests/unit/coverage_boost/test_cli_coverage.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L14 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:`
- L17 [`MOCK`] `args, kwargs = mock_basic_config.call_args`
- L22 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:`
- L25 [`MOCK`] `args, kwargs = mock_basic_config.call_args`
- L43 [`MOCK`] `def test_cli_merge_command(mock_pipeline, runner):`
- L44 [`MOCK`] `# Mock stats object`
- L45 [`MOCK`] `stats_mock = MagicMock()`
- L46 [`MOCK`] `# Configure attributes so getattr(stats, key) returns float/int, not MagicMock`
- L47 [`MOCK`] `stats_mock.duration = 1.5`
- L48 [`MOCK`] `stats_mock.fetched_lines = 100`
- L49 [`MOCK`] `stats_mock.tested = 50`
- L50 [`MOCK`] `stats_mock.working = 40`
- L51 [`MOCK`] `stats_mock.geo_resolved = 30`
- L52 [`MOCK`] `stats_mock.to_dict.return_value = {`
- L60 [`MOCK`] `# Mock pipeline result`
- L61 [`MOCK`] `result_mock = MagicMock()`
- L62 [`MOCK`] `result_mock.success = True`
- L63 [`MOCK`] `result_mock.stats = stats_mock`
- L64 [`MOCK`] `result_mock.error = None`
- L66 [`MOCK`] `mock_pipeline.return_value = result_mock`
- L67 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)`
- L85 [`MOCK`] `def test_cli_merge_command_fail(mock_pipeline, runner):`
- L86 [`MOCK`] `result_mock = MagicMock()`
- L87 [`MOCK`] `result_mock.success = False`
- L88 [`MOCK`] `result_mock.error = "Simulated Failure"`
- L90 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)`

### `tests/unit/coverage_boost/test_server_coverage.py`
- L37 [`MOCK`] `# Mock output directory for static files`

### `tests/unit/coverage_boost/test_washer_coverage.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L9 [`MOCK`] `def mock_warp_keys():`
- L21 [`MOCK`] `def washer(mock_warp_keys):`
- L22 [`MOCK`] `return ProxyWasher(mock_warp_keys)`
- L106 [`MOCK`] `# Fill cache up to limit (mock small limit via private usage if possible, or just check type)`
- L112 [`MOCK`] `# We can mock seen_chains`
- L113 [`MOCK`] `washer.seen_chains = MagicMock()`

### `tests/unit/fetcher/test_fetcher_core.py`
- L7 [`MOCK`] `from unittest.mock import patch`
- L46 [`MOCK`] `# Exception case mocking`

### `tests/unit/generators/test_singbox_comprehensive.py`
- L3 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/geoip/test_geoip_resolver.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock`
- L11 [`MOCK`] `# Mock readers to ensure we don't hit FS`
- L12 [`MOCK`] `resolver.reader_city = MagicMock()`
- L13 [`MOCK`] `resolver.reader_asn = MagicMock()`
- L21 [`MOCK`] `async def test_geoip_lookup_valid_mock():`
- L22 [`MOCK`] `"""Test lookup logic with mocked DB response"""`
- L25 [`MOCK`] `mock_city = MagicMock()`
- L26 [`MOCK`] `mock_city.country.iso_code = "US"`
- L27 [`MOCK`] `mock_city.country.name = "United States"`
- L28 [`MOCK`] `mock_city.city.name = "New York"`
- L29 [`MOCK`] `resolver.reader_city = MagicMock()`
- L30 [`MOCK`] `resolver.reader_city.city.return_value = mock_city`
- L32 [`MOCK`] `mock_asn = MagicMock()`
- L33 [`MOCK`] `mock_asn.autonomous_system_number = 12345`
- L34 [`MOCK`] `mock_asn.autonomous_system_organization = "Test Org"`
- L35 [`MOCK`] `resolver.reader_asn = MagicMock()`
- L36 [`MOCK`] `resolver.reader_asn.asn.return_value = mock_asn`

### `tests/unit/history/test_history_components.py`
- L6 [`MOCK`] `from unittest.mock import patch`
- L36 [`MOCK`] `with patch.object(Path, "stat") as mock_stat:`
- L37 [`MOCK`] `mock_stat.return_value.st_size = 101 * 1024 * 1024  # 101MB`
- L152 [`MOCK`] `with patch("configstream.history.export.datetime") as mock_dt:`
- L153 [`MOCK`] `mock_dt.now.return_value.replace.return_value = mock_dt.now.return_value`
- L156 [`MOCK`] `mock_dt.now.return_value = fixed_now`
- L157 [`MOCK`] `mock_dt.fromisoformat.side_effect = datetime.fromisoformat`
- L158 [`MOCK`] `mock_dt.min = datetime.min`

### `tests/unit/intelligence/test_chaining_extended.py`
- L2 [`MOCK`] `from unittest.mock import patch`
- L75 [`MOCK`] `# Mock converters`

### `tests/unit/intelligence/test_vectors.py`
- L5 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/quality/test_quality_components.py`
- L4 [`MOCK`] `from unittest.mock import patch`
- L156 [`MOCK`] `# Easier to mock`

### `tests/unit/security/test_censorship.py`
- L2 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch`
- L19 [`MOCK`] `mock_response = MagicMock()`
- L20 [`MOCK`] `mock_response.status_code = 200`
- L23 [`MOCK`] `"httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response`
- L36 [`MOCK`] `new_callable=AsyncMock,`

### `tests/unit/security/test_rules.py`
- L11 [`MOCK`] `from unittest.mock import patch`
- L36 [`MOCK`] `# Mock SUSPICIOUS_DOMAINS to test that logic specifically`
- L56 [`MOCK`] `# Mock AppSettings to ensure ALLOW_PRIVATE_IPS is False`
- L57 [`MOCK`] `# Also mock SUSPICIOUS_DOMAINS to be empty so we fall through to private IP check`
- L59 [`MOCK`] `patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings,`
- L62 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = False`
- L81 [`MOCK`] `with patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings:`
- L82 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = True`

### `tests/unit/security/test_utls_wrapper.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L17 [`MOCK`] `new_callable=AsyncMock,`
- L40 [`MOCK`] `new_callable=AsyncMock,`
- L47 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,`
- L50 [`MOCK`] `mock_proc = MagicMock()`
- L51 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))`
- L52 [`MOCK`] `mock_proc.returncode = 0`
- L53 [`MOCK`] `mock_exec.return_value = mock_proc`
- L64 [`MOCK`] `new_callable=AsyncMock,`
- L71 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,`
- L74 [`MOCK`] `mock_proc = MagicMock()`
- L75 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))`
- L76 [`MOCK`] `mock_proc.returncode = 1`
- L77 [`MOCK`] `mock_exec.return_value = mock_proc`

### `tests/unit/security/test_virus_total_comprehensive.py`
- L5 [`MOCK`] `from unittest.mock import patch, MagicMock`
- L18 [`MOCK`] `class MockResponse:`
- L19 [`MOCK`] `"""Mock aiohttp response."""`
- L49 [`MOCK`] `mock_response = MockResponse(200, "not a dict")`
- L53 [`MOCK`] `) as mock_session_cls:`
- L54 [`MOCK`] `mock_session = MagicMock()`
- L55 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L56 [`MOCK`] `mock_session.get.return_value = mock_response`
- L66 [`MOCK`] `mock_response = MockResponse(200, {"data": {}})`
- L70 [`MOCK`] `) as mock_session_cls:`
- L71 [`MOCK`] `mock_session = MagicMock()`
- L72 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L73 [`MOCK`] `mock_session.get.return_value = mock_response`
- L85 [`MOCK`] `) as mock_session_cls:`
- L86 [`MOCK`] `mock_session = MagicMock()`
- L87 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L88 [`MOCK`] `mock_session.get.side_effect = Exception("Network error")`
- L98 [`MOCK`] `mock_response = MockResponse(`
- L104 [`MOCK`] `) as mock_session_cls:`
- L105 [`MOCK`] `mock_session = MagicMock()`
- L106 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L107 [`MOCK`] `mock_session.get.return_value = mock_response`
- L113 [`MOCK`] `call_args = mock_session.get.call_args`
- L135 [`MOCK`] `mock_response = MockResponse(`
- L151 [`MOCK`] `) as mock_session_cls:`
- L152 [`MOCK`] `mock_session = MagicMock()`
- L153 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L154 [`MOCK`] `mock_session.get.return_value = mock_response`
- L164 [`MOCK`] `mock_response = MockResponse(`
- L179 [`MOCK`] `) as mock_session_cls:`
- L180 [`MOCK`] `mock_session = MagicMock()`
- L181 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L182 [`MOCK`] `mock_session.get.return_value = mock_response`
- L200 [`MOCK`] `) as mock_session_cls:`
- L205 [`MOCK`] `mock_session_cls.assert_not_called()`
- L215 [`MOCK`] `mock_response = MockResponse(`
- L230 [`MOCK`] `) as mock_session_cls:`
- L231 [`MOCK`] `mock_session = MagicMock()`
- L232 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L233 [`MOCK`] `mock_session.get.return_value = mock_response`
- L240 [`MOCK`] `mock_session.get.assert_called_once()`
- L258 [`MOCK`] `mock_response = MockResponse(`
- L273 [`MOCK`] `) as mock_session_cls:`
- L274 [`MOCK`] `mock_session = MagicMock()`
- L275 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L276 [`MOCK`] `mock_session.get.return_value = mock_response`
- L289 [`MOCK`] `mock_response = MockResponse(200, ["not", "a", "dict"])`
- L293 [`MOCK`] `) as mock_session_cls:`
- L294 [`MOCK`] `mock_session = MagicMock()`
- L295 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L296 [`MOCK`] `mock_session.get.return_value = mock_response`
- L306 [`MOCK`] `mock_response = MockResponse(429, {})  # Rate limit error`
- L310 [`MOCK`] `) as mock_session_cls:`
- L311 [`MOCK`] `mock_session = MagicMock()`
- L312 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L313 [`MOCK`] `mock_session.get.return_value = mock_response`
- L325 [`MOCK`] `) as mock_session_cls:`
- L326 [`MOCK`] `mock_session = MagicMock()`
- L327 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L328 [`MOCK`] `mock_session.get.side_effect = Exception("Network timeout")`
- L340 [`MOCK`] `mock_response = MockResponse(`
- L355 [`MOCK`] `) as mock_session_cls:`
- L356 [`MOCK`] `mock_session = MagicMock()`
- L357 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L358 [`MOCK`] `mock_session.get.return_value = mock_response`
- L372 [`MOCK`] `mock_response = MockResponse(200, {"data": {"attributes": {}}})`
- L376 [`MOCK`] `) as mock_session_cls:`
- L377 [`MOCK`] `mock_session = MagicMock()`
- L378 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L379 [`MOCK`] `mock_session.get.return_value = mock_response`
- L403 [`MOCK`] `mock_response = MockResponse(`
- L421 [`MOCK`] `) as mock_session_cls:`
- L422 [`MOCK`] `mock_session = MagicMock()`
- L423 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session`
- L424 [`MOCK`] `mock_session.get.return_value = mock_response`

### `tests/unit/test_adapters_comprehensive.py`
- L9 [`MOCK`] `from unittest.mock import Mock, MagicMock, patch`
- L179 [`MOCK`] `) as mock_format:`
- L180 [`MOCK`] `mock_format.return_value = "WireGuard chain config"`
- L189 [`MOCK`] `proxy = Mock(spec=Proxy)`
- L194 [`MOCK`] `# Use MagicMock for details to allow mocking get method`
- L195 [`MOCK`] `proxy.details = MagicMock()`

### `tests/unit/test_adaptive_timeout_extra.py`
- L6 [`MOCK`] `from unittest.mock import patch`
- L91 [`MOCK`] `# We mock write_text`
- L109 [`MOCK`] `with patch("configstream.adaptive_timeout.logger") as mock_logger:`
- L111 [`MOCK`] `assert mock_logger.debug.called`

### `tests/unit/test_adaptive_workers.py`
- L3 [`MOCK`] `from unittest.mock import patch`
- L9 [`MOCK`] `with patch("psutil.virtual_memory") as mock_mem:`
- L10 [`MOCK`] `mock_mem.return_value.available = 2 * 1024 * 1024 * 1024  # 2GB`

### `tests/unit/test_analytics_output.py`
- L12 [`MOCK`] `# Create mock proxies with various latencies`
- L17 [`MOCK`] `config="vmess://mock1",`
- L29 [`MOCK`] `config="ss://mock2", protocol="ss", address="2.2.2.2", port=443, is_working=True`
- L37 [`MOCK`] `config="trojan://mock3",`
- L49 [`MOCK`] `config="vless://mock4",`
- L61 [`MOCK`] `config="vmess://mock5",`
- L71 [`MOCK`] `# Mock pipeline stats object`

### `tests/unit/test_anomaly_extended.py`
- L4 [`MOCK`] `from unittest.mock import patch`
- L129 [`MOCK`] `with patch("time.time") as mock_time:`
- L131 [`MOCK`] `mock_time.return_value = 1000 + i`
- L147 [`MOCK`] `from unittest.mock import MagicMock`
- L150 [`MOCK`] `mock_conn = MagicMock()`
- L151 [`MOCK`] `# Mock specific sqlite3.Error which is caught by the logic`
- L152 [`MOCK`] `mock_conn.execute.side_effect = sqlite3.OperationalError("DB Execution Error")`
- L154 [`MOCK`] `detector._conn = mock_conn`
- L156 [`MOCK`] `# Also mock reconnection attempt failing`

### `tests/unit/test_backup.py`
- L26 [`MOCK`] `# We can't easily mock file stats without patching os.stat`

### `tests/unit/test_backup_extended.py`
- L7 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L153 [`MOCK`] `# but we can mock glob or check logic.`
- L155 [`MOCK`] `# If we had a file named "../traversal.db" returned by glob (unlikely normally but possible via mocks)`
- L157 [`MOCK`] `with patch.object(Path, "glob") as mock_glob:`
- L158 [`MOCK`] `bad_path = MagicMock(spec=Path)`
- L163 [`MOCK`] `mock_glob.return_value = [bad_path]`
- L180 [`MOCK`] `with patch("sqlite3.connect") as mock_connect:`
- L181 [`MOCK`] `mock_connect.side_effect = Exception("Connect Fail")`

### `tests/unit/test_bot_cli.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L8 [`MOCK`] `# Mock register_warp_account globally for this module if possible,`
- L13 [`MOCK`] `# we need to patch 'configstream.tools.warp.register_warp_account' and ensure it's mocked`
- L18 [`MOCK`] `# We should mock `configstream.tools.warp.register_warp_account`.`
- L23 [`MOCK`] `update = MagicMock(spec=Update)`
- L24 [`MOCK`] `update.effective_chat = MagicMock()`
- L26 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)`
- L27 [`MOCK`] `context.bot.send_message = AsyncMock()`
- L36 [`MOCK`] `update = MagicMock(spec=Update)`
- L37 [`MOCK`] `update.effective_chat = MagicMock()`
- L39 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)`
- L40 [`MOCK`] `context.bot.send_message = AsyncMock()`
- L42 [`MOCK`] `# We need to mock the module where it is defined, so the local import picks up the mock`
- L44 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock`
- L45 [`MOCK`] `) as mock_reg:`
- L46 [`MOCK`] `mock_reg.return_value = {`
- L66 [`MOCK`] `update = MagicMock(spec=Update)`
- L67 [`MOCK`] `update.effective_chat = MagicMock()`
- L69 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)`
- L70 [`MOCK`] `context.bot.send_message = AsyncMock()`
- L73 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock`
- L74 [`MOCK`] `) as mock_reg:`
- L75 [`MOCK`] `mock_reg.side_effect = Exception("Fail")`
- L85 [`MOCK`] `update = MagicMock(spec=Update)`
- L86 [`MOCK`] `update.effective_chat = MagicMock()`
- L88 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)`
- L89 [`MOCK`] `context.bot.send_message = AsyncMock()`
- L96 [`MOCK`] `# Mock AppSettings to return None for TELEGRAM_BOT_TOKEN`
- L103 [`MOCK`] `with patch("configstream.config.AppSettings") as mock_settings:`
- L104 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = None`
- L105 [`MOCK`] `with patch("configstream.bot_cli.logger") as mock_logger:`
- L107 [`MOCK`] `mock_logger.error.assert_called_with("TELEGRAM_BOT_TOKEN not set")`
- L112 [`MOCK`] `patch("configstream.config.AppSettings") as mock_settings,`
- L113 [`MOCK`] `patch("configstream.bot_cli.ApplicationBuilder") as mock_builder,`
- L115 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = "fake_token"`
- L117 [`MOCK`] `mock_app = MagicMock()`
- L118 [`MOCK`] `mock_builder.return_value.token.return_value.build.return_value = mock_app`
- L121 [`MOCK`] `mock_app.run_polling.assert_called_once()`

### `tests/unit/test_cache_warming.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock`
- L9 [`MOCK`] `def mock_cache():`
- L10 [`MOCK`] `cache = MagicMock()`
- L11 [`MOCK`] `# Mock get method to return True for some proxies, False for others`
- L12 [`MOCK`] `cache.get = MagicMock()`
- L13 [`MOCK`] `cache.get_health_score = MagicMock()`
- L18 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L19 [`ASSUMING`] `p.id = id  # Assuming models.Proxy has id or is hashable`
- L24 [`MOCK`] `def test_warm_cache(mock_cache):`
- L33 [`MOCK`] `mock_cache.get.side_effect = lambda p: p.id in ["p1", "p3", "p4"]`
- L45 [`MOCK`] `mock_cache.get_health_score.side_effect = health_score`
- L47 [`MOCK`] `result = warm_cache(mock_cache, proxies)`
- L60 [`MOCK`] `def test_warm_cache_all_uncached(mock_cache):`
- L64 [`MOCK`] `mock_cache.get.return_value = False`
- L66 [`MOCK`] `result = warm_cache(mock_cache, proxies)`

### `tests/unit/test_cli_extended.py`
- L5 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch`
- L42 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock`
- L43 [`MOCK`] `) as mock_pipeline,`
- L46 [`MOCK`] `mock_result = MagicMock()`
- L47 [`MOCK`] `mock_result.success = True`
- L48 [`MOCK`] `mock_result.stats = {`
- L55 [`MOCK`] `mock_pipeline.return_value = mock_result`
- L61 [`MOCK`] `mock_pipeline.assert_called_once()`
- L69 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock`
- L70 [`MOCK`] `) as mock_pipeline,`
- L73 [`MOCK`] `mock_result = MagicMock()`
- L74 [`MOCK`] `mock_result.success = False`
- L75 [`MOCK`] `mock_result.error = "Test Failure"`
- L76 [`MOCK`] `mock_pipeline.return_value = mock_result`
- L163 [`MOCK`] `"configstream.cli.generate_warp_proxy", new_callable=AsyncMock`
- L164 [`MOCK`] `) as mock_gen:`
- L165 [`MOCK`] `mock_p = MagicMock()`
- L166 [`MOCK`] `mock_p.protocol = "wireguard"`
- L167 [`MOCK`] `mock_p.details = {}`
- L168 [`MOCK`] `mock_p.config = "conf"`
- L169 [`MOCK`] `mock_gen.return_value = mock_p`
- L178 [`MOCK`] `with patch("configstream.bot_cli.run_bot") as mock_run:`
- L181 [`MOCK`] `mock_run.assert_called_with("FAKE")`

### `tests/unit/test_cli_full.py`
- L4 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/test_concurrency_extended.py`
- L4 [`MOCK`] `from unittest.mock import AsyncMock`
- L60 [`MOCK`] `# Mock semaphore set_limit`
- L61 [`MOCK`] `cm.semaphore.set_limit = AsyncMock()`

### `tests/unit/test_consumer.py`
- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L11 [`MOCK`] `def mock_dependencies_fix():`
- L14 [`MOCK`] `# Mocks`
- L15 [`MOCK`] `tester = MagicMock()`
- L17 [`MOCK`] `tester.test = AsyncMock()`
- L18 [`MOCK`] `tester.test_batch = AsyncMock()`
- L20 [`MOCK`] `washer = MagicMock()`
- L22 [`MOCK`] `scheduler = MagicMock()`
- L25 [`MOCK`] `test_cache = MagicMock()`
- L28 [`MOCK`] `concurrency = MagicMock()`
- L29 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()`
- L32 [`MOCK`] `concurrency.record = AsyncMock()`
- L34 [`MOCK`] `geoip = MagicMock()`
- L35 [`MOCK`] `geoip.lookup = AsyncMock(return_value=None)`
- L37 [`MOCK`] `tracker = MagicMock()`
- L38 [`MOCK`] `tracker.phase.return_value = MagicMock()`
- L42 [`MOCK`] `history = MagicMock()`
- L43 [`MOCK`] `history.update_history = MagicMock()`
- L45 [`MOCK`] `quality = MagicMock()`
- L62 [`MOCK`] `async def test_processing_consumer_revival_crash(mock_dependencies_fix):`
- L63 [`MOCK`] `deps = mock_dependencies_fix`
- L81 [`MOCK`] `# Mock parse_config`
- L83 [`MOCK`] `# Mock validate_batch_configs`

### `tests/unit/test_dns_batch_resolver.py`
- L4 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L19 [`MOCK`] `# Mock aiodns.DNSResolver`
- L20 [`MOCK`] `mock_dns = MagicMock()`
- L21 [`MOCK`] `# Mock query response`
- L23 [`MOCK`] `res_example = MagicMock()`
- L26 [`MOCK`] `res_google = MagicMock()`
- L36 [`MOCK`] `mock_dns.query.side_effect = [future_example, future_google]`
- L38 [`MOCK`] `resolver.resolver = mock_dns  # Set the instance attribute directly`
- L48 [`MOCK`] `resolver.resolver = MagicMock()`
- L57 [`MOCK`] `mock_dns = MagicMock()`
- L60 [`MOCK`] `mock_dns.query.return_value = future_fail`
- L62 [`MOCK`] `resolver.resolver = mock_dns`

### `tests/unit/test_event_stream.py`
- L7 [`MOCK`] `from unittest.mock import patch`
- L36 [`MOCK`] `def test_emit_error_event(self, mock_logger, tmp_path):`
- L41 [`MOCK`] `mock_logger.error.assert_called_once_with("[error] An error occurred")`
- L42 [`MOCK`] `mock_logger.warning.assert_not_called()`
- L43 [`MOCK`] `mock_logger.info.assert_not_called()`
- L46 [`MOCK`] `def test_emit_critical_event(self, mock_logger, tmp_path):`
- L51 [`MOCK`] `mock_logger.error.assert_called_once_with("[critical] Critical failure")`
- L52 [`MOCK`] `mock_logger.warning.assert_not_called()`
- L53 [`MOCK`] `mock_logger.info.assert_not_called()`
- L56 [`MOCK`] `def test_emit_warning_event(self, mock_logger, tmp_path):`
- L61 [`MOCK`] `mock_logger.warning.assert_called_once_with("[warning] Warning message")`
- L62 [`MOCK`] `mock_logger.error.assert_not_called()`
- L63 [`MOCK`] `mock_logger.info.assert_not_called()`
- L66 [`MOCK`] `def test_emit_info_event(self, mock_logger, tmp_path):`
- L71 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] Information message")`
- L72 [`MOCK`] `mock_logger.error.assert_not_called()`
- L73 [`MOCK`] `mock_logger.warning.assert_not_called()`
- L76 [`MOCK`] `def test_emit_default_event_type(self, mock_logger, tmp_path):`
- L81 [`MOCK`] `mock_logger.info.assert_called_once_with("[custom] Custom event")`
- L82 [`MOCK`] `mock_logger.error.assert_not_called()`
- L83 [`MOCK`] `mock_logger.warning.assert_not_called()`
- L86 [`MOCK`] `def test_emit_success_event(self, mock_logger, tmp_path):`
- L91 [`MOCK`] `mock_logger.info.assert_called_once_with("[success] Operation succeeded")`
- L94 [`MOCK`] `def test_emit_empty_message(self, mock_logger, tmp_path):`
- L99 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] ")`
- L102 [`MOCK`] `def test_emit_multiline_message(self, mock_logger, tmp_path):`
- L108 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")`
- L111 [`MOCK`] `def test_emit_message_with_special_characters(self, mock_logger, tmp_path):`
- L119 [`MOCK`] `mock_logger.error.assert_called_once_with(f"[error] {special_message}")`
- L122 [`MOCK`] `def test_emit_message_with_unicode(self, mock_logger, tmp_path):`
- L128 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {unicode_message}")`
- L131 [`MOCK`] `def test_multiple_emit_calls(self, mock_logger, tmp_path):`
- L139 [`MOCK`] `assert mock_logger.info.call_count == 1`
- L140 [`MOCK`] `assert mock_logger.warning.call_count == 1`
- L141 [`MOCK`] `assert mock_logger.error.call_count == 1`
- L144 [`MOCK`] `def test_emit_very_long_message(self, mock_logger, tmp_path):`
- L150 [`MOCK`] `mock_logger.info.assert_called_once()`
- L151 [`MOCK`] `call_args = mock_logger.info.call_args[0][0]`
- L155 [`MOCK`] `def test_emit_with_format_strings(self, mock_logger, tmp_path):`
- L161 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")`
- L164 [`MOCK`] `def test_case_sensitive_event_types(self, mock_logger, tmp_path):`
- L170 [`MOCK`] `mock_logger.error.assert_called_once()`
- L172 [`MOCK`] `mock_logger.reset_mock()`
- L176 [`MOCK`] `mock_logger.info.assert_called_once()`
- L177 [`MOCK`] `mock_logger.error.assert_not_called()`
- L180 [`MOCK`] `def test_emit_with_numeric_message(self, mock_logger, tmp_path):`
- L185 [`MOCK`] `mock_logger.info.assert_called_once()`
- L188 [`MOCK`] `def test_emit_rapid_fire(self, mock_logger, tmp_path):`
- L195 [`MOCK`] `assert mock_logger.info.call_count == 100`
- L198 [`MOCK`] `def test_emit_different_event_types_mixed(self, mock_logger, tmp_path):`
- L209 [`MOCK`] `assert mock_logger.info.call_count == 3  # info, info, custom`
- L210 [`MOCK`] `assert mock_logger.error.call_count == 2  # error, critical`
- L211 [`MOCK`] `assert mock_logger.warning.call_count == 1`
- L222 [`MOCK`] `def test_emit_with_none_message_converted_to_string(self, mock_logger, tmp_path):`
- L228 [`MOCK`] `mock_logger.info.assert_called_once()`
- L231 [`MOCK`] `def test_emit_preserves_message_exactly(self, mock_logger, tmp_path):`
- L238 [`MOCK`] `mock_logger.info.assert_called_once_with(expected_call)`
- L241 [`MOCK`] `def test_emit_with_json_like_message(self, mock_logger, tmp_path):`
- L247 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {json_message}")`
- L250 [`MOCK`] `def test_emit_with_sql_like_message(self, mock_logger, tmp_path):`
- L256 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {sql_message}")`
- L271 [`MOCK`] `def test_emit_with_path_in_message(self, mock_logger, tmp_path):`
- L277 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {path_message}")`
- L280 [`MOCK`] `def test_emit_with_url_in_message(self, mock_logger, tmp_path):`
- L286 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {url_message}")`

### `tests/unit/test_fetcher.py`
- L5 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock`
- L32 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L40 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L50 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L51 [`MOCK`] `mock_response = AsyncMock()`
- L52 [`MOCK`] `mock_response.status_code = 200`
- L53 [`MOCK`] `mock_response.headers = {}`
- L59 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L62 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L63 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L64 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L75 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L76 [`MOCK`] `mock_response = AsyncMock()`
- L77 [`MOCK`] `mock_response.status_code = 429`
- L78 [`MOCK`] `mock_response.headers = {"Retry-After": "0.1"}`
- L80 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L81 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L82 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L84 [`MOCK`] `# Should retry. We mock sleep to be fast.`
- L85 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L91 [`MOCK`] `assert mock_sleep.call_count > 0`
- L95 [`MOCK`] `async def test_fetch_from_source_follows_safe_redirect(respx_mock):`
- L98 [`MOCK`] `respx_mock.get(source).mock(`
- L101 [`MOCK`] `respx_mock.get(target).mock(return_value=httpx.Response(200, text="redirected"))`
- L111 [`MOCK`] `async def test_fetch_from_source_rejects_private_redirect(respx_mock):`
- L113 [`MOCK`] `respx_mock.get(source).mock(`
- L128 [`MOCK`] `async def test_fetch_from_source_limits_redirect_depth(respx_mock):`
- L132 [`MOCK`] `respx_mock.get(source).mock(`
- L150 [`MOCK`] `# If RateLimiter class is gone, we can mock a generic object with the same interface.`
- L151 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L152 [`MOCK`] `rate_limiter = MagicMock()`
- L154 [`MOCK`] `rate_limiter.is_allowed = AsyncMock(side_effect=[False, True])`
- L155 [`MOCK`] `rate_limiter.get_wait_time = AsyncMock(return_value=0.01)`
- L157 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L159 [`MOCK`] `mock_response = AsyncMock()`
- L160 [`MOCK`] `mock_response.status_code = 200`
- L161 [`MOCK`] `mock_response.headers = {}`
- L166 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L167 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L168 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L169 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L176 [`MOCK`] `assert mock_sleep.called`
- L181 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L182 [`MOCK`] `breaker_manager = MagicMock()`
- L183 [`MOCK`] `breaker = MagicMock()`
- L184 [`MOCK`] `breaker.is_open = AsyncMock(return_value=True)`
- L185 [`MOCK`] `breaker_manager.get_breaker = AsyncMock(return_value=breaker)`
- L203 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L204 [`MOCK`] `mock_response = AsyncMock()`
- L205 [`MOCK`] `mock_response.status_code = 200`
- L208 [`MOCK`] `mock_response.headers = {`
- L212 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L213 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L214 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L226 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L227 [`MOCK`] `mock_response = AsyncMock()`
- L228 [`MOCK`] `mock_response.status_code = 200`
- L229 [`MOCK`] `mock_response.headers = {}`
- L237 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L239 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L240 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L241 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L253 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L254 [`MOCK`] `mock_response = AsyncMock()`
- L255 [`MOCK`] `mock_response.status_code = 200`
- L256 [`MOCK`] `mock_response.headers = {}`
- L261 [`MOCK`] `mock_response.aiter_bytes = lambda: async_gen()`
- L263 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L264 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L265 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L267 [`MOCK`] `tracker = MagicMock()`
- L268 [`MOCK`] `tracker.get_timeout = MagicMock(return_value=10.0)`
- L269 [`MOCK`] `tracker.record = AsyncMock()`
- L270 [`MOCK`] `tracker.get_jitter = AsyncMock(return_value=3.0)  # High jitter`
- L273 [`MOCK`] `with patch("configstream.fetcher.logger") as mock_logger:`
- L276 [`MOCK`] `assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)`
- L281 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L285 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L291 [`MOCK`] `assert mock_sleep.call_count > 0`
- L296 [`MOCK`] `# Integration test mocking minimal internals`
- L298 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:`
- L299 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")`
- L310 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L312 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:`
- L313 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")`

### `tests/unit/test_fetcher_advanced.py`
- L3 [`MOCK`] `from unittest.mock import patch, MagicMock`
- L10 [`MOCK`] `# Helper to mock the stream context manager`
- L11 [`MOCK`] `class MockStreamResponse:`
- L39 [`MOCK`] `# Mock stream instead of get`
- L40 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L41 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "ok")`
- L52 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L53 [`MOCK`] `resp1 = MockStreamResponse(429, "", headers={"Retry-After": "0.1"})`
- L54 [`MOCK`] `resp2 = MockStreamResponse(200, "ok")`
- L56 [`MOCK`] `mock_stream.side_effect = [resp1, resp2]`
- L63 [`MOCK`] `assert mock_stream.call_count == 2`
- L94 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L95 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "streamed_content")`
- L104 [`MOCK`] `# We assert mock_stream was called, implying we used the safer path`
- L105 [`MOCK`] `mock_stream.assert_called_once()`
- L122 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L123 [`MOCK`] `mock_stream.return_value = MockStreamResponse(404, "")`
- L151 [`MOCK`] `assert mock_stream.call_count == 2`

### `tests/unit/test_fetcher_config.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock`
- L15 [`MOCK`] `# by mocking the constant or by testing the behavior with a large response.`
- L25 [`MOCK`] `# Create a mock response with Content-Length > MAX_RESPONSE_SIZE`
- L26 [`MOCK`] `mock_client = MagicMock(spec=httpx.AsyncClient)`
- L27 [`MOCK`] `mock_response = MagicMock()`
- L28 [`MOCK`] `mock_response.status_code = 200`
- L29 [`MOCK`] `mock_response.headers = {`
- L33 [`MOCK`] `# Mock stream context manager`
- L34 [`MOCK`] `mock_stream = MagicMock()`
- L35 [`MOCK`] `mock_stream.__aenter__.return_value = mock_response`
- L36 [`MOCK`] `mock_stream.__aexit__.return_value = None`
- L37 [`MOCK`] `mock_client.stream.return_value = mock_stream`
- L41 [`MOCK`] `mock_client, "http://example.com", app_settings=app_settings`

### `tests/unit/test_fetcher_resilience.py`
- L8 [`MOCK`] `async def test_fetch_success(respx_mock):`
- L10 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(200, text="content"))`
- L20 [`MOCK`] `async def test_fetch_404(respx_mock):`
- L22 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(404))`
- L33 [`MOCK`] `async def test_fetch_retry_on_error(respx_mock):`
- L36 [`MOCK`] `route = respx_mock.get(url)`
- L52 [`MOCK`] `async def test_fetch_rate_limit(respx_mock):`
- L55 [`MOCK`] `route = respx_mock.get(url)`

### `tests/unit/test_fetcher_retries.py`
- L11 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:`
- L12 [`MOCK`] `# Mock 404 response`
- L13 [`MOCK`] `respx_mock.get("/missing").mock(return_value=httpx.Response(404))`
- L23 [`MOCK`] `assert respx_mock.calls.call_count == 1  # Should only call once`
- L29 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:`
- L30 [`MOCK`] `# Mock 410 response`
- L31 [`MOCK`] `respx_mock.get("/gone").mock(return_value=httpx.Response(410))`
- L40 [`MOCK`] `assert respx_mock.calls.call_count == 1`
- L46 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:`
- L47 [`MOCK`] `# Mock 500 response`
- L48 [`MOCK`] `respx_mock.get("/error").mock(return_value=httpx.Response(500))`
- L59 [`MOCK`] `assert respx_mock.calls.call_count == 2`

### `tests/unit/test_filtering_extended.py`
- L2 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L24 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L60 [`MOCK`] `# Since we used MagicMock, identity might be tricky if dedupe makes copies,`
- L142 [`MOCK`] `# Mock AppSettings to return seed`
- L144 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:`
- L145 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"`
- L148 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:`
- L149 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"`

### `tests/unit/test_geoip_extended.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L20 [`MOCK`] `resolver.reader_city = MagicMock()`
- L24 [`MOCK`] `resolver.reader_asn = MagicMock()`

### `tests/unit/test_go_tester_streaming.py`
- L5 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch`
- L12 [`MOCK`] `# Mock process`
- L13 [`MOCK`] `proc = MagicMock()`
- L15 [`MOCK`] `proc.stdin = MagicMock()`
- L16 [`MOCK`] `proc.stdin.write = MagicMock()`
- L17 [`MOCK`] `proc.stdin.drain = AsyncMock()`
- L18 [`MOCK`] `proc.stdin.close = MagicMock()`
- L19 [`MOCK`] `proc.wait = AsyncMock()`
- L20 [`MOCK`] `proc.terminate = MagicMock()`
- L21 [`MOCK`] `proc.kill = MagicMock()`
- L23 [`MOCK`] `# Mock stdout with an AsyncMock readline that returns lines then empty string`
- L24 [`MOCK`] `proc.stdout = MagicMock()`
- L30 [`MOCK`] `async def mock_readline():`
- L33 [`MOCK`] `proc.stdout.readline = mock_readline`
- L35 [`MOCK`] `proc.stderr = MagicMock()`
- L37 [`MOCK`] `proc.stderr.readline = AsyncMock(return_value=b"")  # No logs`
- L39 [`MOCK`] `with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):`
- L43 [`MOCK`] `# Mock self_test to succeed since we are mocking process anyway`
- L44 [`MOCK`] `with patch.object(GoBatchTester, "self_test", new=AsyncMock(return_value=True)):`
- L80 [`MOCK`] `print(f"Error in mock write: {e}")`

### `tests/unit/test_honeypot.py`
- L3 [`MOCK`] `from unittest.mock import patch, AsyncMock`
- L10 [`MOCK`] `# Mock VirusTotal to return safe`
- L12 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L13 [`MOCK`] `) as mock_vt:`
- L14 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L19 [`MOCK`] `mock_vt.assert_called_once_with("1.1.1.1")`
- L24 [`MOCK`] `"""Verify passive detection works via VirusTotal mock."""`
- L26 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L27 [`MOCK`] `) as mock_vt:`
- L28 [`MOCK`] `mock_vt.return_value = {"malicious": 5}`
- L38 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L39 [`MOCK`] `) as mock_vt:`
- L40 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L44 [`MOCK`] `mock_vt.assert_called_once_with("8.8.8.8")`
- L51 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L52 [`MOCK`] `) as mock_vt:`
- L53 [`MOCK`] `mock_vt.return_value = {"malicious": 100}`
- L63 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L64 [`MOCK`] `) as mock_vt:`
- L65 [`MOCK`] `mock_vt.return_value = {"malicious": 1}`
- L75 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L76 [`MOCK`] `) as mock_vt:`
- L77 [`MOCK`] `mock_vt.return_value = {}`
- L88 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L89 [`MOCK`] `) as mock_vt:`
- L90 [`MOCK`] `mock_vt.side_effect = Exception("API Error")`
- L101 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L102 [`MOCK`] `) as mock_vt:`
- L103 [`MOCK`] `mock_vt.side_effect = TimeoutError("Request timed out")`
- L113 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L114 [`MOCK`] `) as mock_vt:`
- L115 [`MOCK`] `mock_vt.side_effect = ConnectionError("Network unreachable")`
- L125 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L126 [`MOCK`] `) as mock_vt:`
- L127 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L131 [`MOCK`] `mock_vt.assert_called_once_with("2001:4860:4860::8888")`
- L138 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L139 [`MOCK`] `) as mock_vt:`
- L140 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L144 [`MOCK`] `mock_vt.assert_called_once_with("example.com")`
- L151 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L152 [`MOCK`] `) as mock_vt:`
- L153 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L163 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L164 [`MOCK`] `) as mock_vt:`
- L165 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L175 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L176 [`MOCK`] `) as mock_vt:`
- L177 [`MOCK`] `mock_vt.return_value = {"malicious": -1}`
- L188 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L189 [`MOCK`] `) as mock_vt:`
- L190 [`MOCK`] `mock_vt.return_value = None`
- L206 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L207 [`MOCK`] `) as mock_vt:`
- L208 [`MOCK`] `mock_vt.return_value = "error"`
- L219 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L220 [`MOCK`] `) as mock_vt:`
- L221 [`MOCK`] `mock_vt.return_value = {"malicious": 0}`
- L225 [`MOCK`] `mock_vt.assert_called_once_with("")`
- L232 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L233 [`MOCK`] `) as mock_vt:`
- L234 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:`
- L235 [`MOCK`] `mock_vt.return_value = {"malicious": 3}`
- L241 [`MOCK`] `mock_logger.warning.assert_called_once()`
- L242 [`MOCK`] `call_args = str(mock_logger.warning.call_args)`
- L250 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock`
- L251 [`MOCK`] `) as mock_vt:`
- L252 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:`
- L253 [`MOCK`] `mock_vt.side_effect = ValueError("Invalid IP")`
- L259 [`MOCK`] `mock_logger.error.assert_called_once()`
- L260 [`MOCK`] `call_args = str(mock_logger.error.call_args)`

### `tests/unit/test_init_module.py`
- L6 [`MOCK`] `from unittest.mock import patch`
- L154 [`MOCK`] `# Verify set_event_loop_policy was called (might have been called before mock)`

### `tests/unit/test_output.py`
- L4 [`MOCK`] `from unittest.mock import MagicMock`
- L43 [`MOCK`] `def mock_storage():`
- L44 [`MOCK`] `return MagicMock(spec=QualityStorage)`
- L58 [`MOCK`] `def test_metadata_generation(tmp_path, sample_proxies, mock_storage):`

### `tests/unit/test_output_advanced.py`
- L6 [`MOCK`] `from unittest.mock import MagicMock, patch`

### `tests/unit/test_output_full.py`
- L3 [`MOCK`] `from unittest.mock import patch`
- L48 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:`
- L49 [`MOCK`] `MockHistory.return_value.get_history.return_value = []`
- L62 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:`
- L63 [`MOCK`] `MockHistory.return_value.get_history.return_value = []`
- L105 [`MOCK`] `patch("configstream.generators.singbox.to_singbox_outbound") as mock_conv,`
- L109 [`MOCK`] `mock_conv.return_value = {"type": "vless", "tag": "vless-out"}`
- L131 [`MOCK`] `patch("configstream.output_logic.ProxyWasher") as MockWasher,`
- L140 [`MOCK`] `patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory,`
- L141 [`MOCK`] `):  # Mock history to return serializable data`
- L143 [`MOCK`] `# Configure mock history to return empty list (serializable)`
- L144 [`MOCK`] `history_instance = MockHistory.return_value`
- L147 [`MOCK`] `MockWasher.return_value.wash_batch.return_value = ([], set(), {})`

### `tests/unit/test_output_logic.py`
- L244 [`PLACEHOLDER`] `config="revived://placeholder",`

### `tests/unit/test_parsers_robustness.py`
- L246 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/test_pipeline_coverage.py`
- L3 [`MOCK`] `from unittest.mock import AsyncMock, patch, MagicMock`
- L12 [`MOCK`] `def mock_work_queue():`
- L18 [`MOCK`] `def mock_tester():`
- L19 [`MOCK`] `tester = MagicMock(spec=SingBoxTester)`
- L20 [`MOCK`] `tester.go_tester = MagicMock()`
- L22 [`MOCK`] `tester.test = AsyncMock(`
- L36 [`MOCK`] `def mock_quality_tracker():`
- L37 [`MOCK`] `tracker = MagicMock()`
- L38 [`MOCK`] `tracker.should_fetch = MagicMock(return_value=True)`
- L43 [`MOCK`] `def mock_concurrency():`
- L44 [`MOCK`] `cm = MagicMock()`
- L45 [`MOCK`] `cm.get_semaphore = MagicMock(return_value=AsyncMock())`
- L46 [`MOCK`] `cm.get_semaphore.return_value.__aenter__ = AsyncMock()`
- L47 [`MOCK`] `cm.get_semaphore.return_value.__aexit__ = AsyncMock()`
- L48 [`MOCK`] `cm.start_tuner = MagicMock()`
- L49 [`MOCK`] `cm.stop_tuner = AsyncMock()`
- L50 [`MOCK`] `cm.record = AsyncMock()`
- L56 [`MOCK`] `mock_work_queue, mock_tester, mock_quality_tracker, mock_concurrency`
- L62 [`MOCK`] `# Mock dependencies`
- L63 [`MOCK`] `scheduler = MagicMock()`
- L64 [`MOCK`] `scheduler.should_retest = MagicMock(return_value=True)`
- L66 [`MOCK`] `test_cache = MagicMock()`
- L67 [`MOCK`] `test_cache.get = MagicMock(return_value=None)`
- L69 [`MOCK`] `geoip = MagicMock()`
- L70 [`MOCK`] `geoip.lookup = AsyncMock(`
- L71 [`MOCK`] `return_value=MagicMock(`
- L76 [`MOCK`] `tracker = MagicMock()`
- L77 [`MOCK`] `tracker.phase = MagicMock(`
- L78 [`MOCK`] `return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())`
- L82 [`MOCK`] `raw_lines = ["vmess://eyJaddfqwefqwe..."]  # Mock line`
- L84 [`MOCK`] `await mock_work_queue.put((source, raw_lines))`
- L85 [`MOCK`] `await mock_work_queue.put(None)  # Signal end`
- L87 [`MOCK`] `# Mock parse_config to return a proxy`
- L111 [`MOCK`] `mock_work_queue,`
- L115 [`MOCK`] `mock_tester,`
- L118 [`MOCK`] `mock_concurrency,`
- L122 [`MOCK`] `mock_quality_tracker,`
- L123 [`MOCK`] `MagicMock(),  # history`

### `tests/unit/test_pipeline_deep.py`
- L4 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L26 [`MOCK`] `# Mocks`
- L27 [`MOCK`] `mock_tester = MagicMock()`
- L28 [`MOCK`] `mock_tester.go_tester.available = False  # Use Python path`
- L29 [`MOCK`] `mock_tester.test = MagicMock()`
- L31 [`MOCK`] `# Mock result for test() must be awaitable`
- L32 [`MOCK`] `async def mock_test_result(p):`
- L37 [`MOCK`] `mock_tester.test.side_effect = mock_test_result`
- L39 [`MOCK`] `mock_scheduler = MagicMock(spec=SmartRetestScheduler)`
- L40 [`MOCK`] `mock_scheduler.should_retest.return_value = True`
- L42 [`MOCK`] `mock_cache = MagicMock(spec=TestResultCache)`
- L43 [`MOCK`] `mock_cache.get.return_value = None`
- L45 [`MOCK`] `mock_concurrency = MagicMock(spec=ConcurrencyManager)`
- L46 [`MOCK`] `# mock get_semaphore must return an async context manager`
- L48 [`MOCK`] `mock_concurrency.get_semaphore.return_value = asyncio.Semaphore(10)`
- L49 [`MOCK`] `mock_concurrency.record = MagicMock()  # awaitable? record is async def`
- L51 [`MOCK`] `async def mock_record(*args):`
- L55 [`MOCK`] `mock_concurrency.start_tuner = MagicMock()`
- L59 [`MOCK`] `mock_concurrency.stop_tuner = MagicMock(return_value=f)`
- L61 [`MOCK`] `mock_concurrency.record.side_effect = mock_record`
- L63 [`MOCK`] `from unittest.mock import AsyncMock`
- L65 [`MOCK`] `mock_geoip = MagicMock()`
- L66 [`MOCK`] `mock_geoip.lookup = AsyncMock(`
- L67 [`MOCK`] `return_value=MagicMock(country_code="US", city="Test", asn="AS1", org="Org")`
- L71 [`MOCK`] `mock_quality = MagicMock(spec=SourceQualityTracker)`
- L73 [`MOCK`] `# Need to mock parse_config or ensure "vmess://test" parses`
- L74 [`MOCK`] `with patch("configstream.consumer.parse_config") as mock_parse:`
- L77 [`MOCK`] `mock_parse.return_value = p`
- L79 [`MOCK`] `# We also need to mock validate_batch_configs to just return the list`
- L80 [`MOCK`] `with patch("configstream.consumer.validate_batch_configs") as mock_validate:`
- L81 [`MOCK`] `mock_validate.side_effect = lambda batch, policy: batch`
- L88 [`MOCK`] `tester=mock_tester,`
- L89 [`MOCK`] `scheduler=mock_scheduler,`
- L90 [`MOCK`] `test_cache=mock_cache,`
- L91 [`MOCK`] `concurrency=mock_concurrency,`
- L92 [`MOCK`] `geoip=mock_geoip,`
- L95 [`MOCK`] `quality_tracker=mock_quality,`
- L96 [`MOCK`] `history=MagicMock(),`

### `tests/unit/test_pipeline_extended.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L10 [`MOCK`] `def mock_proxies():`
- L34 [`MOCK`] `async def test_pipeline_dry_run(tmp_path, mock_proxies):`
- L35 [`MOCK`] `# Create a callable that returns mock_proxies to avoid fixture timing issues`
- L36 [`MOCK`] `def filter_unique_mock(*args, **kwargs):`
- L37 [`MOCK`] `return list(mock_proxies)`
- L40 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,`
- L43 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,`
- L44 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),`
- L45 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,`
- L46 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,`
- L49 [`MOCK`] `side_effect=filter_unique_mock,`
- L56 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,`
- L59 [`MOCK`] `new=MagicMock(spec=ProxyWasher),`
- L60 [`MOCK`] `) as MockWasher,`
- L67 [`MOCK`] `# Configure mocked tester to be awaitable on close`
- L68 [`MOCK`] `MockTester.return_value.close = AsyncMock()`
- L69 [`MOCK`] `MockTester.return_value.go_tester.available = False`
- L71 [`MOCK`] `# Configure EventStream mock`
- L72 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()`
- L74 [`MOCK`] `history = MagicMock()`
- L78 [`MOCK`] `MockHistory.return_value = history`
- L80 [`MOCK`] `# Mocking washer methods correctly`
- L81 [`MOCK`] `washer_instance = MockWasher.return_value`
- L82 [`MOCK`] `washer_instance.fetch_clean_ips = AsyncMock()`
- L83 [`MOCK`] `washer_instance.wash_batch = MagicMock(return_value=([], set(), {}))`
- L99 [`MOCK`] `final_proxies.extend(mock_proxies)`
- L100 [`MOCK`] `stats.working = len(mock_proxies)`
- L110 [`MOCK`] `mock_producer.side_effect = fake_producer`
- L111 [`MOCK`] `mock_consumer.side_effect = fake_consumer`
- L117 [`MOCK`] `proxies=mock_proxies,`
- L128 [`MOCK`] `async def test_pipeline_pareto_sort(tmp_path, mock_proxies):`
- L131 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,`
- L134 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,`
- L135 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),`
- L136 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,`
- L137 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,`
- L140 [`MOCK`] `new=AsyncMock(return_value={}),`
- L142 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,`
- L144 [`MOCK`] `MockTester.return_value.close = AsyncMock()`
- L145 [`MOCK`] `MockTester.return_value.go_tester.available = False`
- L147 [`MOCK`] `# Configure EventStream mock`
- L148 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()`
- L150 [`MOCK`] `# Mock history to prefer the higher latency one (reliability > latency scenario)`
- L151 [`MOCK`] `history = MagicMock()`
- L152 [`MOCK`] `MockHistory.return_value = history`
- L164 [`MOCK`] `final_proxies.extend(mock_proxies)`
- L171 [`MOCK`] `mock_producer.side_effect = fake_producer`
- L172 [`MOCK`] `mock_consumer.side_effect = fake_consumer`
- L180 [`MOCK`] `# Since we mock consumer to just append proxies, they are unsorted initially.`
- L182 [`MOCK`] `# We can't easily assert sort order here without mocking the sort function or checking result side effects`
- L187 [`MOCK`] `async def test_pipeline_adapter_export_fail(tmp_path, mock_proxies):`
- L189 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,`
- L192 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,`
- L193 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),`
- L194 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,`
- L195 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,`
- L198 [`MOCK`] `new=AsyncMock(side_effect=Exception("Export Fail")),`
- L202 [`MOCK`] `MockTester.return_value.close = AsyncMock()`
- L203 [`MOCK`] `MockTester.return_value.go_tester.available = False`
- L205 [`MOCK`] `# Configure EventStream mock`
- L206 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()`
- L223 [`MOCK`] `mock_producer.side_effect = fake_producer`
- L224 [`MOCK`] `mock_consumer.side_effect = fake_consumer`

### `tests/unit/test_pipeline_orchestration.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch`
- L14 [`MOCK`] `"configstream.pipeline.source_producer", new_callable=AsyncMock`
- L15 [`MOCK`] `) as mock_prod,`
- L17 [`MOCK`] `"configstream.pipeline.processing_consumer", new_callable=AsyncMock`
- L18 [`MOCK`] `) as mock_cons,`
- L21 [`MOCK`] `new_callable=AsyncMock,`
- L22 [`MOCK`] `) as mock_gen,`
- L23 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),`
- L24 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,`
- L26 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,`
- L29 [`MOCK`] `mock_tester = mock_tester_cls.return_value`
- L30 [`MOCK`] `mock_tester.go_tester = MagicMock()`
- L31 [`MOCK`] `mock_tester.go_tester.available = False`
- L32 [`MOCK`] `mock_tester.close = AsyncMock()`
- L34 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()`
- L47 [`MOCK`] `assert mock_prod.called, "source_producer should have been called"`
- L48 [`MOCK`] `assert mock_cons.called, "processing_consumer should have been called"`
- L49 [`MOCK`] `assert mock_gen.called, "generate_pipeline_outputs should have been called"`
- L58 [`MOCK`] `patch("configstream.pipeline.source_producer", new_callable=AsyncMock),`
- L59 [`MOCK`] `patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),`
- L62 [`MOCK`] `new_callable=AsyncMock,`
- L64 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),`
- L65 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,`
- L68 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,`
- L71 [`MOCK`] `mock_tester = mock_tester_cls.return_value`
- L72 [`MOCK`] `mock_tester.go_tester = MagicMock()`
- L73 [`MOCK`] `mock_tester.go_tester.available = False`
- L74 [`MOCK`] `mock_tester.close = AsyncMock()`
- L75 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()`

### `tests/unit/test_pipeline_stages.py`
- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock`
- L13 [`MOCK`] `def mock_dependencies():`
- L15 [`MOCK`] `quality = MagicMock()`
- L17 [`MOCK`] `anomaly = MagicMock()`
- L20 [`MOCK`] `tester = MagicMock()`
- L22 [`MOCK`] `tester.test = AsyncMock()  # For python fallback`
- L23 [`MOCK`] `tester.test_batch = AsyncMock()  # For go tester`
- L25 [`MOCK`] `scheduler = MagicMock()`
- L28 [`MOCK`] `test_cache = MagicMock()`
- L31 [`MOCK`] `concurrency = MagicMock()`
- L32 [`MOCK`] `concurrency.start_tuner = MagicMock()`
- L33 [`MOCK`] `concurrency.stop_tuner = AsyncMock()`
- L34 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()`
- L35 [`MOCK`] `concurrency.record = AsyncMock()`
- L38 [`MOCK`] `sem = AsyncMock()`
- L43 [`MOCK`] `geoip = MagicMock()`
- L44 [`MOCK`] `geoip.lookup = AsyncMock(`
- L45 [`MOCK`] `return_value=MagicMock(`
- L50 [`MOCK`] `tracker = MagicMock()`
- L51 [`MOCK`] `tracker.phase.return_value = MagicMock()`
- L55 [`MOCK`] `history = MagicMock()`
- L56 [`MOCK`] `history.record_test_result = MagicMock()`
- L83 [`MOCK`] `async def test_source_producer_supplied_proxies(mock_dependencies):`
- L84 [`MOCK`] `queue = mock_dependencies["queue"]`
- L91 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L92 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],`
- L104 [`MOCK`] `async def test_source_producer_local_files(mock_dependencies):`
- L105 [`MOCK`] `queue = mock_dependencies["queue"]`
- L108 [`MOCK`] `with patch("configstream.producer.read_multiple_files_async") as mock_read:`
- L109 [`MOCK`] `mock_read.return_value = [("sources/batch_1.txt", "vmess://file")]`
- L115 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L116 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],`
- L128 [`MOCK`] `async def test_source_producer_remote_urls(mock_dependencies):`
- L129 [`MOCK`] `queue = mock_dependencies["queue"]`
- L137 [`MOCK`] `# Mock fetcher`
- L138 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:`
- L139 [`MOCK`] `mock_fetch.return_value = {`
- L144 [`MOCK`] `# Mock read_multiple_files_async to prevent it from trying to read ss:// as file and logging warnings`
- L153 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L154 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],`
- L181 [`MOCK`] `async def test_source_producer_anomaly_block(mock_dependencies):`
- L182 [`MOCK`] `queue = mock_dependencies["queue"]`
- L185 [`MOCK`] `mock_dependencies["anomaly"].is_safe.return_value = (False, "Malicious")`
- L187 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:`
- L188 [`MOCK`] `mock_fetch.return_value = {`
- L196 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L197 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],`
- L210 [`MOCK`] `async def test_processing_consumer_basic_flow(mock_dependencies):`
- L211 [`MOCK`] `queue = mock_dependencies["queue"]`
- L220 [`MOCK`] `# Mock parse_config to return a valid proxy`
- L223 [`MOCK`] `# Mock tester to succeed`
- L229 [`MOCK`] `mock_dependencies["tester"].test.return_value = res`
- L231 [`MOCK`] `# Mock validate_batch_configs`
- L241 [`MOCK`] `tester=mock_dependencies["tester"],`
- L242 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L243 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L244 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L245 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L246 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L248 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L249 [`MOCK`] `history=mock_dependencies["history"],`
- L259 [`MOCK`] `assert final_proxies[0].country_code == "US"  # From GeoIP mock`
- L263 [`MOCK`] `async def test_processing_consumer_cached_hit(mock_dependencies):`
- L264 [`MOCK`] `queue = mock_dependencies["queue"]`
- L278 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False`
- L279 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = cached_p`
- L291 [`MOCK`] `tester=mock_dependencies["tester"],`
- L292 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L293 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L294 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L295 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L296 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L298 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L299 [`MOCK`] `history=mock_dependencies["history"],`
- L313 [`MOCK`] `async def test_processing_consumer_cache_miss(mock_dependencies):`
- L314 [`MOCK`] `queue = mock_dependencies["queue"]`
- L325 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False`
- L326 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = None`
- L331 [`MOCK`] `mock_dependencies["tester"].test.return_value = res`
- L343 [`MOCK`] `tester=mock_dependencies["tester"],`
- L344 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L345 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L346 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L347 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L348 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L350 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L351 [`MOCK`] `history=mock_dependencies["history"],`
- L365 [`MOCK`] `async def test_processing_consumer_go_tester(mock_dependencies):`
- L366 [`MOCK`] `queue = mock_dependencies["queue"]`
- L377 [`MOCK`] `mock_dependencies["tester"].go_tester.available = True`
- L379 [`MOCK`] `# Mock test_batch updates objects in place`
- L385 [`MOCK`] `mock_dependencies["tester"].test_batch.side_effect = side_effect`
- L397 [`MOCK`] `tester=mock_dependencies["tester"],`
- L398 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L399 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L400 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L401 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L402 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L404 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L405 [`MOCK`] `history=mock_dependencies["history"],`
- L418 [`MOCK`] `async def test_processing_consumer_filters(mock_dependencies):`
- L419 [`MOCK`] `queue = mock_dependencies["queue"]`
- L429 [`MOCK`] `# Mock Python tester returns working but HIGH latency`
- L433 [`MOCK`] `mock_dependencies["tester"].test.return_value = res`
- L445 [`MOCK`] `tester=mock_dependencies["tester"],`
- L446 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L447 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L448 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L449 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L450 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L452 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L453 [`MOCK`] `history=mock_dependencies["history"],`
- L466 [`MOCK`] `async def test_processing_consumer_country_filter(mock_dependencies):`
- L467 [`MOCK`] `queue = mock_dependencies["queue"]`
- L480 [`MOCK`] `mock_dependencies["tester"].test.return_value = res`
- L483 [`MOCK`] `mock_dependencies["geoip"].lookup = AsyncMock(`
- L484 [`MOCK`] `return_value=MagicMock(country_code="US", city="", asn="", org="")`
- L497 [`MOCK`] `tester=mock_dependencies["tester"],`
- L498 [`MOCK`] `scheduler=mock_dependencies["scheduler"],`
- L499 [`MOCK`] `test_cache=mock_dependencies["test_cache"],`
- L500 [`MOCK`] `concurrency=mock_dependencies["concurrency"],`
- L501 [`MOCK`] `geoip=mock_dependencies["geoip"],`
- L502 [`MOCK`] `tracker=mock_dependencies["tracker"],`
- L504 [`MOCK`] `quality_tracker=mock_dependencies["quality"],`
- L505 [`MOCK`] `history=mock_dependencies["history"],`

### `tests/unit/test_producer_quality_accounting.py`
- L8 [`MOCK`] `from unittest.mock import MagicMock`
- L19 [`MOCK`] `quality = MagicMock()`

### `tests/unit/test_proxy_history_extended.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock`
- L15 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L35 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L63 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L82 [`MOCK`] `p = MagicMock(spec=Proxy)`
- L106 [`MOCK`] `p = MagicMock(spec=Proxy)`

### `tests/unit/test_scheduler.py`
- L5 [`MOCK`] `from unittest.mock import MagicMock`
- L15 [`MOCK`] `self.cache = MagicMock(spec=TestResultCache)`
- L62 [`MOCK`] `# Mock: p1 needs test, p2 does not`
- L63 [`MOCK`] `self.scheduler.should_retest = MagicMock(side_effect=[True, False])`

### `tests/unit/test_security.py`
- L3 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock`
- L11 [`MOCK`] `def mock_blocklist_file(tmp_path):`
- L25 [`MOCK`] `async def test_is_blocked_logic(mock_blocklist_file):`
- L28 [`MOCK`] `# Mock the CACHE_FILE path and content loading`
- L29 [`MOCK`] `mock_blocklist_file.write_text("1.2.3.4/32\n5.6.7.0/24")`
- L31 [`MOCK`] `with patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file):`
- L40 [`MOCK`] `async def test_update_blocklist(mock_blocklist_file):`
- L44 [`MOCK`] `patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file),`
- L45 [`MOCK`] `patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,`
- L47 [`MOCK`] `mock_resp = MagicMock()`
- L48 [`MOCK`] `mock_resp.status_code = 200`
- L49 [`MOCK`] `mock_resp.raise_for_status = MagicMock()`
- L50 [`MOCK`] `mock_resp.content = b"9.9.9.9/32\n10.10.10.0/24"`
- L52 [`MOCK`] `mock_get.return_value = mock_resp`
- L56 [`MOCK`] `if not mock_blocklist_file.exists():`
- L59 [`MOCK`] `print("File content:", mock_blocklist_file.read_text())`
- L80 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,`
- L82 [`MOCK`] `mock_resp = MagicMock()`
- L83 [`MOCK`] `mock_resp.status = 200`
- L88 [`MOCK`] `mock_resp.json = async_json`
- L89 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp`
- L99 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,`
- L101 [`MOCK`] `mock_resp = MagicMock()`
- L102 [`MOCK`] `mock_resp.status = 200`
- L107 [`MOCK`] `mock_resp.json = async_json`
- L108 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp`

### `tests/unit/test_security_validator.py`
- L21 [`ASSUMING`] `# Assuming it checks for basic validity.`

### `tests/unit/test_security_validator_extra.py`
- L2 [`MOCK`] `from unittest.mock import patch`
- L18 [`MOCK`] `# Mocking _is_address_safe to simulate failure`
- L58 [`MOCK`] `# Mock validator to fail the second one with a non-fatal reason`
- L61 [`MOCK`] `) as mock_val:`
- L62 [`MOCK`] `mock_val.side_effect = [(True, "ok"), (False, "tls_required")]`

### `tests/unit/test_security_validator_full.py`
- L54 [`ASSUMING`] `# Assuming we want it to fail, but current logic allows it.`

### `tests/unit/test_server.py`
- L3 [`MOCK`] `from unittest.mock import patch`
- L58 [`MOCK`] `# Mock FileResponse to return content from disk (simulating server behavior)`
- L77 [`MOCK`] `def mock_output_dir(tmp_path):`
- L78 [`MOCK`] `"""Mock the output directory and create dummy files."""`
- L113 [`MOCK`] `def mock_frontend_dir(tmp_path):`
- L114 [`MOCK`] `"""Mock the frontend directory."""`
- L124 [`MOCK`] `async def test_health_check(mock_output_dir, async_client):`
- L125 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L134 [`MOCK`] `async def test_get_stats(mock_output_dir, async_client):`
- L135 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L144 [`MOCK`] `mock_output_dir, async_client, monkeypatch`
- L155 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L169 [`MOCK`] `mock_output_dir, async_client, monkeypatch`
- L171 [`MOCK`] `(mock_output_dir / "proxies.old.json").write_text(`
- L175 [`MOCK`] `(mock_output_dir / "proxies.json").write_text(`
- L188 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L203 [`MOCK`] `async def test_get_proxies_all(mock_output_dir, async_client):`
- L204 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L211 [`MOCK`] `async def test_get_proxies_by_country(mock_output_dir, async_client):`
- L212 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L224 [`MOCK`] `async def test_get_proxies_by_protocol(mock_output_dir, async_client):`
- L225 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L237 [`MOCK`] `async def test_download_subscription(mock_output_dir, async_client):`
- L238 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L391 [`MOCK`] `async def test_frontend_serving(mock_frontend_dir, async_client):`
- L392 [`MOCK`] `with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):`
- L415 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L420 [`MOCK`] `side_effect=mock_test,`
- L438 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L443 [`MOCK`] `side_effect=mock_test,`
- L460 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L465 [`MOCK`] `side_effect=mock_test,`
- L513 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L518 [`MOCK`] `side_effect=mock_test,`

### `tests/unit/test_server_new.py`
- L49 [`MOCK`] `# But since we mocked/created dummy files in previous steps or they exist in repo...`

### `tests/unit/test_singbox_binary_resolution.py`
- L41 [`MOCK`] `# Mock Path.cwd to point to a clean temp directory`

### `tests/unit/test_sorter.py`
- L7 [`MOCK`] `from unittest.mock import MagicMock`
- L15 [`MOCK`] `def _setup_history_mock(self, proxies, reliability_map=None, uptime_map=None):`
- L16 [`MOCK`] `history = MagicMock()`
- L40 [`MOCK`] `history = MagicMock()`
- L54 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.9}, {proxy.id: 95.0})`
- L78 [`MOCK`] `history = self._setup_history_mock(`
- L108 [`MOCK`] `history = self._setup_history_mock(`
- L145 [`MOCK`] `history = self._setup_history_mock(`
- L173 [`MOCK`] `history = self._setup_history_mock(`
- L203 [`MOCK`] `history = self._setup_history_mock(`
- L234 [`MOCK`] `# Manually create mock to handle missing key logic`
- L235 [`MOCK`] `history = MagicMock()`
- L269 [`MOCK`] `history = self._setup_history_mock(`
- L295 [`MOCK`] `history = self._setup_history_mock(`
- L321 [`MOCK`] `history = self._setup_history_mock(`
- L351 [`MOCK`] `history = self._setup_history_mock(`
- L383 [`MOCK`] `history = self._setup_history_mock(`
- L410 [`MOCK`] `history = self._setup_history_mock(`
- L442 [`MOCK`] `history = self._setup_history_mock(`
- L465 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.6}, {proxy.id: 70.0})`

### `tests/unit/test_ss_ffi.py`
- L2 [`MOCK`] `from unittest.mock import patch, MagicMock`
- L37 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L39 [`MOCK`] `mock_cdll.assert_not_called()`
- L72 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L73 [`MOCK`] `mock_lib = MagicMock()`
- L74 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1`
- L75 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L77 [`MOCK`] `# Force reload lib (reset global in module is hard, so we mock where it's used)`
- L81 [`MOCK`] `mock_lib.verify_shadowsocks.assert_called()`
- L90 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L91 [`MOCK`] `mock_lib = MagicMock()`
- L92 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0  # Invalid`
- L93 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L105 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L106 [`MOCK`] `mock_lib = MagicMock()`
- L107 [`MOCK`] `mock_lib.verify_shadowsocks.side_effect = Exception("FFI Error")`
- L108 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L120 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L121 [`MOCK`] `mock_lib = MagicMock()`
- L122 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1`
- L123 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L131 [`MOCK`] `call_args = mock_lib.verify_shadowsocks.call_args`
- L150 [`MOCK`] `with patch("configstream.security.ss_ffi.logger") as mock_logger:`
- L154 [`MOCK`] `assert mock_logger.warning.called`
- L163 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L164 [`MOCK`] `mock_lib = MagicMock()`
- L165 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1`
- L166 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L187 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L188 [`MOCK`] `mock_lib = MagicMock()`
- L189 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1`
- L190 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L204 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L205 [`MOCK`] `mock_lib = MagicMock()`
- L206 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0`
- L207 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L243 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L244 [`MOCK`] `mock_lib = MagicMock()`
- L245 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L248 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1`
- L253 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0`
- L258 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = -1`
- L269 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:`
- L270 [`MOCK`] `mock_lib = MagicMock()`
- L271 [`MOCK`] `mock_cdll.return_value = mock_lib`
- L277 [`MOCK`] `mock_cdll.assert_called_once()`
- L279 [`MOCK`] `assert hasattr(mock_lib, "verify_shadowsocks")`

### `tests/unit/test_utils.py`
- L4 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/test_utils_extended.py`
- L26 [`MOCK`] `# Force fail by making directory read-only or mocking`
- L27 [`MOCK`] `# Using mock for stability`
- L28 [`MOCK`] `from unittest.mock import patch`

### `tests/unit/test_validate_frontend_placeholders.py`
- L2 [`PLACEHOLDER`] `"""Tests for frontend production placeholder validation."""`
- L8 [`PLACEHOLDER`] `from scripts.validate_frontend_placeholders import (`
- L10 [`PLACEHOLDER`] `validate_frontend_placeholders,`
- L22 [`PLACEHOLDER`] `'const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";\n',`
- L27 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_detects_public_and_stego_keys(`
- L32 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(tmp_path, strict=True)`
- L34 [`PLACEHOLDER`] `assert any("PUBLIC_KEY placeholder" in error for error in errors)`
- L35 [`PLACEHOLDER`] `assert any("STEGO_KEY placeholder" in error for error in errors)`
- L38 [`PLACEHOLDER`] `def test_inject_frontend_keys_replaces_placeholders(tmp_path: Path) -> None:`
- L50 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=True) == []`
- L59 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(`
- L69 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=False) == []`

### `tests/unit/test_validate_workflows.py`
- L27 [`PLACEHOLDER`] `def test_validate_workflows_requires_pages_frontend_placeholder_guard(`

### `tests/unit/test_washer.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock, patch`
- L103 [`MOCK`] `# Mock _get_clean_endpoint and _get_consistent_exit to ensure success path`
- L104 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("1.1.1.1", 2408))`
- L137 [`MOCK`] `# Mock helpers`
- L138 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("2.2.2.2", 2408))`
- L164 [`MOCK`] `washer_stats_fixture.get_warp_config = MagicMock(`

### `tests/unit/tools/test_dns_scanner.py`
- L17 [`MOCK`] `async def test_test_dns_mock():`
- L20 [`MOCK`] `# Basic existence check since we can't easily mock network calls without respx/aioresponses`
- L21 [`MOCK`] `# and aiodns is tricky to mock fully in this context without real networking`

### `tests/unit/utils/test_cert.py`
- L3 [`MOCK`] `from unittest.mock import MagicMock`
- L5 [`MOCK`] `# Mock OpenSSL if not present`
- L6 [`MOCK`] `sys.modules["OpenSSL"] = MagicMock()`
- L7 [`MOCK`] `sys.modules["OpenSSL.crypto"] = MagicMock()`
- L12 [`MOCK`] `def test_cert_generation_mock():`
- L13 [`MOCK`] `# Since we mocked OpenSSL, we just check if the function runs without import error`
- L14 [`MOCK`] `# and tries to access the mocked object.`
- L19 [`MOCK`] `pass  # Expected due to mock return values not being full objects`
