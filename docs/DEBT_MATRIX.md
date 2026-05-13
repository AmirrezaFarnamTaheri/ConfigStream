# Debt Matrix

Generated: `2026-05-13T00:07:52.444845+00:00`

## Summary

- Total markers: **3082**
- `ASSUMING`: **28**
- `FIXME`: **5**
- `MOCK`: **2613**
- `PLACEHOLDER`: **375**
- `TODO`: **44**
- `XXX`: **17**

## Categories

- `ci`: **1**
- `docs`: **21**
- `frontend`: **49**
- `other`: **1645**
- `production`: **28**
- `test`: **1293**
- `tooling`: **45**

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
| `CHANGELOG.md` | 9 | PLACEHOLDER, TODO |
| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 1641 | ASSUMING, FIXME, MOCK, PLACEHOLDER, TODO, XXX |
| `SECURITY.md` | 2 | PLACEHOLDER |
| `STATUS.md` | 7 | MOCK, PLACEHOLDER |
| `docs/claim_ledger.json` | 2 | MOCK, PLACEHOLDER |
| `docs/wiki/encyclopedia/glossary/networking_terms.md` | 1 | ASSUMING |
| `docs/wiki/encyclopedia/glossary/security_concepts.md` | 1 | XXX |
| `docs/wiki/encyclopedia/networking/warp.md` | 1 | XXX |
| `frontend/assets/js/analytics.js` | 3 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/charts.js` | 1 | MOCK |
| `frontend/assets/js/constants.js` | 1 | PLACEHOLDER |
| `frontend/assets/js/i18n.js` | 12 | PLACEHOLDER |
| `frontend/assets/js/lab.js` | 1 | XXX |
| `frontend/assets/js/main.js` | 2 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/stego.js` | 3 | PLACEHOLDER |
| `frontend/assets/js/verifier.js` | 2 | ASSUMING, PLACEHOLDER |
| `frontend/assets/js/washer_client.js` | 1 | MOCK |
| `frontend/index.html` | 1 | PLACEHOLDER |
| `frontend/lab-offline.html` | 1 | PLACEHOLDER |
| `frontend/lab.html` | 15 | PLACEHOLDER, XXX |
| `frontend/proxies.html` | 5 | PLACEHOLDER |
| `frontend/service-worker.js` | 1 | ASSUMING |
| `scripts/deploy_artifact_smoke.py` | 5 | PLACEHOLDER |
| `scripts/frontend_same_origin_smoke.cjs` | 3 | PLACEHOLDER |
| `scripts/generate_debt_matrix.py` | 6 | FIXME, MOCK, PLACEHOLDER, TODO |
| `scripts/run_test_profile.py` | 1 | PLACEHOLDER |
| `scripts/validate_frontend_placeholders.py` | 14 | PLACEHOLDER |
| `scripts/validate_pages_artifact.py` | 2 | PLACEHOLDER |
| `scripts/validate_workflows.py` | 4 | PLACEHOLDER |
| `scripts/verify_pages_deployment.py` | 10 | PLACEHOLDER |
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
| `tests/unit/test_debt_matrix.py` | 9 | MOCK, TODO |
| `tests/unit/test_dns_batch_resolver.py` | 12 | MOCK |
| `tests/unit/test_event_stream.py` | 65 | MOCK |
| `tests/unit/test_fetcher.py` | 92 | MOCK |
| `tests/unit/test_fetcher_advanced.py` | 25 | MOCK |
| `tests/unit/test_fetcher_config.py` | 13 | MOCK |
| `tests/unit/test_fetcher_resilience.py` | 8 | MOCK |
| `tests/unit/test_fetcher_retries.py` | 12 | MOCK |
| `tests/unit/test_filtering_extended.py` | 8 | MOCK |
| `tests/unit/test_frontend_failover.py` | 3 | PLACEHOLDER |
| `tests/unit/test_frontend_verifier.py` | 4 | PLACEHOLDER |
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
| `tests/unit/test_server.py` | 38 | MOCK |
| `tests/unit/test_server_concurrent_cache.py` | 1 | MOCK |
| `tests/unit/test_server_new.py` | 1 | MOCK |
| `tests/unit/test_singbox_binary_resolution.py` | 1 | MOCK |
| `tests/unit/test_sorter.py` | 20 | MOCK |
| `tests/unit/test_ss_ffi.py` | 47 | MOCK |
| `tests/unit/test_utils.py` | 1 | MOCK |
| `tests/unit/test_utils_extended.py` | 3 | MOCK |
| `tests/unit/test_validate_frontend_placeholders.py` | 13 | PLACEHOLDER |
| `tests/unit/test_validate_workflows.py` | 3 | PLACEHOLDER |
| `tests/unit/test_verify_pages_deployment.py` | 3 | PLACEHOLDER |
| `tests/unit/test_washer.py` | 6 | MOCK |
| `tests/unit/tools/test_dns_scanner.py` | 3 | MOCK |
| `tests/unit/utils/test_cert.py` | 8 | MOCK |

## Raw Entries

### `.github/workflows/deploy-pages.yml`
- L136 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output`

### `AGENTS.md`
- L151 [`ASSUMING`] `*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.`

### `CHANGELOG.md`
- L7 [`PLACEHOLDER`] `- **Frontend Audit**: confirmed the frontend production output uses raw statics deployed into the output directory with placeholders validated and resolved at deploy time into `assets/js/runtime-config.js`.`
- L55 [`PLACEHOLDER`] `- **Frontend runtime-config deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to generate `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, preserving checked-in source JS while failing upload on missing runtime keys or placeholder markers.`
- L57 [`PLACEHOLDER`] `- **Deployed Pages URL smoke**: Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, public artifact aliases, health metadata, base64/chosen subscription endpoints, manifest hash parity, run identity, and placeholder-key absence.`
- L59 [`PLACEHOLDER`] `- **Frontend verifier fail-closed path**: Signed frontend artifacts now reject when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L62 [`PLACEHOLDER`] `- **Frontend runtime-config tests/workflow parity**: Added tests for placeholder detection/runtime-config generation and extended workflow validation so `deploy-pages.yml` cannot drop the frontend runtime-config guard or secret env wiring silently.`
- L106 [`PLACEHOLDER`] `- **Side-product deploy-secret scan**: Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers inside ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L110 [`PLACEHOLDER`] `- **Deterministic public artifact fixture**: Added a unit fixture that builds a Pages-style artifact from the real output generator, adds deploy aliases and static placeholders, refreshes the public contract, and validates the result with `scripts/validate_pages_artifact.py`.`
- L118 [`PLACEHOLDER`] `- **Frontend failover proof**: Added local IPFS/IPNS failover tests for the same-origin connectivity probe, placeholder-key no-op, gateway URL normalization, page/query/hash preservation, and session loop prevention; production-smoke now runs this proof.`
- L243 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts`

### `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`
- L61 [`PLACEHOLDER`] `1. Public Pages readiness requires live evidence for `health.json`, `metadata.json`, `artifact_manifest.json`, `base64.txt`, `chosen/base64.txt`, `proxies.json`, `api/proxies`, `api/stats`, frontend rendering, placeholder absence, and manifest/hash parity after deployment.`
- L68 [`MOCK`] `8. The debt matrix must be triaged into real release blockers, accepted test mocks, accepted user-facing placeholder text, generated-doc noise, production mocks, docs-only historical references, and false positives.`
- L122 [`PLACEHOLDER`] `The prior source-of-truth audit said the repository had serious blockers: invalid workflow YAML, stale public artifacts, schema mismatches, inflated `total_working`, raw frontend deployment with placeholder keys, security defaults that overclaimed fail-closed behavior, and widespread docs drift. `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md``
- L124 [`PLACEHOLDER`] `The latest `STATUS.md` shows many of those have been actively remediated: workflow parsing, Pages contract files, `health.json`, `artifact_manifest.json`, shielded metric accounting, admin fail-closed behavior, CORS tightening, WebSocket lifecycle controls, lab live-test hardening, fetch redirect validation, frontend placeholder injection, protocol/output matrices, claim ledger, docs-sync, debt matrix, and local-first frontend assets. `STATUS.md``
- L165 [`TODO`] `The debt matrix is not cosmetic. It shows **1,402 tracked markers**, including 13 TODOs, 1 FIXME, 5 XXX, 126 PLACEHOLDER, 9 ASSUMING, and 1,248 MOCK markers. It separates categories and still lists production/frontend/tooling/docs debt, not only tests. `DEBT_MATRIX.md``
- L169 [`PLACEHOLDER`] `- `.github/workflows/deploy-pages.yml`: placeholder-related marker.`
- L170 [`PLACEHOLDER`] `- `frontend/assets/js/constants.js`: placeholder public-key detection.`
- L171 [`PLACEHOLDER`] `- `frontend/assets/js/stego.js`: `PLACEHOLDER_KEY_INJECTED_BY_CI`.`
- L172 [`PLACEHOLDER`] `- `frontend/assets/js/verifier.js`: verification skips or weakens when public key is placeholder/missing.`
- L173 [`MOCK`] `- `frontend/assets/js/washer_client.js`: “Mock status check.”`
- L174 [`XXX`] `- `frontend/assets/js/lab.js`: `XXX` in generated bash temp-file path.`
- L175 [`PLACEHOLDER`] `- `src/configstream/generators/base64.py`: intentionally encodes a placeholder when output would otherwise be empty.`
- L176 [`TODO`] `- `src/configstream/tools/dns_scanner/bash/dnsScanner.sh`: several TODO markers.`
- L177 [`TODO`] `- `scripts/generate_debt_matrix.py`: even the debt generator itself contains TODO/FIXME text. `DEBT_MATRIX.md``
- L179 [`PLACEHOLDER`] `Some of these are false positives because the debt scanner counts words inside docs/tests/guard code. But not all are harmless. The presence of frontend placeholder keys and verifier fallback paths means “no placeholder deployed” is only true if deploy-time injection succeeds and validation runs. The repository source itself still contains placeholder material by design. `DEBT_MATRIX.md``
- L181 [`MOCK`] `**Amendment:** previous reporting should have treated the debt matrix as a live blocker class, not a hygiene side note. The next roadmap must triage debt entries into: real production defect, allowed test/mock, allowed user-facing placeholder text, generated-doc noise, and stale scanner false-positive.`
- L239 [`PLACEHOLDER`] `- Live dashboard rendering with no placeholders.`
- L249 [`PLACEHOLDER`] `**Amendment:** frontend placeholder injection is a mitigation, not final architecture. This is resolved: Pages deploy now injects and validates frontend placeholders into a generated runtime config file (`assets/js/runtime-config.js`).`
- L342 [`PLACEHOLDER`] `- **Frontend:** local-first and placeholder guards exist, and raw-static is confirmed canonical.`
- L366 [`PLACEHOLDER`] `11. **The frontend verifier/key model remains transitional.** Placeholder injection is guarded, but source placeholder material remains and canonical build path is unresolved. `STATUS.md` `DEBT_MATRIX.md``
- L447 [`PLACEHOLDER`] `- accepted user-facing placeholders`
- L449 [`MOCK`] `- test mocks`
- L450 [`MOCK`] `- production mocks`
- L480 [`PLACEHOLDER`] `4. Add deploy-time no-placeholder scan across all HTML/JS/CSS, not only known key files.`
- L488 [`PLACEHOLDER`] `4. Secret/placeholder checks inside ZIPs and frontend bundles.`
- L550 [`PLACEHOLDER`] `- Add no-placeholder/no-secret/no-raw-log checks when touching frontend, outputs, logs, or ZIPs.`
- L1571 [`PLACEHOLDER`] `- No placeholder public key in deployed artifact.`
- L1700 [`PLACEHOLDER`] `- Placeholder values.`
- L1768 [`PLACEHOLDER`] `- ZIP scanned for placeholder/deploy secrets.`
- L2201 [`PLACEHOLDER`] `- `frontend_placeholder_error``
- L2336 [`PLACEHOLDER`] `- Placeholder key deployment`
- L2450 [`PLACEHOLDER`] `- Frontend no placeholders.`
- L2972 [`PLACEHOLDER`] `- No placeholder leakage.`
- L3670 [`PLACEHOLDER`] `The prior source-of-truth audit said the repository had serious blockers: invalid workflow YAML, stale public artifacts, schema mismatches, inflated `total_working`, raw frontend deployment with placeholder keys, security defaults that overclaimed fail-closed behavior, and widespread docs drift.`
- L3672 [`PLACEHOLDER`] `The latest `STATUS.md` shows many of those have been actively remediated: workflow parsing, Pages contract files, `health.json`, `artifact_manifest.json`, shielded metric accounting, admin fail-closed behavior, CORS tightening, WebSocket lifecycle controls, lab live-test hardening, fetch redirect validation, frontend placeholder injection, protocol/output matrices, claim ledger, docs-sync, debt matrix, and local-first frontend assets.`
- L3684 [`TODO`] `The debt matrix is not cosmetic. It shows **1,402 tracked markers**, including 13 TODOs, 1 FIXME, 5 XXX, 126 PLACEHOLDER, 9 ASSUMING, and 1,248 MOCK markers. It separates categories and still lists production/frontend/tooling/docs debt, not only tests.`
- L3686 [`PLACEHOLDER`] `* `.github/workflows/deploy-pages.yml`: placeholder-related marker.`
- L3687 [`PLACEHOLDER`] `* `frontend/assets/js/constants.js`: placeholder public-key detection.`
- L3688 [`PLACEHOLDER`] `* `frontend/assets/js/stego.js`: `PLACEHOLDER_KEY_INJECTED_BY_CI`.`
- L3689 [`PLACEHOLDER`] `* `frontend/assets/js/verifier.js`: verification skips or weakens when public key is placeholder/missing.`
- L3690 [`MOCK`] `* `frontend/assets/js/washer_client.js`: “Mock status check.”`
- L3691 [`XXX`] `* `frontend/assets/js/lab.js`: `XXX` in generated bash temp-file path.`
- L3692 [`PLACEHOLDER`] `* `src/configstream/generators/base64.py`: intentionally encodes a placeholder when output would otherwise be empty.`
- L3693 [`TODO`] `* `src/configstream/tools/dns_scanner/bash/dnsScanner.sh`: several TODO markers.`
- L3694 [`TODO`] `* `scripts/generate_debt_matrix.py`: even the debt generator itself contains TODO/FIXME text.`
- L3696 [`PLACEHOLDER`] `Some of these are false positives because the debt scanner counts words inside docs/tests/guard code. But not all are harmless. The presence of frontend placeholder keys and verifier fallback paths means “no placeholder deployed” is only true if deploy-time injection succeeds and validation runs. The repository source itself still contains placeholder material by design.`
- L3730 [`PLACEHOLDER`] `* Live dashboard rendering with no placeholders.`
- L3819 [`PLACEHOLDER`] `11. **The frontend verifier/key model remains transitional.** Placeholder injection is guarded, but source placeholder material remains and canonical build path is unresolved.`
- L3860 [`PLACEHOLDER`] `* accepted user-facing placeholders`
- L3862 [`MOCK`] `* test mocks`
- L3863 [`MOCK`] `* production mocks`
- L4004 [`PLACEHOLDER`] `- Pages deploy now generates `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, leaves checked-in source-shaped JS immutable, and fails before upload if required runtime keys are missing or placeholder markers remain; workflow and Pages artifact validation enforce this guard.`
- L4006 [`PLACEHOLDER`] `- Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, metadata/proxy API alias parity, health metadata, and placeholder-key absence.`
- L4007 [`PLACEHOLDER`] `- Frontend signed-artifact verification now fails closed when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L4021 [`PLACEHOLDER`] `- Optional IPFS/IPNS frontend failover is now covered by local tests: the frontend probes a same-origin static asset, skips placeholder IPNS keys, preserves the current leaf page/query/hash when building gateway URLs, normalizes gateway bases, and prevents repeated redirect attempts within the same session.`
- L4026 [`MOCK`] `- Debt matrix artifacts are portable: generated paths are repo-relative, generated debt files are excluded from self-scans, and marker summaries separate production/frontend/tooling/docs debt from test-only mocks.`
- L4083 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed`
- L4090 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed`
- L4171 [`PLACEHOLDER`] `- **Frontend runtime-config deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to generate `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, preserving checked-in source JS while failing upload on missing runtime keys or placeholder markers.`
- L4173 [`PLACEHOLDER`] `- **Deployed Pages URL smoke**: Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, public artifact aliases, health metadata, base64/chosen subscription endpoints, manifest hash parity, run identity, and placeholder-key absence.`
- L4175 [`PLACEHOLDER`] `- **Frontend verifier fail-closed path**: Signed frontend artifacts now reject when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L4178 [`PLACEHOLDER`] `- **Frontend runtime-config tests/workflow parity**: Added tests for placeholder detection/runtime-config generation and extended workflow validation so `deploy-pages.yml` cannot drop the frontend runtime-config guard or secret env wiring silently.`
- L4222 [`PLACEHOLDER`] `- **Side-product deploy-secret scan**: Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers inside ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L4226 [`PLACEHOLDER`] `- **Deterministic public artifact fixture**: Added a unit fixture that builds a Pages-style artifact from the real output generator, adds deploy aliases and static placeholders, refreshes the public contract, and validates the result with `scripts/validate_pages_artifact.py`.`
- L4234 [`PLACEHOLDER`] `- **Frontend failover proof**: Added local IPFS/IPNS failover tests for the same-origin connectivity probe, placeholder-key no-op, gateway URL normalization, page/query/hash preservation, and session loop prevention; production-smoke now runs this proof.`
- L4359 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts`
- L4710 [`PLACEHOLDER`] `5. The deployed frontend path is now deliberately raw static for GitHub Pages, with generated runtime-config key injection, placeholder validation, workflow guards, and Pages artifact presence checks.`
- L4906 [`PLACEHOLDER`] `- dashboard rendering with no placeholders`
- L5006 [`PLACEHOLDER`] `11. Frontend verifier/key model is transitional until placeholder injection is replaced by a cleaner generated runtime config contract and live no-placeholder proof.`
- L5042 [`MOCK`] `- split real production defects, accepted tests/mocks, allowed user-facing placeholders, generated-doc false positives, and docs-only historical references.`
- L5089 [`PLACEHOLDER`] `- frontend external dependencies, placeholders, and `innerHTML``
- L5410 [`PLACEHOLDER`] `- The frontend renders the degraded state without placeholders.`
- L5727 [`PLACEHOLDER`] `- Production Pages previously risked serving placeholder key material; deploy now writes a generated runtime config artifact before upload.`
- L5734 [`PLACEHOLDER`] `- Added `scripts/validate_frontend_placeholders.py`.`
- L5735 [`PLACEHOLDER`] `- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.`
- L5738 [`PLACEHOLDER`] `- The validator fails if required runtime keys are missing, or if the public key placeholder marker or stego placeholder remains in source-shaped JS or the generated runtime config.`
- L5739 [`PLACEHOLDER`] `- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.`
- L5740 [`PLACEHOLDER`] `- Tests cover placeholder detection, runtime-config generation, optional non-strict stego handling, and workflow guard retention.`
- L5741 [`PLACEHOLDER`] `- `frontend/assets/js/verifier.js` now fails closed for signed objects when WebCrypto is unavailable or the public key is missing/placeholder, while preserving unsigned local/offline parsing.`
- L5742 [`PLACEHOLDER`] `- `tests/unit/test_frontend_verifier.py` executes the browser verifier script in Node VM and covers missing WebCrypto, missing key, placeholder key, and unsigned local content behavior.`
- L5746 [`PLACEHOLDER`] `- `scripts/deploy_artifact_smoke.py` now assembles a temporary Pages-shaped artifact, generates runtime config, validates placeholders and the public artifact contract, and runs `scripts/frontend_same_origin_smoke.cjs --root ... --require-runtime-config` against that exact artifact.`
- L5747 [`PLACEHOLDER`] `- `.github/workflows/deploy-pages.yml` now runs `scripts/verify_pages_deployment.py` after `actions/deploy-pages`, checking the deployed URL for primary HTML pages, runtime config, metadata/proxy alias parity, health metadata, and placeholder-key absence.`
- L5754 [`PLACEHOLDER`] `4. Fail production build if required public key/stego key placeholders remain.`
- L5756 [`PLACEHOLDER`] `6. Add placeholder leak tests.`
- L5764 [`PLACEHOLDER`] `- Deployed frontend contains no placeholder key strings.`
- L5768 [`PLACEHOLDER`] `- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.`
- L6225 [`PLACEHOLDER`] `- If the library is present but does not match the placeholder hash, validation fails.`
- L6300 [`TODO`] `- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.`
- L6388 [`MOCK`] `mocks from production/frontend/tooling/docs debt.`
- L6398 [`PLACEHOLDER`] `##### P3-4. Zero-byte and placeholder assets remain`
- L6409 [`PLACEHOLDER`] `3. Done: unreferenced root `NL` and `US` placeholder files were removed.`
- L6620 [`PLACEHOLDER`] `- Source placeholder key material has been removed from the runtime path; generated runtime config still needs deploy-smoke proof on a fully assembled artifact.`
- L6846 [`PLACEHOLDER`] `- Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers in ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L6850 [`PLACEHOLDER`] `- `tests/unit/test_output.py` now builds a deterministic Pages-style artifact from the real output generator, adds deploy aliases and static placeholder files, refreshes `health.json` / `artifact_manifest.json`, and validates the complete directory with `scripts/validate_pages_artifact.py`.`
- L6941 [`PLACEHOLDER`] `3. Public pages must never show unresolved placeholders.`
- L6950 [`PLACEHOLDER`] `same-origin static connectivity probe, placeholder IPNS-key no-op, gateway base`
- L6960 [`PLACEHOLDER`] `- placeholder leak tests`
- L7032 [`TODO`] `- zero TODO/FIXME`
- L7073 [`PLACEHOLDER`] `4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.`
- L7249 [`PLACEHOLDER`] `5. Done: fail deploy on missing runtime keys or placeholder key markers.`
- L7262 [`PLACEHOLDER`] `- Delete unused build path, unused scripts, and placeholder config files.`
- L7331 [`PLACEHOLDER`] `6. Add no-placeholder, no-network frontend, public contract, and security posture tests.`
- L7376 [`PLACEHOLDER`] `- frontend has no unresolved placeholders.`
- L7377 [`PLACEHOLDER`] `- no placeholder key material is deployed.`
- L7416 [`PLACEHOLDER`] `- No placeholder keys.`
- L7477 [`PLACEHOLDER`] `10. Frontend has no placeholder keys or unresolved template tokens.`
- L7512 [`PLACEHOLDER`] `**Resolution:** Updated `main.yml` to set `continue-on-error: true` for the `frontend-wasm` download step in the merge job. Ensure `scripts/build_wasm.sh` creates the necessary directories and placeholder dummy files gracefully if compilation fails.`
- L7591 [`ASSUMING`] `- `ASSUMING`: **9**`
- L7592 [`FIXME`] `- `FIXME`: **1**`
- L7593 [`MOCK`] `- `MOCK`: **1248**`
- L7594 [`PLACEHOLDER`] `- `PLACEHOLDER`: **126**`
- L7595 [`TODO`] `- `TODO`: **13**`
- L7596 [`XXX`] `- `XXX`: **5**`
- L7610 [`FIXME`] `- `FIXME` / `XXX`: fix inline before release freeze.`
- L7611 [`TODO`] `- `TODO`: create issue with owner + milestone.`
- L7612 [`MOCK`] `- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.`
- L7613 [`PLACEHOLDER`] `- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.`
- L7619 [`PLACEHOLDER`] `| `.github/workflows/deploy-pages.yml` | 1 | PLACEHOLDER |`
- L7620 [`ASSUMING`] `| `AGENTS.md` | 1 | ASSUMING |`
- L7621 [`PLACEHOLDER`] `| `CHANGELOG.md` | 4 | PLACEHOLDER, TODO |`
- L7622 [`PLACEHOLDER`] `| `CLOSURE_REPORT.md` | 1 | PLACEHOLDER |`
- L7623 [`MOCK`] `| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 34 | MOCK, PLACEHOLDER, TODO |`
- L7624 [`PLACEHOLDER`] `| `SECURITY.md` | 2 | PLACEHOLDER |`
- L7625 [`PLACEHOLDER`] `| `STATUS.md` | 3 | PLACEHOLDER |`
- L7626 [`ASSUMING`] `| `docs/wiki/encyclopedia/glossary/networking_terms.md` | 1 | ASSUMING |`
- L7627 [`XXX`] `| `docs/wiki/encyclopedia/glossary/security_concepts.md` | 1 | XXX |`
- L7628 [`XXX`] `| `docs/wiki/encyclopedia/networking/warp.md` | 1 | XXX |`
- L7629 [`ASSUMING`] `| `frontend/assets/js/analytics.js` | 3 | ASSUMING, PLACEHOLDER |`
- L7630 [`MOCK`] `| `frontend/assets/js/charts.js` | 1 | MOCK |`
- L7631 [`PLACEHOLDER`] `| `frontend/assets/js/constants.js` | 3 | PLACEHOLDER |`
- L7632 [`PLACEHOLDER`] `| `frontend/assets/js/i18n.js` | 12 | PLACEHOLDER |`
- L7633 [`XXX`] `| `frontend/assets/js/lab.js` | 1 | XXX |`
- L7634 [`ASSUMING`] `| `frontend/assets/js/main.js` | 2 | ASSUMING, PLACEHOLDER |`
- L7635 [`PLACEHOLDER`] `| `frontend/assets/js/stego.js` | 2 | PLACEHOLDER |`
- L7636 [`ASSUMING`] `| `frontend/assets/js/verifier.js` | 3 | ASSUMING, PLACEHOLDER |`
- L7637 [`MOCK`] `| `frontend/assets/js/washer_client.js` | 1 | MOCK |`
- L7638 [`PLACEHOLDER`] `| `frontend/index.html` | 1 | PLACEHOLDER |`
- L7639 [`PLACEHOLDER`] `| `frontend/lab-offline.html` | 1 | PLACEHOLDER |`
- L7640 [`PLACEHOLDER`] `| `frontend/lab.html` | 15 | PLACEHOLDER, XXX |`
- L7641 [`PLACEHOLDER`] `| `frontend/proxies.html` | 5 | PLACEHOLDER |`
- L7642 [`ASSUMING`] `| `frontend/service-worker.js` | 1 | ASSUMING |`
- L7643 [`FIXME`] `| `scripts/generate_debt_matrix.py` | 6 | FIXME, MOCK, PLACEHOLDER, TODO |`
- L7644 [`PLACEHOLDER`] `| `scripts/run_test_profile.py` | 1 | PLACEHOLDER |`
- L7645 [`PLACEHOLDER`] `| `scripts/validate_frontend_placeholders.py` | 10 | PLACEHOLDER |`
- L7646 [`PLACEHOLDER`] `| `scripts/validate_workflows.py` | 4 | PLACEHOLDER |`
- L7647 [`XXX`] `| `sources/manual_warp.txt` | 1 | XXX |`
- L7648 [`MOCK`] `| `src/configstream/anomaly.py` | 2 | MOCK |`
- L7649 [`PLACEHOLDER`] `| `src/configstream/constants.py` | 1 | PLACEHOLDER |`
- L7650 [`PLACEHOLDER`] `| `src/configstream/generators/base64.py` | 1 | PLACEHOLDER |`
- L7651 [`MOCK`] `| `src/configstream/history/tracker.py` | 1 | MOCK |`
- L7652 [`MOCK`] `| `src/configstream/intelligence/chaining.py` | 1 | MOCK |`
- L7653 [`PLACEHOLDER`] `| `src/configstream/quality/storage.py` | 7 | PLACEHOLDER |`
- L7654 [`MOCK`] `| `src/configstream/security_validator.py` | 4 | MOCK |`
- L7655 [`MOCK`] `| `src/configstream/tools/censorship_lab.py` | 1 | MOCK |`
- L7656 [`TODO`] `| `src/configstream/tools/dns_scanner/bash/dnsScanner.sh` | 7 | TODO |`
- L7657 [`PLACEHOLDER`] `| `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` | 3 | PLACEHOLDER |`
- L7658 [`MOCK`] `| `tests/e2e/test_failure_scenarios.py` | 4 | MOCK |`
- L7659 [`MOCK`] `| `tests/e2e/test_frontend.py` | 10 | MOCK |`
- L7660 [`MOCK`] `| `tests/e2e/test_mixed_protocols.py` | 10 | MOCK |`
- L7661 [`MOCK`] `| `tests/scenarios/test_failure_modes.py` | 9 | MOCK |`
- L7662 [`MOCK`] `| `tests/test_manager.py` | 19 | MOCK |`
- L7663 [`MOCK`] `| `tests/test_output_transport.py` | 7 | MOCK |`
- L7664 [`MOCK`] `| `tests/test_python_tester.py` | 18 | MOCK |`
- L7665 [`MOCK`] `| `tests/test_scanner.py` | 17 | MOCK |`
- L7666 [`MOCK`] `| `tests/test_warp_scraper.py` | 17 | MOCK |`
- L7667 [`MOCK`] `| `tests/test_washer_utils.py` | 1 | MOCK |`
- L7668 [`MOCK`] `| `tests/unit/converters/test_singbox_converters.py` | 1 | MOCK |`
- L7669 [`MOCK`] `| `tests/unit/coverage_boost/test_adaptive_workers_coverage.py` | 13 | MOCK |`
- L7670 [`MOCK`] `| `tests/unit/coverage_boost/test_blocklist_coverage.py` | 2 | MOCK |`
- L7671 [`MOCK`] `| `tests/unit/coverage_boost/test_cli_coverage.py` | 27 | MOCK |`
- L7672 [`MOCK`] `| `tests/unit/coverage_boost/test_server_coverage.py` | 1 | MOCK |`
- L7673 [`MOCK`] `| `tests/unit/coverage_boost/test_washer_coverage.py` | 7 | MOCK |`
- L7674 [`MOCK`] `| `tests/unit/fetcher/test_fetcher_core.py` | 2 | MOCK |`
- L7675 [`MOCK`] `| `tests/unit/generators/test_singbox_comprehensive.py` | 1 | MOCK |`
- L7676 [`MOCK`] `| `tests/unit/geoip/test_geoip_resolver.py` | 17 | MOCK |`
- L7677 [`MOCK`] `| `tests/unit/history/test_history_components.py` | 8 | MOCK |`
- L7678 [`MOCK`] `| `tests/unit/intelligence/test_chaining_extended.py` | 2 | MOCK |`
- L7679 [`MOCK`] `| `tests/unit/intelligence/test_vectors.py` | 1 | MOCK |`
- L7680 [`MOCK`] `| `tests/unit/quality/test_quality_components.py` | 2 | MOCK |`
- L7681 [`MOCK`] `| `tests/unit/security/test_censorship.py` | 5 | MOCK |`
- L7682 [`MOCK`] `| `tests/unit/security/test_rules.py` | 8 | MOCK |`
- L7683 [`MOCK`] `| `tests/unit/security/test_utls_wrapper.py` | 14 | MOCK |`
- L7684 [`MOCK`] `| `tests/unit/security/test_virus_total_comprehensive.py` | 75 | MOCK |`
- L7685 [`MOCK`] `| `tests/unit/test_adapters_comprehensive.py` | 6 | MOCK |`
- L7686 [`MOCK`] `| `tests/unit/test_adaptive_timeout_extra.py` | 4 | MOCK |`
- L7687 [`MOCK`] `| `tests/unit/test_adaptive_workers.py` | 3 | MOCK |`
- L7688 [`MOCK`] `| `tests/unit/test_analytics_output.py` | 7 | MOCK |`
- L7689 [`MOCK`] `| `tests/unit/test_anomaly_extended.py` | 9 | MOCK |`
- L7690 [`MOCK`] `| `tests/unit/test_backup.py` | 1 | MOCK |`
- L7691 [`MOCK`] `| `tests/unit/test_backup_extended.py` | 8 | MOCK |`
- L7692 [`MOCK`] `| `tests/unit/test_bot_cli.py` | 38 | MOCK |`
- L7693 [`ASSUMING`] `| `tests/unit/test_cache_warming.py` | 15 | ASSUMING, MOCK |`
- L7694 [`MOCK`] `| `tests/unit/test_cli_extended.py` | 23 | MOCK |`
- L7695 [`MOCK`] `| `tests/unit/test_cli_full.py` | 1 | MOCK |`
- L7696 [`MOCK`] `| `tests/unit/test_concurrency_extended.py` | 3 | MOCK |`
- L7697 [`MOCK`] `| `tests/unit/test_consumer.py` | 23 | MOCK |`
- L7698 [`MOCK`] `| `tests/unit/test_dns_batch_resolver.py` | 12 | MOCK |`
- L7699 [`MOCK`] `| `tests/unit/test_event_stream.py` | 65 | MOCK |`
- L7700 [`MOCK`] `| `tests/unit/test_fetcher.py` | 85 | MOCK |`
- L7701 [`MOCK`] `| `tests/unit/test_fetcher_advanced.py` | 18 | MOCK |`
- L7702 [`MOCK`] `| `tests/unit/test_fetcher_config.py` | 13 | MOCK |`
- L7703 [`MOCK`] `| `tests/unit/test_fetcher_resilience.py` | 8 | MOCK |`
- L7704 [`MOCK`] `| `tests/unit/test_fetcher_retries.py` | 12 | MOCK |`
- L7705 [`MOCK`] `| `tests/unit/test_filtering_extended.py` | 8 | MOCK |`
- L7706 [`MOCK`] `| `tests/unit/test_geoip_extended.py` | 3 | MOCK |`
- L7707 [`MOCK`] `| `tests/unit/test_go_tester_streaming.py` | 20 | MOCK |`
- L7708 [`MOCK`] `| `tests/unit/test_honeypot.py` | 71 | MOCK |`
- L7709 [`MOCK`] `| `tests/unit/test_init_module.py` | 2 | MOCK |`
- L7710 [`MOCK`] `| `tests/unit/test_output.py` | 4 | MOCK |`
- L7711 [`MOCK`] `| `tests/unit/test_output_advanced.py` | 1 | MOCK |`
- L7712 [`MOCK`] `| `tests/unit/test_output_full.py` | 13 | MOCK |`
- L7713 [`PLACEHOLDER`] `| `tests/unit/test_output_logic.py` | 1 | PLACEHOLDER |`
- L7714 [`MOCK`] `| `tests/unit/test_parsers_robustness.py` | 1 | MOCK |`
- L7715 [`MOCK`] `| `tests/unit/test_pipeline_coverage.py` | 38 | MOCK |`
- L7716 [`MOCK`] `| `tests/unit/test_pipeline_deep.py` | 38 | MOCK |`
- L7717 [`MOCK`] `| `tests/unit/test_pipeline_extended.py` | 64 | MOCK |`
- L7718 [`MOCK`] `| `tests/unit/test_pipeline_orchestration.py` | 29 | MOCK |`
- L7719 [`MOCK`] `| `tests/unit/test_pipeline_stages.py` | 125 | MOCK |`
- L7720 [`MOCK`] `| `tests/unit/test_producer_quality_accounting.py` | 2 | MOCK |`
- L7721 [`MOCK`] `| `tests/unit/test_proxy_history_extended.py` | 6 | MOCK |`
- L7722 [`MOCK`] `| `tests/unit/test_scheduler.py` | 4 | MOCK |`
- L7723 [`MOCK`] `| `tests/unit/test_security.py` | 26 | MOCK |`
- L7724 [`ASSUMING`] `| `tests/unit/test_security_validator.py` | 1 | ASSUMING |`
- L7725 [`MOCK`] `| `tests/unit/test_security_validator_extra.py` | 5 | MOCK |`
- L7726 [`ASSUMING`] `| `tests/unit/test_security_validator_full.py` | 1 | ASSUMING |`
- L7727 [`MOCK`] `| `tests/unit/test_server.py` | 34 | MOCK |`
- L7728 [`MOCK`] `| `tests/unit/test_server_new.py` | 1 | MOCK |`
- L7729 [`MOCK`] `| `tests/unit/test_singbox_binary_resolution.py` | 1 | MOCK |`
- L7730 [`MOCK`] `| `tests/unit/test_sorter.py` | 20 | MOCK |`
- L7731 [`MOCK`] `| `tests/unit/test_ss_ffi.py` | 47 | MOCK |`
- L7732 [`MOCK`] `| `tests/unit/test_utils.py` | 1 | MOCK |`
- L7733 [`MOCK`] `| `tests/unit/test_utils_extended.py` | 3 | MOCK |`
- L7734 [`PLACEHOLDER`] `| `tests/unit/test_validate_frontend_placeholders.py` | 12 | PLACEHOLDER |`
- L7735 [`PLACEHOLDER`] `| `tests/unit/test_validate_workflows.py` | 1 | PLACEHOLDER |`
- L7736 [`MOCK`] `| `tests/unit/test_washer.py` | 6 | MOCK |`
- L7737 [`MOCK`] `| `tests/unit/tools/test_dns_scanner.py` | 3 | MOCK |`
- L7738 [`MOCK`] `| `tests/unit/utils/test_cert.py` | 8 | MOCK |`
- L7743 [`PLACEHOLDER`] `- L136 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output``
- L7746 [`ASSUMING`] `- L148 [`ASSUMING`] `*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.``
- L7749 [`PLACEHOLDER`] `- L36 [`PLACEHOLDER`] `- **Frontend placeholder deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to inject `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets before upload.``
- L7750 [`PLACEHOLDER`] `- L37 [`PLACEHOLDER`] `- **Frontend placeholder tests/workflow parity**: Added tests for placeholder detection/injection and extended workflow validation so `deploy-pages.yml` cannot drop the frontend placeholder guard or secret env wiring silently.``
- L7751 [`PLACEHOLDER`] `- L68 [`PLACEHOLDER`] `- **Validation run**: `scripts/validate_workflows.py` passes for 6 workflow files; `scripts/validate_versions.py` passes; focused remediation tests pass with 127 tests across server, fetcher, output, deploy-contract, analytics, merge, docs hygiene, frontend-placeholder, lab-strategy, concurrency-contract, producer-quality, logging-sanitization, workflow, and version validation.``
- L7752 [`TODO`] `- L191 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts``
- L7755 [`PLACEHOLDER`] `- L11 [`PLACEHOLDER`] `**Resolution:** Updated `main.yml` to set `continue-on-error: true` for the `frontend-wasm` download step in the merge job. Ensure `scripts/build_wasm.sh` creates the necessary directories and placeholder dummy files gracefully if compilation fails.``
- L7758 [`PLACEHOLDER`] `- L20 [`PLACEHOLDER`] `5. The deployed frontend path bypasses the Vite build output and serves raw static files with placeholder key material.``
- L7759 [`PLACEHOLDER`] `- L57 [`PLACEHOLDER`] `- frontend external dependencies, placeholders, and `innerHTML```
- L7760 [`PLACEHOLDER`] `- L378 [`PLACEHOLDER`] `- The frontend renders the degraded state without placeholders.``
- L7761 [`PLACEHOLDER`] `- L679 [`PLACEHOLDER`] `Status: partially remediated on 2026-05-04. Pages deploy now injects and validates frontend placeholders; the larger Vite-vs-raw-frontend production-build decision remains open.``
- L7762 [`PLACEHOLDER`] `- L683 [`PLACEHOLDER`] `- `frontend/assets/js/constants.js` contains placeholder `PUBLIC_KEY`.``
- L7763 [`PLACEHOLDER`] `- L684 [`PLACEHOLDER`] `- `frontend/assets/js/stego.js` contains `PLACEHOLDER_KEY_INJECTED_BY_CI`.``
- L7764 [`PLACEHOLDER`] `- L693 [`PLACEHOLDER`] `- Production Pages likely serves placeholder key material.``
- L7765 [`PLACEHOLDER`] `- L700 [`PLACEHOLDER`] `- Added `scripts/validate_frontend_placeholders.py`.``
- L7766 [`PLACEHOLDER`] `- L701 [`PLACEHOLDER`] `- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.``
- L7767 [`PLACEHOLDER`] `- L702 [`PLACEHOLDER`] `- Pages deploy now passes `CS_PUBLIC_KEY` and `STEGO_KEY` into the frontend placeholder guard step from GitHub secrets.``
- L7768 [`PLACEHOLDER`] `- L705 [`PLACEHOLDER`] `- The validator fails if the public key placeholder marker or stego placeholder remains in the Pages artifact.``
- L7769 [`PLACEHOLDER`] `- L706 [`PLACEHOLDER`] `- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.``
- L7770 [`PLACEHOLDER`] `- L707 [`PLACEHOLDER`] `- Tests cover placeholder detection, env injection, optional non-strict stego handling, and workflow guard retention.``
- L7771 [`PLACEHOLDER`] `- L714 [`PLACEHOLDER`] `4. Fail production build if required public key/stego key placeholders remain.``
- L7772 [`PLACEHOLDER`] `- L716 [`PLACEHOLDER`] `6. Add placeholder leak tests.``
- L7773 [`PLACEHOLDER`] `- L727 [`PLACEHOLDER`] `- Deployed frontend contains no placeholder key strings.``
- L7774 [`PLACEHOLDER`] `- L731 [`PLACEHOLDER`] `- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.``
- L7775 [`PLACEHOLDER`] `- L1183 [`PLACEHOLDER`] `- If the library is present but does not match the placeholder hash, validation fails.``
- L7776 [`TODO`] `- L1258 [`TODO`] `- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.``
- L7777 [`MOCK`] `- L1336 [`MOCK`] `3. Separate test-only mocks from production TODOs.``
- L7778 [`PLACEHOLDER`] `- L1341 [`PLACEHOLDER`] `### P3-4. Zero-byte and placeholder assets remain``
- L7779 [`PLACEHOLDER`] `- L1554 [`PLACEHOLDER`] `- Placeholder key material remains.``
- L7780 [`PLACEHOLDER`] `- L1560 [`PLACEHOLDER`] `- Make frontend local-first, build-driven, no-placeholder, and no-network smoke-tested.``
- L7781 [`PLACEHOLDER`] `- L1813 [`PLACEHOLDER`] `3. Public pages must never show unresolved placeholders.``
- L7782 [`PLACEHOLDER`] `- L1823 [`PLACEHOLDER`] `- placeholder leak tests``
- L7783 [`TODO`] `- L1895 [`TODO`] `- zero TODO/FIXME``
- L7784 [`PLACEHOLDER`] `- L1936 [`PLACEHOLDER`] `4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.``
- L7785 [`PLACEHOLDER`] `- L2112 [`PLACEHOLDER`] `5. Fail build on placeholder keys.``
- L7786 [`PLACEHOLDER`] `- L2125 [`PLACEHOLDER`] `- Delete unused build path, unused scripts, and placeholder config files.``
- L7787 [`PLACEHOLDER`] `- L2194 [`PLACEHOLDER`] `6. Add no-placeholder, no-network frontend, public contract, and security posture tests.``
- L7788 [`PLACEHOLDER`] `- L2239 [`PLACEHOLDER`] `- frontend has no unresolved placeholders.``
- L7789 [`PLACEHOLDER`] `- L2240 [`PLACEHOLDER`] `- no placeholder key material is deployed.``
- L7790 [`PLACEHOLDER`] `- L2279 [`PLACEHOLDER`] `- No placeholder keys.``
- L7791 [`PLACEHOLDER`] `- L2339 [`PLACEHOLDER`] `10. Frontend has no placeholder keys or unresolved template tokens.``
- L7794 [`PLACEHOLDER`] `- L46 [`PLACEHOLDER`] `- Deploy fails if the public-key placeholder or stego placeholder remains in the Pages artifact.``
- L7795 [`PLACEHOLDER`] `- L47 [`PLACEHOLDER`] `- Workflow validation enforces the frontend placeholder guard so it cannot be removed from deploy without breaking validation.``
- L7798 [`PLACEHOLDER`] `- L40 [`PLACEHOLDER`] `- Pages deploy now injects `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets and fails before upload if frontend public-key or stego placeholders remain; workflow validation enforces this guard.``
- L7799 [`PLACEHOLDER`] `- L85 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed``
- L7800 [`PLACEHOLDER`] `- L92 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed``
- L7803 [`ASSUMING`] `- L114 [`ASSUMING`] `*   **ConfigStream Usage:** Some parsers reject input if the "Noise Ratio" (non-printable characters) is too high, assuming it's garbage. Conversely, obfuscation protocols add noise to look like static.``
- L7806 [`XXX`] `- L73 [`XXX`] `*   **Format:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (36 characters with hyphens).``
- L7809 [`XXX`] `- L96 [`XXX`] `*   **WARP+ Key:** Format `xxxxxxxx-xxxxxxxx-xxxxxxxx`. Provides optimized routing (Argo Smart Routing). Optional — free tier is sufficient for circumvention.``
- L7812 [`PLACEHOLDER`] `- L40 [`PLACEHOLDER`] `// Show empty state or placeholder``
- L7813 [`PLACEHOLDER`] `- L161 [`PLACEHOLDER`] `container.innerHTML = '<div class="error-placeholder">Visualization Unavailable (Network Error)</div>';``
- L7814 [`ASSUMING`] `- L776 [`ASSUMING`] `// Assuming all rejection reasons are worth showing if present``
- L7817 [`MOCK`] `- L106 [`MOCK`] `// Audit: Removed random mock data to prevent misleading users.``
- L7820 [`PLACEHOLDER`] `- L29 [`PLACEHOLDER`] `// Validation: Detect placeholder values in production``
- L7821 [`PLACEHOLDER`] `- L43 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder PUBLIC_KEY!");``
- L7822 [`PLACEHOLDER`] `- L48 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder IPNS_KEY!");``
- L7825 [`PLACEHOLDER`] `- L135 [`PLACEHOLDER`] `"byow.url.placeholder": "Paste your Cloudflare Worker URL...",``
- L7826 [`PLACEHOLDER`] `- L136 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Optional: UUID",``
- L7827 [`PLACEHOLDER`] `- L362 [`PLACEHOLDER`] `"byow.url.placeholder": "在此输入 Cloudflare Worker 地址...",``
- L7828 [`PLACEHOLDER`] `- L363 [`PLACEHOLDER`] `"byow.uuid.placeholder": "可选: UUID",``
- L7829 [`PLACEHOLDER`] `- L582 [`PLACEHOLDER`] `"byow.url.placeholder": "آدرس Cloudflare Worker خود را وارد کنید...",``
- L7830 [`PLACEHOLDER`] `- L583 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختیاری: UUID",``
- L7831 [`PLACEHOLDER`] `- L802 [`PLACEHOLDER`] `"byow.url.placeholder": "Вставьте ссылку на ваш Cloudflare Worker...",``
- L7832 [`PLACEHOLDER`] `- L803 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Опционально: UUID",``
- L7833 [`PLACEHOLDER`] `- L1022 [`PLACEHOLDER`] `"byow.url.placeholder": "رابط Cloudflare Worker...",``
- L7834 [`PLACEHOLDER`] `- L1023 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختياري: UUID",``
- L7835 [`PLACEHOLDER`] `- L1187 [`PLACEHOLDER`] `if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {``
- L7836 [`PLACEHOLDER`] `- L1188 [`PLACEHOLDER`] `el.setAttribute('placeholder', translation);``
- L7839 [`XXX`] `- L1425 [`XXX`] `CFG=$(mktemp /tmp/cs-chain-XXXX.json)``
- L7842 [`ASSUMING`] `- L102 [`ASSUMING`] `// Assuming proxies have 'id'``
- L7843 [`PLACEHOLDER`] `- L183 [`PLACEHOLDER`] `// Initialize immediately with defaults to avoid "--" flash or placeholders``
- L7846 [`PLACEHOLDER`] `- L9 [`PLACEHOLDER`] `const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";``
- L7847 [`PLACEHOLDER`] `- L13 [`PLACEHOLDER`] `SECRET_KEY === "PLACEHOLDER_KEY_INJECTED_BY_CI" ||``
- L7850 [`PLACEHOLDER`] `- L42 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {``
- L7851 [`ASSUMING`] `- L49 [`ASSUMING`] `// Assuming Base64 SPKI from constants.js example``
- L7852 [`PLACEHOLDER`] `- L96 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {``
- L7855 [`MOCK`] `- L9 [`MOCK`] `// Mock status check``
- L7858 [`PLACEHOLDER`] `- L515 [`PLACEHOLDER`] `placeholder="your-worker.username.workers.dev"``
- L7861 [`PLACEHOLDER`] `- L129 [`PLACEHOLDER`] `warp:'<div class="row"><div><label>Clean IP</label><input data-f="ip" value="162.159.192.1"></div><div><label>Port</label><input data-f="port" type="number" value="2408"></div></div><div><label>WARP+ Key (optional)</label><input data-f="key" placeholder="Leave blank for free"></div>',``
- L7864 [`PLACEHOLDER`] `- L573 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="localProxyAddr" placeholder="127.0.0.1:1080">``
- L7865 [`PLACEHOLDER`] `- L584 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="proxyUri" placeholder="vless://uuid@server:443?type=ws&security=tls&sni=example.com#MyProxy"></textarea>``
- L7866 [`PLACEHOLDER`] `- L628 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="manualCleanIps" placeholder="162.159.192.1:2408&#10;188.114.98.224:854"></textarea>``
- L7867 [`PLACEHOLDER`] `- L710 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warpKeyInput" placeholder="Leave blank for free tier">``
- L7868 [`XXX`] `- L711 [`XXX`] `<div class="hint">WARP+ key for better speed. Format: xxxxxxxx-xxxxxxxx-xxxxxxxx</div>``
- L7869 [`PLACEHOLDER`] `- L717 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2CleanIp" placeholder="162.159.192.1:2408">``
- L7870 [`PLACEHOLDER`] `- L722 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2Key" placeholder="Leave blank for free tier">``
- L7871 [`PLACEHOLDER`] `- L732 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragSize" value="10-30" placeholder="10-30">``
- L7872 [`PLACEHOLDER`] `- L737 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragDelay" value="5-10" placeholder="5-10">``
- L7873 [`PLACEHOLDER`] `- L789 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="workerUrl" placeholder="https://my-worker.username.workers.dev">``
- L7874 [`PLACEHOLDER`] `- L814 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="1" placeholder="127.0.0.1:1080 or vless://...">``
- L7875 [`PLACEHOLDER`] `- L836 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="2" placeholder="10.0.0.50:3128 or trojan://...">``
- L7876 [`PLACEHOLDER`] `- L857 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="3" placeholder="162.159.192.1:2408 or vmess://...">``
- L7877 [`PLACEHOLDER`] `- L878 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="4" placeholder="ss://... or socks5://...">``
- L7878 [`PLACEHOLDER`] `- L892 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="customOutboundsJson" placeholder='[{"type":"wireguard","tag":"warp-out","server":"162.159.192.1",...}]' style="min-height:160px;"></textarea>``
- L7881 [`PLACEHOLDER`] `- L140 [`PLACEHOLDER`] `<input type="text" id="worker-url" data-i18n="byow.url.placeholder" placeholder="Paste Worker URL..." class="input-modern">``
- L7882 [`PLACEHOLDER`] `- L141 [`PLACEHOLDER`] `<input type="text" id="worker-uuid" data-i18n="byow.uuid.placeholder" placeholder="UUID (Optional)" class="input-modern input-short">``
- L7883 [`PLACEHOLDER`] `- L154 [`PLACEHOLDER`] `<input type="text" id="searchInput" data-i18n="filters.search" placeholder="e.g., fastest US vmess, or Germany < 100ms" aria-label="Search proxies">``
- L7884 [`PLACEHOLDER`] `- L188 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMin" placeholder="Min" aria-label="Minimum latency">``
- L7885 [`PLACEHOLDER`] `- L190 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMax" placeholder="Max" aria-label="Maximum latency">``
- L7888 [`ASSUMING`] `- L42 [`ASSUMING`] `// Assuming prefix "configstream-v" from cache-config.js logic``
- L7891 [`TODO`] `- L3 [`TODO`] `"""Generate a repository debt matrix from TODO/FIXME-style markers."""``
- L7892 [`TODO`] `- L16 [`TODO`] `PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"``
- L7893 [`FIXME`] `- L160 [`FIXME`] `"- `FIXME` / `XXX`: fix inline before release freeze.",``
- L7894 [`TODO`] `- L161 [`TODO`] `"- `TODO`: create issue with owner + milestone.",``
- L7895 [`MOCK`] `- L162 [`MOCK`] `"- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.",``
- L7896 [`PLACEHOLDER`] `- L163 [`PLACEHOLDER`] `"- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.",``
- L7899 [`PLACEHOLDER`] `- L94 [`PLACEHOLDER`] `"tests/unit/test_validate_frontend_placeholders.py",``
- L7901 [`PLACEHOLDER`] `##### `scripts/validate_frontend_placeholders.py``
- L7902 [`PLACEHOLDER`] `- L4 [`PLACEHOLDER`] `This guard keeps deploy artifacts from silently shipping placeholder verification``
- L7903 [`PLACEHOLDER`] `- L18 [`PLACEHOLDER`] `PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")``
- L7904 [`PLACEHOLDER`] `- L19 [`PLACEHOLDER`] `STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"``
- L7905 [`PLACEHOLDER`] `- L68 [`PLACEHOLDER`] `def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:``
- L7906 [`PLACEHOLDER`] `- L77 [`PLACEHOLDER`] `if any(marker in constants for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):``
- L7907 [`PLACEHOLDER`] `- L79 [`PLACEHOLDER`] `"Frontend PUBLIC_KEY placeholder remains in assets/js/constants.js"``
- L7908 [`PLACEHOLDER`] `- L87 [`PLACEHOLDER`] `if STEGO_KEY_PLACEHOLDER in stego:``
- L7909 [`PLACEHOLDER`] `- L89 [`PLACEHOLDER`] `"Frontend STEGO_KEY placeholder remains in assets/js/stego.js"``
- L7910 [`PLACEHOLDER`] `- L120 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(root, strict=bool(args.strict))``
- L7911 [`PLACEHOLDER`] `- L126 [`PLACEHOLDER`] `print("OK: frontend production placeholders validated.")``
- L7914 [`PLACEHOLDER`] `- L46 [`PLACEHOLDER`] `def _deploy_pages_has_frontend_placeholder_guard(path: Path) -> bool:``
- L7915 [`PLACEHOLDER`] `- L52 [`PLACEHOLDER`] `"scripts/validate_frontend_placeholders.py --inject-env --strict output"``
- L7916 [`PLACEHOLDER`] `- L108 [`PLACEHOLDER`] `and not _deploy_pages_has_frontend_placeholder_guard(path)``
- L7917 [`PLACEHOLDER`] `- L111 [`PLACEHOLDER`] `f"{path}: missing frontend placeholder injection/validation guard"``
- L7920 [`XXX`] `- L10 [`XXX`] `wireguard://UJckB8h6r2P6xxx8UEspxw8r3YkpzBEbjxol3jeoqEw%3D@188.114.97.82:5956?address=172.16.0.2/32, 2606:4700:110:846c:e510:bfa1:ea9f:5247/128&publickey=bmXOC%2BF1FxEMF9dyiK2H5%2F1SUtzH0JuVo51h2wPfgyo%3D&reserved=61%2C41%2C250#Tel= @arshiacomplus wire``
- L7923 [`MOCK`] `- L193 [`MOCK`] `# However, the test 'test_failure_mode_anomaly_db_crash' explicitly mocks this method``
- L7924 [`MOCK`] `- L194 [`MOCK`] `# to raise RuntimeError. If the real method catches it, the test mock is bypassed if we use spy.``
- L7927 [`PLACEHOLDER`] `- L128 [`PLACEHOLDER`] `"ws",  # Test fixtures / transport placeholders``
- L7930 [`PLACEHOLDER`] `- L12 [`PLACEHOLDER`] `a minimal placeholder is encoded so output files are always ≥ 1 byte.``
- L7933 [`MOCK`] `- L97 [`MOCK`] `# Fallback for mock storage``
- L7936 [`MOCK`] `- L187 [`MOCK`] `)  # Fallback if library returns raw float (unlikely for geopy but good for mocks)``
- L7939 [`PLACEHOLDER`] `- L354 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns_to_use))``
- L7940 [`PLACEHOLDER`] `- L376 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec``
- L7941 [`PLACEHOLDER`] `- L384 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec``
- L7942 [`PLACEHOLDER`] `- L396 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(cols_no_id))``
- L7943 [`PLACEHOLDER`] `- L403 [`PLACEHOLDER`] `f"INSERT INTO source_runs ({','.join(cols_no_id)}) VALUES ({placeholders})",  # nosec``
- L7944 [`PLACEHOLDER`] `- L419 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns))``
- L7945 [`PLACEHOLDER`] `- L422 [`PLACEHOLDER`] `f"INSERT INTO proxy_history VALUES ({placeholders})",  # nosec``
- L7948 [`MOCK`] `- L6 [`MOCK`] `# Import urlparse directly to allow mocking in tests``
- L7949 [`MOCK`] `- L153 [`MOCK`] `Internal check for address safety. Used by tests to mock safety checks.``
- L7950 [`MOCK`] `- L177 [`MOCK`] `# Use internal check (to allow mocking by tests)``
- L7951 [`MOCK`] `- L279 [`MOCK`] `# Use SecurityValidator.validate_proxy_config to allow mocking on the class``
- L7954 [`MOCK`] `- L63 [`MOCK`] `"""Mock IP blocklist for testing."""``
- L7957 [`TODO`] `- L130 [`TODO`] `barCharTodo=" "``
- L7958 [`TODO`] `- L140 [`TODO`] `# The number of done and todo characters``
- L7959 [`TODO`] `- L142 [`TODO`] `todo=$(bc <<< "scale=0; $barSize - $done")``
- L7960 [`TODO`] `- L143 [`TODO`] `# build the done and todo sub-bars``
- L7961 [`TODO`] `- L145 [`TODO`] `todoSubBar=$(printf "%${todo}s" | tr " " "${barCharTodo} - 1") # 1 for barSplitter``
- L7962 [`TODO`] `- L146 [`TODO`] `spacesSubBar=$(printf "%${todo}s" | tr " " " ")``
- L7963 [`TODO`] `- L149 [`TODO`] `progressBar="| Progress bar of main IPs: [${doneSubBar}${barSplitter}${todoSubBar}] ${percent}%${spacesSubBar}" # Some end space for pretty formatting``
- L7966 [`PLACEHOLDER`] `- L722 [`PLACEHOLDER`] `placeholder="Enter path or click Browse",``
- L7967 [`PLACEHOLDER`] `- L734 [`PLACEHOLDER`] `placeholder="e.g., google.com",``
- L7968 [`PLACEHOLDER`] `- L758 [`PLACEHOLDER`] `placeholder="100",``
- L7971 [`MOCK`] `- L12 [`MOCK`] `# Mock quality tracker to reject everything``
- L7972 [`MOCK`] `- L37 [`MOCK`] `# Mock AnomalyDetector to fail on is_safe``
- L7973 [`MOCK`] `- L43 [`MOCK`] `# Mock fetcher to return something``
- L7974 [`MOCK`] `- L58 [`MOCK`] `# Mock GeoIP``
- L7977 [`MOCK`] `- L45 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing``
- L7978 [`MOCK`] `- L107 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing``
- L7979 [`MOCK`] `- L145 [`MOCK`] `# Mock the metadata request data (using canonical field names from v2.0.8)``
- L7980 [`MOCK`] `- L146 [`MOCK`] `mock_data = {``
- L7981 [`MOCK`] `- L161 [`MOCK`] `mock_json = json.dumps(mock_data)``
- L7982 [`MOCK`] `- L163 [`MOCK`] `# Inject a mock fetch function that returns our data for statistics endpoints``
- L7983 [`MOCK`] `- L169 [`MOCK`] `// Mock metadata.json (unified stats) and api/stats endpoints``
- L7984 [`MOCK`] `- L174 [`MOCK`] `json: async () => ({mock_json})``
- L7985 [`MOCK`] `- L180 [`MOCK`] `// Mock window.api.fetchStatistics directly if needed``
- L7986 [`MOCK`] `- L182 [`MOCK`] `window.api.fetchStatistics = async () => ({mock_json});``
- L7989 [`MOCK`] `- L28 [`MOCK`] `# 2. Mock external dependencies that might block or fail without network``
- L7990 [`MOCK`] `- L30 [`MOCK`] `# Mock GeoIP to return deterministic data``
- L7991 [`MOCK`] `- L34 [`MOCK`] `# We need self because we are mocking the instance method or class method?``
- L7992 [`MOCK`] `- L35 [`MOCK`] `# Actually standard mock usually mocks the function on the class.``
- L7993 [`MOCK`] `- L49 [`MOCK`] `# Mock Blocklist update``
- L7994 [`MOCK`] `- L55 [`MOCK`] `# Mock Output Generation to avoid filesystem overhead but verify data presence``
- L7995 [`MOCK`] `- L60 [`MOCK`] `# The roadmap says: "assert that parsing, validation, dedup, washing, and GeoIP enrichment all execute without mocks."``
- L7996 [`MOCK`] `- L62 [`MOCK`] `# So we MOCKED GeoIP above. The roadmap allows mocks for things that strictly require network.``
- L7997 [`MOCK`] `- L64 [`MOCK`] `# However, we need to mock `generate_stego_assets` since it requires assets/images which might not exist in tmp env.``
- L7998 [`MOCK`] `- L66 [`MOCK`] `# So we remove the mock that causes AttributeError.``
- L8001 [`MOCK`] `- L16 [`MOCK`] `# Mock SourceQualityTracker to always return False for should_fetch``
- L8002 [`MOCK`] `- L27 [`MOCK`] `# Mock Blocklist update to avoid network``
- L8003 [`MOCK`] `- L64 [`MOCK`] `# Mock SourceQualityTracker to allow fetch``
- L8004 [`MOCK`] `- L70 [`MOCK`] `# Mock network fetch``
- L8005 [`MOCK`] `- L85 [`MOCK`] `# Mock Blocklist``
- L8006 [`MOCK`] `- L91 [`MOCK`] `# Mock GeoIP``
- L8007 [`MOCK`] `- L94 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData``
- L8008 [`MOCK`] `- L126 [`MOCK`] `# Mock fetch/geoip/blocklist as usual``
- L8009 [`MOCK`] `- L148 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData``
- L8012 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8013 [`MOCK`] `- L8 [`MOCK`] `def mock_settings():``
- L8014 [`MOCK`] `- L9 [`MOCK`] `with patch("configstream.testers.manager.AppSettings") as MockSettings:``
- L8015 [`MOCK`] `- L10 [`MOCK`] `settings = MockSettings.return_value``
- L8016 [`MOCK`] `- L16 [`MOCK`] `async def test_singbox_tester_dry_run(mock_settings):``
- L8017 [`MOCK`] `- L29 [`MOCK`] `async def test_singbox_tester_batch_dry_run(mock_settings):``
- L8018 [`MOCK`] `- L47 [`MOCK`] `async def test_singbox_tester_cache_hit(mock_settings):``
- L8019 [`MOCK`] `- L48 [`MOCK`] `cache = MagicMock()``
- L8020 [`MOCK`] `- L72 [`MOCK`] `async def test_singbox_tester_python_direct(mock_settings):``
- L8021 [`MOCK`] `- L74 [`MOCK`] `tester.python_tester.test_direct = AsyncMock(``
- L8022 [`MOCK`] `- L75 [`MOCK`] `return_value=MagicMock(is_working=True)``
- L8023 [`MOCK`] `- L90 [`MOCK`] `async def test_singbox_tester_go_fallback(mock_settings):``
- L8024 [`MOCK`] `- L92 [`MOCK`] `# Mock Go tester as unavailable``
- L8025 [`MOCK`] `- L94 [`MOCK`] `tester.python_tester.test_via_singbox = AsyncMock(``
- L8026 [`MOCK`] `- L95 [`MOCK`] `return_value=MagicMock(is_working=True)``
- L8027 [`MOCK`] `- L103 [`MOCK`] `# Should call python tester via semaphore wrapper (internal details hard to mock perfectly, but we check if result populated)``
- L8028 [`MOCK`] `- L104 [`MOCK`] `# Actually we mocked the method, so let's verify call.``
- L8029 [`MOCK`] `- L111 [`MOCK`] `async def test_singbox_tester_close(mock_settings):``
- L8030 [`MOCK`] `- L113 [`MOCK`] `tester.go_tester.close = AsyncMock()``
- L8033 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8034 [`MOCK`] `- L9 [`MOCK`] `def mock_history():``
- L8035 [`MOCK`] `- L10 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8036 [`MOCK`] `- L11 [`MOCK`] `hist = MockHistory.return_value``
- L8037 [`MOCK`] `- L16 [`MOCK`] `def test_save_json(tmp_path, mock_history):``
- L8038 [`MOCK`] `- L35 [`MOCK`] `def test_save_json_outputs_array_not_single_object(tmp_path, mock_history):``
- L8039 [`MOCK`] `- L50 [`MOCK`] `def test_save_json_compress(tmp_path, mock_history):``
- L8042 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8043 [`MOCK`] `- L8 [`MOCK`] `def mock_settings():``
- L8044 [`MOCK`] `- L9 [`MOCK`] `settings = MagicMock()``
- L8045 [`MOCK`] `- L16 [`MOCK`] `async def test_python_tester_direct_http(mock_settings):``
- L8046 [`MOCK`] `- L17 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8047 [`MOCK`] `- L22 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:``
- L8048 [`MOCK`] `- L23 [`MOCK`] `session = MockSession.return_value``
- L8049 [`MOCK`] `- L26 [`MOCK`] `# Mock successful response``
- L8050 [`MOCK`] `- L27 [`MOCK`] `resp = MagicMock()``
- L8051 [`MOCK`] `- L38 [`MOCK`] `async def test_python_tester_direct_fail(mock_settings):``
- L8052 [`MOCK`] `- L39 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8053 [`MOCK`] `- L47 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:``
- L8054 [`MOCK`] `- L48 [`MOCK`] `session = MockSession.return_value``
- L8055 [`MOCK`] `- L51 [`MOCK`] `# Mock exception for get()``
- L8056 [`MOCK`] `- L75 [`MOCK`] `async def test_python_tester_singbox_missing_factory(mock_settings):``
- L8057 [`MOCK`] `- L77 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8058 [`MOCK`] `- L91 [`MOCK`] `async def test_python_tester_no_config(mock_settings):``
- L8059 [`MOCK`] `- L92 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8062 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8063 [`MOCK`] `- L8 [`MOCK`] `# Mock settings to NOT force scanner``
- L8064 [`MOCK`] `- L9 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8065 [`MOCK`] `- L10 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False``
- L8066 [`MOCK`] `- L18 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8067 [`MOCK`] `- L19 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = True``
- L8068 [`MOCK`] `- L20 [`MOCK`] `MockSettings.return_value.CONFIGSTREAM_TESTER_BIN = "/bin/ls"  # Dummy path``
- L8069 [`MOCK`] `- L30 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8070 [`MOCK`] `- L31 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = False``
- L8071 [`MOCK`] `- L32 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False``
- L8072 [`MOCK`] `- L43 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8073 [`MOCK`] `- L44 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True``
- L8074 [`MOCK`] `- L46 [`MOCK`] `# Mock subprocess``
- L8075 [`MOCK`] `- L47 [`MOCK`] `proc = AsyncMock()``
- L8076 [`MOCK`] `- L66 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8077 [`MOCK`] `- L67 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True``
- L8078 [`MOCK`] `- L69 [`MOCK`] `proc = AsyncMock()``
- L8081 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8082 [`MOCK`] `- L7 [`MOCK`] `def _mock_httpx_response(text: str):``
- L8083 [`MOCK`] `- L9 [`MOCK`] `mock_resp = MagicMock(spec=httpx.Response)``
- L8084 [`MOCK`] `- L10 [`MOCK`] `mock_resp.text = text``
- L8085 [`MOCK`] `- L11 [`MOCK`] `mock_resp.status_code = 200``
- L8086 [`MOCK`] `- L12 [`MOCK`] `mock_resp.raise_for_status = MagicMock()``
- L8087 [`MOCK`] `- L14 [`MOCK`] `mock_client = AsyncMock(spec=httpx.AsyncClient)``
- L8088 [`MOCK`] `- L15 [`MOCK`] `mock_client.get = AsyncMock(return_value=mock_resp)``
- L8089 [`MOCK`] `- L16 [`MOCK`] `mock_client.__aenter__ = AsyncMock(return_value=mock_client)``
- L8090 [`MOCK`] `- L17 [`MOCK`] `mock_client.__aexit__ = AsyncMock(return_value=False)``
- L8091 [`MOCK`] `- L18 [`MOCK`] `return mock_client``
- L8092 [`MOCK`] `- L24 [`MOCK`] `mock_client = _mock_httpx_response("162.159.192.1:2408\ninvalid\n1.1.1.1")``
- L8093 [`MOCK`] `- L33 [`MOCK`] `return_value=mock_client,``
- L8094 [`MOCK`] `- L48 [`MOCK`] `mock_client = _mock_httpx_response(warp_uri)``
- L8095 [`MOCK`] `- L57 [`MOCK`] `return_value=mock_client,``
- L8096 [`MOCK`] `- L87 [`MOCK`] `mock_client = _mock_httpx_response(json_content)``
- L8097 [`MOCK`] `- L96 [`MOCK`] `return_value=mock_client,``
- L8100 [`MOCK`] `- L6 [`MOCK`] `key = "a" * 44  # Mock key``
- L8103 [`MOCK`] `- L22 [`MOCK`] `# Mocking logger is tricky in unit test without fixtures, but we can check return None``
- L8106 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8107 [`MOCK`] `- L12 [`MOCK`] `# Mock psutil not present (fallback to CPU logic)``
- L8108 [`MOCK`] `- L15 [`MOCK`] `# Mock CI detection to False for deterministic test``
- L8109 [`MOCK`] `- L35 [`MOCK`] `mock_psutil = MagicMock()``
- L8110 [`MOCK`] `- L36 [`MOCK`] `mock_mem = MagicMock()``
- L8111 [`MOCK`] `- L38 [`MOCK`] `mock_mem.available = 1024 * 1024 * 1024``
- L8112 [`MOCK`] `- L39 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem``
- L8113 [`MOCK`] `- L41 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):``
- L8114 [`MOCK`] `- L51 [`MOCK`] `mock_psutil = MagicMock()``
- L8115 [`MOCK`] `- L52 [`MOCK`] `mock_mem = MagicMock()``
- L8116 [`MOCK`] `- L53 [`MOCK`] `mock_mem.available = 64 * 1024 * 1024 * 1024  # Huge RAM``
- L8117 [`MOCK`] `- L54 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem``
- L8118 [`MOCK`] `- L56 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):``
- L8121 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch``
- L8122 [`MOCK`] `- L27 [`MOCK`] `# Mock cache file``
- L8125 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8126 [`MOCK`] `- L14 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:``
- L8127 [`MOCK`] `- L17 [`MOCK`] `args, kwargs = mock_basic_config.call_args``
- L8128 [`MOCK`] `- L22 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:``
- L8129 [`MOCK`] `- L25 [`MOCK`] `args, kwargs = mock_basic_config.call_args``
- L8130 [`MOCK`] `- L43 [`MOCK`] `def test_cli_merge_command(mock_pipeline, runner):``
- L8131 [`MOCK`] `- L44 [`MOCK`] `# Mock stats object``
- L8132 [`MOCK`] `- L45 [`MOCK`] `stats_mock = MagicMock()``
- L8133 [`MOCK`] `- L46 [`MOCK`] `# Configure attributes so getattr(stats, key) returns float/int, not MagicMock``
- L8134 [`MOCK`] `- L47 [`MOCK`] `stats_mock.duration = 1.5``
- L8135 [`MOCK`] `- L48 [`MOCK`] `stats_mock.fetched_lines = 100``
- L8136 [`MOCK`] `- L49 [`MOCK`] `stats_mock.tested = 50``
- L8137 [`MOCK`] `- L50 [`MOCK`] `stats_mock.working = 40``
- L8138 [`MOCK`] `- L51 [`MOCK`] `stats_mock.geo_resolved = 30``
- L8139 [`MOCK`] `- L52 [`MOCK`] `stats_mock.to_dict.return_value = {``
- L8140 [`MOCK`] `- L60 [`MOCK`] `# Mock pipeline result``
- L8141 [`MOCK`] `- L61 [`MOCK`] `result_mock = MagicMock()``
- L8142 [`MOCK`] `- L62 [`MOCK`] `result_mock.success = True``
- L8143 [`MOCK`] `- L63 [`MOCK`] `result_mock.stats = stats_mock``
- L8144 [`MOCK`] `- L64 [`MOCK`] `result_mock.error = None``
- L8145 [`MOCK`] `- L66 [`MOCK`] `mock_pipeline.return_value = result_mock``
- L8146 [`MOCK`] `- L67 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)``
- L8147 [`MOCK`] `- L85 [`MOCK`] `def test_cli_merge_command_fail(mock_pipeline, runner):``
- L8148 [`MOCK`] `- L86 [`MOCK`] `result_mock = MagicMock()``
- L8149 [`MOCK`] `- L87 [`MOCK`] `result_mock.success = False``
- L8150 [`MOCK`] `- L88 [`MOCK`] `result_mock.error = "Simulated Failure"``
- L8151 [`MOCK`] `- L90 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)``
- L8154 [`MOCK`] `- L37 [`MOCK`] `# Mock output directory for static files``
- L8157 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8158 [`MOCK`] `- L9 [`MOCK`] `def mock_warp_keys():``
- L8159 [`MOCK`] `- L21 [`MOCK`] `def washer(mock_warp_keys):``
- L8160 [`MOCK`] `- L22 [`MOCK`] `return ProxyWasher(mock_warp_keys)``
- L8161 [`MOCK`] `- L106 [`MOCK`] `# Fill cache up to limit (mock small limit via private usage if possible, or just check type)``
- L8162 [`MOCK`] `- L112 [`MOCK`] `# We can mock seen_chains``
- L8163 [`MOCK`] `- L113 [`MOCK`] `washer.seen_chains = MagicMock()``
- L8166 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import patch``
- L8167 [`MOCK`] `- L46 [`MOCK`] `# Exception case mocking``
- L8170 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8173 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8174 [`MOCK`] `- L11 [`MOCK`] `# Mock readers to ensure we don't hit FS``
- L8175 [`MOCK`] `- L12 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8176 [`MOCK`] `- L13 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8177 [`MOCK`] `- L21 [`MOCK`] `async def test_geoip_lookup_valid_mock():``
- L8178 [`MOCK`] `- L22 [`MOCK`] `"""Test lookup logic with mocked DB response"""``
- L8179 [`MOCK`] `- L25 [`MOCK`] `mock_city = MagicMock()``
- L8180 [`MOCK`] `- L26 [`MOCK`] `mock_city.country.iso_code = "US"``
- L8181 [`MOCK`] `- L27 [`MOCK`] `mock_city.country.name = "United States"``
- L8182 [`MOCK`] `- L28 [`MOCK`] `mock_city.city.name = "New York"``
- L8183 [`MOCK`] `- L29 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8184 [`MOCK`] `- L30 [`MOCK`] `resolver.reader_city.city.return_value = mock_city``
- L8185 [`MOCK`] `- L32 [`MOCK`] `mock_asn = MagicMock()``
- L8186 [`MOCK`] `- L33 [`MOCK`] `mock_asn.autonomous_system_number = 12345``
- L8187 [`MOCK`] `- L34 [`MOCK`] `mock_asn.autonomous_system_organization = "Test Org"``
- L8188 [`MOCK`] `- L35 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8189 [`MOCK`] `- L36 [`MOCK`] `resolver.reader_asn.asn.return_value = mock_asn``
- L8192 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8193 [`MOCK`] `- L36 [`MOCK`] `with patch.object(Path, "stat") as mock_stat:``
- L8194 [`MOCK`] `- L37 [`MOCK`] `mock_stat.return_value.st_size = 101 * 1024 * 1024  # 101MB``
- L8195 [`MOCK`] `- L152 [`MOCK`] `with patch("configstream.history.export.datetime") as mock_dt:``
- L8196 [`MOCK`] `- L153 [`MOCK`] `mock_dt.now.return_value.replace.return_value = mock_dt.now.return_value``
- L8197 [`MOCK`] `- L156 [`MOCK`] `mock_dt.now.return_value = fixed_now``
- L8198 [`MOCK`] `- L157 [`MOCK`] `mock_dt.fromisoformat.side_effect = datetime.fromisoformat``
- L8199 [`MOCK`] `- L158 [`MOCK`] `mock_dt.min = datetime.min``
- L8202 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch``
- L8203 [`MOCK`] `- L75 [`MOCK`] `# Mock converters``
- L8206 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch``
- L8209 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8210 [`MOCK`] `- L156 [`MOCK`] `# Easier to mock``
- L8213 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8214 [`MOCK`] `- L19 [`MOCK`] `mock_response = MagicMock()``
- L8215 [`MOCK`] `- L20 [`MOCK`] `mock_response.status_code = 200``
- L8216 [`MOCK`] `- L23 [`MOCK`] `"httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response``
- L8217 [`MOCK`] `- L36 [`MOCK`] `new_callable=AsyncMock,``
- L8220 [`MOCK`] `- L11 [`MOCK`] `from unittest.mock import patch``
- L8221 [`MOCK`] `- L36 [`MOCK`] `# Mock SUSPICIOUS_DOMAINS to test that logic specifically``
- L8222 [`MOCK`] `- L56 [`MOCK`] `# Mock AppSettings to ensure ALLOW_PRIVATE_IPS is False``
- L8223 [`MOCK`] `- L57 [`MOCK`] `# Also mock SUSPICIOUS_DOMAINS to be empty so we fall through to private IP check``
- L8224 [`MOCK`] `- L59 [`MOCK`] `patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings,``
- L8225 [`MOCK`] `- L62 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = False``
- L8226 [`MOCK`] `- L81 [`MOCK`] `with patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings:``
- L8227 [`MOCK`] `- L82 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = True``
- L8230 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8231 [`MOCK`] `- L17 [`MOCK`] `new_callable=AsyncMock,``
- L8232 [`MOCK`] `- L40 [`MOCK`] `new_callable=AsyncMock,``
- L8233 [`MOCK`] `- L47 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,``
- L8234 [`MOCK`] `- L50 [`MOCK`] `mock_proc = MagicMock()``
- L8235 [`MOCK`] `- L51 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))``
- L8236 [`MOCK`] `- L52 [`MOCK`] `mock_proc.returncode = 0``
- L8237 [`MOCK`] `- L53 [`MOCK`] `mock_exec.return_value = mock_proc``
- L8238 [`MOCK`] `- L64 [`MOCK`] `new_callable=AsyncMock,``
- L8239 [`MOCK`] `- L71 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,``
- L8240 [`MOCK`] `- L74 [`MOCK`] `mock_proc = MagicMock()``
- L8241 [`MOCK`] `- L75 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))``
- L8242 [`MOCK`] `- L76 [`MOCK`] `mock_proc.returncode = 1``
- L8243 [`MOCK`] `- L77 [`MOCK`] `mock_exec.return_value = mock_proc``
- L8246 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8247 [`MOCK`] `- L18 [`MOCK`] `class MockResponse:``
- L8248 [`MOCK`] `- L19 [`MOCK`] `"""Mock aiohttp response."""``
- L8249 [`MOCK`] `- L49 [`MOCK`] `mock_response = MockResponse(200, "not a dict")``
- L8250 [`MOCK`] `- L53 [`MOCK`] `) as mock_session_cls:``
- L8251 [`MOCK`] `- L54 [`MOCK`] `mock_session = MagicMock()``
- L8252 [`MOCK`] `- L55 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8253 [`MOCK`] `- L56 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8254 [`MOCK`] `- L66 [`MOCK`] `mock_response = MockResponse(200, {"data": {}})``
- L8255 [`MOCK`] `- L70 [`MOCK`] `) as mock_session_cls:``
- L8256 [`MOCK`] `- L71 [`MOCK`] `mock_session = MagicMock()``
- L8257 [`MOCK`] `- L72 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8258 [`MOCK`] `- L73 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8259 [`MOCK`] `- L85 [`MOCK`] `) as mock_session_cls:``
- L8260 [`MOCK`] `- L86 [`MOCK`] `mock_session = MagicMock()``
- L8261 [`MOCK`] `- L87 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8262 [`MOCK`] `- L88 [`MOCK`] `mock_session.get.side_effect = Exception("Network error")``
- L8263 [`MOCK`] `- L98 [`MOCK`] `mock_response = MockResponse(``
- L8264 [`MOCK`] `- L104 [`MOCK`] `) as mock_session_cls:``
- L8265 [`MOCK`] `- L105 [`MOCK`] `mock_session = MagicMock()``
- L8266 [`MOCK`] `- L106 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8267 [`MOCK`] `- L107 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8268 [`MOCK`] `- L113 [`MOCK`] `call_args = mock_session.get.call_args``
- L8269 [`MOCK`] `- L135 [`MOCK`] `mock_response = MockResponse(``
- L8270 [`MOCK`] `- L151 [`MOCK`] `) as mock_session_cls:``
- L8271 [`MOCK`] `- L152 [`MOCK`] `mock_session = MagicMock()``
- L8272 [`MOCK`] `- L153 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8273 [`MOCK`] `- L154 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8274 [`MOCK`] `- L164 [`MOCK`] `mock_response = MockResponse(``
- L8275 [`MOCK`] `- L179 [`MOCK`] `) as mock_session_cls:``
- L8276 [`MOCK`] `- L180 [`MOCK`] `mock_session = MagicMock()``
- L8277 [`MOCK`] `- L181 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8278 [`MOCK`] `- L182 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8279 [`MOCK`] `- L200 [`MOCK`] `) as mock_session_cls:``
- L8280 [`MOCK`] `- L205 [`MOCK`] `mock_session_cls.assert_not_called()``
- L8281 [`MOCK`] `- L215 [`MOCK`] `mock_response = MockResponse(``
- L8282 [`MOCK`] `- L230 [`MOCK`] `) as mock_session_cls:``
- L8283 [`MOCK`] `- L231 [`MOCK`] `mock_session = MagicMock()``
- L8284 [`MOCK`] `- L232 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8285 [`MOCK`] `- L233 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8286 [`MOCK`] `- L240 [`MOCK`] `mock_session.get.assert_called_once()``
- L8287 [`MOCK`] `- L258 [`MOCK`] `mock_response = MockResponse(``
- L8288 [`MOCK`] `- L273 [`MOCK`] `) as mock_session_cls:``
- L8289 [`MOCK`] `- L274 [`MOCK`] `mock_session = MagicMock()``
- L8290 [`MOCK`] `- L275 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8291 [`MOCK`] `- L276 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8292 [`MOCK`] `- L289 [`MOCK`] `mock_response = MockResponse(200, ["not", "a", "dict"])``
- L8293 [`MOCK`] `- L293 [`MOCK`] `) as mock_session_cls:``
- L8294 [`MOCK`] `- L294 [`MOCK`] `mock_session = MagicMock()``
- L8295 [`MOCK`] `- L295 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8296 [`MOCK`] `- L296 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8297 [`MOCK`] `- L306 [`MOCK`] `mock_response = MockResponse(429, {})  # Rate limit error``
- L8298 [`MOCK`] `- L310 [`MOCK`] `) as mock_session_cls:``
- L8299 [`MOCK`] `- L311 [`MOCK`] `mock_session = MagicMock()``
- L8300 [`MOCK`] `- L312 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8301 [`MOCK`] `- L313 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8302 [`MOCK`] `- L325 [`MOCK`] `) as mock_session_cls:``
- L8303 [`MOCK`] `- L326 [`MOCK`] `mock_session = MagicMock()``
- L8304 [`MOCK`] `- L327 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8305 [`MOCK`] `- L328 [`MOCK`] `mock_session.get.side_effect = Exception("Network timeout")``
- L8306 [`MOCK`] `- L340 [`MOCK`] `mock_response = MockResponse(``
- L8307 [`MOCK`] `- L355 [`MOCK`] `) as mock_session_cls:``
- L8308 [`MOCK`] `- L356 [`MOCK`] `mock_session = MagicMock()``
- L8309 [`MOCK`] `- L357 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8310 [`MOCK`] `- L358 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8311 [`MOCK`] `- L372 [`MOCK`] `mock_response = MockResponse(200, {"data": {"attributes": {}}})``
- L8312 [`MOCK`] `- L376 [`MOCK`] `) as mock_session_cls:``
- L8313 [`MOCK`] `- L377 [`MOCK`] `mock_session = MagicMock()``
- L8314 [`MOCK`] `- L378 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8315 [`MOCK`] `- L379 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8316 [`MOCK`] `- L403 [`MOCK`] `mock_response = MockResponse(``
- L8317 [`MOCK`] `- L421 [`MOCK`] `) as mock_session_cls:``
- L8318 [`MOCK`] `- L422 [`MOCK`] `mock_session = MagicMock()``
- L8319 [`MOCK`] `- L423 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8320 [`MOCK`] `- L424 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8323 [`MOCK`] `- L9 [`MOCK`] `from unittest.mock import Mock, MagicMock, patch``
- L8324 [`MOCK`] `- L179 [`MOCK`] `) as mock_format:``
- L8325 [`MOCK`] `- L180 [`MOCK`] `mock_format.return_value = "WireGuard chain config"``
- L8326 [`MOCK`] `- L189 [`MOCK`] `proxy = Mock(spec=Proxy)``
- L8327 [`MOCK`] `- L194 [`MOCK`] `# Use MagicMock for details to allow mocking get method``
- L8328 [`MOCK`] `- L195 [`MOCK`] `proxy.details = MagicMock()``
- L8331 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8332 [`MOCK`] `- L91 [`MOCK`] `# We mock write_text``
- L8333 [`MOCK`] `- L109 [`MOCK`] `with patch("configstream.adaptive_timeout.logger") as mock_logger:``
- L8334 [`MOCK`] `- L111 [`MOCK`] `assert mock_logger.debug.called``
- L8337 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8338 [`MOCK`] `- L9 [`MOCK`] `with patch("psutil.virtual_memory") as mock_mem:``
- L8339 [`MOCK`] `- L10 [`MOCK`] `mock_mem.return_value.available = 2 * 1024 * 1024 * 1024  # 2GB``
- L8342 [`MOCK`] `- L12 [`MOCK`] `# Create mock proxies with various latencies``
- L8343 [`MOCK`] `- L17 [`MOCK`] `config="vmess://mock1",``
- L8344 [`MOCK`] `- L29 [`MOCK`] `config="ss://mock2", protocol="ss", address="2.2.2.2", port=443, is_working=True``
- L8345 [`MOCK`] `- L37 [`MOCK`] `config="trojan://mock3",``
- L8346 [`MOCK`] `- L49 [`MOCK`] `config="vless://mock4",``
- L8347 [`MOCK`] `- L61 [`MOCK`] `config="vmess://mock5",``
- L8348 [`MOCK`] `- L71 [`MOCK`] `# Mock pipeline stats object``
- L8351 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8352 [`MOCK`] `- L129 [`MOCK`] `with patch("time.time") as mock_time:``
- L8353 [`MOCK`] `- L131 [`MOCK`] `mock_time.return_value = 1000 + i``
- L8354 [`MOCK`] `- L147 [`MOCK`] `from unittest.mock import MagicMock``
- L8355 [`MOCK`] `- L150 [`MOCK`] `mock_conn = MagicMock()``
- L8356 [`MOCK`] `- L151 [`MOCK`] `# Mock specific sqlite3.Error which is caught by the logic``
- L8357 [`MOCK`] `- L152 [`MOCK`] `mock_conn.execute.side_effect = sqlite3.OperationalError("DB Execution Error")``
- L8358 [`MOCK`] `- L154 [`MOCK`] `detector._conn = mock_conn``
- L8359 [`MOCK`] `- L156 [`MOCK`] `# Also mock reconnection attempt failing``
- L8362 [`MOCK`] `- L26 [`MOCK`] `# We can't easily mock file stats without patching os.stat``
- L8365 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8366 [`MOCK`] `- L153 [`MOCK`] `# but we can mock glob or check logic.``
- L8367 [`MOCK`] `- L155 [`MOCK`] `# If we had a file named "../traversal.db" returned by glob (unlikely normally but possible via mocks)``
- L8368 [`MOCK`] `- L157 [`MOCK`] `with patch.object(Path, "glob") as mock_glob:``
- L8369 [`MOCK`] `- L158 [`MOCK`] `bad_path = MagicMock(spec=Path)``
- L8370 [`MOCK`] `- L163 [`MOCK`] `mock_glob.return_value = [bad_path]``
- L8371 [`MOCK`] `- L180 [`MOCK`] `with patch("sqlite3.connect") as mock_connect:``
- L8372 [`MOCK`] `- L181 [`MOCK`] `mock_connect.side_effect = Exception("Connect Fail")``
- L8375 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8376 [`MOCK`] `- L8 [`MOCK`] `# Mock register_warp_account globally for this module if possible,``
- L8377 [`MOCK`] `- L13 [`MOCK`] `# we need to patch 'configstream.tools.warp.register_warp_account' and ensure it's mocked``
- L8378 [`MOCK`] `- L18 [`MOCK`] `# We should mock `configstream.tools.warp.register_warp_account`.``
- L8379 [`MOCK`] `- L23 [`MOCK`] `update = MagicMock(spec=Update)``
- L8380 [`MOCK`] `- L24 [`MOCK`] `update.effective_chat = MagicMock()``
- L8381 [`MOCK`] `- L26 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8382 [`MOCK`] `- L27 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8383 [`MOCK`] `- L36 [`MOCK`] `update = MagicMock(spec=Update)``
- L8384 [`MOCK`] `- L37 [`MOCK`] `update.effective_chat = MagicMock()``
- L8385 [`MOCK`] `- L39 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8386 [`MOCK`] `- L40 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8387 [`MOCK`] `- L42 [`MOCK`] `# We need to mock the module where it is defined, so the local import picks up the mock``
- L8388 [`MOCK`] `- L44 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock``
- L8389 [`MOCK`] `- L45 [`MOCK`] `) as mock_reg:``
- L8390 [`MOCK`] `- L46 [`MOCK`] `mock_reg.return_value = {``
- L8391 [`MOCK`] `- L66 [`MOCK`] `update = MagicMock(spec=Update)``
- L8392 [`MOCK`] `- L67 [`MOCK`] `update.effective_chat = MagicMock()``
- L8393 [`MOCK`] `- L69 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8394 [`MOCK`] `- L70 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8395 [`MOCK`] `- L73 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock``
- L8396 [`MOCK`] `- L74 [`MOCK`] `) as mock_reg:``
- L8397 [`MOCK`] `- L75 [`MOCK`] `mock_reg.side_effect = Exception("Fail")``
- L8398 [`MOCK`] `- L85 [`MOCK`] `update = MagicMock(spec=Update)``
- L8399 [`MOCK`] `- L86 [`MOCK`] `update.effective_chat = MagicMock()``
- L8400 [`MOCK`] `- L88 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8401 [`MOCK`] `- L89 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8402 [`MOCK`] `- L96 [`MOCK`] `# Mock AppSettings to return None for TELEGRAM_BOT_TOKEN``
- L8403 [`MOCK`] `- L103 [`MOCK`] `with patch("configstream.config.AppSettings") as mock_settings:``
- L8404 [`MOCK`] `- L104 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = None``
- L8405 [`MOCK`] `- L105 [`MOCK`] `with patch("configstream.bot_cli.logger") as mock_logger:``
- L8406 [`MOCK`] `- L107 [`MOCK`] `mock_logger.error.assert_called_with("TELEGRAM_BOT_TOKEN not set")``
- L8407 [`MOCK`] `- L112 [`MOCK`] `patch("configstream.config.AppSettings") as mock_settings,``
- L8408 [`MOCK`] `- L113 [`MOCK`] `patch("configstream.bot_cli.ApplicationBuilder") as mock_builder,``
- L8409 [`MOCK`] `- L115 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = "fake_token"``
- L8410 [`MOCK`] `- L117 [`MOCK`] `mock_app = MagicMock()``
- L8411 [`MOCK`] `- L118 [`MOCK`] `mock_builder.return_value.token.return_value.build.return_value = mock_app``
- L8412 [`MOCK`] `- L121 [`MOCK`] `mock_app.run_polling.assert_called_once()``
- L8415 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8416 [`MOCK`] `- L9 [`MOCK`] `def mock_cache():``
- L8417 [`MOCK`] `- L10 [`MOCK`] `cache = MagicMock()``
- L8418 [`MOCK`] `- L11 [`MOCK`] `# Mock get method to return True for some proxies, False for others``
- L8419 [`MOCK`] `- L12 [`MOCK`] `cache.get = MagicMock()``
- L8420 [`MOCK`] `- L13 [`MOCK`] `cache.get_health_score = MagicMock()``
- L8421 [`MOCK`] `- L18 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L8422 [`ASSUMING`] `- L19 [`ASSUMING`] `p.id = id  # Assuming models.Proxy has id or is hashable``
- L8423 [`MOCK`] `- L24 [`MOCK`] `def test_warm_cache(mock_cache):``
- L8424 [`MOCK`] `- L33 [`MOCK`] `mock_cache.get.side_effect = lambda p: p.id in ["p1", "p3", "p4"]``
- L8425 [`MOCK`] `- L45 [`MOCK`] `mock_cache.get_health_score.side_effect = health_score``
- L8426 [`MOCK`] `- L47 [`MOCK`] `result = warm_cache(mock_cache, proxies)``
- L8427 [`MOCK`] `- L60 [`MOCK`] `def test_warm_cache_all_uncached(mock_cache):``
- L8428 [`MOCK`] `- L64 [`MOCK`] `mock_cache.get.return_value = False``
- L8429 [`MOCK`] `- L66 [`MOCK`] `result = warm_cache(mock_cache, proxies)``
- L8432 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8433 [`MOCK`] `- L42 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock``
- L8434 [`MOCK`] `- L43 [`MOCK`] `) as mock_pipeline,``
- L8435 [`MOCK`] `- L46 [`MOCK`] `mock_result = MagicMock()``
- L8436 [`MOCK`] `- L47 [`MOCK`] `mock_result.success = True``
- L8437 [`MOCK`] `- L48 [`MOCK`] `mock_result.stats = {``
- L8438 [`MOCK`] `- L55 [`MOCK`] `mock_pipeline.return_value = mock_result``
- L8439 [`MOCK`] `- L61 [`MOCK`] `mock_pipeline.assert_called_once()``
- L8440 [`MOCK`] `- L69 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock``
- L8441 [`MOCK`] `- L70 [`MOCK`] `) as mock_pipeline,``
- L8442 [`MOCK`] `- L73 [`MOCK`] `mock_result = MagicMock()``
- L8443 [`MOCK`] `- L74 [`MOCK`] `mock_result.success = False``
- L8444 [`MOCK`] `- L75 [`MOCK`] `mock_result.error = "Test Failure"``
- L8445 [`MOCK`] `- L76 [`MOCK`] `mock_pipeline.return_value = mock_result``
- L8446 [`MOCK`] `- L163 [`MOCK`] `"configstream.cli.generate_warp_proxy", new_callable=AsyncMock``
- L8447 [`MOCK`] `- L164 [`MOCK`] `) as mock_gen:``
- L8448 [`MOCK`] `- L165 [`MOCK`] `mock_p = MagicMock()``
- L8449 [`MOCK`] `- L166 [`MOCK`] `mock_p.protocol = "wireguard"``
- L8450 [`MOCK`] `- L167 [`MOCK`] `mock_p.details = {}``
- L8451 [`MOCK`] `- L168 [`MOCK`] `mock_p.config = "conf"``
- L8452 [`MOCK`] `- L169 [`MOCK`] `mock_gen.return_value = mock_p``
- L8453 [`MOCK`] `- L178 [`MOCK`] `with patch("configstream.bot_cli.run_bot") as mock_run:``
- L8454 [`MOCK`] `- L181 [`MOCK`] `mock_run.assert_called_with("FAKE")``
- L8457 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8460 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import AsyncMock``
- L8461 [`MOCK`] `- L60 [`MOCK`] `# Mock semaphore set_limit``
- L8462 [`MOCK`] `- L61 [`MOCK`] `cm.semaphore.set_limit = AsyncMock()``
- L8465 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8466 [`MOCK`] `- L11 [`MOCK`] `def mock_dependencies_fix():``
- L8467 [`MOCK`] `- L14 [`MOCK`] `# Mocks``
- L8468 [`MOCK`] `- L15 [`MOCK`] `tester = MagicMock()``
- L8469 [`MOCK`] `- L17 [`MOCK`] `tester.test = AsyncMock()``
- L8470 [`MOCK`] `- L18 [`MOCK`] `tester.test_batch = AsyncMock()``
- L8471 [`MOCK`] `- L20 [`MOCK`] `washer = MagicMock()``
- L8472 [`MOCK`] `- L22 [`MOCK`] `scheduler = MagicMock()``
- L8473 [`MOCK`] `- L25 [`MOCK`] `test_cache = MagicMock()``
- L8474 [`MOCK`] `- L28 [`MOCK`] `concurrency = MagicMock()``
- L8475 [`MOCK`] `- L29 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()``
- L8476 [`MOCK`] `- L32 [`MOCK`] `concurrency.record = AsyncMock()``
- L8477 [`MOCK`] `- L34 [`MOCK`] `geoip = MagicMock()``
- L8478 [`MOCK`] `- L35 [`MOCK`] `geoip.lookup = AsyncMock(return_value=None)``
- L8479 [`MOCK`] `- L37 [`MOCK`] `tracker = MagicMock()``
- L8480 [`MOCK`] `- L38 [`MOCK`] `tracker.phase.return_value = MagicMock()``
- L8481 [`MOCK`] `- L42 [`MOCK`] `history = MagicMock()``
- L8482 [`MOCK`] `- L43 [`MOCK`] `history.update_history = MagicMock()``
- L8483 [`MOCK`] `- L45 [`MOCK`] `quality = MagicMock()``
- L8484 [`MOCK`] `- L62 [`MOCK`] `async def test_processing_consumer_revival_crash(mock_dependencies_fix):``
- L8485 [`MOCK`] `- L63 [`MOCK`] `deps = mock_dependencies_fix``
- L8486 [`MOCK`] `- L81 [`MOCK`] `# Mock parse_config``
- L8487 [`MOCK`] `- L83 [`MOCK`] `# Mock validate_batch_configs``
- L8490 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8491 [`MOCK`] `- L19 [`MOCK`] `# Mock aiodns.DNSResolver``
- L8492 [`MOCK`] `- L20 [`MOCK`] `mock_dns = MagicMock()``
- L8493 [`MOCK`] `- L21 [`MOCK`] `# Mock query response``
- L8494 [`MOCK`] `- L23 [`MOCK`] `res_example = MagicMock()``
- L8495 [`MOCK`] `- L26 [`MOCK`] `res_google = MagicMock()``
- L8496 [`MOCK`] `- L36 [`MOCK`] `mock_dns.query.side_effect = [future_example, future_google]``
- L8497 [`MOCK`] `- L38 [`MOCK`] `resolver.resolver = mock_dns  # Set the instance attribute directly``
- L8498 [`MOCK`] `- L48 [`MOCK`] `resolver.resolver = MagicMock()``
- L8499 [`MOCK`] `- L57 [`MOCK`] `mock_dns = MagicMock()``
- L8500 [`MOCK`] `- L60 [`MOCK`] `mock_dns.query.return_value = future_fail``
- L8501 [`MOCK`] `- L62 [`MOCK`] `resolver.resolver = mock_dns``
- L8504 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import patch``
- L8505 [`MOCK`] `- L36 [`MOCK`] `def test_emit_error_event(self, mock_logger, tmp_path):``
- L8506 [`MOCK`] `- L41 [`MOCK`] `mock_logger.error.assert_called_once_with("[error] An error occurred")``
- L8507 [`MOCK`] `- L42 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8508 [`MOCK`] `- L43 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8509 [`MOCK`] `- L46 [`MOCK`] `def test_emit_critical_event(self, mock_logger, tmp_path):``
- L8510 [`MOCK`] `- L51 [`MOCK`] `mock_logger.error.assert_called_once_with("[critical] Critical failure")``
- L8511 [`MOCK`] `- L52 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8512 [`MOCK`] `- L53 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8513 [`MOCK`] `- L56 [`MOCK`] `def test_emit_warning_event(self, mock_logger, tmp_path):``
- L8514 [`MOCK`] `- L61 [`MOCK`] `mock_logger.warning.assert_called_once_with("[warning] Warning message")``
- L8515 [`MOCK`] `- L62 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8516 [`MOCK`] `- L63 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8517 [`MOCK`] `- L66 [`MOCK`] `def test_emit_info_event(self, mock_logger, tmp_path):``
- L8518 [`MOCK`] `- L71 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] Information message")``
- L8519 [`MOCK`] `- L72 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8520 [`MOCK`] `- L73 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8521 [`MOCK`] `- L76 [`MOCK`] `def test_emit_default_event_type(self, mock_logger, tmp_path):``
- L8522 [`MOCK`] `- L81 [`MOCK`] `mock_logger.info.assert_called_once_with("[custom] Custom event")``
- L8523 [`MOCK`] `- L82 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8524 [`MOCK`] `- L83 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8525 [`MOCK`] `- L86 [`MOCK`] `def test_emit_success_event(self, mock_logger, tmp_path):``
- L8526 [`MOCK`] `- L91 [`MOCK`] `mock_logger.info.assert_called_once_with("[success] Operation succeeded")``
- L8527 [`MOCK`] `- L94 [`MOCK`] `def test_emit_empty_message(self, mock_logger, tmp_path):``
- L8528 [`MOCK`] `- L99 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] ")``
- L8529 [`MOCK`] `- L102 [`MOCK`] `def test_emit_multiline_message(self, mock_logger, tmp_path):``
- L8530 [`MOCK`] `- L108 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")``
- L8531 [`MOCK`] `- L111 [`MOCK`] `def test_emit_message_with_special_characters(self, mock_logger, tmp_path):``
- L8532 [`MOCK`] `- L119 [`MOCK`] `mock_logger.error.assert_called_once_with(f"[error] {special_message}")``
- L8533 [`MOCK`] `- L122 [`MOCK`] `def test_emit_message_with_unicode(self, mock_logger, tmp_path):``
- L8534 [`MOCK`] `- L128 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {unicode_message}")``
- L8535 [`MOCK`] `- L131 [`MOCK`] `def test_multiple_emit_calls(self, mock_logger, tmp_path):``
- L8536 [`MOCK`] `- L139 [`MOCK`] `assert mock_logger.info.call_count == 1``
- L8537 [`MOCK`] `- L140 [`MOCK`] `assert mock_logger.warning.call_count == 1``
- L8538 [`MOCK`] `- L141 [`MOCK`] `assert mock_logger.error.call_count == 1``
- L8539 [`MOCK`] `- L144 [`MOCK`] `def test_emit_very_long_message(self, mock_logger, tmp_path):``
- L8540 [`MOCK`] `- L150 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8541 [`MOCK`] `- L151 [`MOCK`] `call_args = mock_logger.info.call_args[0][0]``
- L8542 [`MOCK`] `- L155 [`MOCK`] `def test_emit_with_format_strings(self, mock_logger, tmp_path):``
- L8543 [`MOCK`] `- L161 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")``
- L8544 [`MOCK`] `- L164 [`MOCK`] `def test_case_sensitive_event_types(self, mock_logger, tmp_path):``
- L8545 [`MOCK`] `- L170 [`MOCK`] `mock_logger.error.assert_called_once()``
- L8546 [`MOCK`] `- L172 [`MOCK`] `mock_logger.reset_mock()``
- L8547 [`MOCK`] `- L176 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8548 [`MOCK`] `- L177 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8549 [`MOCK`] `- L180 [`MOCK`] `def test_emit_with_numeric_message(self, mock_logger, tmp_path):``
- L8550 [`MOCK`] `- L185 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8551 [`MOCK`] `- L188 [`MOCK`] `def test_emit_rapid_fire(self, mock_logger, tmp_path):``
- L8552 [`MOCK`] `- L195 [`MOCK`] `assert mock_logger.info.call_count == 100``
- L8553 [`MOCK`] `- L198 [`MOCK`] `def test_emit_different_event_types_mixed(self, mock_logger, tmp_path):``
- L8554 [`MOCK`] `- L209 [`MOCK`] `assert mock_logger.info.call_count == 3  # info, info, custom``
- L8555 [`MOCK`] `- L210 [`MOCK`] `assert mock_logger.error.call_count == 2  # error, critical``
- L8556 [`MOCK`] `- L211 [`MOCK`] `assert mock_logger.warning.call_count == 1``
- L8557 [`MOCK`] `- L222 [`MOCK`] `def test_emit_with_none_message_converted_to_string(self, mock_logger, tmp_path):``
- L8558 [`MOCK`] `- L228 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8559 [`MOCK`] `- L231 [`MOCK`] `def test_emit_preserves_message_exactly(self, mock_logger, tmp_path):``
- L8560 [`MOCK`] `- L238 [`MOCK`] `mock_logger.info.assert_called_once_with(expected_call)``
- L8561 [`MOCK`] `- L241 [`MOCK`] `def test_emit_with_json_like_message(self, mock_logger, tmp_path):``
- L8562 [`MOCK`] `- L247 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {json_message}")``
- L8563 [`MOCK`] `- L250 [`MOCK`] `def test_emit_with_sql_like_message(self, mock_logger, tmp_path):``
- L8564 [`MOCK`] `- L256 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {sql_message}")``
- L8565 [`MOCK`] `- L271 [`MOCK`] `def test_emit_with_path_in_message(self, mock_logger, tmp_path):``
- L8566 [`MOCK`] `- L277 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {path_message}")``
- L8567 [`MOCK`] `- L280 [`MOCK`] `def test_emit_with_url_in_message(self, mock_logger, tmp_path):``
- L8568 [`MOCK`] `- L286 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {url_message}")``
- L8571 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock``
- L8572 [`MOCK`] `- L32 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8573 [`MOCK`] `- L40 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8574 [`MOCK`] `- L50 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8575 [`MOCK`] `- L51 [`MOCK`] `mock_response = AsyncMock()``
- L8576 [`MOCK`] `- L52 [`MOCK`] `mock_response.status_code = 200``
- L8577 [`MOCK`] `- L53 [`MOCK`] `mock_response.headers = {}``
- L8578 [`MOCK`] `- L59 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8579 [`MOCK`] `- L62 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8580 [`MOCK`] `- L63 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8581 [`MOCK`] `- L64 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8582 [`MOCK`] `- L75 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8583 [`MOCK`] `- L76 [`MOCK`] `mock_response = AsyncMock()``
- L8584 [`MOCK`] `- L77 [`MOCK`] `mock_response.status_code = 429``
- L8585 [`MOCK`] `- L78 [`MOCK`] `mock_response.headers = {"Retry-After": "0.1"}``
- L8586 [`MOCK`] `- L80 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8587 [`MOCK`] `- L81 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8588 [`MOCK`] `- L82 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8589 [`MOCK`] `- L84 [`MOCK`] `# Should retry. We mock sleep to be fast.``
- L8590 [`MOCK`] `- L85 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8591 [`MOCK`] `- L91 [`MOCK`] `assert mock_sleep.call_count > 0``
- L8592 [`MOCK`] `- L95 [`MOCK`] `async def test_fetch_from_source_follows_safe_redirect(respx_mock):``
- L8593 [`MOCK`] `- L98 [`MOCK`] `respx_mock.get(source).mock(``
- L8594 [`MOCK`] `- L101 [`MOCK`] `respx_mock.get(target).mock(return_value=httpx.Response(200, text="redirected"))``
- L8595 [`MOCK`] `- L111 [`MOCK`] `async def test_fetch_from_source_rejects_private_redirect(respx_mock):``
- L8596 [`MOCK`] `- L113 [`MOCK`] `respx_mock.get(source).mock(``
- L8597 [`MOCK`] `- L128 [`MOCK`] `async def test_fetch_from_source_limits_redirect_depth(respx_mock):``
- L8598 [`MOCK`] `- L132 [`MOCK`] `respx_mock.get(source).mock(``
- L8599 [`MOCK`] `- L150 [`MOCK`] `# If RateLimiter class is gone, we can mock a generic object with the same interface.``
- L8600 [`MOCK`] `- L151 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8601 [`MOCK`] `- L152 [`MOCK`] `rate_limiter = MagicMock()``
- L8602 [`MOCK`] `- L154 [`MOCK`] `rate_limiter.is_allowed = AsyncMock(side_effect=[False, True])``
- L8603 [`MOCK`] `- L155 [`MOCK`] `rate_limiter.get_wait_time = AsyncMock(return_value=0.01)``
- L8604 [`MOCK`] `- L157 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8605 [`MOCK`] `- L159 [`MOCK`] `mock_response = AsyncMock()``
- L8606 [`MOCK`] `- L160 [`MOCK`] `mock_response.status_code = 200``
- L8607 [`MOCK`] `- L161 [`MOCK`] `mock_response.headers = {}``
- L8608 [`MOCK`] `- L166 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8609 [`MOCK`] `- L167 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8610 [`MOCK`] `- L168 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8611 [`MOCK`] `- L169 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8612 [`MOCK`] `- L176 [`MOCK`] `assert mock_sleep.called``
- L8613 [`MOCK`] `- L181 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8614 [`MOCK`] `- L182 [`MOCK`] `breaker_manager = MagicMock()``
- L8615 [`MOCK`] `- L183 [`MOCK`] `breaker = MagicMock()``
- L8616 [`MOCK`] `- L184 [`MOCK`] `breaker.is_open = AsyncMock(return_value=True)``
- L8617 [`MOCK`] `- L185 [`MOCK`] `breaker_manager.get_breaker = AsyncMock(return_value=breaker)``
- L8618 [`MOCK`] `- L203 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8619 [`MOCK`] `- L204 [`MOCK`] `mock_response = AsyncMock()``
- L8620 [`MOCK`] `- L205 [`MOCK`] `mock_response.status_code = 200``
- L8621 [`MOCK`] `- L208 [`MOCK`] `mock_response.headers = {``
- L8622 [`MOCK`] `- L212 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8623 [`MOCK`] `- L213 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8624 [`MOCK`] `- L214 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8625 [`MOCK`] `- L226 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8626 [`MOCK`] `- L227 [`MOCK`] `mock_response = AsyncMock()``
- L8627 [`MOCK`] `- L228 [`MOCK`] `mock_response.status_code = 200``
- L8628 [`MOCK`] `- L229 [`MOCK`] `mock_response.headers = {}``
- L8629 [`MOCK`] `- L237 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8630 [`MOCK`] `- L239 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8631 [`MOCK`] `- L240 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8632 [`MOCK`] `- L241 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8633 [`MOCK`] `- L253 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8634 [`MOCK`] `- L254 [`MOCK`] `mock_response = AsyncMock()``
- L8635 [`MOCK`] `- L255 [`MOCK`] `mock_response.status_code = 200``
- L8636 [`MOCK`] `- L256 [`MOCK`] `mock_response.headers = {}``
- L8637 [`MOCK`] `- L261 [`MOCK`] `mock_response.aiter_bytes = lambda: async_gen()``
- L8638 [`MOCK`] `- L263 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8639 [`MOCK`] `- L264 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8640 [`MOCK`] `- L265 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8641 [`MOCK`] `- L267 [`MOCK`] `tracker = MagicMock()``
- L8642 [`MOCK`] `- L268 [`MOCK`] `tracker.get_timeout = MagicMock(return_value=10.0)``
- L8643 [`MOCK`] `- L269 [`MOCK`] `tracker.record = AsyncMock()``
- L8644 [`MOCK`] `- L270 [`MOCK`] `tracker.get_jitter = AsyncMock(return_value=3.0)  # High jitter``
- L8645 [`MOCK`] `- L273 [`MOCK`] `with patch("configstream.fetcher.logger") as mock_logger:``
- L8646 [`MOCK`] `- L276 [`MOCK`] `assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)``
- L8647 [`MOCK`] `- L281 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8648 [`MOCK`] `- L285 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8649 [`MOCK`] `- L291 [`MOCK`] `assert mock_sleep.call_count > 0``
- L8650 [`MOCK`] `- L296 [`MOCK`] `# Integration test mocking minimal internals``
- L8651 [`MOCK`] `- L298 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:``
- L8652 [`MOCK`] `- L299 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")``
- L8653 [`MOCK`] `- L310 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8654 [`MOCK`] `- L312 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:``
- L8655 [`MOCK`] `- L313 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")``
- L8658 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8659 [`MOCK`] `- L10 [`MOCK`] `# Helper to mock the stream context manager``
- L8660 [`MOCK`] `- L11 [`MOCK`] `class MockStreamResponse:``
- L8661 [`MOCK`] `- L39 [`MOCK`] `# Mock stream instead of get``
- L8662 [`MOCK`] `- L40 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8663 [`MOCK`] `- L41 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "ok")``
- L8664 [`MOCK`] `- L52 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8665 [`MOCK`] `- L53 [`MOCK`] `resp1 = MockStreamResponse(429, "", headers={"Retry-After": "0.1"})``
- L8666 [`MOCK`] `- L54 [`MOCK`] `resp2 = MockStreamResponse(200, "ok")``
- L8667 [`MOCK`] `- L56 [`MOCK`] `mock_stream.side_effect = [resp1, resp2]``
- L8668 [`MOCK`] `- L63 [`MOCK`] `assert mock_stream.call_count == 2``
- L8669 [`MOCK`] `- L94 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8670 [`MOCK`] `- L95 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "streamed_content")``
- L8671 [`MOCK`] `- L104 [`MOCK`] `# We assert mock_stream was called, implying we used the safer path``
- L8672 [`MOCK`] `- L105 [`MOCK`] `mock_stream.assert_called_once()``
- L8673 [`MOCK`] `- L122 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8674 [`MOCK`] `- L123 [`MOCK`] `mock_stream.return_value = MockStreamResponse(404, "")``
- L8675 [`MOCK`] `- L151 [`MOCK`] `assert mock_stream.call_count == 2``
- L8678 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8679 [`MOCK`] `- L15 [`MOCK`] `# by mocking the constant or by testing the behavior with a large response.``
- L8680 [`MOCK`] `- L25 [`MOCK`] `# Create a mock response with Content-Length > MAX_RESPONSE_SIZE``
- L8681 [`MOCK`] `- L26 [`MOCK`] `mock_client = MagicMock(spec=httpx.AsyncClient)``
- L8682 [`MOCK`] `- L27 [`MOCK`] `mock_response = MagicMock()``
- L8683 [`MOCK`] `- L28 [`MOCK`] `mock_response.status_code = 200``
- L8684 [`MOCK`] `- L29 [`MOCK`] `mock_response.headers = {``
- L8685 [`MOCK`] `- L33 [`MOCK`] `# Mock stream context manager``
- L8686 [`MOCK`] `- L34 [`MOCK`] `mock_stream = MagicMock()``
- L8687 [`MOCK`] `- L35 [`MOCK`] `mock_stream.__aenter__.return_value = mock_response``
- L8688 [`MOCK`] `- L36 [`MOCK`] `mock_stream.__aexit__.return_value = None``
- L8689 [`MOCK`] `- L37 [`MOCK`] `mock_client.stream.return_value = mock_stream``
- L8690 [`MOCK`] `- L41 [`MOCK`] `mock_client, "http://example.com", app_settings=app_settings``
- L8693 [`MOCK`] `- L8 [`MOCK`] `async def test_fetch_success(respx_mock):``
- L8694 [`MOCK`] `- L10 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(200, text="content"))``
- L8695 [`MOCK`] `- L20 [`MOCK`] `async def test_fetch_404(respx_mock):``
- L8696 [`MOCK`] `- L22 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(404))``
- L8697 [`MOCK`] `- L33 [`MOCK`] `async def test_fetch_retry_on_error(respx_mock):``
- L8698 [`MOCK`] `- L36 [`MOCK`] `route = respx_mock.get(url)``
- L8699 [`MOCK`] `- L52 [`MOCK`] `async def test_fetch_rate_limit(respx_mock):``
- L8700 [`MOCK`] `- L55 [`MOCK`] `route = respx_mock.get(url)``
- L8703 [`MOCK`] `- L11 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8704 [`MOCK`] `- L12 [`MOCK`] `# Mock 404 response``
- L8705 [`MOCK`] `- L13 [`MOCK`] `respx_mock.get("/missing").mock(return_value=httpx.Response(404))``
- L8706 [`MOCK`] `- L23 [`MOCK`] `assert respx_mock.calls.call_count == 1  # Should only call once``
- L8707 [`MOCK`] `- L29 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8708 [`MOCK`] `- L30 [`MOCK`] `# Mock 410 response``
- L8709 [`MOCK`] `- L31 [`MOCK`] `respx_mock.get("/gone").mock(return_value=httpx.Response(410))``
- L8710 [`MOCK`] `- L40 [`MOCK`] `assert respx_mock.calls.call_count == 1``
- L8711 [`MOCK`] `- L46 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8712 [`MOCK`] `- L47 [`MOCK`] `# Mock 500 response``
- L8713 [`MOCK`] `- L48 [`MOCK`] `respx_mock.get("/error").mock(return_value=httpx.Response(500))``
- L8714 [`MOCK`] `- L59 [`MOCK`] `assert respx_mock.calls.call_count == 2``
- L8717 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8718 [`MOCK`] `- L24 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L8719 [`MOCK`] `- L60 [`MOCK`] `# Since we used MagicMock, identity might be tricky if dedupe makes copies,``
- L8720 [`MOCK`] `- L142 [`MOCK`] `# Mock AppSettings to return seed``
- L8721 [`MOCK`] `- L144 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:``
- L8722 [`MOCK`] `- L145 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"``
- L8723 [`MOCK`] `- L148 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:``
- L8724 [`MOCK`] `- L149 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"``
- L8727 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8728 [`MOCK`] `- L20 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8729 [`MOCK`] `- L24 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8732 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8733 [`MOCK`] `- L12 [`MOCK`] `# Mock process``
- L8734 [`MOCK`] `- L13 [`MOCK`] `proc = MagicMock()``
- L8735 [`MOCK`] `- L15 [`MOCK`] `proc.stdin = MagicMock()``
- L8736 [`MOCK`] `- L16 [`MOCK`] `proc.stdin.write = MagicMock()``
- L8737 [`MOCK`] `- L17 [`MOCK`] `proc.stdin.drain = AsyncMock()``
- L8738 [`MOCK`] `- L18 [`MOCK`] `proc.stdin.close = MagicMock()``
- L8739 [`MOCK`] `- L19 [`MOCK`] `proc.wait = AsyncMock()``
- L8740 [`MOCK`] `- L20 [`MOCK`] `proc.terminate = MagicMock()``
- L8741 [`MOCK`] `- L21 [`MOCK`] `proc.kill = MagicMock()``
- L8742 [`MOCK`] `- L23 [`MOCK`] `# Mock stdout with an AsyncMock readline that returns lines then empty string``
- L8743 [`MOCK`] `- L24 [`MOCK`] `proc.stdout = MagicMock()``
- L8744 [`MOCK`] `- L30 [`MOCK`] `async def mock_readline():``
- L8745 [`MOCK`] `- L33 [`MOCK`] `proc.stdout.readline = mock_readline``
- L8746 [`MOCK`] `- L35 [`MOCK`] `proc.stderr = MagicMock()``
- L8747 [`MOCK`] `- L37 [`MOCK`] `proc.stderr.readline = AsyncMock(return_value=b"")  # No logs``
- L8748 [`MOCK`] `- L39 [`MOCK`] `with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):``
- L8749 [`MOCK`] `- L43 [`MOCK`] `# Mock self_test to succeed since we are mocking process anyway``
- L8750 [`MOCK`] `- L44 [`MOCK`] `with patch.object(GoBatchTester, "self_test", new=AsyncMock(return_value=True)):``
- L8751 [`MOCK`] `- L80 [`MOCK`] `print(f"Error in mock write: {e}")``
- L8754 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, AsyncMock``
- L8755 [`MOCK`] `- L10 [`MOCK`] `# Mock VirusTotal to return safe``
- L8756 [`MOCK`] `- L12 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8757 [`MOCK`] `- L13 [`MOCK`] `) as mock_vt:``
- L8758 [`MOCK`] `- L14 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8759 [`MOCK`] `- L19 [`MOCK`] `mock_vt.assert_called_once_with("1.1.1.1")``
- L8760 [`MOCK`] `- L24 [`MOCK`] `"""Verify passive detection works via VirusTotal mock."""``
- L8761 [`MOCK`] `- L26 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8762 [`MOCK`] `- L27 [`MOCK`] `) as mock_vt:``
- L8763 [`MOCK`] `- L28 [`MOCK`] `mock_vt.return_value = {"malicious": 5}``
- L8764 [`MOCK`] `- L38 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8765 [`MOCK`] `- L39 [`MOCK`] `) as mock_vt:``
- L8766 [`MOCK`] `- L40 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8767 [`MOCK`] `- L44 [`MOCK`] `mock_vt.assert_called_once_with("8.8.8.8")``
- L8768 [`MOCK`] `- L51 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8769 [`MOCK`] `- L52 [`MOCK`] `) as mock_vt:``
- L8770 [`MOCK`] `- L53 [`MOCK`] `mock_vt.return_value = {"malicious": 100}``
- L8771 [`MOCK`] `- L63 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8772 [`MOCK`] `- L64 [`MOCK`] `) as mock_vt:``
- L8773 [`MOCK`] `- L65 [`MOCK`] `mock_vt.return_value = {"malicious": 1}``
- L8774 [`MOCK`] `- L75 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8775 [`MOCK`] `- L76 [`MOCK`] `) as mock_vt:``
- L8776 [`MOCK`] `- L77 [`MOCK`] `mock_vt.return_value = {}``
- L8777 [`MOCK`] `- L88 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8778 [`MOCK`] `- L89 [`MOCK`] `) as mock_vt:``
- L8779 [`MOCK`] `- L90 [`MOCK`] `mock_vt.side_effect = Exception("API Error")``
- L8780 [`MOCK`] `- L101 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8781 [`MOCK`] `- L102 [`MOCK`] `) as mock_vt:``
- L8782 [`MOCK`] `- L103 [`MOCK`] `mock_vt.side_effect = TimeoutError("Request timed out")``
- L8783 [`MOCK`] `- L113 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8784 [`MOCK`] `- L114 [`MOCK`] `) as mock_vt:``
- L8785 [`MOCK`] `- L115 [`MOCK`] `mock_vt.side_effect = ConnectionError("Network unreachable")``
- L8786 [`MOCK`] `- L125 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8787 [`MOCK`] `- L126 [`MOCK`] `) as mock_vt:``
- L8788 [`MOCK`] `- L127 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8789 [`MOCK`] `- L131 [`MOCK`] `mock_vt.assert_called_once_with("2001:4860:4860::8888")``
- L8790 [`MOCK`] `- L138 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8791 [`MOCK`] `- L139 [`MOCK`] `) as mock_vt:``
- L8792 [`MOCK`] `- L140 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8793 [`MOCK`] `- L144 [`MOCK`] `mock_vt.assert_called_once_with("example.com")``
- L8794 [`MOCK`] `- L151 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8795 [`MOCK`] `- L152 [`MOCK`] `) as mock_vt:``
- L8796 [`MOCK`] `- L153 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8797 [`MOCK`] `- L163 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8798 [`MOCK`] `- L164 [`MOCK`] `) as mock_vt:``
- L8799 [`MOCK`] `- L165 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8800 [`MOCK`] `- L175 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8801 [`MOCK`] `- L176 [`MOCK`] `) as mock_vt:``
- L8802 [`MOCK`] `- L177 [`MOCK`] `mock_vt.return_value = {"malicious": -1}``
- L8803 [`MOCK`] `- L188 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8804 [`MOCK`] `- L189 [`MOCK`] `) as mock_vt:``
- L8805 [`MOCK`] `- L190 [`MOCK`] `mock_vt.return_value = None``
- L8806 [`MOCK`] `- L206 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8807 [`MOCK`] `- L207 [`MOCK`] `) as mock_vt:``
- L8808 [`MOCK`] `- L208 [`MOCK`] `mock_vt.return_value = "error"``
- L8809 [`MOCK`] `- L219 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8810 [`MOCK`] `- L220 [`MOCK`] `) as mock_vt:``
- L8811 [`MOCK`] `- L221 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8812 [`MOCK`] `- L225 [`MOCK`] `mock_vt.assert_called_once_with("")``
- L8813 [`MOCK`] `- L232 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8814 [`MOCK`] `- L233 [`MOCK`] `) as mock_vt:``
- L8815 [`MOCK`] `- L234 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:``
- L8816 [`MOCK`] `- L235 [`MOCK`] `mock_vt.return_value = {"malicious": 3}``
- L8817 [`MOCK`] `- L241 [`MOCK`] `mock_logger.warning.assert_called_once()``
- L8818 [`MOCK`] `- L242 [`MOCK`] `call_args = str(mock_logger.warning.call_args)``
- L8819 [`MOCK`] `- L250 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8820 [`MOCK`] `- L251 [`MOCK`] `) as mock_vt:``
- L8821 [`MOCK`] `- L252 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:``
- L8822 [`MOCK`] `- L253 [`MOCK`] `mock_vt.side_effect = ValueError("Invalid IP")``
- L8823 [`MOCK`] `- L259 [`MOCK`] `mock_logger.error.assert_called_once()``
- L8824 [`MOCK`] `- L260 [`MOCK`] `call_args = str(mock_logger.error.call_args)``
- L8827 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8828 [`MOCK`] `- L154 [`MOCK`] `# Verify set_event_loop_policy was called (might have been called before mock)``
- L8831 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock``
- L8832 [`MOCK`] `- L43 [`MOCK`] `def mock_storage():``
- L8833 [`MOCK`] `- L44 [`MOCK`] `return MagicMock(spec=QualityStorage)``
- L8834 [`MOCK`] `- L58 [`MOCK`] `def test_metadata_generation(tmp_path, sample_proxies, mock_storage):``
- L8837 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8840 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8841 [`MOCK`] `- L48 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8842 [`MOCK`] `- L49 [`MOCK`] `MockHistory.return_value.get_history.return_value = []``
- L8843 [`MOCK`] `- L62 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8844 [`MOCK`] `- L63 [`MOCK`] `MockHistory.return_value.get_history.return_value = []``
- L8845 [`MOCK`] `- L105 [`MOCK`] `patch("configstream.generators.singbox.to_singbox_outbound") as mock_conv,``
- L8846 [`MOCK`] `- L109 [`MOCK`] `mock_conv.return_value = {"type": "vless", "tag": "vless-out"}``
- L8847 [`MOCK`] `- L131 [`MOCK`] `patch("configstream.output_logic.ProxyWasher") as MockWasher,``
- L8848 [`MOCK`] `- L140 [`MOCK`] `patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory,``
- L8849 [`MOCK`] `- L141 [`MOCK`] `):  # Mock history to return serializable data``
- L8850 [`MOCK`] `- L143 [`MOCK`] `# Configure mock history to return empty list (serializable)``
- L8851 [`MOCK`] `- L144 [`MOCK`] `history_instance = MockHistory.return_value``
- L8852 [`MOCK`] `- L147 [`MOCK`] `MockWasher.return_value.wash_batch.return_value = ([], set(), {})``
- L8855 [`PLACEHOLDER`] `- L244 [`PLACEHOLDER`] `config="revived://placeholder",``
- L8858 [`MOCK`] `- L246 [`MOCK`] `from unittest.mock import patch``
- L8861 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import AsyncMock, patch, MagicMock``
- L8862 [`MOCK`] `- L12 [`MOCK`] `def mock_work_queue():``
- L8863 [`MOCK`] `- L18 [`MOCK`] `def mock_tester():``
- L8864 [`MOCK`] `- L19 [`MOCK`] `tester = MagicMock(spec=SingBoxTester)``
- L8865 [`MOCK`] `- L20 [`MOCK`] `tester.go_tester = MagicMock()``
- L8866 [`MOCK`] `- L22 [`MOCK`] `tester.test = AsyncMock(``
- L8867 [`MOCK`] `- L36 [`MOCK`] `def mock_quality_tracker():``
- L8868 [`MOCK`] `- L37 [`MOCK`] `tracker = MagicMock()``
- L8869 [`MOCK`] `- L38 [`MOCK`] `tracker.should_fetch = MagicMock(return_value=True)``
- L8870 [`MOCK`] `- L43 [`MOCK`] `def mock_concurrency():``
- L8871 [`MOCK`] `- L44 [`MOCK`] `cm = MagicMock()``
- L8872 [`MOCK`] `- L45 [`MOCK`] `cm.get_semaphore = MagicMock(return_value=AsyncMock())``
- L8873 [`MOCK`] `- L46 [`MOCK`] `cm.get_semaphore.return_value.__aenter__ = AsyncMock()``
- L8874 [`MOCK`] `- L47 [`MOCK`] `cm.get_semaphore.return_value.__aexit__ = AsyncMock()``
- L8875 [`MOCK`] `- L48 [`MOCK`] `cm.start_tuner = MagicMock()``
- L8876 [`MOCK`] `- L49 [`MOCK`] `cm.stop_tuner = AsyncMock()``
- L8877 [`MOCK`] `- L50 [`MOCK`] `cm.record = AsyncMock()``
- L8878 [`MOCK`] `- L56 [`MOCK`] `mock_work_queue, mock_tester, mock_quality_tracker, mock_concurrency``
- L8879 [`MOCK`] `- L62 [`MOCK`] `# Mock dependencies``
- L8880 [`MOCK`] `- L63 [`MOCK`] `scheduler = MagicMock()``
- L8881 [`MOCK`] `- L64 [`MOCK`] `scheduler.should_retest = MagicMock(return_value=True)``
- L8882 [`MOCK`] `- L66 [`MOCK`] `test_cache = MagicMock()``
- L8883 [`MOCK`] `- L67 [`MOCK`] `test_cache.get = MagicMock(return_value=None)``
- L8884 [`MOCK`] `- L69 [`MOCK`] `geoip = MagicMock()``
- L8885 [`MOCK`] `- L70 [`MOCK`] `geoip.lookup = AsyncMock(``
- L8886 [`MOCK`] `- L71 [`MOCK`] `return_value=MagicMock(``
- L8887 [`MOCK`] `- L76 [`MOCK`] `tracker = MagicMock()``
- L8888 [`MOCK`] `- L77 [`MOCK`] `tracker.phase = MagicMock(``
- L8889 [`MOCK`] `- L78 [`MOCK`] `return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())``
- L8890 [`MOCK`] `- L82 [`MOCK`] `raw_lines = ["vmess://eyJaddfqwefqwe..."]  # Mock line``
- L8891 [`MOCK`] `- L84 [`MOCK`] `await mock_work_queue.put((source, raw_lines))``
- L8892 [`MOCK`] `- L85 [`MOCK`] `await mock_work_queue.put(None)  # Signal end``
- L8893 [`MOCK`] `- L87 [`MOCK`] `# Mock parse_config to return a proxy``
- L8894 [`MOCK`] `- L111 [`MOCK`] `mock_work_queue,``
- L8895 [`MOCK`] `- L115 [`MOCK`] `mock_tester,``
- L8896 [`MOCK`] `- L118 [`MOCK`] `mock_concurrency,``
- L8897 [`MOCK`] `- L122 [`MOCK`] `mock_quality_tracker,``
- L8898 [`MOCK`] `- L123 [`MOCK`] `MagicMock(),  # history``
- L8901 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8902 [`MOCK`] `- L26 [`MOCK`] `# Mocks``
- L8903 [`MOCK`] `- L27 [`MOCK`] `mock_tester = MagicMock()``
- L8904 [`MOCK`] `- L28 [`MOCK`] `mock_tester.go_tester.available = False  # Use Python path``
- L8905 [`MOCK`] `- L29 [`MOCK`] `mock_tester.test = MagicMock()``
- L8906 [`MOCK`] `- L31 [`MOCK`] `# Mock result for test() must be awaitable``
- L8907 [`MOCK`] `- L32 [`MOCK`] `async def mock_test_result(p):``
- L8908 [`MOCK`] `- L37 [`MOCK`] `mock_tester.test.side_effect = mock_test_result``
- L8909 [`MOCK`] `- L39 [`MOCK`] `mock_scheduler = MagicMock(spec=SmartRetestScheduler)``
- L8910 [`MOCK`] `- L40 [`MOCK`] `mock_scheduler.should_retest.return_value = True``
- L8911 [`MOCK`] `- L42 [`MOCK`] `mock_cache = MagicMock(spec=TestResultCache)``
- L8912 [`MOCK`] `- L43 [`MOCK`] `mock_cache.get.return_value = None``
- L8913 [`MOCK`] `- L45 [`MOCK`] `mock_concurrency = MagicMock(spec=ConcurrencyManager)``
- L8914 [`MOCK`] `- L46 [`MOCK`] `# mock get_semaphore must return an async context manager``
- L8915 [`MOCK`] `- L48 [`MOCK`] `mock_concurrency.get_semaphore.return_value = asyncio.Semaphore(10)``
- L8916 [`MOCK`] `- L49 [`MOCK`] `mock_concurrency.record = MagicMock()  # awaitable? record is async def``
- L8917 [`MOCK`] `- L51 [`MOCK`] `async def mock_record(*args):``
- L8918 [`MOCK`] `- L55 [`MOCK`] `mock_concurrency.start_tuner = MagicMock()``
- L8919 [`MOCK`] `- L59 [`MOCK`] `mock_concurrency.stop_tuner = MagicMock(return_value=f)``
- L8920 [`MOCK`] `- L61 [`MOCK`] `mock_concurrency.record.side_effect = mock_record``
- L8921 [`MOCK`] `- L63 [`MOCK`] `from unittest.mock import AsyncMock``
- L8922 [`MOCK`] `- L65 [`MOCK`] `mock_geoip = MagicMock()``
- L8923 [`MOCK`] `- L66 [`MOCK`] `mock_geoip.lookup = AsyncMock(``
- L8924 [`MOCK`] `- L67 [`MOCK`] `return_value=MagicMock(country_code="US", city="Test", asn="AS1", org="Org")``
- L8925 [`MOCK`] `- L71 [`MOCK`] `mock_quality = MagicMock(spec=SourceQualityTracker)``
- L8926 [`MOCK`] `- L73 [`MOCK`] `# Need to mock parse_config or ensure "vmess://test" parses``
- L8927 [`MOCK`] `- L74 [`MOCK`] `with patch("configstream.consumer.parse_config") as mock_parse:``
- L8928 [`MOCK`] `- L77 [`MOCK`] `mock_parse.return_value = p``
- L8929 [`MOCK`] `- L79 [`MOCK`] `# We also need to mock validate_batch_configs to just return the list``
- L8930 [`MOCK`] `- L80 [`MOCK`] `with patch("configstream.consumer.validate_batch_configs") as mock_validate:``
- L8931 [`MOCK`] `- L81 [`MOCK`] `mock_validate.side_effect = lambda batch, policy: batch``
- L8932 [`MOCK`] `- L88 [`MOCK`] `tester=mock_tester,``
- L8933 [`MOCK`] `- L89 [`MOCK`] `scheduler=mock_scheduler,``
- L8934 [`MOCK`] `- L90 [`MOCK`] `test_cache=mock_cache,``
- L8935 [`MOCK`] `- L91 [`MOCK`] `concurrency=mock_concurrency,``
- L8936 [`MOCK`] `- L92 [`MOCK`] `geoip=mock_geoip,``
- L8937 [`MOCK`] `- L95 [`MOCK`] `quality_tracker=mock_quality,``
- L8938 [`MOCK`] `- L96 [`MOCK`] `history=MagicMock(),``
- L8941 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8942 [`MOCK`] `- L10 [`MOCK`] `def mock_proxies():``
- L8943 [`MOCK`] `- L34 [`MOCK`] `async def test_pipeline_dry_run(tmp_path, mock_proxies):``
- L8944 [`MOCK`] `- L35 [`MOCK`] `# Create a callable that returns mock_proxies to avoid fixture timing issues``
- L8945 [`MOCK`] `- L36 [`MOCK`] `def filter_unique_mock(*args, **kwargs):``
- L8946 [`MOCK`] `- L37 [`MOCK`] `return list(mock_proxies)``
- L8947 [`MOCK`] `- L40 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L8948 [`MOCK`] `- L43 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L8949 [`MOCK`] `- L44 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L8950 [`MOCK`] `- L45 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L8951 [`MOCK`] `- L46 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L8952 [`MOCK`] `- L49 [`MOCK`] `side_effect=filter_unique_mock,``
- L8953 [`MOCK`] `- L56 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,``
- L8954 [`MOCK`] `- L59 [`MOCK`] `new=MagicMock(spec=ProxyWasher),``
- L8955 [`MOCK`] `- L60 [`MOCK`] `) as MockWasher,``
- L8956 [`MOCK`] `- L67 [`MOCK`] `# Configure mocked tester to be awaitable on close``
- L8957 [`MOCK`] `- L68 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L8958 [`MOCK`] `- L69 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L8959 [`MOCK`] `- L71 [`MOCK`] `# Configure EventStream mock``
- L8960 [`MOCK`] `- L72 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L8961 [`MOCK`] `- L74 [`MOCK`] `history = MagicMock()``
- L8962 [`MOCK`] `- L78 [`MOCK`] `MockHistory.return_value = history``
- L8963 [`MOCK`] `- L80 [`MOCK`] `# Mocking washer methods correctly``
- L8964 [`MOCK`] `- L81 [`MOCK`] `washer_instance = MockWasher.return_value``
- L8965 [`MOCK`] `- L82 [`MOCK`] `washer_instance.fetch_clean_ips = AsyncMock()``
- L8966 [`MOCK`] `- L83 [`MOCK`] `washer_instance.wash_batch = MagicMock(return_value=([], set(), {}))``
- L8967 [`MOCK`] `- L99 [`MOCK`] `final_proxies.extend(mock_proxies)``
- L8968 [`MOCK`] `- L100 [`MOCK`] `stats.working = len(mock_proxies)``
- L8969 [`MOCK`] `- L110 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L8970 [`MOCK`] `- L111 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L8971 [`MOCK`] `- L117 [`MOCK`] `proxies=mock_proxies,``
- L8972 [`MOCK`] `- L128 [`MOCK`] `async def test_pipeline_pareto_sort(tmp_path, mock_proxies):``
- L8973 [`MOCK`] `- L131 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L8974 [`MOCK`] `- L134 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L8975 [`MOCK`] `- L135 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L8976 [`MOCK`] `- L136 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L8977 [`MOCK`] `- L137 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L8978 [`MOCK`] `- L140 [`MOCK`] `new=AsyncMock(return_value={}),``
- L8979 [`MOCK`] `- L142 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,``
- L8980 [`MOCK`] `- L144 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L8981 [`MOCK`] `- L145 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L8982 [`MOCK`] `- L147 [`MOCK`] `# Configure EventStream mock``
- L8983 [`MOCK`] `- L148 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L8984 [`MOCK`] `- L150 [`MOCK`] `# Mock history to prefer the higher latency one (reliability > latency scenario)``
- L8985 [`MOCK`] `- L151 [`MOCK`] `history = MagicMock()``
- L8986 [`MOCK`] `- L152 [`MOCK`] `MockHistory.return_value = history``
- L8987 [`MOCK`] `- L164 [`MOCK`] `final_proxies.extend(mock_proxies)``
- L8988 [`MOCK`] `- L171 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L8989 [`MOCK`] `- L172 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L8990 [`MOCK`] `- L180 [`MOCK`] `# Since we mock consumer to just append proxies, they are unsorted initially.``
- L8991 [`MOCK`] `- L182 [`MOCK`] `# We can't easily assert sort order here without mocking the sort function or checking result side effects``
- L8992 [`MOCK`] `- L187 [`MOCK`] `async def test_pipeline_adapter_export_fail(tmp_path, mock_proxies):``
- L8993 [`MOCK`] `- L189 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L8994 [`MOCK`] `- L192 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L8995 [`MOCK`] `- L193 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L8996 [`MOCK`] `- L194 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L8997 [`MOCK`] `- L195 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L8998 [`MOCK`] `- L198 [`MOCK`] `new=AsyncMock(side_effect=Exception("Export Fail")),``
- L8999 [`MOCK`] `- L202 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L9000 [`MOCK`] `- L203 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L9001 [`MOCK`] `- L205 [`MOCK`] `# Configure EventStream mock``
- L9002 [`MOCK`] `- L206 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L9003 [`MOCK`] `- L223 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L9004 [`MOCK`] `- L224 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L9007 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L9008 [`MOCK`] `- L14 [`MOCK`] `"configstream.pipeline.source_producer", new_callable=AsyncMock``
- L9009 [`MOCK`] `- L15 [`MOCK`] `) as mock_prod,``
- L9010 [`MOCK`] `- L17 [`MOCK`] `"configstream.pipeline.processing_consumer", new_callable=AsyncMock``
- L9011 [`MOCK`] `- L18 [`MOCK`] `) as mock_cons,``
- L9012 [`MOCK`] `- L21 [`MOCK`] `new_callable=AsyncMock,``
- L9013 [`MOCK`] `- L22 [`MOCK`] `) as mock_gen,``
- L9014 [`MOCK`] `- L23 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),``
- L9015 [`MOCK`] `- L24 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,``
- L9016 [`MOCK`] `- L26 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,``
- L9017 [`MOCK`] `- L29 [`MOCK`] `mock_tester = mock_tester_cls.return_value``
- L9018 [`MOCK`] `- L30 [`MOCK`] `mock_tester.go_tester = MagicMock()``
- L9019 [`MOCK`] `- L31 [`MOCK`] `mock_tester.go_tester.available = False``
- L9020 [`MOCK`] `- L32 [`MOCK`] `mock_tester.close = AsyncMock()``
- L9021 [`MOCK`] `- L34 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()``
- L9022 [`MOCK`] `- L47 [`MOCK`] `assert mock_prod.called, "source_producer should have been called"``
- L9023 [`MOCK`] `- L48 [`MOCK`] `assert mock_cons.called, "processing_consumer should have been called"``
- L9024 [`MOCK`] `- L49 [`MOCK`] `assert mock_gen.called, "generate_pipeline_outputs should have been called"``
- L9025 [`MOCK`] `- L58 [`MOCK`] `patch("configstream.pipeline.source_producer", new_callable=AsyncMock),``
- L9026 [`MOCK`] `- L59 [`MOCK`] `patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),``
- L9027 [`MOCK`] `- L62 [`MOCK`] `new_callable=AsyncMock,``
- L9028 [`MOCK`] `- L64 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),``
- L9029 [`MOCK`] `- L65 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,``
- L9030 [`MOCK`] `- L68 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,``
- L9031 [`MOCK`] `- L71 [`MOCK`] `mock_tester = mock_tester_cls.return_value``
- L9032 [`MOCK`] `- L72 [`MOCK`] `mock_tester.go_tester = MagicMock()``
- L9033 [`MOCK`] `- L73 [`MOCK`] `mock_tester.go_tester.available = False``
- L9034 [`MOCK`] `- L74 [`MOCK`] `mock_tester.close = AsyncMock()``
- L9035 [`MOCK`] `- L75 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()``
- L9038 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L9039 [`MOCK`] `- L13 [`MOCK`] `def mock_dependencies():``
- L9040 [`MOCK`] `- L15 [`MOCK`] `quality = MagicMock()``
- L9041 [`MOCK`] `- L17 [`MOCK`] `anomaly = MagicMock()``
- L9042 [`MOCK`] `- L20 [`MOCK`] `tester = MagicMock()``
- L9043 [`MOCK`] `- L22 [`MOCK`] `tester.test = AsyncMock()  # For python fallback``
- L9044 [`MOCK`] `- L23 [`MOCK`] `tester.test_batch = AsyncMock()  # For go tester``
- L9045 [`MOCK`] `- L25 [`MOCK`] `scheduler = MagicMock()``
- L9046 [`MOCK`] `- L28 [`MOCK`] `test_cache = MagicMock()``
- L9047 [`MOCK`] `- L31 [`MOCK`] `concurrency = MagicMock()``
- L9048 [`MOCK`] `- L32 [`MOCK`] `concurrency.start_tuner = MagicMock()``
- L9049 [`MOCK`] `- L33 [`MOCK`] `concurrency.stop_tuner = AsyncMock()``
- L9050 [`MOCK`] `- L34 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()``
- L9051 [`MOCK`] `- L35 [`MOCK`] `concurrency.record = AsyncMock()``
- L9052 [`MOCK`] `- L38 [`MOCK`] `sem = AsyncMock()``
- L9053 [`MOCK`] `- L43 [`MOCK`] `geoip = MagicMock()``
- L9054 [`MOCK`] `- L44 [`MOCK`] `geoip.lookup = AsyncMock(``
- L9055 [`MOCK`] `- L45 [`MOCK`] `return_value=MagicMock(``
- L9056 [`MOCK`] `- L50 [`MOCK`] `tracker = MagicMock()``
- L9057 [`MOCK`] `- L51 [`MOCK`] `tracker.phase.return_value = MagicMock()``
- L9058 [`MOCK`] `- L55 [`MOCK`] `history = MagicMock()``
- L9059 [`MOCK`] `- L56 [`MOCK`] `history.record_test_result = MagicMock()``
- L9060 [`MOCK`] `- L83 [`MOCK`] `async def test_source_producer_supplied_proxies(mock_dependencies):``
- L9061 [`MOCK`] `- L84 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9062 [`MOCK`] `- L91 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9063 [`MOCK`] `- L92 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9064 [`MOCK`] `- L104 [`MOCK`] `async def test_source_producer_local_files(mock_dependencies):``
- L9065 [`MOCK`] `- L105 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9066 [`MOCK`] `- L108 [`MOCK`] `with patch("configstream.producer.read_multiple_files_async") as mock_read:``
- L9067 [`MOCK`] `- L109 [`MOCK`] `mock_read.return_value = [("sources/batch_1.txt", "vmess://file")]``
- L9068 [`MOCK`] `- L115 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9069 [`MOCK`] `- L116 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9070 [`MOCK`] `- L128 [`MOCK`] `async def test_source_producer_remote_urls(mock_dependencies):``
- L9071 [`MOCK`] `- L129 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9072 [`MOCK`] `- L137 [`MOCK`] `# Mock fetcher``
- L9073 [`MOCK`] `- L138 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:``
- L9074 [`MOCK`] `- L139 [`MOCK`] `mock_fetch.return_value = {``
- L9075 [`MOCK`] `- L144 [`MOCK`] `# Mock read_multiple_files_async to prevent it from trying to read ss:// as file and logging warnings``
- L9076 [`MOCK`] `- L153 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9077 [`MOCK`] `- L154 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9078 [`MOCK`] `- L181 [`MOCK`] `async def test_source_producer_anomaly_block(mock_dependencies):``
- L9079 [`MOCK`] `- L182 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9080 [`MOCK`] `- L185 [`MOCK`] `mock_dependencies["anomaly"].is_safe.return_value = (False, "Malicious")``
- L9081 [`MOCK`] `- L187 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:``
- L9082 [`MOCK`] `- L188 [`MOCK`] `mock_fetch.return_value = {``
- L9083 [`MOCK`] `- L196 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9084 [`MOCK`] `- L197 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9085 [`MOCK`] `- L210 [`MOCK`] `async def test_processing_consumer_basic_flow(mock_dependencies):``
- L9086 [`MOCK`] `- L211 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9087 [`MOCK`] `- L220 [`MOCK`] `# Mock parse_config to return a valid proxy``
- L9088 [`MOCK`] `- L223 [`MOCK`] `# Mock tester to succeed``
- L9089 [`MOCK`] `- L229 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9090 [`MOCK`] `- L231 [`MOCK`] `# Mock validate_batch_configs``
- L9091 [`MOCK`] `- L241 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9092 [`MOCK`] `- L242 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9093 [`MOCK`] `- L243 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9094 [`MOCK`] `- L244 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9095 [`MOCK`] `- L245 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9096 [`MOCK`] `- L246 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9097 [`MOCK`] `- L248 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9098 [`MOCK`] `- L249 [`MOCK`] `history=mock_dependencies["history"],``
- L9099 [`MOCK`] `- L259 [`MOCK`] `assert final_proxies[0].country_code == "US"  # From GeoIP mock``
- L9100 [`MOCK`] `- L263 [`MOCK`] `async def test_processing_consumer_cached_hit(mock_dependencies):``
- L9101 [`MOCK`] `- L264 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9102 [`MOCK`] `- L278 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False``
- L9103 [`MOCK`] `- L279 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = cached_p``
- L9104 [`MOCK`] `- L291 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9105 [`MOCK`] `- L292 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9106 [`MOCK`] `- L293 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9107 [`MOCK`] `- L294 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9108 [`MOCK`] `- L295 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9109 [`MOCK`] `- L296 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9110 [`MOCK`] `- L298 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9111 [`MOCK`] `- L299 [`MOCK`] `history=mock_dependencies["history"],``
- L9112 [`MOCK`] `- L313 [`MOCK`] `async def test_processing_consumer_cache_miss(mock_dependencies):``
- L9113 [`MOCK`] `- L314 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9114 [`MOCK`] `- L325 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False``
- L9115 [`MOCK`] `- L326 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = None``
- L9116 [`MOCK`] `- L331 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9117 [`MOCK`] `- L343 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9118 [`MOCK`] `- L344 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9119 [`MOCK`] `- L345 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9120 [`MOCK`] `- L346 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9121 [`MOCK`] `- L347 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9122 [`MOCK`] `- L348 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9123 [`MOCK`] `- L350 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9124 [`MOCK`] `- L351 [`MOCK`] `history=mock_dependencies["history"],``
- L9125 [`MOCK`] `- L365 [`MOCK`] `async def test_processing_consumer_go_tester(mock_dependencies):``
- L9126 [`MOCK`] `- L366 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9127 [`MOCK`] `- L377 [`MOCK`] `mock_dependencies["tester"].go_tester.available = True``
- L9128 [`MOCK`] `- L379 [`MOCK`] `# Mock test_batch updates objects in place``
- L9129 [`MOCK`] `- L385 [`MOCK`] `mock_dependencies["tester"].test_batch.side_effect = side_effect``
- L9130 [`MOCK`] `- L397 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9131 [`MOCK`] `- L398 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9132 [`MOCK`] `- L399 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9133 [`MOCK`] `- L400 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9134 [`MOCK`] `- L401 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9135 [`MOCK`] `- L402 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9136 [`MOCK`] `- L404 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9137 [`MOCK`] `- L405 [`MOCK`] `history=mock_dependencies["history"],``
- L9138 [`MOCK`] `- L418 [`MOCK`] `async def test_processing_consumer_filters(mock_dependencies):``
- L9139 [`MOCK`] `- L419 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9140 [`MOCK`] `- L429 [`MOCK`] `# Mock Python tester returns working but HIGH latency``
- L9141 [`MOCK`] `- L433 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9142 [`MOCK`] `- L445 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9143 [`MOCK`] `- L446 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9144 [`MOCK`] `- L447 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9145 [`MOCK`] `- L448 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9146 [`MOCK`] `- L449 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9147 [`MOCK`] `- L450 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9148 [`MOCK`] `- L452 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9149 [`MOCK`] `- L453 [`MOCK`] `history=mock_dependencies["history"],``
- L9150 [`MOCK`] `- L466 [`MOCK`] `async def test_processing_consumer_country_filter(mock_dependencies):``
- L9151 [`MOCK`] `- L467 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9152 [`MOCK`] `- L480 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9153 [`MOCK`] `- L483 [`MOCK`] `mock_dependencies["geoip"].lookup = AsyncMock(``
- L9154 [`MOCK`] `- L484 [`MOCK`] `return_value=MagicMock(country_code="US", city="", asn="", org="")``
- L9155 [`MOCK`] `- L497 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9156 [`MOCK`] `- L498 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9157 [`MOCK`] `- L499 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9158 [`MOCK`] `- L500 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9159 [`MOCK`] `- L501 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9160 [`MOCK`] `- L502 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9161 [`MOCK`] `- L504 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9162 [`MOCK`] `- L505 [`MOCK`] `history=mock_dependencies["history"],``
- L9165 [`MOCK`] `- L8 [`MOCK`] `from unittest.mock import MagicMock``
- L9166 [`MOCK`] `- L19 [`MOCK`] `quality = MagicMock()``
- L9169 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L9170 [`MOCK`] `- L15 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9171 [`MOCK`] `- L35 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9172 [`MOCK`] `- L63 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9173 [`MOCK`] `- L82 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9174 [`MOCK`] `- L106 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9177 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import MagicMock``
- L9178 [`MOCK`] `- L15 [`MOCK`] `self.cache = MagicMock(spec=TestResultCache)``
- L9179 [`MOCK`] `- L62 [`MOCK`] `# Mock: p1 needs test, p2 does not``
- L9180 [`MOCK`] `- L63 [`MOCK`] `self.scheduler.should_retest = MagicMock(side_effect=[True, False])``
- L9183 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock``
- L9184 [`MOCK`] `- L11 [`MOCK`] `def mock_blocklist_file(tmp_path):``
- L9185 [`MOCK`] `- L25 [`MOCK`] `async def test_is_blocked_logic(mock_blocklist_file):``
- L9186 [`MOCK`] `- L28 [`MOCK`] `# Mock the CACHE_FILE path and content loading``
- L9187 [`MOCK`] `- L29 [`MOCK`] `mock_blocklist_file.write_text("1.2.3.4/32\n5.6.7.0/24")``
- L9188 [`MOCK`] `- L31 [`MOCK`] `with patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file):``
- L9189 [`MOCK`] `- L40 [`MOCK`] `async def test_update_blocklist(mock_blocklist_file):``
- L9190 [`MOCK`] `- L44 [`MOCK`] `patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file),``
- L9191 [`MOCK`] `- L45 [`MOCK`] `patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,``
- L9192 [`MOCK`] `- L47 [`MOCK`] `mock_resp = MagicMock()``
- L9193 [`MOCK`] `- L48 [`MOCK`] `mock_resp.status_code = 200``
- L9194 [`MOCK`] `- L49 [`MOCK`] `mock_resp.raise_for_status = MagicMock()``
- L9195 [`MOCK`] `- L50 [`MOCK`] `mock_resp.content = b"9.9.9.9/32\n10.10.10.0/24"``
- L9196 [`MOCK`] `- L52 [`MOCK`] `mock_get.return_value = mock_resp``
- L9197 [`MOCK`] `- L56 [`MOCK`] `if not mock_blocklist_file.exists():``
- L9198 [`MOCK`] `- L59 [`MOCK`] `print("File content:", mock_blocklist_file.read_text())``
- L9199 [`MOCK`] `- L80 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,``
- L9200 [`MOCK`] `- L82 [`MOCK`] `mock_resp = MagicMock()``
- L9201 [`MOCK`] `- L83 [`MOCK`] `mock_resp.status = 200``
- L9202 [`MOCK`] `- L88 [`MOCK`] `mock_resp.json = async_json``
- L9203 [`MOCK`] `- L89 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp``
- L9204 [`MOCK`] `- L99 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,``
- L9205 [`MOCK`] `- L101 [`MOCK`] `mock_resp = MagicMock()``
- L9206 [`MOCK`] `- L102 [`MOCK`] `mock_resp.status = 200``
- L9207 [`MOCK`] `- L107 [`MOCK`] `mock_resp.json = async_json``
- L9208 [`MOCK`] `- L108 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp``
- L9211 [`ASSUMING`] `- L21 [`ASSUMING`] `# Assuming it checks for basic validity.``
- L9214 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch``
- L9215 [`MOCK`] `- L18 [`MOCK`] `# Mocking _is_address_safe to simulate failure``
- L9216 [`MOCK`] `- L58 [`MOCK`] `# Mock validator to fail the second one with a non-fatal reason``
- L9217 [`MOCK`] `- L61 [`MOCK`] `) as mock_val:``
- L9218 [`MOCK`] `- L62 [`MOCK`] `mock_val.side_effect = [(True, "ok"), (False, "tls_required")]``
- L9221 [`ASSUMING`] `- L54 [`ASSUMING`] `# Assuming we want it to fail, but current logic allows it.``
- L9224 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L9225 [`MOCK`] `- L58 [`MOCK`] `# Mock FileResponse to return content from disk (simulating server behavior)``
- L9226 [`MOCK`] `- L77 [`MOCK`] `def mock_output_dir(tmp_path):``
- L9227 [`MOCK`] `- L78 [`MOCK`] `"""Mock the output directory and create dummy files."""``
- L9228 [`MOCK`] `- L113 [`MOCK`] `def mock_frontend_dir(tmp_path):``
- L9229 [`MOCK`] `- L114 [`MOCK`] `"""Mock the frontend directory."""``
- L9230 [`MOCK`] `- L124 [`MOCK`] `async def test_health_check(mock_output_dir, async_client):``
- L9231 [`MOCK`] `- L125 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9232 [`MOCK`] `- L134 [`MOCK`] `async def test_get_stats(mock_output_dir, async_client):``
- L9233 [`MOCK`] `- L135 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9234 [`MOCK`] `- L144 [`MOCK`] `mock_output_dir, async_client, monkeypatch``
- L9235 [`MOCK`] `- L155 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9236 [`MOCK`] `- L169 [`MOCK`] `mock_output_dir, async_client, monkeypatch``
- L9237 [`MOCK`] `- L171 [`MOCK`] `(mock_output_dir / "proxies.old.json").write_text(``
- L9238 [`MOCK`] `- L175 [`MOCK`] `(mock_output_dir / "proxies.json").write_text(``
- L9239 [`MOCK`] `- L188 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9240 [`MOCK`] `- L203 [`MOCK`] `async def test_get_proxies_all(mock_output_dir, async_client):``
- L9241 [`MOCK`] `- L204 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9242 [`MOCK`] `- L211 [`MOCK`] `async def test_get_proxies_by_country(mock_output_dir, async_client):``
- L9243 [`MOCK`] `- L212 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9244 [`MOCK`] `- L224 [`MOCK`] `async def test_get_proxies_by_protocol(mock_output_dir, async_client):``
- L9245 [`MOCK`] `- L225 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9246 [`MOCK`] `- L237 [`MOCK`] `async def test_download_subscription(mock_output_dir, async_client):``
- L9247 [`MOCK`] `- L238 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9248 [`MOCK`] `- L391 [`MOCK`] `async def test_frontend_serving(mock_frontend_dir, async_client):``
- L9249 [`MOCK`] `- L392 [`MOCK`] `with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):``
- L9250 [`MOCK`] `- L415 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9251 [`MOCK`] `- L420 [`MOCK`] `side_effect=mock_test,``
- L9252 [`MOCK`] `- L438 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9253 [`MOCK`] `- L443 [`MOCK`] `side_effect=mock_test,``
- L9254 [`MOCK`] `- L460 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9255 [`MOCK`] `- L465 [`MOCK`] `side_effect=mock_test,``
- L9256 [`MOCK`] `- L513 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9257 [`MOCK`] `- L518 [`MOCK`] `side_effect=mock_test,``
- L9260 [`MOCK`] `- L49 [`MOCK`] `# But since we mocked/created dummy files in previous steps or they exist in repo...``
- L9263 [`MOCK`] `- L41 [`MOCK`] `# Mock Path.cwd to point to a clean temp directory``
- L9266 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import MagicMock``
- L9267 [`MOCK`] `- L15 [`MOCK`] `def _setup_history_mock(self, proxies, reliability_map=None, uptime_map=None):``
- L9268 [`MOCK`] `- L16 [`MOCK`] `history = MagicMock()``
- L9269 [`MOCK`] `- L40 [`MOCK`] `history = MagicMock()``
- L9270 [`MOCK`] `- L54 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.9}, {proxy.id: 95.0})``
- L9271 [`MOCK`] `- L78 [`MOCK`] `history = self._setup_history_mock(``
- L9272 [`MOCK`] `- L108 [`MOCK`] `history = self._setup_history_mock(``
- L9273 [`MOCK`] `- L145 [`MOCK`] `history = self._setup_history_mock(``
- L9274 [`MOCK`] `- L173 [`MOCK`] `history = self._setup_history_mock(``
- L9275 [`MOCK`] `- L203 [`MOCK`] `history = self._setup_history_mock(``
- L9276 [`MOCK`] `- L234 [`MOCK`] `# Manually create mock to handle missing key logic``
- L9277 [`MOCK`] `- L235 [`MOCK`] `history = MagicMock()``
- L9278 [`MOCK`] `- L269 [`MOCK`] `history = self._setup_history_mock(``
- L9279 [`MOCK`] `- L295 [`MOCK`] `history = self._setup_history_mock(``
- L9280 [`MOCK`] `- L321 [`MOCK`] `history = self._setup_history_mock(``
- L9281 [`MOCK`] `- L351 [`MOCK`] `history = self._setup_history_mock(``
- L9282 [`MOCK`] `- L383 [`MOCK`] `history = self._setup_history_mock(``
- L9283 [`MOCK`] `- L410 [`MOCK`] `history = self._setup_history_mock(``
- L9284 [`MOCK`] `- L442 [`MOCK`] `history = self._setup_history_mock(``
- L9285 [`MOCK`] `- L465 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.6}, {proxy.id: 70.0})``
- L9288 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L9289 [`MOCK`] `- L37 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9290 [`MOCK`] `- L39 [`MOCK`] `mock_cdll.assert_not_called()``
- L9291 [`MOCK`] `- L72 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9292 [`MOCK`] `- L73 [`MOCK`] `mock_lib = MagicMock()``
- L9293 [`MOCK`] `- L74 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9294 [`MOCK`] `- L75 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9295 [`MOCK`] `- L77 [`MOCK`] `# Force reload lib (reset global in module is hard, so we mock where it's used)``
- L9296 [`MOCK`] `- L81 [`MOCK`] `mock_lib.verify_shadowsocks.assert_called()``
- L9297 [`MOCK`] `- L90 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9298 [`MOCK`] `- L91 [`MOCK`] `mock_lib = MagicMock()``
- L9299 [`MOCK`] `- L92 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0  # Invalid``
- L9300 [`MOCK`] `- L93 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9301 [`MOCK`] `- L105 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9302 [`MOCK`] `- L106 [`MOCK`] `mock_lib = MagicMock()``
- L9303 [`MOCK`] `- L107 [`MOCK`] `mock_lib.verify_shadowsocks.side_effect = Exception("FFI Error")``
- L9304 [`MOCK`] `- L108 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9305 [`MOCK`] `- L120 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9306 [`MOCK`] `- L121 [`MOCK`] `mock_lib = MagicMock()``
- L9307 [`MOCK`] `- L122 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9308 [`MOCK`] `- L123 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9309 [`MOCK`] `- L131 [`MOCK`] `call_args = mock_lib.verify_shadowsocks.call_args``
- L9310 [`MOCK`] `- L150 [`MOCK`] `with patch("configstream.security.ss_ffi.logger") as mock_logger:``
- L9311 [`MOCK`] `- L154 [`MOCK`] `assert mock_logger.warning.called``
- L9312 [`MOCK`] `- L163 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9313 [`MOCK`] `- L164 [`MOCK`] `mock_lib = MagicMock()``
- L9314 [`MOCK`] `- L165 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9315 [`MOCK`] `- L166 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9316 [`MOCK`] `- L187 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9317 [`MOCK`] `- L188 [`MOCK`] `mock_lib = MagicMock()``
- L9318 [`MOCK`] `- L189 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9319 [`MOCK`] `- L190 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9320 [`MOCK`] `- L204 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9321 [`MOCK`] `- L205 [`MOCK`] `mock_lib = MagicMock()``
- L9322 [`MOCK`] `- L206 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0``
- L9323 [`MOCK`] `- L207 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9324 [`MOCK`] `- L243 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9325 [`MOCK`] `- L244 [`MOCK`] `mock_lib = MagicMock()``
- L9326 [`MOCK`] `- L245 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9327 [`MOCK`] `- L248 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9328 [`MOCK`] `- L253 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0``
- L9329 [`MOCK`] `- L258 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = -1``
- L9330 [`MOCK`] `- L269 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9331 [`MOCK`] `- L270 [`MOCK`] `mock_lib = MagicMock()``
- L9332 [`MOCK`] `- L271 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9333 [`MOCK`] `- L277 [`MOCK`] `mock_cdll.assert_called_once()``
- L9334 [`MOCK`] `- L279 [`MOCK`] `assert hasattr(mock_lib, "verify_shadowsocks")``
- L9337 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L9340 [`MOCK`] `- L26 [`MOCK`] `# Force fail by making directory read-only or mocking``
- L9341 [`MOCK`] `- L27 [`MOCK`] `# Using mock for stability``
- L9342 [`MOCK`] `- L28 [`MOCK`] `from unittest.mock import patch``
- L9344 [`PLACEHOLDER`] `##### `tests/unit/test_validate_frontend_placeholders.py``
- L9345 [`PLACEHOLDER`] `- L2 [`PLACEHOLDER`] `"""Tests for frontend production placeholder validation."""``
- L9346 [`PLACEHOLDER`] `- L8 [`PLACEHOLDER`] `from scripts.validate_frontend_placeholders import (``
- L9347 [`PLACEHOLDER`] `- L10 [`PLACEHOLDER`] `validate_frontend_placeholders,``
- L9348 [`PLACEHOLDER`] `- L22 [`PLACEHOLDER`] `'const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";\n',``
- L9349 [`PLACEHOLDER`] `- L27 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_detects_public_and_stego_keys(``
- L9350 [`PLACEHOLDER`] `- L32 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(tmp_path, strict=True)``
- L9351 [`PLACEHOLDER`] `- L34 [`PLACEHOLDER`] `assert any("PUBLIC_KEY placeholder" in error for error in errors)``
- L9352 [`PLACEHOLDER`] `- L35 [`PLACEHOLDER`] `assert any("STEGO_KEY placeholder" in error for error in errors)``
- L9353 [`PLACEHOLDER`] `- L38 [`PLACEHOLDER`] `def test_inject_frontend_keys_replaces_placeholders(tmp_path: Path) -> None:``
- L9354 [`PLACEHOLDER`] `- L50 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=True) == []``
- L9355 [`PLACEHOLDER`] `- L59 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(``
- L9356 [`PLACEHOLDER`] `- L69 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=False) == []``
- L9359 [`PLACEHOLDER`] `- L27 [`PLACEHOLDER`] `def test_validate_workflows_requires_pages_frontend_placeholder_guard(``
- L9362 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L9363 [`MOCK`] `- L103 [`MOCK`] `# Mock _get_clean_endpoint and _get_consistent_exit to ensure success path``
- L9364 [`MOCK`] `- L104 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("1.1.1.1", 2408))``
- L9365 [`MOCK`] `- L137 [`MOCK`] `# Mock helpers``
- L9366 [`MOCK`] `- L138 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("2.2.2.2", 2408))``
- L9367 [`MOCK`] `- L164 [`MOCK`] `washer_stats_fixture.get_warp_config = MagicMock(``
- L9370 [`MOCK`] `- L17 [`MOCK`] `async def test_test_dns_mock():``
- L9371 [`MOCK`] `- L20 [`MOCK`] `# Basic existence check since we can't easily mock network calls without respx/aioresponses``
- L9372 [`MOCK`] `- L21 [`MOCK`] `# and aiodns is tricky to mock fully in this context without real networking``
- L9375 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L9376 [`MOCK`] `- L5 [`MOCK`] `# Mock OpenSSL if not present``
- L9377 [`MOCK`] `- L6 [`MOCK`] `sys.modules["OpenSSL"] = MagicMock()``
- L9378 [`MOCK`] `- L7 [`MOCK`] `sys.modules["OpenSSL.crypto"] = MagicMock()``
- L9379 [`MOCK`] `- L12 [`MOCK`] `def test_cert_generation_mock():``
- L9380 [`MOCK`] `- L13 [`MOCK`] `# Since we mocked OpenSSL, we just check if the function runs without import error``
- L9381 [`MOCK`] `- L14 [`MOCK`] `# and tries to access the mocked object.``
- L9382 [`MOCK`] `- L19 [`MOCK`] `pass  # Expected due to mock return values not being full objects``

### `SECURITY.md`
- L44 [`PLACEHOLDER`] `- Signed frontend artifacts fail closed when WebCrypto is unavailable or public key material is missing/placeholder. Unsigned local content can still be parsed without verification.`
- L48 [`PLACEHOLDER`] `- Deploy fails if required runtime keys are missing or if the public-key placeholder or stego placeholder remains in the Pages artifact.`

### `STATUS.md`
- L44 [`PLACEHOLDER`] `- Pages deploy now generates `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, leaves checked-in source-shaped JS immutable, and fails before upload if required runtime keys are missing or placeholder markers remain; workflow and Pages artifact validation enforce this guard.`
- L46 [`PLACEHOLDER`] `- Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, metadata/proxy API alias parity, health metadata, and placeholder-key absence.`
- L47 [`PLACEHOLDER`] `- Frontend signed-artifact verification now fails closed when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L61 [`PLACEHOLDER`] `- Optional IPFS/IPNS frontend failover is now covered by local tests: the frontend probes a same-origin static asset, skips placeholder IPNS keys, preserves the current leaf page/query/hash when building gateway URLs, normalizes gateway bases, and prevents repeated redirect attempts within the same session.`
- L66 [`MOCK`] `- Debt matrix artifacts are portable: generated paths are repo-relative, generated debt files are excluded from self-scans, and marker summaries separate production/frontend/tooling/docs debt from test-only mocks.`
- L123 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed`
- L130 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed`

### `docs/claim_ledger.json`
- L75 [`MOCK`] `"claim": "Debt matrix artifacts use repo-relative paths and separate production/frontend/tooling/docs debt from test-only mocks.",`
- L204 [`PLACEHOLDER`] `"cleanup_decision": "IPFS/IPNS failover remains optional and requires a configured IPNS key; local tests prove the same-origin connectivity probe, placeholder-key no-op, leaf-page/query/hash preservation, gateway URL normalization, and session loop prevention without requiring a live IPFS gateway."`

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
- L28 [`PLACEHOLDER`] `// Validation: Detect placeholder values in production`

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
- L1460 [`XXX`] `CFG=$(mktemp /tmp/cs-chain-XXXX.json)`

### `frontend/assets/js/main.js`
- L102 [`ASSUMING`] `// Assuming proxies have 'id'`
- L183 [`PLACEHOLDER`] `// Initialize immediately with defaults to avoid "--" flash or placeholders`

### `frontend/assets/js/stego.js`
- L15 [`PLACEHOLDER`] `function _isPlaceholderSecretKey(secretKey) {`
- L16 [`PLACEHOLDER`] `return secretKey === "PLACEHOLDER_" + "KEY_INJECTED_BY_CI";`
- L22 [`PLACEHOLDER`] `_isPlaceholderSecretKey(secretKey) ||`

### `frontend/assets/js/verifier.js`
- L35 [`PLACEHOLDER`] `!publicKey.includes("PLACEHOLDER") &&`
- L62 [`ASSUMING`] `// Assuming Base64 SPKI from constants.js example`

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

### `scripts/deploy_artifact_smoke.py`
- L29 [`PLACEHOLDER`] `from scripts.validate_frontend_placeholders import (`
- L31 [`PLACEHOLDER`] `validate_frontend_placeholders,`
- L215 [`PLACEHOLDER`] `placeholder_errors = validate_frontend_placeholders(temp_dir, strict=True)`
- L216 [`PLACEHOLDER`] `if placeholder_errors:`
- L218 [`PLACEHOLDER`] `for error in placeholder_errors:`

### `scripts/frontend_same_origin_smoke.cjs`
- L143 [`PLACEHOLDER`] `"PLACEHOLDER_PUBLIC_KEY",`
- L144 [`PLACEHOLDER`] `"PLACEHOLDER_KEY_INJECTED_BY_CI",`
- L148 [`PLACEHOLDER`] `throw new Error(`Deploy runtime config still contains placeholder marker: ${marker}`);`

### `scripts/generate_debt_matrix.py`
- L3 [`TODO`] `"""Generate a repository debt matrix from TODO/FIXME-style markers."""`
- L16 [`TODO`] `PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"`
- L160 [`FIXME`] `"- `FIXME` / `XXX`: fix inline before release freeze.",`
- L161 [`TODO`] `"- `TODO`: create issue with owner + milestone.",`
- L162 [`MOCK`] `"- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.",`
- L163 [`PLACEHOLDER`] `"- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.",`

### `scripts/run_test_profile.py`
- L107 [`PLACEHOLDER`] `"tests/unit/test_validate_frontend_placeholders.py",`

### `scripts/validate_frontend_placeholders.py`
- L4 [`PLACEHOLDER`] `This guard keeps deploy artifacts from silently shipping placeholder verification`
- L18 [`PLACEHOLDER`] `PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")`
- L19 [`PLACEHOLDER`] `STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"`
- L65 [`PLACEHOLDER`] `def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:`
- L75 [`PLACEHOLDER`] `if any(marker in constants for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):`
- L77 [`PLACEHOLDER`] `"Frontend PUBLIC_KEY placeholder remains in assets/js/constants.js"`
- L85 [`PLACEHOLDER`] `if STEGO_KEY_PLACEHOLDER in stego:`
- L87 [`PLACEHOLDER`] `"Frontend STEGO_KEY placeholder remains in assets/js/stego.js"`
- L95 [`PLACEHOLDER`] `if any(marker in runtime_config for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):`
- L97 [`PLACEHOLDER`] `"Frontend PUBLIC_KEY placeholder remains in assets/js/runtime-config.js"`
- L99 [`PLACEHOLDER`] `if STEGO_KEY_PLACEHOLDER in runtime_config:`
- L101 [`PLACEHOLDER`] `"Frontend STEGO_KEY placeholder remains in assets/js/runtime-config.js"`
- L136 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(root, strict=bool(args.strict))`
- L142 [`PLACEHOLDER`] `print("OK: frontend production placeholders validated.")`

### `scripts/validate_pages_artifact.py`
- L142 [`PLACEHOLDER`] `"PLACEHOLDER_KEY_INJECTED_BY_CI",`
- L143 [`PLACEHOLDER`] `"PLACEHOLDER_PUBLIC_KEY",`

### `scripts/validate_workflows.py`
- L82 [`PLACEHOLDER`] `def _deploy_pages_has_frontend_placeholder_guard(path: Path) -> bool:`
- L88 [`PLACEHOLDER`] `"scripts/validate_frontend_placeholders.py --inject-env --strict output"`
- L168 [`PLACEHOLDER`] `and not _deploy_pages_has_frontend_placeholder_guard(path)`
- L171 [`PLACEHOLDER`] `f"{path}: missing frontend placeholder injection/validation guard"`

### `scripts/verify_pages_deployment.py`
- L14 [`PLACEHOLDER`] `PLACEHOLDER_MARKERS = (`
- L16 [`PLACEHOLDER`] `"PLACEHOLDER_PUBLIC_KEY",`
- L17 [`PLACEHOLDER`] `"PLACEHOLDER_KEY_INJECTED_BY_CI",`
- L104 [`PLACEHOLDER`] `def _assert_no_placeholders(label: str, text: str, errors: list[str]) -> None:`
- L105 [`PLACEHOLDER`] `for marker in PLACEHOLDER_MARKERS:`
- L107 [`PLACEHOLDER`] `errors.append(f"{label} contains placeholder marker: {marker}")`
- L159 [`PLACEHOLDER`] `_assert_no_placeholders(page, text, errors)`
- L164 [`PLACEHOLDER`] `_assert_no_placeholders("assets/js/runtime-config.js", runtime_text, errors)`
- L172 [`PLACEHOLDER`] `_assert_no_placeholders("assets/js/constants.js", constants.text, errors)`
- L176 [`PLACEHOLDER`] `_assert_no_placeholders("assets/js/stego.js", stego.text, errors)`

### `sources/manual_warp.txt`
- L10 [`XXX`] `wireguard://UJckB8h6r2P6xxx8UEspxw8r3YkpzBEbjxol3jeoqEw%3D@188.114.97.82:5956?address=172.16.0.2/32, 2606:4700:110:846c:e510:bfa1:ea9f:5247/128&publickey=bmXOC%2BF1FxEMF9dyiK2H5%2F1SUtzH0JuVo51h2wPfgyo%3D&reserved=61%2C41%2C250#Tel= @arshiacomplus wire`

### `src/configstream/anomaly.py`
- L194 [`MOCK`] `# However, the test 'test_failure_mode_anomaly_db_crash' explicitly mocks this method`
- L195 [`MOCK`] `# to raise RuntimeError. If the real method catches it, the test mock is bypassed if we use spy.`

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
- L66 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing`
- L129 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing`
- L168 [`MOCK`] `# Mock the metadata request data (using canonical field names from v2.0.8)`
- L169 [`MOCK`] `mock_data = {`
- L184 [`MOCK`] `mock_json = json.dumps(mock_data)`
- L186 [`MOCK`] `# Inject a mock fetch function that returns our data for statistics endpoints`
- L193 [`MOCK`] `// Mock metadata.json (unified stats) and api/stats endpoints`
- L198 [`MOCK`] `json: async () => ({mock_json})`
- L204 [`MOCK`] `// Mock window.api.fetchStatistics directly if needed`
- L206 [`MOCK`] `window.api.fetchStatistics = async () => ({mock_json});`

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

### `tests/unit/test_debt_matrix.py`
- L17 [`TODO`] `file_path.write_text("# TODO: tighten behavior\n", encoding="utf-8")`
- L27 [`TODO`] `"marker": "TODO",`
- L29 [`TODO`] `"text": "# TODO: tighten behavior",`
- L39 [`MOCK`] `def test_generate_debt_matrix_classifies_test_mocks() -> None:`
- L55 [`TODO`] `"marker": "TODO",`
- L57 [`TODO`] `"text": "TODO",`
- L87 [`TODO`] `"marker": "TODO",`
- L89 [`TODO`] `"text": "TODO",`
- L97 [`TODO`] `"## Categories\n\n| `src/example.py` | 1 | TODO |\n",`

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
- L6 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock`
- L15 [`MOCK`] `def _mocked_fetch_settings() -> AppSettings:`
- L39 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L47 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L57 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L60 [`MOCK`] `mock_response = AsyncMock()`
- L61 [`MOCK`] `mock_response.status_code = 200`
- L62 [`MOCK`] `mock_response.headers = {}`
- L68 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L71 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L72 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L73 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L86 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L89 [`MOCK`] `mock_response = AsyncMock()`
- L90 [`MOCK`] `mock_response.status_code = 429`
- L91 [`MOCK`] `mock_response.headers = {"Retry-After": "0.1"}`
- L93 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L94 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L95 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L97 [`MOCK`] `# Should retry. We mock sleep to be fast.`
- L98 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L106 [`MOCK`] `assert mock_sleep.call_count > 0`
- L110 [`MOCK`] `async def test_fetch_from_source_follows_safe_redirect(respx_mock):`
- L113 [`MOCK`] `respx_mock.get(source).mock(`
- L116 [`MOCK`] `respx_mock.get(target).mock(return_value=httpx.Response(200, text="redirected"))`
- L126 [`MOCK`] `async def test_fetch_from_source_rejects_private_redirect(respx_mock):`
- L128 [`MOCK`] `respx_mock.get(source).mock(`
- L144 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L167 [`MOCK`] `async def test_fetch_from_source_validates_redirect_dns_before_fetch(respx_mock):`
- L171 [`MOCK`] `respx_mock.get(source).mock(`
- L191 [`MOCK`] `async def test_fetch_from_source_limits_redirect_depth(respx_mock):`
- L195 [`MOCK`] `respx_mock.get(source).mock(`
- L213 [`MOCK`] `# If RateLimiter class is gone, we can mock a generic object with the same interface.`
- L214 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L215 [`MOCK`] `rate_limiter = MagicMock()`
- L217 [`MOCK`] `rate_limiter.is_allowed = AsyncMock(side_effect=[False, True])`
- L218 [`MOCK`] `rate_limiter.get_wait_time = AsyncMock(return_value=0.01)`
- L220 [`MOCK`] `app_settings = _mocked_fetch_settings()`
- L221 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L223 [`MOCK`] `mock_response = AsyncMock()`
- L224 [`MOCK`] `mock_response.status_code = 200`
- L225 [`MOCK`] `mock_response.headers = {}`
- L230 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L231 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L232 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L233 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L243 [`MOCK`] `assert mock_sleep.called`
- L248 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L249 [`MOCK`] `breaker_manager = MagicMock()`
- L250 [`MOCK`] `breaker = MagicMock()`
- L251 [`MOCK`] `breaker.is_open = AsyncMock(return_value=True)`
- L252 [`MOCK`] `breaker_manager.get_breaker = AsyncMock(return_value=breaker)`
- L270 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L271 [`MOCK`] `mock_response = AsyncMock()`
- L272 [`MOCK`] `mock_response.status_code = 200`
- L276 [`MOCK`] `mock_response.headers = {`
- L280 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L281 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L282 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L294 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L295 [`MOCK`] `mock_response = AsyncMock()`
- L296 [`MOCK`] `mock_response.status_code = 200`
- L297 [`MOCK`] `mock_response.headers = {}`
- L306 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()`
- L308 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L309 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L310 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L322 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L323 [`MOCK`] `app_settings = _mocked_fetch_settings()`
- L324 [`MOCK`] `mock_response = AsyncMock()`
- L325 [`MOCK`] `mock_response.status_code = 200`
- L326 [`MOCK`] `mock_response.headers = {}`
- L331 [`MOCK`] `mock_response.aiter_bytes = lambda: async_gen()`
- L333 [`MOCK`] `mock_stream_ctx = AsyncMock()`
- L334 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response`
- L335 [`MOCK`] `client.stream.return_value = mock_stream_ctx`
- L337 [`MOCK`] `tracker = MagicMock()`
- L338 [`MOCK`] `tracker.get_timeout = MagicMock(return_value=10.0)`
- L339 [`MOCK`] `tracker.record = AsyncMock()`
- L340 [`MOCK`] `tracker.get_jitter = AsyncMock(return_value=3.0)  # High jitter`
- L343 [`MOCK`] `with patch("configstream.fetcher.logger") as mock_logger:`
- L351 [`MOCK`] `assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)`
- L356 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L357 [`MOCK`] `app_settings = _mocked_fetch_settings()`
- L361 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:`
- L372 [`MOCK`] `assert mock_sleep.call_count > 0`
- L377 [`MOCK`] `# Integration test mocking minimal internals`
- L379 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:`
- L380 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")`
- L391 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)`
- L393 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:`
- L394 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")`

### `tests/unit/test_fetcher_advanced.py`
- L3 [`MOCK`] `from unittest.mock import patch, MagicMock`
- L10 [`MOCK`] `def mocked_fetch_settings(**kwargs):`
- L16 [`MOCK`] `# Helper to mock the stream context manager`
- L17 [`MOCK`] `class MockStreamResponse:`
- L45 [`MOCK`] `# Mock stream instead of get`
- L46 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L47 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "ok")`
- L51 [`MOCK`] `client, "http://ok.com", app_settings=mocked_fetch_settings()`
- L60 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L61 [`MOCK`] `resp1 = MockStreamResponse(429, "", headers={"Retry-After": "0.1"})`
- L62 [`MOCK`] `resp2 = MockStreamResponse(200, "ok")`
- L64 [`MOCK`] `mock_stream.side_effect = [resp1, resp2]`
- L71 [`MOCK`] `app_settings=mocked_fetch_settings(),`
- L76 [`MOCK`] `assert mock_stream.call_count == 2`
- L107 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L108 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "streamed_content")`
- L110 [`MOCK`] `settings = mocked_fetch_settings(HEDGING_ENABLED=True, HEDGE_AFTER_MS=100)`
- L117 [`MOCK`] `# We assert mock_stream was called, implying we used the safer path`
- L118 [`MOCK`] `mock_stream.assert_called_once()`
- L135 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:`
- L136 [`MOCK`] `mock_stream.return_value = MockStreamResponse(404, "")`
- L143 [`MOCK`] `app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),`
- L150 [`MOCK`] `app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),`
- L157 [`MOCK`] `app_settings=mocked_fetch_settings(CIRCUIT_BREAKER_ENABLED=True),`
- L164 [`MOCK`] `assert mock_stream.call_count == 2`

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

### `tests/unit/test_frontend_failover.py`
- L81 [`PLACEHOLDER`] `if ({json.dumps(case)} === 'placeholder') {{`
- L163 [`PLACEHOLDER`] `def test_failover_skips_placeholder_ipns_key(tmp_path: Path) -> None:`
- L164 [`PLACEHOLDER`] `result = _run_failover_case(tmp_path, "placeholder")`

### `tests/unit/test_frontend_verifier.py`
- L50 [`PLACEHOLDER`] `const placeholderKey = 'MCowBQYDK2VwAyEA79e/79e/79e/79e/79e/79e/79e/79e/79e/79e/79e=';`
- L54 [`PLACEHOLDER`] `const placeholder = await runCase(true, placeholderKey, signed);`
- L63 [`PLACEHOLDER`] `if (placeholder.ok || !placeholder.message.includes('Public Key not configured')) {{`
- L64 [`PLACEHOLDER`] `throw new Error('signed artifact did not fail closed with placeholder public key');`

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
- L44 [`MOCK`] `def mock_storage():`
- L45 [`MOCK`] `return MagicMock(spec=QualityStorage)`
- L59 [`MOCK`] `def test_metadata_generation(tmp_path, sample_proxies, mock_storage):`

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
- L22 [`ASSUMING`] `# Assuming it checks for basic validity.`

### `tests/unit/test_security_validator_extra.py`
- L2 [`MOCK`] `from unittest.mock import patch`
- L18 [`MOCK`] `# Mocking _is_address_safe to simulate failure`
- L58 [`MOCK`] `# Mock validator to fail the second one with a non-fatal reason`
- L61 [`MOCK`] `) as mock_val:`
- L62 [`MOCK`] `mock_val.side_effect = [(True, "ok"), (False, "tls_required")]`

### `tests/unit/test_security_validator_full.py`
- L73 [`ASSUMING`] `# Assuming we want it to fail, but current logic allows it.`

### `tests/unit/test_server.py`
- L4 [`MOCK`] `from unittest.mock import patch`
- L70 [`MOCK`] `# Mock FileResponse to return content from disk (simulating server behavior)`
- L89 [`MOCK`] `def mock_output_dir(tmp_path):`
- L90 [`MOCK`] `"""Mock the output directory and create dummy files."""`
- L125 [`MOCK`] `def mock_frontend_dir(tmp_path):`
- L126 [`MOCK`] `"""Mock the frontend directory."""`
- L136 [`MOCK`] `async def test_health_check(mock_output_dir, async_client):`
- L137 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L146 [`MOCK`] `async def test_get_stats(mock_output_dir, async_client):`
- L147 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L156 [`MOCK`] `mock_output_dir, async_client, monkeypatch`
- L167 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L181 [`MOCK`] `mock_output_dir, async_client, monkeypatch`
- L184 [`MOCK`] `(mock_output_dir / "proxies.old.json").write_text(`
- L187 [`MOCK`] `(mock_output_dir / "proxies.json").write_text(`
- L200 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L218 [`MOCK`] `mock_output_dir, async_client`
- L221 [`MOCK`] `(mock_output_dir / "proxies.old.json").write_text(`
- L225 [`MOCK`] `(mock_output_dir / "proxies.json").write_text(`
- L230 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L243 [`MOCK`] `async def test_get_proxies_all(mock_output_dir, async_client):`
- L244 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L251 [`MOCK`] `async def test_get_proxies_by_country(mock_output_dir, async_client):`
- L252 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L264 [`MOCK`] `async def test_get_proxies_by_protocol(mock_output_dir, async_client):`
- L265 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L277 [`MOCK`] `async def test_download_subscription(mock_output_dir, async_client):`
- L278 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):`
- L431 [`MOCK`] `async def test_frontend_serving(mock_frontend_dir, async_client):`
- L432 [`MOCK`] `with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):`
- L455 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L460 [`MOCK`] `side_effect=mock_test,`
- L478 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L483 [`MOCK`] `side_effect=mock_test,`
- L500 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L505 [`MOCK`] `side_effect=mock_test,`
- L553 [`MOCK`] `async def mock_test(config, timeout=15.0):`
- L558 [`MOCK`] `side_effect=mock_test,`

### `tests/unit/test_server_concurrent_cache.py`
- L5 [`MOCK`] `from unittest.mock import patch`

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
- L26 [`PLACEHOLDER`] `'window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/", STEGO_KEY: "PLACEHOLDER_KEY_INJECTED_BY_CI" };\n',`
- L31 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_detects_public_and_stego_keys(`
- L36 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(tmp_path, strict=True)`
- L38 [`PLACEHOLDER`] `assert any("PUBLIC_KEY placeholder" in error for error in errors)`
- L39 [`PLACEHOLDER`] `assert any("STEGO_KEY placeholder" in error for error in errors)`
- L55 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=True) == []`
- L67 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(`
- L77 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=False) == []`
- L80 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_strict_requires_runtime_config_keys(`
- L95 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(tmp_path, strict=True)`

### `tests/unit/test_validate_workflows.py`
- L27 [`PLACEHOLDER`] `def test_validate_workflows_requires_pages_frontend_placeholder_guard(`
- L71 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output`
- L101 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output`

### `tests/unit/test_verify_pages_deployment.py`
- L129 [`PLACEHOLDER`] `def test_verify_pages_deployment_rejects_runtime_placeholder(tmp_path: Path) -> None:`
- L132 [`PLACEHOLDER`] `runtime_config='window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "PLACEHOLDER_PUBLIC_KEY", STEGO_KEY: "stego-key" };\n',`
- L141 [`PLACEHOLDER`] `assert any("placeholder marker" in error for error in errors)`

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
