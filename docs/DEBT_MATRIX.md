# Debt Matrix

Generated: `2026-05-12T17:48:42.714069+00:00`

## Summary

- Total markers: **3088**
- `ASSUMING`: **28**
- `FIXME`: **5**
- `MOCK`: **2613**
- `PLACEHOLDER`: **379**
- `TODO`: **46**
- `XXX`: **17**

## Categories

- `ci`: **1**
- `docs`: **20**
- `frontend`: **49**
- `other`: **1652**
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
| `CHANGELOG.md` | 8 | PLACEHOLDER, TODO |
| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 1648 | ASSUMING, FIXME, MOCK, PLACEHOLDER, TODO, XXX |
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
- L50 [`PLACEHOLDER`] `- **Frontend runtime-config deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to generate `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, preserving checked-in source JS while failing upload on missing runtime keys or placeholder markers.`
- L52 [`PLACEHOLDER`] `- **Deployed Pages URL smoke**: Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, public artifact aliases, health metadata, base64/chosen subscription endpoints, manifest hash parity, run identity, and placeholder-key absence.`
- L54 [`PLACEHOLDER`] `- **Frontend verifier fail-closed path**: Signed frontend artifacts now reject when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L57 [`PLACEHOLDER`] `- **Frontend runtime-config tests/workflow parity**: Added tests for placeholder detection/runtime-config generation and extended workflow validation so `deploy-pages.yml` cannot drop the frontend runtime-config guard or secret env wiring silently.`
- L101 [`PLACEHOLDER`] `- **Side-product deploy-secret scan**: Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers inside ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L105 [`PLACEHOLDER`] `- **Deterministic public artifact fixture**: Added a unit fixture that builds a Pages-style artifact from the real output generator, adds deploy aliases and static placeholders, refreshes the public contract, and validates the result with `scripts/validate_pages_artifact.py`.`
- L113 [`PLACEHOLDER`] `- **Frontend failover proof**: Added local IPFS/IPNS failover tests for the same-origin connectivity probe, placeholder-key no-op, gateway URL normalization, page/query/hash preservation, and session loop prevention; production-smoke now runs this proof.`
- L238 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts`

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
- L246 [`PLACEHOLDER`] `The latest deploy workflow still copies `frontend/.` into `output/`, injects placeholders, and deploys raw static assets. `deploy-pages.yml` `STATUS.md` still lists “frontend deployment must be made canonical: either tested Vite output or raw static output, not both.” `STATUS.md``
- L250 [`PLACEHOLDER`] `Also, deployment-time key injection is better than before, but the source still contains placeholder logic in `constants.js`, `stego.js`, and `verifier.js` according to the debt matrix. `DEBT_MATRIX.md` That is acceptable only if the deploy validator is guaranteed and post-deploy smoke proves the deployed artifact has no placeholder strings.`
- L252 [`PLACEHOLDER`] `**Amendment:** frontend placeholder injection is a mitigation, not final architecture. The canonical fix is a generated runtime config file plus fail-closed verification behavior.`
- L279 [`TODO`] `The project’s core rules say no active scanning of third-party infrastructure. `AGENTS.md` But README advertises offline tools that perform clean IP scan, proxy discovery, DNS probe, and lab-runner IP scans. `README.md` The debt matrix also lists TODOs in the DNS scanner bash tool and placeholder fields in the DNS scanner UI. `DEBT_MATRIX.md``
- L363 [`PLACEHOLDER`] `- **Frontend:** local-first and placeholder guards exist, but raw-static vs Vite build remains unresolved.`
- L391 [`PLACEHOLDER`] `11. **The frontend verifier/key model remains transitional.** Placeholder injection is guarded, but source placeholder material remains and canonical build path is unresolved. `STATUS.md` `DEBT_MATRIX.md``
- L472 [`PLACEHOLDER`] `- accepted user-facing placeholders`
- L474 [`MOCK`] `- test mocks`
- L475 [`MOCK`] `- production mocks`
- L505 [`PLACEHOLDER`] `4. Add deploy-time no-placeholder scan across all HTML/JS/CSS, not only known key files.`
- L513 [`PLACEHOLDER`] `4. Secret/placeholder checks inside ZIPs and frontend bundles.`
- L575 [`PLACEHOLDER`] `- Add no-placeholder/no-secret/no-raw-log checks when touching frontend, outputs, logs, or ZIPs.`
- L1596 [`PLACEHOLDER`] `- No placeholder public key in deployed artifact.`
- L1725 [`PLACEHOLDER`] `- Placeholder values.`
- L1793 [`PLACEHOLDER`] `- ZIP scanned for placeholder/deploy secrets.`
- L2226 [`PLACEHOLDER`] `- `frontend_placeholder_error``
- L2361 [`PLACEHOLDER`] `- Placeholder key deployment`
- L2475 [`PLACEHOLDER`] `- Frontend no placeholders.`
- L2997 [`PLACEHOLDER`] `- No placeholder leakage.`
- L3695 [`PLACEHOLDER`] `The prior source-of-truth audit said the repository had serious blockers: invalid workflow YAML, stale public artifacts, schema mismatches, inflated `total_working`, raw frontend deployment with placeholder keys, security defaults that overclaimed fail-closed behavior, and widespread docs drift.`
- L3697 [`PLACEHOLDER`] `The latest `STATUS.md` shows many of those have been actively remediated: workflow parsing, Pages contract files, `health.json`, `artifact_manifest.json`, shielded metric accounting, admin fail-closed behavior, CORS tightening, WebSocket lifecycle controls, lab live-test hardening, fetch redirect validation, frontend placeholder injection, protocol/output matrices, claim ledger, docs-sync, debt matrix, and local-first frontend assets.`
- L3709 [`TODO`] `The debt matrix is not cosmetic. It shows **1,402 tracked markers**, including 13 TODOs, 1 FIXME, 5 XXX, 126 PLACEHOLDER, 9 ASSUMING, and 1,248 MOCK markers. It separates categories and still lists production/frontend/tooling/docs debt, not only tests.`
- L3711 [`PLACEHOLDER`] `* `.github/workflows/deploy-pages.yml`: placeholder-related marker.`
- L3712 [`PLACEHOLDER`] `* `frontend/assets/js/constants.js`: placeholder public-key detection.`
- L3713 [`PLACEHOLDER`] `* `frontend/assets/js/stego.js`: `PLACEHOLDER_KEY_INJECTED_BY_CI`.`
- L3714 [`PLACEHOLDER`] `* `frontend/assets/js/verifier.js`: verification skips or weakens when public key is placeholder/missing.`
- L3715 [`MOCK`] `* `frontend/assets/js/washer_client.js`: “Mock status check.”`
- L3716 [`XXX`] `* `frontend/assets/js/lab.js`: `XXX` in generated bash temp-file path.`
- L3717 [`PLACEHOLDER`] `* `src/configstream/generators/base64.py`: intentionally encodes a placeholder when output would otherwise be empty.`
- L3718 [`TODO`] `* `src/configstream/tools/dns_scanner/bash/dnsScanner.sh`: several TODO markers.`
- L3719 [`TODO`] `* `scripts/generate_debt_matrix.py`: even the debt generator itself contains TODO/FIXME text.`
- L3721 [`PLACEHOLDER`] `Some of these are false positives because the debt scanner counts words inside docs/tests/guard code. But not all are harmless. The presence of frontend placeholder keys and verifier fallback paths means “no placeholder deployed” is only true if deploy-time injection succeeds and validation runs. The repository source itself still contains placeholder material by design.`
- L3755 [`PLACEHOLDER`] `* Live dashboard rendering with no placeholders.`
- L3760 [`PLACEHOLDER`] `The latest deploy workflow still copies `frontend/.` into `output/`, injects placeholders, and deploys raw static assets.  `STATUS.md` still lists “frontend deployment must be made canonical: either tested Vite output or raw static output, not both.”`
- L3762 [`PLACEHOLDER`] `Also, deployment-time key injection is better than before, but the source still contains placeholder logic in `constants.js`, `stego.js`, and `verifier.js` according to the debt matrix.  That is acceptable only if the deploy validator is guaranteed and post-deploy smoke proves the deployed artifact has no placeholder strings.`
- L3779 [`TODO`] `The project’s core rules say no active scanning of third-party infrastructure.  But README advertises offline tools that perform clean IP scan, proxy discovery, DNS probe, and lab-runner IP scans.  The debt matrix also lists TODOs in the DNS scanner bash tool and placeholder fields in the DNS scanner UI.`
- L3835 [`PLACEHOLDER`] `* **Frontend:** local-first and placeholder guards exist, but raw-static vs Vite build remains unresolved.`
- L3861 [`PLACEHOLDER`] `11. **The frontend verifier/key model remains transitional.** Placeholder injection is guarded, but source placeholder material remains and canonical build path is unresolved.`
- L3902 [`PLACEHOLDER`] `* accepted user-facing placeholders`
- L3904 [`MOCK`] `* test mocks`
- L3905 [`MOCK`] `* production mocks`
- L4046 [`PLACEHOLDER`] `- Pages deploy now generates `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, leaves checked-in source-shaped JS immutable, and fails before upload if required runtime keys are missing or placeholder markers remain; workflow and Pages artifact validation enforce this guard.`
- L4048 [`PLACEHOLDER`] `- Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, metadata/proxy API alias parity, health metadata, and placeholder-key absence.`
- L4049 [`PLACEHOLDER`] `- Frontend signed-artifact verification now fails closed when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L4063 [`PLACEHOLDER`] `- Optional IPFS/IPNS frontend failover is now covered by local tests: the frontend probes a same-origin static asset, skips placeholder IPNS keys, preserves the current leaf page/query/hash when building gateway URLs, normalizes gateway bases, and prevents repeated redirect attempts within the same session.`
- L4068 [`MOCK`] `- Debt matrix artifacts are portable: generated paths are repo-relative, generated debt files are excluded from self-scans, and marker summaries separate production/frontend/tooling/docs debt from test-only mocks.`
- L4125 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed`
- L4132 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed`
- L4213 [`PLACEHOLDER`] `- **Frontend runtime-config deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to generate `assets/js/runtime-config.js` from `CS_PUBLIC_KEY`/`STEGO_KEY` after copying frontend assets, preserving checked-in source JS while failing upload on missing runtime keys or placeholder markers.`
- L4215 [`PLACEHOLDER`] `- **Deployed Pages URL smoke**: Pages deployment now runs a post-upload HTTP smoke against the deployed URL, checking primary HTML pages, generated runtime config, public artifact aliases, health metadata, base64/chosen subscription endpoints, manifest hash parity, run identity, and placeholder-key absence.`
- L4217 [`PLACEHOLDER`] `- **Frontend verifier fail-closed path**: Signed frontend artifacts now reject when WebCrypto is unavailable or public key material is missing/placeholder, while unsigned local content remains parseable for offline use.`
- L4220 [`PLACEHOLDER`] `- **Frontend runtime-config tests/workflow parity**: Added tests for placeholder detection/runtime-config generation and extended workflow validation so `deploy-pages.yml` cannot drop the frontend runtime-config guard or secret env wiring silently.`
- L4264 [`PLACEHOLDER`] `- **Side-product deploy-secret scan**: Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers inside ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L4268 [`PLACEHOLDER`] `- **Deterministic public artifact fixture**: Added a unit fixture that builds a Pages-style artifact from the real output generator, adds deploy aliases and static placeholders, refreshes the public contract, and validates the result with `scripts/validate_pages_artifact.py`.`
- L4276 [`PLACEHOLDER`] `- **Frontend failover proof**: Added local IPFS/IPNS failover tests for the same-origin connectivity probe, placeholder-key no-op, gateway URL normalization, page/query/hash preservation, and session loop prevention; production-smoke now runs this proof.`
- L4401 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts`
- L4752 [`PLACEHOLDER`] `5. The deployed frontend path is now deliberately raw static for GitHub Pages, with generated runtime-config key injection, placeholder validation, workflow guards, and Pages artifact presence checks.`
- L4948 [`PLACEHOLDER`] `- dashboard rendering with no placeholders`
- L5048 [`PLACEHOLDER`] `11. Frontend verifier/key model is transitional until placeholder injection is replaced by a cleaner generated runtime config contract and live no-placeholder proof.`
- L5084 [`MOCK`] `- split real production defects, accepted tests/mocks, allowed user-facing placeholders, generated-doc false positives, and docs-only historical references.`
- L5131 [`PLACEHOLDER`] `- frontend external dependencies, placeholders, and `innerHTML``
- L5452 [`PLACEHOLDER`] `- The frontend renders the degraded state without placeholders.`
- L5769 [`PLACEHOLDER`] `- Production Pages previously risked serving placeholder key material; deploy now writes a generated runtime config artifact before upload.`
- L5776 [`PLACEHOLDER`] `- Added `scripts/validate_frontend_placeholders.py`.`
- L5777 [`PLACEHOLDER`] `- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.`
- L5780 [`PLACEHOLDER`] `- The validator fails if required runtime keys are missing, or if the public key placeholder marker or stego placeholder remains in source-shaped JS or the generated runtime config.`
- L5781 [`PLACEHOLDER`] `- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.`
- L5782 [`PLACEHOLDER`] `- Tests cover placeholder detection, runtime-config generation, optional non-strict stego handling, and workflow guard retention.`
- L5783 [`PLACEHOLDER`] `- `frontend/assets/js/verifier.js` now fails closed for signed objects when WebCrypto is unavailable or the public key is missing/placeholder, while preserving unsigned local/offline parsing.`
- L5784 [`PLACEHOLDER`] `- `tests/unit/test_frontend_verifier.py` executes the browser verifier script in Node VM and covers missing WebCrypto, missing key, placeholder key, and unsigned local content behavior.`
- L5788 [`PLACEHOLDER`] `- `scripts/deploy_artifact_smoke.py` now assembles a temporary Pages-shaped artifact, generates runtime config, validates placeholders and the public artifact contract, and runs `scripts/frontend_same_origin_smoke.cjs --root ... --require-runtime-config` against that exact artifact.`
- L5789 [`PLACEHOLDER`] `- `.github/workflows/deploy-pages.yml` now runs `scripts/verify_pages_deployment.py` after `actions/deploy-pages`, checking the deployed URL for primary HTML pages, runtime config, metadata/proxy alias parity, health metadata, and placeholder-key absence.`
- L5796 [`PLACEHOLDER`] `4. Fail production build if required public key/stego key placeholders remain.`
- L5798 [`PLACEHOLDER`] `6. Add placeholder leak tests.`
- L5806 [`PLACEHOLDER`] `- Deployed frontend contains no placeholder key strings.`
- L5810 [`PLACEHOLDER`] `- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.`
- L6267 [`PLACEHOLDER`] `- If the library is present but does not match the placeholder hash, validation fails.`
- L6342 [`TODO`] `- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.`
- L6430 [`MOCK`] `mocks from production/frontend/tooling/docs debt.`
- L6440 [`PLACEHOLDER`] `##### P3-4. Zero-byte and placeholder assets remain`
- L6451 [`PLACEHOLDER`] `3. Done: unreferenced root `NL` and `US` placeholder files were removed.`
- L6662 [`PLACEHOLDER`] `- Source placeholder key material has been removed from the runtime path; generated runtime config still needs deploy-smoke proof on a fully assembled artifact.`
- L6888 [`PLACEHOLDER`] `- Side-product ZIP validation now rejects deploy/CI secret assignments and placeholder markers in ZIP members while allowing normal proxy credentials and WireGuard/OpenVPN material.`
- L6892 [`PLACEHOLDER`] `- `tests/unit/test_output.py` now builds a deterministic Pages-style artifact from the real output generator, adds deploy aliases and static placeholder files, refreshes `health.json` / `artifact_manifest.json`, and validates the complete directory with `scripts/validate_pages_artifact.py`.`
- L6983 [`PLACEHOLDER`] `3. Public pages must never show unresolved placeholders.`
- L6992 [`PLACEHOLDER`] `same-origin static connectivity probe, placeholder IPNS-key no-op, gateway base`
- L7002 [`PLACEHOLDER`] `- placeholder leak tests`
- L7074 [`TODO`] `- zero TODO/FIXME`
- L7115 [`PLACEHOLDER`] `4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.`
- L7291 [`PLACEHOLDER`] `5. Done: fail deploy on missing runtime keys or placeholder key markers.`
- L7304 [`PLACEHOLDER`] `- Delete unused build path, unused scripts, and placeholder config files.`
- L7373 [`PLACEHOLDER`] `6. Add no-placeholder, no-network frontend, public contract, and security posture tests.`
- L7418 [`PLACEHOLDER`] `- frontend has no unresolved placeholders.`
- L7419 [`PLACEHOLDER`] `- no placeholder key material is deployed.`
- L7458 [`PLACEHOLDER`] `- No placeholder keys.`
- L7519 [`PLACEHOLDER`] `10. Frontend has no placeholder keys or unresolved template tokens.`
- L7554 [`PLACEHOLDER`] `**Resolution:** Updated `main.yml` to set `continue-on-error: true` for the `frontend-wasm` download step in the merge job. Ensure `scripts/build_wasm.sh` creates the necessary directories and placeholder dummy files gracefully if compilation fails.`
- L7633 [`ASSUMING`] `- `ASSUMING`: **9**`
- L7634 [`FIXME`] `- `FIXME`: **1**`
- L7635 [`MOCK`] `- `MOCK`: **1248**`
- L7636 [`PLACEHOLDER`] `- `PLACEHOLDER`: **126**`
- L7637 [`TODO`] `- `TODO`: **13**`
- L7638 [`XXX`] `- `XXX`: **5**`
- L7652 [`FIXME`] `- `FIXME` / `XXX`: fix inline before release freeze.`
- L7653 [`TODO`] `- `TODO`: create issue with owner + milestone.`
- L7654 [`MOCK`] `- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.`
- L7655 [`PLACEHOLDER`] `- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.`
- L7661 [`PLACEHOLDER`] `| `.github/workflows/deploy-pages.yml` | 1 | PLACEHOLDER |`
- L7662 [`ASSUMING`] `| `AGENTS.md` | 1 | ASSUMING |`
- L7663 [`PLACEHOLDER`] `| `CHANGELOG.md` | 4 | PLACEHOLDER, TODO |`
- L7664 [`PLACEHOLDER`] `| `CLOSURE_REPORT.md` | 1 | PLACEHOLDER |`
- L7665 [`MOCK`] `| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 34 | MOCK, PLACEHOLDER, TODO |`
- L7666 [`PLACEHOLDER`] `| `SECURITY.md` | 2 | PLACEHOLDER |`
- L7667 [`PLACEHOLDER`] `| `STATUS.md` | 3 | PLACEHOLDER |`
- L7668 [`ASSUMING`] `| `docs/wiki/encyclopedia/glossary/networking_terms.md` | 1 | ASSUMING |`
- L7669 [`XXX`] `| `docs/wiki/encyclopedia/glossary/security_concepts.md` | 1 | XXX |`
- L7670 [`XXX`] `| `docs/wiki/encyclopedia/networking/warp.md` | 1 | XXX |`
- L7671 [`ASSUMING`] `| `frontend/assets/js/analytics.js` | 3 | ASSUMING, PLACEHOLDER |`
- L7672 [`MOCK`] `| `frontend/assets/js/charts.js` | 1 | MOCK |`
- L7673 [`PLACEHOLDER`] `| `frontend/assets/js/constants.js` | 3 | PLACEHOLDER |`
- L7674 [`PLACEHOLDER`] `| `frontend/assets/js/i18n.js` | 12 | PLACEHOLDER |`
- L7675 [`XXX`] `| `frontend/assets/js/lab.js` | 1 | XXX |`
- L7676 [`ASSUMING`] `| `frontend/assets/js/main.js` | 2 | ASSUMING, PLACEHOLDER |`
- L7677 [`PLACEHOLDER`] `| `frontend/assets/js/stego.js` | 2 | PLACEHOLDER |`
- L7678 [`ASSUMING`] `| `frontend/assets/js/verifier.js` | 3 | ASSUMING, PLACEHOLDER |`
- L7679 [`MOCK`] `| `frontend/assets/js/washer_client.js` | 1 | MOCK |`
- L7680 [`PLACEHOLDER`] `| `frontend/index.html` | 1 | PLACEHOLDER |`
- L7681 [`PLACEHOLDER`] `| `frontend/lab-offline.html` | 1 | PLACEHOLDER |`
- L7682 [`PLACEHOLDER`] `| `frontend/lab.html` | 15 | PLACEHOLDER, XXX |`
- L7683 [`PLACEHOLDER`] `| `frontend/proxies.html` | 5 | PLACEHOLDER |`
- L7684 [`ASSUMING`] `| `frontend/service-worker.js` | 1 | ASSUMING |`
- L7685 [`FIXME`] `| `scripts/generate_debt_matrix.py` | 6 | FIXME, MOCK, PLACEHOLDER, TODO |`
- L7686 [`PLACEHOLDER`] `| `scripts/run_test_profile.py` | 1 | PLACEHOLDER |`
- L7687 [`PLACEHOLDER`] `| `scripts/validate_frontend_placeholders.py` | 10 | PLACEHOLDER |`
- L7688 [`PLACEHOLDER`] `| `scripts/validate_workflows.py` | 4 | PLACEHOLDER |`
- L7689 [`XXX`] `| `sources/manual_warp.txt` | 1 | XXX |`
- L7690 [`MOCK`] `| `src/configstream/anomaly.py` | 2 | MOCK |`
- L7691 [`PLACEHOLDER`] `| `src/configstream/constants.py` | 1 | PLACEHOLDER |`
- L7692 [`PLACEHOLDER`] `| `src/configstream/generators/base64.py` | 1 | PLACEHOLDER |`
- L7693 [`MOCK`] `| `src/configstream/history/tracker.py` | 1 | MOCK |`
- L7694 [`MOCK`] `| `src/configstream/intelligence/chaining.py` | 1 | MOCK |`
- L7695 [`PLACEHOLDER`] `| `src/configstream/quality/storage.py` | 7 | PLACEHOLDER |`
- L7696 [`MOCK`] `| `src/configstream/security_validator.py` | 4 | MOCK |`
- L7697 [`MOCK`] `| `src/configstream/tools/censorship_lab.py` | 1 | MOCK |`
- L7698 [`TODO`] `| `src/configstream/tools/dns_scanner/bash/dnsScanner.sh` | 7 | TODO |`
- L7699 [`PLACEHOLDER`] `| `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` | 3 | PLACEHOLDER |`
- L7700 [`MOCK`] `| `tests/e2e/test_failure_scenarios.py` | 4 | MOCK |`
- L7701 [`MOCK`] `| `tests/e2e/test_frontend.py` | 10 | MOCK |`
- L7702 [`MOCK`] `| `tests/e2e/test_mixed_protocols.py` | 10 | MOCK |`
- L7703 [`MOCK`] `| `tests/scenarios/test_failure_modes.py` | 9 | MOCK |`
- L7704 [`MOCK`] `| `tests/test_manager.py` | 19 | MOCK |`
- L7705 [`MOCK`] `| `tests/test_output_transport.py` | 7 | MOCK |`
- L7706 [`MOCK`] `| `tests/test_python_tester.py` | 18 | MOCK |`
- L7707 [`MOCK`] `| `tests/test_scanner.py` | 17 | MOCK |`
- L7708 [`MOCK`] `| `tests/test_warp_scraper.py` | 17 | MOCK |`
- L7709 [`MOCK`] `| `tests/test_washer_utils.py` | 1 | MOCK |`
- L7710 [`MOCK`] `| `tests/unit/converters/test_singbox_converters.py` | 1 | MOCK |`
- L7711 [`MOCK`] `| `tests/unit/coverage_boost/test_adaptive_workers_coverage.py` | 13 | MOCK |`
- L7712 [`MOCK`] `| `tests/unit/coverage_boost/test_blocklist_coverage.py` | 2 | MOCK |`
- L7713 [`MOCK`] `| `tests/unit/coverage_boost/test_cli_coverage.py` | 27 | MOCK |`
- L7714 [`MOCK`] `| `tests/unit/coverage_boost/test_server_coverage.py` | 1 | MOCK |`
- L7715 [`MOCK`] `| `tests/unit/coverage_boost/test_washer_coverage.py` | 7 | MOCK |`
- L7716 [`MOCK`] `| `tests/unit/fetcher/test_fetcher_core.py` | 2 | MOCK |`
- L7717 [`MOCK`] `| `tests/unit/generators/test_singbox_comprehensive.py` | 1 | MOCK |`
- L7718 [`MOCK`] `| `tests/unit/geoip/test_geoip_resolver.py` | 17 | MOCK |`
- L7719 [`MOCK`] `| `tests/unit/history/test_history_components.py` | 8 | MOCK |`
- L7720 [`MOCK`] `| `tests/unit/intelligence/test_chaining_extended.py` | 2 | MOCK |`
- L7721 [`MOCK`] `| `tests/unit/intelligence/test_vectors.py` | 1 | MOCK |`
- L7722 [`MOCK`] `| `tests/unit/quality/test_quality_components.py` | 2 | MOCK |`
- L7723 [`MOCK`] `| `tests/unit/security/test_censorship.py` | 5 | MOCK |`
- L7724 [`MOCK`] `| `tests/unit/security/test_rules.py` | 8 | MOCK |`
- L7725 [`MOCK`] `| `tests/unit/security/test_utls_wrapper.py` | 14 | MOCK |`
- L7726 [`MOCK`] `| `tests/unit/security/test_virus_total_comprehensive.py` | 75 | MOCK |`
- L7727 [`MOCK`] `| `tests/unit/test_adapters_comprehensive.py` | 6 | MOCK |`
- L7728 [`MOCK`] `| `tests/unit/test_adaptive_timeout_extra.py` | 4 | MOCK |`
- L7729 [`MOCK`] `| `tests/unit/test_adaptive_workers.py` | 3 | MOCK |`
- L7730 [`MOCK`] `| `tests/unit/test_analytics_output.py` | 7 | MOCK |`
- L7731 [`MOCK`] `| `tests/unit/test_anomaly_extended.py` | 9 | MOCK |`
- L7732 [`MOCK`] `| `tests/unit/test_backup.py` | 1 | MOCK |`
- L7733 [`MOCK`] `| `tests/unit/test_backup_extended.py` | 8 | MOCK |`
- L7734 [`MOCK`] `| `tests/unit/test_bot_cli.py` | 38 | MOCK |`
- L7735 [`ASSUMING`] `| `tests/unit/test_cache_warming.py` | 15 | ASSUMING, MOCK |`
- L7736 [`MOCK`] `| `tests/unit/test_cli_extended.py` | 23 | MOCK |`
- L7737 [`MOCK`] `| `tests/unit/test_cli_full.py` | 1 | MOCK |`
- L7738 [`MOCK`] `| `tests/unit/test_concurrency_extended.py` | 3 | MOCK |`
- L7739 [`MOCK`] `| `tests/unit/test_consumer.py` | 23 | MOCK |`
- L7740 [`MOCK`] `| `tests/unit/test_dns_batch_resolver.py` | 12 | MOCK |`
- L7741 [`MOCK`] `| `tests/unit/test_event_stream.py` | 65 | MOCK |`
- L7742 [`MOCK`] `| `tests/unit/test_fetcher.py` | 85 | MOCK |`
- L7743 [`MOCK`] `| `tests/unit/test_fetcher_advanced.py` | 18 | MOCK |`
- L7744 [`MOCK`] `| `tests/unit/test_fetcher_config.py` | 13 | MOCK |`
- L7745 [`MOCK`] `| `tests/unit/test_fetcher_resilience.py` | 8 | MOCK |`
- L7746 [`MOCK`] `| `tests/unit/test_fetcher_retries.py` | 12 | MOCK |`
- L7747 [`MOCK`] `| `tests/unit/test_filtering_extended.py` | 8 | MOCK |`
- L7748 [`MOCK`] `| `tests/unit/test_geoip_extended.py` | 3 | MOCK |`
- L7749 [`MOCK`] `| `tests/unit/test_go_tester_streaming.py` | 20 | MOCK |`
- L7750 [`MOCK`] `| `tests/unit/test_honeypot.py` | 71 | MOCK |`
- L7751 [`MOCK`] `| `tests/unit/test_init_module.py` | 2 | MOCK |`
- L7752 [`MOCK`] `| `tests/unit/test_output.py` | 4 | MOCK |`
- L7753 [`MOCK`] `| `tests/unit/test_output_advanced.py` | 1 | MOCK |`
- L7754 [`MOCK`] `| `tests/unit/test_output_full.py` | 13 | MOCK |`
- L7755 [`PLACEHOLDER`] `| `tests/unit/test_output_logic.py` | 1 | PLACEHOLDER |`
- L7756 [`MOCK`] `| `tests/unit/test_parsers_robustness.py` | 1 | MOCK |`
- L7757 [`MOCK`] `| `tests/unit/test_pipeline_coverage.py` | 38 | MOCK |`
- L7758 [`MOCK`] `| `tests/unit/test_pipeline_deep.py` | 38 | MOCK |`
- L7759 [`MOCK`] `| `tests/unit/test_pipeline_extended.py` | 64 | MOCK |`
- L7760 [`MOCK`] `| `tests/unit/test_pipeline_orchestration.py` | 29 | MOCK |`
- L7761 [`MOCK`] `| `tests/unit/test_pipeline_stages.py` | 125 | MOCK |`
- L7762 [`MOCK`] `| `tests/unit/test_producer_quality_accounting.py` | 2 | MOCK |`
- L7763 [`MOCK`] `| `tests/unit/test_proxy_history_extended.py` | 6 | MOCK |`
- L7764 [`MOCK`] `| `tests/unit/test_scheduler.py` | 4 | MOCK |`
- L7765 [`MOCK`] `| `tests/unit/test_security.py` | 26 | MOCK |`
- L7766 [`ASSUMING`] `| `tests/unit/test_security_validator.py` | 1 | ASSUMING |`
- L7767 [`MOCK`] `| `tests/unit/test_security_validator_extra.py` | 5 | MOCK |`
- L7768 [`ASSUMING`] `| `tests/unit/test_security_validator_full.py` | 1 | ASSUMING |`
- L7769 [`MOCK`] `| `tests/unit/test_server.py` | 34 | MOCK |`
- L7770 [`MOCK`] `| `tests/unit/test_server_new.py` | 1 | MOCK |`
- L7771 [`MOCK`] `| `tests/unit/test_singbox_binary_resolution.py` | 1 | MOCK |`
- L7772 [`MOCK`] `| `tests/unit/test_sorter.py` | 20 | MOCK |`
- L7773 [`MOCK`] `| `tests/unit/test_ss_ffi.py` | 47 | MOCK |`
- L7774 [`MOCK`] `| `tests/unit/test_utils.py` | 1 | MOCK |`
- L7775 [`MOCK`] `| `tests/unit/test_utils_extended.py` | 3 | MOCK |`
- L7776 [`PLACEHOLDER`] `| `tests/unit/test_validate_frontend_placeholders.py` | 12 | PLACEHOLDER |`
- L7777 [`PLACEHOLDER`] `| `tests/unit/test_validate_workflows.py` | 1 | PLACEHOLDER |`
- L7778 [`MOCK`] `| `tests/unit/test_washer.py` | 6 | MOCK |`
- L7779 [`MOCK`] `| `tests/unit/tools/test_dns_scanner.py` | 3 | MOCK |`
- L7780 [`MOCK`] `| `tests/unit/utils/test_cert.py` | 8 | MOCK |`
- L7785 [`PLACEHOLDER`] `- L136 [`PLACEHOLDER`] `python scripts/validate_frontend_placeholders.py --inject-env --strict output``
- L7788 [`ASSUMING`] `- L148 [`ASSUMING`] `*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.``
- L7791 [`PLACEHOLDER`] `- L36 [`PLACEHOLDER`] `- **Frontend placeholder deploy guard**: Added `scripts/validate_frontend_placeholders.py` and wired Pages deploy to inject `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets before upload.``
- L7792 [`PLACEHOLDER`] `- L37 [`PLACEHOLDER`] `- **Frontend placeholder tests/workflow parity**: Added tests for placeholder detection/injection and extended workflow validation so `deploy-pages.yml` cannot drop the frontend placeholder guard or secret env wiring silently.``
- L7793 [`PLACEHOLDER`] `- L68 [`PLACEHOLDER`] `- **Validation run**: `scripts/validate_workflows.py` passes for 6 workflow files; `scripts/validate_versions.py` passes; focused remediation tests pass with 127 tests across server, fetcher, output, deploy-contract, analytics, merge, docs hygiene, frontend-placeholder, lab-strategy, concurrency-contract, producer-quality, logging-sanitization, workflow, and version validation.``
- L7794 [`TODO`] `- L191 [`TODO`] `- Full codebase scan: zero TODOs/FIXMEs, zero unused private functions, zero dead aliases, zero redundant exception tuples, zero `orjson` + `ensure_ascii` conflicts``
- L7797 [`PLACEHOLDER`] `- L11 [`PLACEHOLDER`] `**Resolution:** Updated `main.yml` to set `continue-on-error: true` for the `frontend-wasm` download step in the merge job. Ensure `scripts/build_wasm.sh` creates the necessary directories and placeholder dummy files gracefully if compilation fails.``
- L7800 [`PLACEHOLDER`] `- L20 [`PLACEHOLDER`] `5. The deployed frontend path bypasses the Vite build output and serves raw static files with placeholder key material.``
- L7801 [`PLACEHOLDER`] `- L57 [`PLACEHOLDER`] `- frontend external dependencies, placeholders, and `innerHTML```
- L7802 [`PLACEHOLDER`] `- L378 [`PLACEHOLDER`] `- The frontend renders the degraded state without placeholders.``
- L7803 [`PLACEHOLDER`] `- L679 [`PLACEHOLDER`] `Status: partially remediated on 2026-05-04. Pages deploy now injects and validates frontend placeholders; the larger Vite-vs-raw-frontend production-build decision remains open.``
- L7804 [`PLACEHOLDER`] `- L683 [`PLACEHOLDER`] `- `frontend/assets/js/constants.js` contains placeholder `PUBLIC_KEY`.``
- L7805 [`PLACEHOLDER`] `- L684 [`PLACEHOLDER`] `- `frontend/assets/js/stego.js` contains `PLACEHOLDER_KEY_INJECTED_BY_CI`.``
- L7806 [`PLACEHOLDER`] `- L693 [`PLACEHOLDER`] `- Production Pages likely serves placeholder key material.``
- L7807 [`PLACEHOLDER`] `- L700 [`PLACEHOLDER`] `- Added `scripts/validate_frontend_placeholders.py`.``
- L7808 [`PLACEHOLDER`] `- L701 [`PLACEHOLDER`] `- Pages deploy runs `python scripts/validate_frontend_placeholders.py --inject-env --strict output` after copying frontend assets and before refreshing the public artifact contract.``
- L7809 [`PLACEHOLDER`] `- L702 [`PLACEHOLDER`] `- Pages deploy now passes `CS_PUBLIC_KEY` and `STEGO_KEY` into the frontend placeholder guard step from GitHub secrets.``
- L7810 [`PLACEHOLDER`] `- L705 [`PLACEHOLDER`] `- The validator fails if the public key placeholder marker or stego placeholder remains in the Pages artifact.``
- L7811 [`PLACEHOLDER`] `- L706 [`PLACEHOLDER`] `- `scripts/validate_workflows.py` now requires the Pages frontend placeholder guard and secret env wiring.``
- L7812 [`PLACEHOLDER`] `- L707 [`PLACEHOLDER`] `- Tests cover placeholder detection, env injection, optional non-strict stego handling, and workflow guard retention.``
- L7813 [`PLACEHOLDER`] `- L714 [`PLACEHOLDER`] `4. Fail production build if required public key/stego key placeholders remain.``
- L7814 [`PLACEHOLDER`] `- L716 [`PLACEHOLDER`] `6. Add placeholder leak tests.``
- L7815 [`PLACEHOLDER`] `- L727 [`PLACEHOLDER`] `- Deployed frontend contains no placeholder key strings.``
- L7816 [`PLACEHOLDER`] `- L731 [`PLACEHOLDER`] `- After each frontend contract change, verify backend output, deploy workflow, frontend files, tests, README/wiki/security/status/changelog, and delete stale placeholder/build-path language completely.``
- L7817 [`PLACEHOLDER`] `- L1183 [`PLACEHOLDER`] `- If the library is present but does not match the placeholder hash, validation fails.``
- L7818 [`TODO`] `- L1258 [`TODO`] `- `STATUS.md` and `CHANGELOG.md` claim zero TODO/FIXME despite generated debt matrices listing many markers.``
- L7819 [`MOCK`] `- L1336 [`MOCK`] `3. Separate test-only mocks from production TODOs.``
- L7820 [`PLACEHOLDER`] `- L1341 [`PLACEHOLDER`] `### P3-4. Zero-byte and placeholder assets remain``
- L7821 [`PLACEHOLDER`] `- L1554 [`PLACEHOLDER`] `- Placeholder key material remains.``
- L7822 [`PLACEHOLDER`] `- L1560 [`PLACEHOLDER`] `- Make frontend local-first, build-driven, no-placeholder, and no-network smoke-tested.``
- L7823 [`PLACEHOLDER`] `- L1813 [`PLACEHOLDER`] `3. Public pages must never show unresolved placeholders.``
- L7824 [`PLACEHOLDER`] `- L1823 [`PLACEHOLDER`] `- placeholder leak tests``
- L7825 [`TODO`] `- L1895 [`TODO`] `- zero TODO/FIXME``
- L7826 [`PLACEHOLDER`] `- L1936 [`PLACEHOLDER`] `4. **No-placeholder gate:** Add a CI check for unresolved `{tokens}`, placeholder keys, example secrets, and stale production-ready claims.``
- L7827 [`PLACEHOLDER`] `- L2112 [`PLACEHOLDER`] `5. Fail build on placeholder keys.``
- L7828 [`PLACEHOLDER`] `- L2125 [`PLACEHOLDER`] `- Delete unused build path, unused scripts, and placeholder config files.``
- L7829 [`PLACEHOLDER`] `- L2194 [`PLACEHOLDER`] `6. Add no-placeholder, no-network frontend, public contract, and security posture tests.``
- L7830 [`PLACEHOLDER`] `- L2239 [`PLACEHOLDER`] `- frontend has no unresolved placeholders.``
- L7831 [`PLACEHOLDER`] `- L2240 [`PLACEHOLDER`] `- no placeholder key material is deployed.``
- L7832 [`PLACEHOLDER`] `- L2279 [`PLACEHOLDER`] `- No placeholder keys.``
- L7833 [`PLACEHOLDER`] `- L2339 [`PLACEHOLDER`] `10. Frontend has no placeholder keys or unresolved template tokens.``
- L7836 [`PLACEHOLDER`] `- L46 [`PLACEHOLDER`] `- Deploy fails if the public-key placeholder or stego placeholder remains in the Pages artifact.``
- L7837 [`PLACEHOLDER`] `- L47 [`PLACEHOLDER`] `- Workflow validation enforces the frontend placeholder guard so it cannot be removed from deploy without breaking validation.``
- L7840 [`PLACEHOLDER`] `- L40 [`PLACEHOLDER`] `- Pages deploy now injects `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets and fails before upload if frontend public-key or stego placeholders remain; workflow validation enforces this guard.``
- L7841 [`PLACEHOLDER`] `- L85 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed``
- L7842 [`PLACEHOLDER`] `- L92 [`PLACEHOLDER`] `- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed``
- L7845 [`ASSUMING`] `- L114 [`ASSUMING`] `*   **ConfigStream Usage:** Some parsers reject input if the "Noise Ratio" (non-printable characters) is too high, assuming it's garbage. Conversely, obfuscation protocols add noise to look like static.``
- L7848 [`XXX`] `- L73 [`XXX`] `*   **Format:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (36 characters with hyphens).``
- L7851 [`XXX`] `- L96 [`XXX`] `*   **WARP+ Key:** Format `xxxxxxxx-xxxxxxxx-xxxxxxxx`. Provides optimized routing (Argo Smart Routing). Optional — free tier is sufficient for circumvention.``
- L7854 [`PLACEHOLDER`] `- L40 [`PLACEHOLDER`] `// Show empty state or placeholder``
- L7855 [`PLACEHOLDER`] `- L161 [`PLACEHOLDER`] `container.innerHTML = '<div class="error-placeholder">Visualization Unavailable (Network Error)</div>';``
- L7856 [`ASSUMING`] `- L776 [`ASSUMING`] `// Assuming all rejection reasons are worth showing if present``
- L7859 [`MOCK`] `- L106 [`MOCK`] `// Audit: Removed random mock data to prevent misleading users.``
- L7862 [`PLACEHOLDER`] `- L29 [`PLACEHOLDER`] `// Validation: Detect placeholder values in production``
- L7863 [`PLACEHOLDER`] `- L43 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder PUBLIC_KEY!");``
- L7864 [`PLACEHOLDER`] `- L48 [`PLACEHOLDER`] `logError("❌ CRITICAL: Production deployment using placeholder IPNS_KEY!");``
- L7867 [`PLACEHOLDER`] `- L135 [`PLACEHOLDER`] `"byow.url.placeholder": "Paste your Cloudflare Worker URL...",``
- L7868 [`PLACEHOLDER`] `- L136 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Optional: UUID",``
- L7869 [`PLACEHOLDER`] `- L362 [`PLACEHOLDER`] `"byow.url.placeholder": "在此输入 Cloudflare Worker 地址...",``
- L7870 [`PLACEHOLDER`] `- L363 [`PLACEHOLDER`] `"byow.uuid.placeholder": "可选: UUID",``
- L7871 [`PLACEHOLDER`] `- L582 [`PLACEHOLDER`] `"byow.url.placeholder": "آدرس Cloudflare Worker خود را وارد کنید...",``
- L7872 [`PLACEHOLDER`] `- L583 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختیاری: UUID",``
- L7873 [`PLACEHOLDER`] `- L802 [`PLACEHOLDER`] `"byow.url.placeholder": "Вставьте ссылку на ваш Cloudflare Worker...",``
- L7874 [`PLACEHOLDER`] `- L803 [`PLACEHOLDER`] `"byow.uuid.placeholder": "Опционально: UUID",``
- L7875 [`PLACEHOLDER`] `- L1022 [`PLACEHOLDER`] `"byow.url.placeholder": "رابط Cloudflare Worker...",``
- L7876 [`PLACEHOLDER`] `- L1023 [`PLACEHOLDER`] `"byow.uuid.placeholder": "اختياري: UUID",``
- L7877 [`PLACEHOLDER`] `- L1187 [`PLACEHOLDER`] `if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {``
- L7878 [`PLACEHOLDER`] `- L1188 [`PLACEHOLDER`] `el.setAttribute('placeholder', translation);``
- L7881 [`XXX`] `- L1425 [`XXX`] `CFG=$(mktemp /tmp/cs-chain-XXXX.json)``
- L7884 [`ASSUMING`] `- L102 [`ASSUMING`] `// Assuming proxies have 'id'``
- L7885 [`PLACEHOLDER`] `- L183 [`PLACEHOLDER`] `// Initialize immediately with defaults to avoid "--" flash or placeholders``
- L7888 [`PLACEHOLDER`] `- L9 [`PLACEHOLDER`] `const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";``
- L7889 [`PLACEHOLDER`] `- L13 [`PLACEHOLDER`] `SECRET_KEY === "PLACEHOLDER_KEY_INJECTED_BY_CI" ||``
- L7892 [`PLACEHOLDER`] `- L42 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {``
- L7893 [`ASSUMING`] `- L49 [`ASSUMING`] `// Assuming Base64 SPKI from constants.js example``
- L7894 [`PLACEHOLDER`] `- L96 [`PLACEHOLDER`] `if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {``
- L7897 [`MOCK`] `- L9 [`MOCK`] `// Mock status check``
- L7900 [`PLACEHOLDER`] `- L515 [`PLACEHOLDER`] `placeholder="your-worker.username.workers.dev"``
- L7903 [`PLACEHOLDER`] `- L129 [`PLACEHOLDER`] `warp:'<div class="row"><div><label>Clean IP</label><input data-f="ip" value="162.159.192.1"></div><div><label>Port</label><input data-f="port" type="number" value="2408"></div></div><div><label>WARP+ Key (optional)</label><input data-f="key" placeholder="Leave blank for free"></div>',``
- L7906 [`PLACEHOLDER`] `- L573 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="localProxyAddr" placeholder="127.0.0.1:1080">``
- L7907 [`PLACEHOLDER`] `- L584 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="proxyUri" placeholder="vless://uuid@server:443?type=ws&security=tls&sni=example.com#MyProxy"></textarea>``
- L7908 [`PLACEHOLDER`] `- L628 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="manualCleanIps" placeholder="162.159.192.1:2408&#10;188.114.98.224:854"></textarea>``
- L7909 [`PLACEHOLDER`] `- L710 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warpKeyInput" placeholder="Leave blank for free tier">``
- L7910 [`XXX`] `- L711 [`XXX`] `<div class="hint">WARP+ key for better speed. Format: xxxxxxxx-xxxxxxxx-xxxxxxxx</div>``
- L7911 [`PLACEHOLDER`] `- L717 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2CleanIp" placeholder="162.159.192.1:2408">``
- L7912 [`PLACEHOLDER`] `- L722 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="warp2Key" placeholder="Leave blank for free tier">``
- L7913 [`PLACEHOLDER`] `- L732 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragSize" value="10-30" placeholder="10-30">``
- L7914 [`PLACEHOLDER`] `- L737 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="fragDelay" value="5-10" placeholder="5-10">``
- L7915 [`PLACEHOLDER`] `- L789 [`PLACEHOLDER`] `<input type="text" class="lab-input" id="workerUrl" placeholder="https://my-worker.username.workers.dev">``
- L7916 [`PLACEHOLDER`] `- L814 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="1" placeholder="127.0.0.1:1080 or vless://...">``
- L7917 [`PLACEHOLDER`] `- L836 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="2" placeholder="10.0.0.50:3128 or trojan://...">``
- L7918 [`PLACEHOLDER`] `- L857 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="3" placeholder="162.159.192.1:2408 or vmess://...">``
- L7919 [`PLACEHOLDER`] `- L878 [`PLACEHOLDER`] `<input type="text" class="lab-input relay-layer-addr" data-layer="4" placeholder="ss://... or socks5://...">``
- L7920 [`PLACEHOLDER`] `- L892 [`PLACEHOLDER`] `<textarea class="lab-textarea" id="customOutboundsJson" placeholder='[{"type":"wireguard","tag":"warp-out","server":"162.159.192.1",...}]' style="min-height:160px;"></textarea>``
- L7923 [`PLACEHOLDER`] `- L140 [`PLACEHOLDER`] `<input type="text" id="worker-url" data-i18n="byow.url.placeholder" placeholder="Paste Worker URL..." class="input-modern">``
- L7924 [`PLACEHOLDER`] `- L141 [`PLACEHOLDER`] `<input type="text" id="worker-uuid" data-i18n="byow.uuid.placeholder" placeholder="UUID (Optional)" class="input-modern input-short">``
- L7925 [`PLACEHOLDER`] `- L154 [`PLACEHOLDER`] `<input type="text" id="searchInput" data-i18n="filters.search" placeholder="e.g., fastest US vmess, or Germany < 100ms" aria-label="Search proxies">``
- L7926 [`PLACEHOLDER`] `- L188 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMin" placeholder="Min" aria-label="Minimum latency">``
- L7927 [`PLACEHOLDER`] `- L190 [`PLACEHOLDER`] `<input type="number" id="filterLatencyMax" placeholder="Max" aria-label="Maximum latency">``
- L7930 [`ASSUMING`] `- L42 [`ASSUMING`] `// Assuming prefix "configstream-v" from cache-config.js logic``
- L7933 [`TODO`] `- L3 [`TODO`] `"""Generate a repository debt matrix from TODO/FIXME-style markers."""``
- L7934 [`TODO`] `- L16 [`TODO`] `PATTERN = r"(?i)(TODO|FIXME|XXX|MOCK|@mock|placeholder|assuming)"``
- L7935 [`FIXME`] `- L160 [`FIXME`] `"- `FIXME` / `XXX`: fix inline before release freeze.",``
- L7936 [`TODO`] `- L161 [`TODO`] `"- `TODO`: create issue with owner + milestone.",``
- L7937 [`MOCK`] `- L162 [`MOCK`] `"- `MOCK` / `@MOCK`: production mocks require owner review; test-only mocks are tracked separately.",``
- L7938 [`PLACEHOLDER`] `- L163 [`PLACEHOLDER`] `"- `PLACEHOLDER` / `ASSUMING`: remove assumptions, enforce validation.",``
- L7941 [`PLACEHOLDER`] `- L94 [`PLACEHOLDER`] `"tests/unit/test_validate_frontend_placeholders.py",``
- L7943 [`PLACEHOLDER`] `##### `scripts/validate_frontend_placeholders.py``
- L7944 [`PLACEHOLDER`] `- L4 [`PLACEHOLDER`] `This guard keeps deploy artifacts from silently shipping placeholder verification``
- L7945 [`PLACEHOLDER`] `- L18 [`PLACEHOLDER`] `PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")``
- L7946 [`PLACEHOLDER`] `- L19 [`PLACEHOLDER`] `STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"``
- L7947 [`PLACEHOLDER`] `- L68 [`PLACEHOLDER`] `def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:``
- L7948 [`PLACEHOLDER`] `- L77 [`PLACEHOLDER`] `if any(marker in constants for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):``
- L7949 [`PLACEHOLDER`] `- L79 [`PLACEHOLDER`] `"Frontend PUBLIC_KEY placeholder remains in assets/js/constants.js"``
- L7950 [`PLACEHOLDER`] `- L87 [`PLACEHOLDER`] `if STEGO_KEY_PLACEHOLDER in stego:``
- L7951 [`PLACEHOLDER`] `- L89 [`PLACEHOLDER`] `"Frontend STEGO_KEY placeholder remains in assets/js/stego.js"``
- L7952 [`PLACEHOLDER`] `- L120 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(root, strict=bool(args.strict))``
- L7953 [`PLACEHOLDER`] `- L126 [`PLACEHOLDER`] `print("OK: frontend production placeholders validated.")``
- L7956 [`PLACEHOLDER`] `- L46 [`PLACEHOLDER`] `def _deploy_pages_has_frontend_placeholder_guard(path: Path) -> bool:``
- L7957 [`PLACEHOLDER`] `- L52 [`PLACEHOLDER`] `"scripts/validate_frontend_placeholders.py --inject-env --strict output"``
- L7958 [`PLACEHOLDER`] `- L108 [`PLACEHOLDER`] `and not _deploy_pages_has_frontend_placeholder_guard(path)``
- L7959 [`PLACEHOLDER`] `- L111 [`PLACEHOLDER`] `f"{path}: missing frontend placeholder injection/validation guard"``
- L7962 [`XXX`] `- L10 [`XXX`] `wireguard://UJckB8h6r2P6xxx8UEspxw8r3YkpzBEbjxol3jeoqEw%3D@188.114.97.82:5956?address=172.16.0.2/32, 2606:4700:110:846c:e510:bfa1:ea9f:5247/128&publickey=bmXOC%2BF1FxEMF9dyiK2H5%2F1SUtzH0JuVo51h2wPfgyo%3D&reserved=61%2C41%2C250#Tel= @arshiacomplus wire``
- L7965 [`MOCK`] `- L193 [`MOCK`] `# However, the test 'test_failure_mode_anomaly_db_crash' explicitly mocks this method``
- L7966 [`MOCK`] `- L194 [`MOCK`] `# to raise RuntimeError. If the real method catches it, the test mock is bypassed if we use spy.``
- L7969 [`PLACEHOLDER`] `- L128 [`PLACEHOLDER`] `"ws",  # Test fixtures / transport placeholders``
- L7972 [`PLACEHOLDER`] `- L12 [`PLACEHOLDER`] `a minimal placeholder is encoded so output files are always ≥ 1 byte.``
- L7975 [`MOCK`] `- L97 [`MOCK`] `# Fallback for mock storage``
- L7978 [`MOCK`] `- L187 [`MOCK`] `)  # Fallback if library returns raw float (unlikely for geopy but good for mocks)``
- L7981 [`PLACEHOLDER`] `- L354 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns_to_use))``
- L7982 [`PLACEHOLDER`] `- L376 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec``
- L7983 [`PLACEHOLDER`] `- L384 [`PLACEHOLDER`] `f"INSERT INTO source_stats ({column_list}) VALUES ({placeholders})",  # nosec``
- L7984 [`PLACEHOLDER`] `- L396 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(cols_no_id))``
- L7985 [`PLACEHOLDER`] `- L403 [`PLACEHOLDER`] `f"INSERT INTO source_runs ({','.join(cols_no_id)}) VALUES ({placeholders})",  # nosec``
- L7986 [`PLACEHOLDER`] `- L419 [`PLACEHOLDER`] `placeholders = ",".join(["?"] * len(columns))``
- L7987 [`PLACEHOLDER`] `- L422 [`PLACEHOLDER`] `f"INSERT INTO proxy_history VALUES ({placeholders})",  # nosec``
- L7990 [`MOCK`] `- L6 [`MOCK`] `# Import urlparse directly to allow mocking in tests``
- L7991 [`MOCK`] `- L153 [`MOCK`] `Internal check for address safety. Used by tests to mock safety checks.``
- L7992 [`MOCK`] `- L177 [`MOCK`] `# Use internal check (to allow mocking by tests)``
- L7993 [`MOCK`] `- L279 [`MOCK`] `# Use SecurityValidator.validate_proxy_config to allow mocking on the class``
- L7996 [`MOCK`] `- L63 [`MOCK`] `"""Mock IP blocklist for testing."""``
- L7999 [`TODO`] `- L130 [`TODO`] `barCharTodo=" "``
- L8000 [`TODO`] `- L140 [`TODO`] `# The number of done and todo characters``
- L8001 [`TODO`] `- L142 [`TODO`] `todo=$(bc <<< "scale=0; $barSize - $done")``
- L8002 [`TODO`] `- L143 [`TODO`] `# build the done and todo sub-bars``
- L8003 [`TODO`] `- L145 [`TODO`] `todoSubBar=$(printf "%${todo}s" | tr " " "${barCharTodo} - 1") # 1 for barSplitter``
- L8004 [`TODO`] `- L146 [`TODO`] `spacesSubBar=$(printf "%${todo}s" | tr " " " ")``
- L8005 [`TODO`] `- L149 [`TODO`] `progressBar="| Progress bar of main IPs: [${doneSubBar}${barSplitter}${todoSubBar}] ${percent}%${spacesSubBar}" # Some end space for pretty formatting``
- L8008 [`PLACEHOLDER`] `- L722 [`PLACEHOLDER`] `placeholder="Enter path or click Browse",``
- L8009 [`PLACEHOLDER`] `- L734 [`PLACEHOLDER`] `placeholder="e.g., google.com",``
- L8010 [`PLACEHOLDER`] `- L758 [`PLACEHOLDER`] `placeholder="100",``
- L8013 [`MOCK`] `- L12 [`MOCK`] `# Mock quality tracker to reject everything``
- L8014 [`MOCK`] `- L37 [`MOCK`] `# Mock AnomalyDetector to fail on is_safe``
- L8015 [`MOCK`] `- L43 [`MOCK`] `# Mock fetcher to return something``
- L8016 [`MOCK`] `- L58 [`MOCK`] `# Mock GeoIP``
- L8019 [`MOCK`] `- L45 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing``
- L8020 [`MOCK`] `- L107 [`MOCK`] `# Mock metadata.json to prevent update-detector from failing``
- L8021 [`MOCK`] `- L145 [`MOCK`] `# Mock the metadata request data (using canonical field names from v2.0.8)``
- L8022 [`MOCK`] `- L146 [`MOCK`] `mock_data = {``
- L8023 [`MOCK`] `- L161 [`MOCK`] `mock_json = json.dumps(mock_data)``
- L8024 [`MOCK`] `- L163 [`MOCK`] `# Inject a mock fetch function that returns our data for statistics endpoints``
- L8025 [`MOCK`] `- L169 [`MOCK`] `// Mock metadata.json (unified stats) and api/stats endpoints``
- L8026 [`MOCK`] `- L174 [`MOCK`] `json: async () => ({mock_json})``
- L8027 [`MOCK`] `- L180 [`MOCK`] `// Mock window.api.fetchStatistics directly if needed``
- L8028 [`MOCK`] `- L182 [`MOCK`] `window.api.fetchStatistics = async () => ({mock_json});``
- L8031 [`MOCK`] `- L28 [`MOCK`] `# 2. Mock external dependencies that might block or fail without network``
- L8032 [`MOCK`] `- L30 [`MOCK`] `# Mock GeoIP to return deterministic data``
- L8033 [`MOCK`] `- L34 [`MOCK`] `# We need self because we are mocking the instance method or class method?``
- L8034 [`MOCK`] `- L35 [`MOCK`] `# Actually standard mock usually mocks the function on the class.``
- L8035 [`MOCK`] `- L49 [`MOCK`] `# Mock Blocklist update``
- L8036 [`MOCK`] `- L55 [`MOCK`] `# Mock Output Generation to avoid filesystem overhead but verify data presence``
- L8037 [`MOCK`] `- L60 [`MOCK`] `# The roadmap says: "assert that parsing, validation, dedup, washing, and GeoIP enrichment all execute without mocks."``
- L8038 [`MOCK`] `- L62 [`MOCK`] `# So we MOCKED GeoIP above. The roadmap allows mocks for things that strictly require network.``
- L8039 [`MOCK`] `- L64 [`MOCK`] `# However, we need to mock `generate_stego_assets` since it requires assets/images which might not exist in tmp env.``
- L8040 [`MOCK`] `- L66 [`MOCK`] `# So we remove the mock that causes AttributeError.``
- L8043 [`MOCK`] `- L16 [`MOCK`] `# Mock SourceQualityTracker to always return False for should_fetch``
- L8044 [`MOCK`] `- L27 [`MOCK`] `# Mock Blocklist update to avoid network``
- L8045 [`MOCK`] `- L64 [`MOCK`] `# Mock SourceQualityTracker to allow fetch``
- L8046 [`MOCK`] `- L70 [`MOCK`] `# Mock network fetch``
- L8047 [`MOCK`] `- L85 [`MOCK`] `# Mock Blocklist``
- L8048 [`MOCK`] `- L91 [`MOCK`] `# Mock GeoIP``
- L8049 [`MOCK`] `- L94 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData``
- L8050 [`MOCK`] `- L126 [`MOCK`] `# Mock fetch/geoip/blocklist as usual``
- L8051 [`MOCK`] `- L148 [`MOCK`] `# Use async mock for GeoIP lookup and keyword arguments for GeoData``
- L8054 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8055 [`MOCK`] `- L8 [`MOCK`] `def mock_settings():``
- L8056 [`MOCK`] `- L9 [`MOCK`] `with patch("configstream.testers.manager.AppSettings") as MockSettings:``
- L8057 [`MOCK`] `- L10 [`MOCK`] `settings = MockSettings.return_value``
- L8058 [`MOCK`] `- L16 [`MOCK`] `async def test_singbox_tester_dry_run(mock_settings):``
- L8059 [`MOCK`] `- L29 [`MOCK`] `async def test_singbox_tester_batch_dry_run(mock_settings):``
- L8060 [`MOCK`] `- L47 [`MOCK`] `async def test_singbox_tester_cache_hit(mock_settings):``
- L8061 [`MOCK`] `- L48 [`MOCK`] `cache = MagicMock()``
- L8062 [`MOCK`] `- L72 [`MOCK`] `async def test_singbox_tester_python_direct(mock_settings):``
- L8063 [`MOCK`] `- L74 [`MOCK`] `tester.python_tester.test_direct = AsyncMock(``
- L8064 [`MOCK`] `- L75 [`MOCK`] `return_value=MagicMock(is_working=True)``
- L8065 [`MOCK`] `- L90 [`MOCK`] `async def test_singbox_tester_go_fallback(mock_settings):``
- L8066 [`MOCK`] `- L92 [`MOCK`] `# Mock Go tester as unavailable``
- L8067 [`MOCK`] `- L94 [`MOCK`] `tester.python_tester.test_via_singbox = AsyncMock(``
- L8068 [`MOCK`] `- L95 [`MOCK`] `return_value=MagicMock(is_working=True)``
- L8069 [`MOCK`] `- L103 [`MOCK`] `# Should call python tester via semaphore wrapper (internal details hard to mock perfectly, but we check if result populated)``
- L8070 [`MOCK`] `- L104 [`MOCK`] `# Actually we mocked the method, so let's verify call.``
- L8071 [`MOCK`] `- L111 [`MOCK`] `async def test_singbox_tester_close(mock_settings):``
- L8072 [`MOCK`] `- L113 [`MOCK`] `tester.go_tester.close = AsyncMock()``
- L8075 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8076 [`MOCK`] `- L9 [`MOCK`] `def mock_history():``
- L8077 [`MOCK`] `- L10 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8078 [`MOCK`] `- L11 [`MOCK`] `hist = MockHistory.return_value``
- L8079 [`MOCK`] `- L16 [`MOCK`] `def test_save_json(tmp_path, mock_history):``
- L8080 [`MOCK`] `- L35 [`MOCK`] `def test_save_json_outputs_array_not_single_object(tmp_path, mock_history):``
- L8081 [`MOCK`] `- L50 [`MOCK`] `def test_save_json_compress(tmp_path, mock_history):``
- L8084 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8085 [`MOCK`] `- L8 [`MOCK`] `def mock_settings():``
- L8086 [`MOCK`] `- L9 [`MOCK`] `settings = MagicMock()``
- L8087 [`MOCK`] `- L16 [`MOCK`] `async def test_python_tester_direct_http(mock_settings):``
- L8088 [`MOCK`] `- L17 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8089 [`MOCK`] `- L22 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:``
- L8090 [`MOCK`] `- L23 [`MOCK`] `session = MockSession.return_value``
- L8091 [`MOCK`] `- L26 [`MOCK`] `# Mock successful response``
- L8092 [`MOCK`] `- L27 [`MOCK`] `resp = MagicMock()``
- L8093 [`MOCK`] `- L38 [`MOCK`] `async def test_python_tester_direct_fail(mock_settings):``
- L8094 [`MOCK`] `- L39 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8095 [`MOCK`] `- L47 [`MOCK`] `with patch("aiohttp.ClientSession") as MockSession:``
- L8096 [`MOCK`] `- L48 [`MOCK`] `session = MockSession.return_value``
- L8097 [`MOCK`] `- L51 [`MOCK`] `# Mock exception for get()``
- L8098 [`MOCK`] `- L75 [`MOCK`] `async def test_python_tester_singbox_missing_factory(mock_settings):``
- L8099 [`MOCK`] `- L77 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8100 [`MOCK`] `- L91 [`MOCK`] `async def test_python_tester_no_config(mock_settings):``
- L8101 [`MOCK`] `- L92 [`MOCK`] `tester = PythonTester(mock_settings)``
- L8104 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8105 [`MOCK`] `- L8 [`MOCK`] `# Mock settings to NOT force scanner``
- L8106 [`MOCK`] `- L9 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8107 [`MOCK`] `- L10 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False``
- L8108 [`MOCK`] `- L18 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8109 [`MOCK`] `- L19 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = True``
- L8110 [`MOCK`] `- L20 [`MOCK`] `MockSettings.return_value.CONFIGSTREAM_TESTER_BIN = "/bin/ls"  # Dummy path``
- L8111 [`MOCK`] `- L30 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8112 [`MOCK`] `- L31 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = False``
- L8113 [`MOCK`] `- L32 [`MOCK`] `MockSettings.return_value.FORCE_SCANNER = False``
- L8114 [`MOCK`] `- L43 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8115 [`MOCK`] `- L44 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True``
- L8116 [`MOCK`] `- L46 [`MOCK`] `# Mock subprocess``
- L8117 [`MOCK`] `- L47 [`MOCK`] `proc = AsyncMock()``
- L8118 [`MOCK`] `- L66 [`MOCK`] `with patch("configstream.config.AppSettings") as MockSettings:``
- L8119 [`MOCK`] `- L67 [`MOCK`] `MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True``
- L8120 [`MOCK`] `- L69 [`MOCK`] `proc = AsyncMock()``
- L8123 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8124 [`MOCK`] `- L7 [`MOCK`] `def _mock_httpx_response(text: str):``
- L8125 [`MOCK`] `- L9 [`MOCK`] `mock_resp = MagicMock(spec=httpx.Response)``
- L8126 [`MOCK`] `- L10 [`MOCK`] `mock_resp.text = text``
- L8127 [`MOCK`] `- L11 [`MOCK`] `mock_resp.status_code = 200``
- L8128 [`MOCK`] `- L12 [`MOCK`] `mock_resp.raise_for_status = MagicMock()``
- L8129 [`MOCK`] `- L14 [`MOCK`] `mock_client = AsyncMock(spec=httpx.AsyncClient)``
- L8130 [`MOCK`] `- L15 [`MOCK`] `mock_client.get = AsyncMock(return_value=mock_resp)``
- L8131 [`MOCK`] `- L16 [`MOCK`] `mock_client.__aenter__ = AsyncMock(return_value=mock_client)``
- L8132 [`MOCK`] `- L17 [`MOCK`] `mock_client.__aexit__ = AsyncMock(return_value=False)``
- L8133 [`MOCK`] `- L18 [`MOCK`] `return mock_client``
- L8134 [`MOCK`] `- L24 [`MOCK`] `mock_client = _mock_httpx_response("162.159.192.1:2408\ninvalid\n1.1.1.1")``
- L8135 [`MOCK`] `- L33 [`MOCK`] `return_value=mock_client,``
- L8136 [`MOCK`] `- L48 [`MOCK`] `mock_client = _mock_httpx_response(warp_uri)``
- L8137 [`MOCK`] `- L57 [`MOCK`] `return_value=mock_client,``
- L8138 [`MOCK`] `- L87 [`MOCK`] `mock_client = _mock_httpx_response(json_content)``
- L8139 [`MOCK`] `- L96 [`MOCK`] `return_value=mock_client,``
- L8142 [`MOCK`] `- L6 [`MOCK`] `key = "a" * 44  # Mock key``
- L8145 [`MOCK`] `- L22 [`MOCK`] `# Mocking logger is tricky in unit test without fixtures, but we can check return None``
- L8148 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8149 [`MOCK`] `- L12 [`MOCK`] `# Mock psutil not present (fallback to CPU logic)``
- L8150 [`MOCK`] `- L15 [`MOCK`] `# Mock CI detection to False for deterministic test``
- L8151 [`MOCK`] `- L35 [`MOCK`] `mock_psutil = MagicMock()``
- L8152 [`MOCK`] `- L36 [`MOCK`] `mock_mem = MagicMock()``
- L8153 [`MOCK`] `- L38 [`MOCK`] `mock_mem.available = 1024 * 1024 * 1024``
- L8154 [`MOCK`] `- L39 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem``
- L8155 [`MOCK`] `- L41 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):``
- L8156 [`MOCK`] `- L51 [`MOCK`] `mock_psutil = MagicMock()``
- L8157 [`MOCK`] `- L52 [`MOCK`] `mock_mem = MagicMock()``
- L8158 [`MOCK`] `- L53 [`MOCK`] `mock_mem.available = 64 * 1024 * 1024 * 1024  # Huge RAM``
- L8159 [`MOCK`] `- L54 [`MOCK`] `mock_psutil.virtual_memory.return_value = mock_mem``
- L8160 [`MOCK`] `- L56 [`MOCK`] `with patch("configstream.adaptive_workers.psutil_module", mock_psutil):``
- L8163 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch``
- L8164 [`MOCK`] `- L27 [`MOCK`] `# Mock cache file``
- L8167 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8168 [`MOCK`] `- L14 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:``
- L8169 [`MOCK`] `- L17 [`MOCK`] `args, kwargs = mock_basic_config.call_args``
- L8170 [`MOCK`] `- L22 [`MOCK`] `with patch("logging.basicConfig") as mock_basic_config:``
- L8171 [`MOCK`] `- L25 [`MOCK`] `args, kwargs = mock_basic_config.call_args``
- L8172 [`MOCK`] `- L43 [`MOCK`] `def test_cli_merge_command(mock_pipeline, runner):``
- L8173 [`MOCK`] `- L44 [`MOCK`] `# Mock stats object``
- L8174 [`MOCK`] `- L45 [`MOCK`] `stats_mock = MagicMock()``
- L8175 [`MOCK`] `- L46 [`MOCK`] `# Configure attributes so getattr(stats, key) returns float/int, not MagicMock``
- L8176 [`MOCK`] `- L47 [`MOCK`] `stats_mock.duration = 1.5``
- L8177 [`MOCK`] `- L48 [`MOCK`] `stats_mock.fetched_lines = 100``
- L8178 [`MOCK`] `- L49 [`MOCK`] `stats_mock.tested = 50``
- L8179 [`MOCK`] `- L50 [`MOCK`] `stats_mock.working = 40``
- L8180 [`MOCK`] `- L51 [`MOCK`] `stats_mock.geo_resolved = 30``
- L8181 [`MOCK`] `- L52 [`MOCK`] `stats_mock.to_dict.return_value = {``
- L8182 [`MOCK`] `- L60 [`MOCK`] `# Mock pipeline result``
- L8183 [`MOCK`] `- L61 [`MOCK`] `result_mock = MagicMock()``
- L8184 [`MOCK`] `- L62 [`MOCK`] `result_mock.success = True``
- L8185 [`MOCK`] `- L63 [`MOCK`] `result_mock.stats = stats_mock``
- L8186 [`MOCK`] `- L64 [`MOCK`] `result_mock.error = None``
- L8187 [`MOCK`] `- L66 [`MOCK`] `mock_pipeline.return_value = result_mock``
- L8188 [`MOCK`] `- L67 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)``
- L8189 [`MOCK`] `- L85 [`MOCK`] `def test_cli_merge_command_fail(mock_pipeline, runner):``
- L8190 [`MOCK`] `- L86 [`MOCK`] `result_mock = MagicMock()``
- L8191 [`MOCK`] `- L87 [`MOCK`] `result_mock.success = False``
- L8192 [`MOCK`] `- L88 [`MOCK`] `result_mock.error = "Simulated Failure"``
- L8193 [`MOCK`] `- L90 [`MOCK`] `mock_pipeline.side_effect = AsyncMock(return_value=result_mock)``
- L8196 [`MOCK`] `- L37 [`MOCK`] `# Mock output directory for static files``
- L8199 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8200 [`MOCK`] `- L9 [`MOCK`] `def mock_warp_keys():``
- L8201 [`MOCK`] `- L21 [`MOCK`] `def washer(mock_warp_keys):``
- L8202 [`MOCK`] `- L22 [`MOCK`] `return ProxyWasher(mock_warp_keys)``
- L8203 [`MOCK`] `- L106 [`MOCK`] `# Fill cache up to limit (mock small limit via private usage if possible, or just check type)``
- L8204 [`MOCK`] `- L112 [`MOCK`] `# We can mock seen_chains``
- L8205 [`MOCK`] `- L113 [`MOCK`] `washer.seen_chains = MagicMock()``
- L8208 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import patch``
- L8209 [`MOCK`] `- L46 [`MOCK`] `# Exception case mocking``
- L8212 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8215 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8216 [`MOCK`] `- L11 [`MOCK`] `# Mock readers to ensure we don't hit FS``
- L8217 [`MOCK`] `- L12 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8218 [`MOCK`] `- L13 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8219 [`MOCK`] `- L21 [`MOCK`] `async def test_geoip_lookup_valid_mock():``
- L8220 [`MOCK`] `- L22 [`MOCK`] `"""Test lookup logic with mocked DB response"""``
- L8221 [`MOCK`] `- L25 [`MOCK`] `mock_city = MagicMock()``
- L8222 [`MOCK`] `- L26 [`MOCK`] `mock_city.country.iso_code = "US"``
- L8223 [`MOCK`] `- L27 [`MOCK`] `mock_city.country.name = "United States"``
- L8224 [`MOCK`] `- L28 [`MOCK`] `mock_city.city.name = "New York"``
- L8225 [`MOCK`] `- L29 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8226 [`MOCK`] `- L30 [`MOCK`] `resolver.reader_city.city.return_value = mock_city``
- L8227 [`MOCK`] `- L32 [`MOCK`] `mock_asn = MagicMock()``
- L8228 [`MOCK`] `- L33 [`MOCK`] `mock_asn.autonomous_system_number = 12345``
- L8229 [`MOCK`] `- L34 [`MOCK`] `mock_asn.autonomous_system_organization = "Test Org"``
- L8230 [`MOCK`] `- L35 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8231 [`MOCK`] `- L36 [`MOCK`] `resolver.reader_asn.asn.return_value = mock_asn``
- L8234 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8235 [`MOCK`] `- L36 [`MOCK`] `with patch.object(Path, "stat") as mock_stat:``
- L8236 [`MOCK`] `- L37 [`MOCK`] `mock_stat.return_value.st_size = 101 * 1024 * 1024  # 101MB``
- L8237 [`MOCK`] `- L152 [`MOCK`] `with patch("configstream.history.export.datetime") as mock_dt:``
- L8238 [`MOCK`] `- L153 [`MOCK`] `mock_dt.now.return_value.replace.return_value = mock_dt.now.return_value``
- L8239 [`MOCK`] `- L156 [`MOCK`] `mock_dt.now.return_value = fixed_now``
- L8240 [`MOCK`] `- L157 [`MOCK`] `mock_dt.fromisoformat.side_effect = datetime.fromisoformat``
- L8241 [`MOCK`] `- L158 [`MOCK`] `mock_dt.min = datetime.min``
- L8244 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch``
- L8245 [`MOCK`] `- L75 [`MOCK`] `# Mock converters``
- L8248 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch``
- L8251 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8252 [`MOCK`] `- L156 [`MOCK`] `# Easier to mock``
- L8255 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8256 [`MOCK`] `- L19 [`MOCK`] `mock_response = MagicMock()``
- L8257 [`MOCK`] `- L20 [`MOCK`] `mock_response.status_code = 200``
- L8258 [`MOCK`] `- L23 [`MOCK`] `"httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response``
- L8259 [`MOCK`] `- L36 [`MOCK`] `new_callable=AsyncMock,``
- L8262 [`MOCK`] `- L11 [`MOCK`] `from unittest.mock import patch``
- L8263 [`MOCK`] `- L36 [`MOCK`] `# Mock SUSPICIOUS_DOMAINS to test that logic specifically``
- L8264 [`MOCK`] `- L56 [`MOCK`] `# Mock AppSettings to ensure ALLOW_PRIVATE_IPS is False``
- L8265 [`MOCK`] `- L57 [`MOCK`] `# Also mock SUSPICIOUS_DOMAINS to be empty so we fall through to private IP check``
- L8266 [`MOCK`] `- L59 [`MOCK`] `patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings,``
- L8267 [`MOCK`] `- L62 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = False``
- L8268 [`MOCK`] `- L81 [`MOCK`] `with patch("configstream.security.rules._APP_SETTINGS_CACHE") as mock_settings:``
- L8269 [`MOCK`] `- L82 [`MOCK`] `mock_settings.ALLOW_PRIVATE_IPS = True``
- L8272 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8273 [`MOCK`] `- L17 [`MOCK`] `new_callable=AsyncMock,``
- L8274 [`MOCK`] `- L40 [`MOCK`] `new_callable=AsyncMock,``
- L8275 [`MOCK`] `- L47 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,``
- L8276 [`MOCK`] `- L50 [`MOCK`] `mock_proc = MagicMock()``
- L8277 [`MOCK`] `- L51 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))``
- L8278 [`MOCK`] `- L52 [`MOCK`] `mock_proc.returncode = 0``
- L8279 [`MOCK`] `- L53 [`MOCK`] `mock_exec.return_value = mock_proc``
- L8280 [`MOCK`] `- L64 [`MOCK`] `new_callable=AsyncMock,``
- L8281 [`MOCK`] `- L71 [`MOCK`] `patch("asyncio.create_subprocess_exec") as mock_exec,``
- L8282 [`MOCK`] `- L74 [`MOCK`] `mock_proc = MagicMock()``
- L8283 [`MOCK`] `- L75 [`MOCK`] `mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))``
- L8284 [`MOCK`] `- L76 [`MOCK`] `mock_proc.returncode = 1``
- L8285 [`MOCK`] `- L77 [`MOCK`] `mock_exec.return_value = mock_proc``
- L8288 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8289 [`MOCK`] `- L18 [`MOCK`] `class MockResponse:``
- L8290 [`MOCK`] `- L19 [`MOCK`] `"""Mock aiohttp response."""``
- L8291 [`MOCK`] `- L49 [`MOCK`] `mock_response = MockResponse(200, "not a dict")``
- L8292 [`MOCK`] `- L53 [`MOCK`] `) as mock_session_cls:``
- L8293 [`MOCK`] `- L54 [`MOCK`] `mock_session = MagicMock()``
- L8294 [`MOCK`] `- L55 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8295 [`MOCK`] `- L56 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8296 [`MOCK`] `- L66 [`MOCK`] `mock_response = MockResponse(200, {"data": {}})``
- L8297 [`MOCK`] `- L70 [`MOCK`] `) as mock_session_cls:``
- L8298 [`MOCK`] `- L71 [`MOCK`] `mock_session = MagicMock()``
- L8299 [`MOCK`] `- L72 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8300 [`MOCK`] `- L73 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8301 [`MOCK`] `- L85 [`MOCK`] `) as mock_session_cls:``
- L8302 [`MOCK`] `- L86 [`MOCK`] `mock_session = MagicMock()``
- L8303 [`MOCK`] `- L87 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8304 [`MOCK`] `- L88 [`MOCK`] `mock_session.get.side_effect = Exception("Network error")``
- L8305 [`MOCK`] `- L98 [`MOCK`] `mock_response = MockResponse(``
- L8306 [`MOCK`] `- L104 [`MOCK`] `) as mock_session_cls:``
- L8307 [`MOCK`] `- L105 [`MOCK`] `mock_session = MagicMock()``
- L8308 [`MOCK`] `- L106 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8309 [`MOCK`] `- L107 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8310 [`MOCK`] `- L113 [`MOCK`] `call_args = mock_session.get.call_args``
- L8311 [`MOCK`] `- L135 [`MOCK`] `mock_response = MockResponse(``
- L8312 [`MOCK`] `- L151 [`MOCK`] `) as mock_session_cls:``
- L8313 [`MOCK`] `- L152 [`MOCK`] `mock_session = MagicMock()``
- L8314 [`MOCK`] `- L153 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8315 [`MOCK`] `- L154 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8316 [`MOCK`] `- L164 [`MOCK`] `mock_response = MockResponse(``
- L8317 [`MOCK`] `- L179 [`MOCK`] `) as mock_session_cls:``
- L8318 [`MOCK`] `- L180 [`MOCK`] `mock_session = MagicMock()``
- L8319 [`MOCK`] `- L181 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8320 [`MOCK`] `- L182 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8321 [`MOCK`] `- L200 [`MOCK`] `) as mock_session_cls:``
- L8322 [`MOCK`] `- L205 [`MOCK`] `mock_session_cls.assert_not_called()``
- L8323 [`MOCK`] `- L215 [`MOCK`] `mock_response = MockResponse(``
- L8324 [`MOCK`] `- L230 [`MOCK`] `) as mock_session_cls:``
- L8325 [`MOCK`] `- L231 [`MOCK`] `mock_session = MagicMock()``
- L8326 [`MOCK`] `- L232 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8327 [`MOCK`] `- L233 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8328 [`MOCK`] `- L240 [`MOCK`] `mock_session.get.assert_called_once()``
- L8329 [`MOCK`] `- L258 [`MOCK`] `mock_response = MockResponse(``
- L8330 [`MOCK`] `- L273 [`MOCK`] `) as mock_session_cls:``
- L8331 [`MOCK`] `- L274 [`MOCK`] `mock_session = MagicMock()``
- L8332 [`MOCK`] `- L275 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8333 [`MOCK`] `- L276 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8334 [`MOCK`] `- L289 [`MOCK`] `mock_response = MockResponse(200, ["not", "a", "dict"])``
- L8335 [`MOCK`] `- L293 [`MOCK`] `) as mock_session_cls:``
- L8336 [`MOCK`] `- L294 [`MOCK`] `mock_session = MagicMock()``
- L8337 [`MOCK`] `- L295 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8338 [`MOCK`] `- L296 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8339 [`MOCK`] `- L306 [`MOCK`] `mock_response = MockResponse(429, {})  # Rate limit error``
- L8340 [`MOCK`] `- L310 [`MOCK`] `) as mock_session_cls:``
- L8341 [`MOCK`] `- L311 [`MOCK`] `mock_session = MagicMock()``
- L8342 [`MOCK`] `- L312 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8343 [`MOCK`] `- L313 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8344 [`MOCK`] `- L325 [`MOCK`] `) as mock_session_cls:``
- L8345 [`MOCK`] `- L326 [`MOCK`] `mock_session = MagicMock()``
- L8346 [`MOCK`] `- L327 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8347 [`MOCK`] `- L328 [`MOCK`] `mock_session.get.side_effect = Exception("Network timeout")``
- L8348 [`MOCK`] `- L340 [`MOCK`] `mock_response = MockResponse(``
- L8349 [`MOCK`] `- L355 [`MOCK`] `) as mock_session_cls:``
- L8350 [`MOCK`] `- L356 [`MOCK`] `mock_session = MagicMock()``
- L8351 [`MOCK`] `- L357 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8352 [`MOCK`] `- L358 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8353 [`MOCK`] `- L372 [`MOCK`] `mock_response = MockResponse(200, {"data": {"attributes": {}}})``
- L8354 [`MOCK`] `- L376 [`MOCK`] `) as mock_session_cls:``
- L8355 [`MOCK`] `- L377 [`MOCK`] `mock_session = MagicMock()``
- L8356 [`MOCK`] `- L378 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8357 [`MOCK`] `- L379 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8358 [`MOCK`] `- L403 [`MOCK`] `mock_response = MockResponse(``
- L8359 [`MOCK`] `- L421 [`MOCK`] `) as mock_session_cls:``
- L8360 [`MOCK`] `- L422 [`MOCK`] `mock_session = MagicMock()``
- L8361 [`MOCK`] `- L423 [`MOCK`] `mock_session_cls.return_value.__aenter__.return_value = mock_session``
- L8362 [`MOCK`] `- L424 [`MOCK`] `mock_session.get.return_value = mock_response``
- L8365 [`MOCK`] `- L9 [`MOCK`] `from unittest.mock import Mock, MagicMock, patch``
- L8366 [`MOCK`] `- L179 [`MOCK`] `) as mock_format:``
- L8367 [`MOCK`] `- L180 [`MOCK`] `mock_format.return_value = "WireGuard chain config"``
- L8368 [`MOCK`] `- L189 [`MOCK`] `proxy = Mock(spec=Proxy)``
- L8369 [`MOCK`] `- L194 [`MOCK`] `# Use MagicMock for details to allow mocking get method``
- L8370 [`MOCK`] `- L195 [`MOCK`] `proxy.details = MagicMock()``
- L8373 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8374 [`MOCK`] `- L91 [`MOCK`] `# We mock write_text``
- L8375 [`MOCK`] `- L109 [`MOCK`] `with patch("configstream.adaptive_timeout.logger") as mock_logger:``
- L8376 [`MOCK`] `- L111 [`MOCK`] `assert mock_logger.debug.called``
- L8379 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8380 [`MOCK`] `- L9 [`MOCK`] `with patch("psutil.virtual_memory") as mock_mem:``
- L8381 [`MOCK`] `- L10 [`MOCK`] `mock_mem.return_value.available = 2 * 1024 * 1024 * 1024  # 2GB``
- L8384 [`MOCK`] `- L12 [`MOCK`] `# Create mock proxies with various latencies``
- L8385 [`MOCK`] `- L17 [`MOCK`] `config="vmess://mock1",``
- L8386 [`MOCK`] `- L29 [`MOCK`] `config="ss://mock2", protocol="ss", address="2.2.2.2", port=443, is_working=True``
- L8387 [`MOCK`] `- L37 [`MOCK`] `config="trojan://mock3",``
- L8388 [`MOCK`] `- L49 [`MOCK`] `config="vless://mock4",``
- L8389 [`MOCK`] `- L61 [`MOCK`] `config="vmess://mock5",``
- L8390 [`MOCK`] `- L71 [`MOCK`] `# Mock pipeline stats object``
- L8393 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8394 [`MOCK`] `- L129 [`MOCK`] `with patch("time.time") as mock_time:``
- L8395 [`MOCK`] `- L131 [`MOCK`] `mock_time.return_value = 1000 + i``
- L8396 [`MOCK`] `- L147 [`MOCK`] `from unittest.mock import MagicMock``
- L8397 [`MOCK`] `- L150 [`MOCK`] `mock_conn = MagicMock()``
- L8398 [`MOCK`] `- L151 [`MOCK`] `# Mock specific sqlite3.Error which is caught by the logic``
- L8399 [`MOCK`] `- L152 [`MOCK`] `mock_conn.execute.side_effect = sqlite3.OperationalError("DB Execution Error")``
- L8400 [`MOCK`] `- L154 [`MOCK`] `detector._conn = mock_conn``
- L8401 [`MOCK`] `- L156 [`MOCK`] `# Also mock reconnection attempt failing``
- L8404 [`MOCK`] `- L26 [`MOCK`] `# We can't easily mock file stats without patching os.stat``
- L8407 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8408 [`MOCK`] `- L153 [`MOCK`] `# but we can mock glob or check logic.``
- L8409 [`MOCK`] `- L155 [`MOCK`] `# If we had a file named "../traversal.db" returned by glob (unlikely normally but possible via mocks)``
- L8410 [`MOCK`] `- L157 [`MOCK`] `with patch.object(Path, "glob") as mock_glob:``
- L8411 [`MOCK`] `- L158 [`MOCK`] `bad_path = MagicMock(spec=Path)``
- L8412 [`MOCK`] `- L163 [`MOCK`] `mock_glob.return_value = [bad_path]``
- L8413 [`MOCK`] `- L180 [`MOCK`] `with patch("sqlite3.connect") as mock_connect:``
- L8414 [`MOCK`] `- L181 [`MOCK`] `mock_connect.side_effect = Exception("Connect Fail")``
- L8417 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8418 [`MOCK`] `- L8 [`MOCK`] `# Mock register_warp_account globally for this module if possible,``
- L8419 [`MOCK`] `- L13 [`MOCK`] `# we need to patch 'configstream.tools.warp.register_warp_account' and ensure it's mocked``
- L8420 [`MOCK`] `- L18 [`MOCK`] `# We should mock `configstream.tools.warp.register_warp_account`.``
- L8421 [`MOCK`] `- L23 [`MOCK`] `update = MagicMock(spec=Update)``
- L8422 [`MOCK`] `- L24 [`MOCK`] `update.effective_chat = MagicMock()``
- L8423 [`MOCK`] `- L26 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8424 [`MOCK`] `- L27 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8425 [`MOCK`] `- L36 [`MOCK`] `update = MagicMock(spec=Update)``
- L8426 [`MOCK`] `- L37 [`MOCK`] `update.effective_chat = MagicMock()``
- L8427 [`MOCK`] `- L39 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8428 [`MOCK`] `- L40 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8429 [`MOCK`] `- L42 [`MOCK`] `# We need to mock the module where it is defined, so the local import picks up the mock``
- L8430 [`MOCK`] `- L44 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock``
- L8431 [`MOCK`] `- L45 [`MOCK`] `) as mock_reg:``
- L8432 [`MOCK`] `- L46 [`MOCK`] `mock_reg.return_value = {``
- L8433 [`MOCK`] `- L66 [`MOCK`] `update = MagicMock(spec=Update)``
- L8434 [`MOCK`] `- L67 [`MOCK`] `update.effective_chat = MagicMock()``
- L8435 [`MOCK`] `- L69 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8436 [`MOCK`] `- L70 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8437 [`MOCK`] `- L73 [`MOCK`] `"configstream.tools.warp.register_warp_account", new_callable=AsyncMock``
- L8438 [`MOCK`] `- L74 [`MOCK`] `) as mock_reg:``
- L8439 [`MOCK`] `- L75 [`MOCK`] `mock_reg.side_effect = Exception("Fail")``
- L8440 [`MOCK`] `- L85 [`MOCK`] `update = MagicMock(spec=Update)``
- L8441 [`MOCK`] `- L86 [`MOCK`] `update.effective_chat = MagicMock()``
- L8442 [`MOCK`] `- L88 [`MOCK`] `context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)``
- L8443 [`MOCK`] `- L89 [`MOCK`] `context.bot.send_message = AsyncMock()``
- L8444 [`MOCK`] `- L96 [`MOCK`] `# Mock AppSettings to return None for TELEGRAM_BOT_TOKEN``
- L8445 [`MOCK`] `- L103 [`MOCK`] `with patch("configstream.config.AppSettings") as mock_settings:``
- L8446 [`MOCK`] `- L104 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = None``
- L8447 [`MOCK`] `- L105 [`MOCK`] `with patch("configstream.bot_cli.logger") as mock_logger:``
- L8448 [`MOCK`] `- L107 [`MOCK`] `mock_logger.error.assert_called_with("TELEGRAM_BOT_TOKEN not set")``
- L8449 [`MOCK`] `- L112 [`MOCK`] `patch("configstream.config.AppSettings") as mock_settings,``
- L8450 [`MOCK`] `- L113 [`MOCK`] `patch("configstream.bot_cli.ApplicationBuilder") as mock_builder,``
- L8451 [`MOCK`] `- L115 [`MOCK`] `mock_settings.return_value.TELEGRAM_BOT_TOKEN = "fake_token"``
- L8452 [`MOCK`] `- L117 [`MOCK`] `mock_app = MagicMock()``
- L8453 [`MOCK`] `- L118 [`MOCK`] `mock_builder.return_value.token.return_value.build.return_value = mock_app``
- L8454 [`MOCK`] `- L121 [`MOCK`] `mock_app.run_polling.assert_called_once()``
- L8457 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8458 [`MOCK`] `- L9 [`MOCK`] `def mock_cache():``
- L8459 [`MOCK`] `- L10 [`MOCK`] `cache = MagicMock()``
- L8460 [`MOCK`] `- L11 [`MOCK`] `# Mock get method to return True for some proxies, False for others``
- L8461 [`MOCK`] `- L12 [`MOCK`] `cache.get = MagicMock()``
- L8462 [`MOCK`] `- L13 [`MOCK`] `cache.get_health_score = MagicMock()``
- L8463 [`MOCK`] `- L18 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L8464 [`ASSUMING`] `- L19 [`ASSUMING`] `p.id = id  # Assuming models.Proxy has id or is hashable``
- L8465 [`MOCK`] `- L24 [`MOCK`] `def test_warm_cache(mock_cache):``
- L8466 [`MOCK`] `- L33 [`MOCK`] `mock_cache.get.side_effect = lambda p: p.id in ["p1", "p3", "p4"]``
- L8467 [`MOCK`] `- L45 [`MOCK`] `mock_cache.get_health_score.side_effect = health_score``
- L8468 [`MOCK`] `- L47 [`MOCK`] `result = warm_cache(mock_cache, proxies)``
- L8469 [`MOCK`] `- L60 [`MOCK`] `def test_warm_cache_all_uncached(mock_cache):``
- L8470 [`MOCK`] `- L64 [`MOCK`] `mock_cache.get.return_value = False``
- L8471 [`MOCK`] `- L66 [`MOCK`] `result = warm_cache(mock_cache, proxies)``
- L8474 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import AsyncMock, MagicMock, patch``
- L8475 [`MOCK`] `- L42 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock``
- L8476 [`MOCK`] `- L43 [`MOCK`] `) as mock_pipeline,``
- L8477 [`MOCK`] `- L46 [`MOCK`] `mock_result = MagicMock()``
- L8478 [`MOCK`] `- L47 [`MOCK`] `mock_result.success = True``
- L8479 [`MOCK`] `- L48 [`MOCK`] `mock_result.stats = {``
- L8480 [`MOCK`] `- L55 [`MOCK`] `mock_pipeline.return_value = mock_result``
- L8481 [`MOCK`] `- L61 [`MOCK`] `mock_pipeline.assert_called_once()``
- L8482 [`MOCK`] `- L69 [`MOCK`] `"configstream.cli.run_full_pipeline", new_callable=AsyncMock``
- L8483 [`MOCK`] `- L70 [`MOCK`] `) as mock_pipeline,``
- L8484 [`MOCK`] `- L73 [`MOCK`] `mock_result = MagicMock()``
- L8485 [`MOCK`] `- L74 [`MOCK`] `mock_result.success = False``
- L8486 [`MOCK`] `- L75 [`MOCK`] `mock_result.error = "Test Failure"``
- L8487 [`MOCK`] `- L76 [`MOCK`] `mock_pipeline.return_value = mock_result``
- L8488 [`MOCK`] `- L163 [`MOCK`] `"configstream.cli.generate_warp_proxy", new_callable=AsyncMock``
- L8489 [`MOCK`] `- L164 [`MOCK`] `) as mock_gen:``
- L8490 [`MOCK`] `- L165 [`MOCK`] `mock_p = MagicMock()``
- L8491 [`MOCK`] `- L166 [`MOCK`] `mock_p.protocol = "wireguard"``
- L8492 [`MOCK`] `- L167 [`MOCK`] `mock_p.details = {}``
- L8493 [`MOCK`] `- L168 [`MOCK`] `mock_p.config = "conf"``
- L8494 [`MOCK`] `- L169 [`MOCK`] `mock_gen.return_value = mock_p``
- L8495 [`MOCK`] `- L178 [`MOCK`] `with patch("configstream.bot_cli.run_bot") as mock_run:``
- L8496 [`MOCK`] `- L181 [`MOCK`] `mock_run.assert_called_with("FAKE")``
- L8499 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L8502 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import AsyncMock``
- L8503 [`MOCK`] `- L60 [`MOCK`] `# Mock semaphore set_limit``
- L8504 [`MOCK`] `- L61 [`MOCK`] `cm.semaphore.set_limit = AsyncMock()``
- L8507 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8508 [`MOCK`] `- L11 [`MOCK`] `def mock_dependencies_fix():``
- L8509 [`MOCK`] `- L14 [`MOCK`] `# Mocks``
- L8510 [`MOCK`] `- L15 [`MOCK`] `tester = MagicMock()``
- L8511 [`MOCK`] `- L17 [`MOCK`] `tester.test = AsyncMock()``
- L8512 [`MOCK`] `- L18 [`MOCK`] `tester.test_batch = AsyncMock()``
- L8513 [`MOCK`] `- L20 [`MOCK`] `washer = MagicMock()``
- L8514 [`MOCK`] `- L22 [`MOCK`] `scheduler = MagicMock()``
- L8515 [`MOCK`] `- L25 [`MOCK`] `test_cache = MagicMock()``
- L8516 [`MOCK`] `- L28 [`MOCK`] `concurrency = MagicMock()``
- L8517 [`MOCK`] `- L29 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()``
- L8518 [`MOCK`] `- L32 [`MOCK`] `concurrency.record = AsyncMock()``
- L8519 [`MOCK`] `- L34 [`MOCK`] `geoip = MagicMock()``
- L8520 [`MOCK`] `- L35 [`MOCK`] `geoip.lookup = AsyncMock(return_value=None)``
- L8521 [`MOCK`] `- L37 [`MOCK`] `tracker = MagicMock()``
- L8522 [`MOCK`] `- L38 [`MOCK`] `tracker.phase.return_value = MagicMock()``
- L8523 [`MOCK`] `- L42 [`MOCK`] `history = MagicMock()``
- L8524 [`MOCK`] `- L43 [`MOCK`] `history.update_history = MagicMock()``
- L8525 [`MOCK`] `- L45 [`MOCK`] `quality = MagicMock()``
- L8526 [`MOCK`] `- L62 [`MOCK`] `async def test_processing_consumer_revival_crash(mock_dependencies_fix):``
- L8527 [`MOCK`] `- L63 [`MOCK`] `deps = mock_dependencies_fix``
- L8528 [`MOCK`] `- L81 [`MOCK`] `# Mock parse_config``
- L8529 [`MOCK`] `- L83 [`MOCK`] `# Mock validate_batch_configs``
- L8532 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8533 [`MOCK`] `- L19 [`MOCK`] `# Mock aiodns.DNSResolver``
- L8534 [`MOCK`] `- L20 [`MOCK`] `mock_dns = MagicMock()``
- L8535 [`MOCK`] `- L21 [`MOCK`] `# Mock query response``
- L8536 [`MOCK`] `- L23 [`MOCK`] `res_example = MagicMock()``
- L8537 [`MOCK`] `- L26 [`MOCK`] `res_google = MagicMock()``
- L8538 [`MOCK`] `- L36 [`MOCK`] `mock_dns.query.side_effect = [future_example, future_google]``
- L8539 [`MOCK`] `- L38 [`MOCK`] `resolver.resolver = mock_dns  # Set the instance attribute directly``
- L8540 [`MOCK`] `- L48 [`MOCK`] `resolver.resolver = MagicMock()``
- L8541 [`MOCK`] `- L57 [`MOCK`] `mock_dns = MagicMock()``
- L8542 [`MOCK`] `- L60 [`MOCK`] `mock_dns.query.return_value = future_fail``
- L8543 [`MOCK`] `- L62 [`MOCK`] `resolver.resolver = mock_dns``
- L8546 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import patch``
- L8547 [`MOCK`] `- L36 [`MOCK`] `def test_emit_error_event(self, mock_logger, tmp_path):``
- L8548 [`MOCK`] `- L41 [`MOCK`] `mock_logger.error.assert_called_once_with("[error] An error occurred")``
- L8549 [`MOCK`] `- L42 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8550 [`MOCK`] `- L43 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8551 [`MOCK`] `- L46 [`MOCK`] `def test_emit_critical_event(self, mock_logger, tmp_path):``
- L8552 [`MOCK`] `- L51 [`MOCK`] `mock_logger.error.assert_called_once_with("[critical] Critical failure")``
- L8553 [`MOCK`] `- L52 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8554 [`MOCK`] `- L53 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8555 [`MOCK`] `- L56 [`MOCK`] `def test_emit_warning_event(self, mock_logger, tmp_path):``
- L8556 [`MOCK`] `- L61 [`MOCK`] `mock_logger.warning.assert_called_once_with("[warning] Warning message")``
- L8557 [`MOCK`] `- L62 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8558 [`MOCK`] `- L63 [`MOCK`] `mock_logger.info.assert_not_called()``
- L8559 [`MOCK`] `- L66 [`MOCK`] `def test_emit_info_event(self, mock_logger, tmp_path):``
- L8560 [`MOCK`] `- L71 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] Information message")``
- L8561 [`MOCK`] `- L72 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8562 [`MOCK`] `- L73 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8563 [`MOCK`] `- L76 [`MOCK`] `def test_emit_default_event_type(self, mock_logger, tmp_path):``
- L8564 [`MOCK`] `- L81 [`MOCK`] `mock_logger.info.assert_called_once_with("[custom] Custom event")``
- L8565 [`MOCK`] `- L82 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8566 [`MOCK`] `- L83 [`MOCK`] `mock_logger.warning.assert_not_called()``
- L8567 [`MOCK`] `- L86 [`MOCK`] `def test_emit_success_event(self, mock_logger, tmp_path):``
- L8568 [`MOCK`] `- L91 [`MOCK`] `mock_logger.info.assert_called_once_with("[success] Operation succeeded")``
- L8569 [`MOCK`] `- L94 [`MOCK`] `def test_emit_empty_message(self, mock_logger, tmp_path):``
- L8570 [`MOCK`] `- L99 [`MOCK`] `mock_logger.info.assert_called_once_with("[info] ")``
- L8571 [`MOCK`] `- L102 [`MOCK`] `def test_emit_multiline_message(self, mock_logger, tmp_path):``
- L8572 [`MOCK`] `- L108 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")``
- L8573 [`MOCK`] `- L111 [`MOCK`] `def test_emit_message_with_special_characters(self, mock_logger, tmp_path):``
- L8574 [`MOCK`] `- L119 [`MOCK`] `mock_logger.error.assert_called_once_with(f"[error] {special_message}")``
- L8575 [`MOCK`] `- L122 [`MOCK`] `def test_emit_message_with_unicode(self, mock_logger, tmp_path):``
- L8576 [`MOCK`] `- L128 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {unicode_message}")``
- L8577 [`MOCK`] `- L131 [`MOCK`] `def test_multiple_emit_calls(self, mock_logger, tmp_path):``
- L8578 [`MOCK`] `- L139 [`MOCK`] `assert mock_logger.info.call_count == 1``
- L8579 [`MOCK`] `- L140 [`MOCK`] `assert mock_logger.warning.call_count == 1``
- L8580 [`MOCK`] `- L141 [`MOCK`] `assert mock_logger.error.call_count == 1``
- L8581 [`MOCK`] `- L144 [`MOCK`] `def test_emit_very_long_message(self, mock_logger, tmp_path):``
- L8582 [`MOCK`] `- L150 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8583 [`MOCK`] `- L151 [`MOCK`] `call_args = mock_logger.info.call_args[0][0]``
- L8584 [`MOCK`] `- L155 [`MOCK`] `def test_emit_with_format_strings(self, mock_logger, tmp_path):``
- L8585 [`MOCK`] `- L161 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {message}")``
- L8586 [`MOCK`] `- L164 [`MOCK`] `def test_case_sensitive_event_types(self, mock_logger, tmp_path):``
- L8587 [`MOCK`] `- L170 [`MOCK`] `mock_logger.error.assert_called_once()``
- L8588 [`MOCK`] `- L172 [`MOCK`] `mock_logger.reset_mock()``
- L8589 [`MOCK`] `- L176 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8590 [`MOCK`] `- L177 [`MOCK`] `mock_logger.error.assert_not_called()``
- L8591 [`MOCK`] `- L180 [`MOCK`] `def test_emit_with_numeric_message(self, mock_logger, tmp_path):``
- L8592 [`MOCK`] `- L185 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8593 [`MOCK`] `- L188 [`MOCK`] `def test_emit_rapid_fire(self, mock_logger, tmp_path):``
- L8594 [`MOCK`] `- L195 [`MOCK`] `assert mock_logger.info.call_count == 100``
- L8595 [`MOCK`] `- L198 [`MOCK`] `def test_emit_different_event_types_mixed(self, mock_logger, tmp_path):``
- L8596 [`MOCK`] `- L209 [`MOCK`] `assert mock_logger.info.call_count == 3  # info, info, custom``
- L8597 [`MOCK`] `- L210 [`MOCK`] `assert mock_logger.error.call_count == 2  # error, critical``
- L8598 [`MOCK`] `- L211 [`MOCK`] `assert mock_logger.warning.call_count == 1``
- L8599 [`MOCK`] `- L222 [`MOCK`] `def test_emit_with_none_message_converted_to_string(self, mock_logger, tmp_path):``
- L8600 [`MOCK`] `- L228 [`MOCK`] `mock_logger.info.assert_called_once()``
- L8601 [`MOCK`] `- L231 [`MOCK`] `def test_emit_preserves_message_exactly(self, mock_logger, tmp_path):``
- L8602 [`MOCK`] `- L238 [`MOCK`] `mock_logger.info.assert_called_once_with(expected_call)``
- L8603 [`MOCK`] `- L241 [`MOCK`] `def test_emit_with_json_like_message(self, mock_logger, tmp_path):``
- L8604 [`MOCK`] `- L247 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {json_message}")``
- L8605 [`MOCK`] `- L250 [`MOCK`] `def test_emit_with_sql_like_message(self, mock_logger, tmp_path):``
- L8606 [`MOCK`] `- L256 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {sql_message}")``
- L8607 [`MOCK`] `- L271 [`MOCK`] `def test_emit_with_path_in_message(self, mock_logger, tmp_path):``
- L8608 [`MOCK`] `- L277 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {path_message}")``
- L8609 [`MOCK`] `- L280 [`MOCK`] `def test_emit_with_url_in_message(self, mock_logger, tmp_path):``
- L8610 [`MOCK`] `- L286 [`MOCK`] `mock_logger.info.assert_called_once_with(f"[info] {url_message}")``
- L8613 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock``
- L8614 [`MOCK`] `- L32 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8615 [`MOCK`] `- L40 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8616 [`MOCK`] `- L50 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8617 [`MOCK`] `- L51 [`MOCK`] `mock_response = AsyncMock()``
- L8618 [`MOCK`] `- L52 [`MOCK`] `mock_response.status_code = 200``
- L8619 [`MOCK`] `- L53 [`MOCK`] `mock_response.headers = {}``
- L8620 [`MOCK`] `- L59 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8621 [`MOCK`] `- L62 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8622 [`MOCK`] `- L63 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8623 [`MOCK`] `- L64 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8624 [`MOCK`] `- L75 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8625 [`MOCK`] `- L76 [`MOCK`] `mock_response = AsyncMock()``
- L8626 [`MOCK`] `- L77 [`MOCK`] `mock_response.status_code = 429``
- L8627 [`MOCK`] `- L78 [`MOCK`] `mock_response.headers = {"Retry-After": "0.1"}``
- L8628 [`MOCK`] `- L80 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8629 [`MOCK`] `- L81 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8630 [`MOCK`] `- L82 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8631 [`MOCK`] `- L84 [`MOCK`] `# Should retry. We mock sleep to be fast.``
- L8632 [`MOCK`] `- L85 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8633 [`MOCK`] `- L91 [`MOCK`] `assert mock_sleep.call_count > 0``
- L8634 [`MOCK`] `- L95 [`MOCK`] `async def test_fetch_from_source_follows_safe_redirect(respx_mock):``
- L8635 [`MOCK`] `- L98 [`MOCK`] `respx_mock.get(source).mock(``
- L8636 [`MOCK`] `- L101 [`MOCK`] `respx_mock.get(target).mock(return_value=httpx.Response(200, text="redirected"))``
- L8637 [`MOCK`] `- L111 [`MOCK`] `async def test_fetch_from_source_rejects_private_redirect(respx_mock):``
- L8638 [`MOCK`] `- L113 [`MOCK`] `respx_mock.get(source).mock(``
- L8639 [`MOCK`] `- L128 [`MOCK`] `async def test_fetch_from_source_limits_redirect_depth(respx_mock):``
- L8640 [`MOCK`] `- L132 [`MOCK`] `respx_mock.get(source).mock(``
- L8641 [`MOCK`] `- L150 [`MOCK`] `# If RateLimiter class is gone, we can mock a generic object with the same interface.``
- L8642 [`MOCK`] `- L151 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8643 [`MOCK`] `- L152 [`MOCK`] `rate_limiter = MagicMock()``
- L8644 [`MOCK`] `- L154 [`MOCK`] `rate_limiter.is_allowed = AsyncMock(side_effect=[False, True])``
- L8645 [`MOCK`] `- L155 [`MOCK`] `rate_limiter.get_wait_time = AsyncMock(return_value=0.01)``
- L8646 [`MOCK`] `- L157 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8647 [`MOCK`] `- L159 [`MOCK`] `mock_response = AsyncMock()``
- L8648 [`MOCK`] `- L160 [`MOCK`] `mock_response.status_code = 200``
- L8649 [`MOCK`] `- L161 [`MOCK`] `mock_response.headers = {}``
- L8650 [`MOCK`] `- L166 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8651 [`MOCK`] `- L167 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8652 [`MOCK`] `- L168 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8653 [`MOCK`] `- L169 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8654 [`MOCK`] `- L176 [`MOCK`] `assert mock_sleep.called``
- L8655 [`MOCK`] `- L181 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8656 [`MOCK`] `- L182 [`MOCK`] `breaker_manager = MagicMock()``
- L8657 [`MOCK`] `- L183 [`MOCK`] `breaker = MagicMock()``
- L8658 [`MOCK`] `- L184 [`MOCK`] `breaker.is_open = AsyncMock(return_value=True)``
- L8659 [`MOCK`] `- L185 [`MOCK`] `breaker_manager.get_breaker = AsyncMock(return_value=breaker)``
- L8660 [`MOCK`] `- L203 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8661 [`MOCK`] `- L204 [`MOCK`] `mock_response = AsyncMock()``
- L8662 [`MOCK`] `- L205 [`MOCK`] `mock_response.status_code = 200``
- L8663 [`MOCK`] `- L208 [`MOCK`] `mock_response.headers = {``
- L8664 [`MOCK`] `- L212 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8665 [`MOCK`] `- L213 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8666 [`MOCK`] `- L214 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8667 [`MOCK`] `- L226 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8668 [`MOCK`] `- L227 [`MOCK`] `mock_response = AsyncMock()``
- L8669 [`MOCK`] `- L228 [`MOCK`] `mock_response.status_code = 200``
- L8670 [`MOCK`] `- L229 [`MOCK`] `mock_response.headers = {}``
- L8671 [`MOCK`] `- L237 [`MOCK`] `mock_response.aiter_bytes = lambda: async_iter()``
- L8672 [`MOCK`] `- L239 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8673 [`MOCK`] `- L240 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8674 [`MOCK`] `- L241 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8675 [`MOCK`] `- L253 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8676 [`MOCK`] `- L254 [`MOCK`] `mock_response = AsyncMock()``
- L8677 [`MOCK`] `- L255 [`MOCK`] `mock_response.status_code = 200``
- L8678 [`MOCK`] `- L256 [`MOCK`] `mock_response.headers = {}``
- L8679 [`MOCK`] `- L261 [`MOCK`] `mock_response.aiter_bytes = lambda: async_gen()``
- L8680 [`MOCK`] `- L263 [`MOCK`] `mock_stream_ctx = AsyncMock()``
- L8681 [`MOCK`] `- L264 [`MOCK`] `mock_stream_ctx.__aenter__.return_value = mock_response``
- L8682 [`MOCK`] `- L265 [`MOCK`] `client.stream.return_value = mock_stream_ctx``
- L8683 [`MOCK`] `- L267 [`MOCK`] `tracker = MagicMock()``
- L8684 [`MOCK`] `- L268 [`MOCK`] `tracker.get_timeout = MagicMock(return_value=10.0)``
- L8685 [`MOCK`] `- L269 [`MOCK`] `tracker.record = AsyncMock()``
- L8686 [`MOCK`] `- L270 [`MOCK`] `tracker.get_jitter = AsyncMock(return_value=3.0)  # High jitter``
- L8687 [`MOCK`] `- L273 [`MOCK`] `with patch("configstream.fetcher.logger") as mock_logger:``
- L8688 [`MOCK`] `- L276 [`MOCK`] `assert any("High Jitter" in str(call) for call in mock_logger.info.mock_calls)``
- L8689 [`MOCK`] `- L281 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8690 [`MOCK`] `- L285 [`MOCK`] `with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:``
- L8691 [`MOCK`] `- L291 [`MOCK`] `assert mock_sleep.call_count > 0``
- L8692 [`MOCK`] `- L296 [`MOCK`] `# Integration test mocking minimal internals``
- L8693 [`MOCK`] `- L298 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:``
- L8694 [`MOCK`] `- L299 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")``
- L8695 [`MOCK`] `- L310 [`MOCK`] `client = AsyncMock(spec=httpx.AsyncClient)``
- L8696 [`MOCK`] `- L312 [`MOCK`] `with patch("configstream.fetcher.fetch_from_source") as mock_single:``
- L8697 [`MOCK`] `- L313 [`MOCK`] `mock_single.return_value = FetchResult(True, "src1")``
- L8700 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L8701 [`MOCK`] `- L10 [`MOCK`] `# Helper to mock the stream context manager``
- L8702 [`MOCK`] `- L11 [`MOCK`] `class MockStreamResponse:``
- L8703 [`MOCK`] `- L39 [`MOCK`] `# Mock stream instead of get``
- L8704 [`MOCK`] `- L40 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8705 [`MOCK`] `- L41 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "ok")``
- L8706 [`MOCK`] `- L52 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8707 [`MOCK`] `- L53 [`MOCK`] `resp1 = MockStreamResponse(429, "", headers={"Retry-After": "0.1"})``
- L8708 [`MOCK`] `- L54 [`MOCK`] `resp2 = MockStreamResponse(200, "ok")``
- L8709 [`MOCK`] `- L56 [`MOCK`] `mock_stream.side_effect = [resp1, resp2]``
- L8710 [`MOCK`] `- L63 [`MOCK`] `assert mock_stream.call_count == 2``
- L8711 [`MOCK`] `- L94 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8712 [`MOCK`] `- L95 [`MOCK`] `mock_stream.return_value = MockStreamResponse(200, "streamed_content")``
- L8713 [`MOCK`] `- L104 [`MOCK`] `# We assert mock_stream was called, implying we used the safer path``
- L8714 [`MOCK`] `- L105 [`MOCK`] `mock_stream.assert_called_once()``
- L8715 [`MOCK`] `- L122 [`MOCK`] `with patch("httpx.AsyncClient.stream", new_callable=MagicMock) as mock_stream:``
- L8716 [`MOCK`] `- L123 [`MOCK`] `mock_stream.return_value = MockStreamResponse(404, "")``
- L8717 [`MOCK`] `- L151 [`MOCK`] `assert mock_stream.call_count == 2``
- L8720 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L8721 [`MOCK`] `- L15 [`MOCK`] `# by mocking the constant or by testing the behavior with a large response.``
- L8722 [`MOCK`] `- L25 [`MOCK`] `# Create a mock response with Content-Length > MAX_RESPONSE_SIZE``
- L8723 [`MOCK`] `- L26 [`MOCK`] `mock_client = MagicMock(spec=httpx.AsyncClient)``
- L8724 [`MOCK`] `- L27 [`MOCK`] `mock_response = MagicMock()``
- L8725 [`MOCK`] `- L28 [`MOCK`] `mock_response.status_code = 200``
- L8726 [`MOCK`] `- L29 [`MOCK`] `mock_response.headers = {``
- L8727 [`MOCK`] `- L33 [`MOCK`] `# Mock stream context manager``
- L8728 [`MOCK`] `- L34 [`MOCK`] `mock_stream = MagicMock()``
- L8729 [`MOCK`] `- L35 [`MOCK`] `mock_stream.__aenter__.return_value = mock_response``
- L8730 [`MOCK`] `- L36 [`MOCK`] `mock_stream.__aexit__.return_value = None``
- L8731 [`MOCK`] `- L37 [`MOCK`] `mock_client.stream.return_value = mock_stream``
- L8732 [`MOCK`] `- L41 [`MOCK`] `mock_client, "http://example.com", app_settings=app_settings``
- L8735 [`MOCK`] `- L8 [`MOCK`] `async def test_fetch_success(respx_mock):``
- L8736 [`MOCK`] `- L10 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(200, text="content"))``
- L8737 [`MOCK`] `- L20 [`MOCK`] `async def test_fetch_404(respx_mock):``
- L8738 [`MOCK`] `- L22 [`MOCK`] `respx_mock.get(url).mock(return_value=httpx.Response(404))``
- L8739 [`MOCK`] `- L33 [`MOCK`] `async def test_fetch_retry_on_error(respx_mock):``
- L8740 [`MOCK`] `- L36 [`MOCK`] `route = respx_mock.get(url)``
- L8741 [`MOCK`] `- L52 [`MOCK`] `async def test_fetch_rate_limit(respx_mock):``
- L8742 [`MOCK`] `- L55 [`MOCK`] `route = respx_mock.get(url)``
- L8745 [`MOCK`] `- L11 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8746 [`MOCK`] `- L12 [`MOCK`] `# Mock 404 response``
- L8747 [`MOCK`] `- L13 [`MOCK`] `respx_mock.get("/missing").mock(return_value=httpx.Response(404))``
- L8748 [`MOCK`] `- L23 [`MOCK`] `assert respx_mock.calls.call_count == 1  # Should only call once``
- L8749 [`MOCK`] `- L29 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8750 [`MOCK`] `- L30 [`MOCK`] `# Mock 410 response``
- L8751 [`MOCK`] `- L31 [`MOCK`] `respx_mock.get("/gone").mock(return_value=httpx.Response(410))``
- L8752 [`MOCK`] `- L40 [`MOCK`] `assert respx_mock.calls.call_count == 1``
- L8753 [`MOCK`] `- L46 [`MOCK`] `with respx.mock(base_url="https://example.com") as respx_mock:``
- L8754 [`MOCK`] `- L47 [`MOCK`] `# Mock 500 response``
- L8755 [`MOCK`] `- L48 [`MOCK`] `respx_mock.get("/error").mock(return_value=httpx.Response(500))``
- L8756 [`MOCK`] `- L59 [`MOCK`] `assert respx_mock.calls.call_count == 2``
- L8759 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8760 [`MOCK`] `- L24 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L8761 [`MOCK`] `- L60 [`MOCK`] `# Since we used MagicMock, identity might be tricky if dedupe makes copies,``
- L8762 [`MOCK`] `- L142 [`MOCK`] `# Mock AppSettings to return seed``
- L8763 [`MOCK`] `- L144 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:``
- L8764 [`MOCK`] `- L145 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"``
- L8765 [`MOCK`] `- L148 [`MOCK`] `with patch("configstream.filtering.AppSettings") as mock_settings:``
- L8766 [`MOCK`] `- L149 [`MOCK`] `mock_settings.return_value.CONFIGSTREAM_SHUFFLE_SEED = "42"``
- L8769 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8770 [`MOCK`] `- L20 [`MOCK`] `resolver.reader_city = MagicMock()``
- L8771 [`MOCK`] `- L24 [`MOCK`] `resolver.reader_asn = MagicMock()``
- L8774 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L8775 [`MOCK`] `- L12 [`MOCK`] `# Mock process``
- L8776 [`MOCK`] `- L13 [`MOCK`] `proc = MagicMock()``
- L8777 [`MOCK`] `- L15 [`MOCK`] `proc.stdin = MagicMock()``
- L8778 [`MOCK`] `- L16 [`MOCK`] `proc.stdin.write = MagicMock()``
- L8779 [`MOCK`] `- L17 [`MOCK`] `proc.stdin.drain = AsyncMock()``
- L8780 [`MOCK`] `- L18 [`MOCK`] `proc.stdin.close = MagicMock()``
- L8781 [`MOCK`] `- L19 [`MOCK`] `proc.wait = AsyncMock()``
- L8782 [`MOCK`] `- L20 [`MOCK`] `proc.terminate = MagicMock()``
- L8783 [`MOCK`] `- L21 [`MOCK`] `proc.kill = MagicMock()``
- L8784 [`MOCK`] `- L23 [`MOCK`] `# Mock stdout with an AsyncMock readline that returns lines then empty string``
- L8785 [`MOCK`] `- L24 [`MOCK`] `proc.stdout = MagicMock()``
- L8786 [`MOCK`] `- L30 [`MOCK`] `async def mock_readline():``
- L8787 [`MOCK`] `- L33 [`MOCK`] `proc.stdout.readline = mock_readline``
- L8788 [`MOCK`] `- L35 [`MOCK`] `proc.stderr = MagicMock()``
- L8789 [`MOCK`] `- L37 [`MOCK`] `proc.stderr.readline = AsyncMock(return_value=b"")  # No logs``
- L8790 [`MOCK`] `- L39 [`MOCK`] `with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):``
- L8791 [`MOCK`] `- L43 [`MOCK`] `# Mock self_test to succeed since we are mocking process anyway``
- L8792 [`MOCK`] `- L44 [`MOCK`] `with patch.object(GoBatchTester, "self_test", new=AsyncMock(return_value=True)):``
- L8793 [`MOCK`] `- L80 [`MOCK`] `print(f"Error in mock write: {e}")``
- L8796 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, AsyncMock``
- L8797 [`MOCK`] `- L10 [`MOCK`] `# Mock VirusTotal to return safe``
- L8798 [`MOCK`] `- L12 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8799 [`MOCK`] `- L13 [`MOCK`] `) as mock_vt:``
- L8800 [`MOCK`] `- L14 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8801 [`MOCK`] `- L19 [`MOCK`] `mock_vt.assert_called_once_with("1.1.1.1")``
- L8802 [`MOCK`] `- L24 [`MOCK`] `"""Verify passive detection works via VirusTotal mock."""``
- L8803 [`MOCK`] `- L26 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8804 [`MOCK`] `- L27 [`MOCK`] `) as mock_vt:``
- L8805 [`MOCK`] `- L28 [`MOCK`] `mock_vt.return_value = {"malicious": 5}``
- L8806 [`MOCK`] `- L38 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8807 [`MOCK`] `- L39 [`MOCK`] `) as mock_vt:``
- L8808 [`MOCK`] `- L40 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8809 [`MOCK`] `- L44 [`MOCK`] `mock_vt.assert_called_once_with("8.8.8.8")``
- L8810 [`MOCK`] `- L51 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8811 [`MOCK`] `- L52 [`MOCK`] `) as mock_vt:``
- L8812 [`MOCK`] `- L53 [`MOCK`] `mock_vt.return_value = {"malicious": 100}``
- L8813 [`MOCK`] `- L63 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8814 [`MOCK`] `- L64 [`MOCK`] `) as mock_vt:``
- L8815 [`MOCK`] `- L65 [`MOCK`] `mock_vt.return_value = {"malicious": 1}``
- L8816 [`MOCK`] `- L75 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8817 [`MOCK`] `- L76 [`MOCK`] `) as mock_vt:``
- L8818 [`MOCK`] `- L77 [`MOCK`] `mock_vt.return_value = {}``
- L8819 [`MOCK`] `- L88 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8820 [`MOCK`] `- L89 [`MOCK`] `) as mock_vt:``
- L8821 [`MOCK`] `- L90 [`MOCK`] `mock_vt.side_effect = Exception("API Error")``
- L8822 [`MOCK`] `- L101 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8823 [`MOCK`] `- L102 [`MOCK`] `) as mock_vt:``
- L8824 [`MOCK`] `- L103 [`MOCK`] `mock_vt.side_effect = TimeoutError("Request timed out")``
- L8825 [`MOCK`] `- L113 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8826 [`MOCK`] `- L114 [`MOCK`] `) as mock_vt:``
- L8827 [`MOCK`] `- L115 [`MOCK`] `mock_vt.side_effect = ConnectionError("Network unreachable")``
- L8828 [`MOCK`] `- L125 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8829 [`MOCK`] `- L126 [`MOCK`] `) as mock_vt:``
- L8830 [`MOCK`] `- L127 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8831 [`MOCK`] `- L131 [`MOCK`] `mock_vt.assert_called_once_with("2001:4860:4860::8888")``
- L8832 [`MOCK`] `- L138 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8833 [`MOCK`] `- L139 [`MOCK`] `) as mock_vt:``
- L8834 [`MOCK`] `- L140 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8835 [`MOCK`] `- L144 [`MOCK`] `mock_vt.assert_called_once_with("example.com")``
- L8836 [`MOCK`] `- L151 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8837 [`MOCK`] `- L152 [`MOCK`] `) as mock_vt:``
- L8838 [`MOCK`] `- L153 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8839 [`MOCK`] `- L163 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8840 [`MOCK`] `- L164 [`MOCK`] `) as mock_vt:``
- L8841 [`MOCK`] `- L165 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8842 [`MOCK`] `- L175 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8843 [`MOCK`] `- L176 [`MOCK`] `) as mock_vt:``
- L8844 [`MOCK`] `- L177 [`MOCK`] `mock_vt.return_value = {"malicious": -1}``
- L8845 [`MOCK`] `- L188 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8846 [`MOCK`] `- L189 [`MOCK`] `) as mock_vt:``
- L8847 [`MOCK`] `- L190 [`MOCK`] `mock_vt.return_value = None``
- L8848 [`MOCK`] `- L206 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8849 [`MOCK`] `- L207 [`MOCK`] `) as mock_vt:``
- L8850 [`MOCK`] `- L208 [`MOCK`] `mock_vt.return_value = "error"``
- L8851 [`MOCK`] `- L219 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8852 [`MOCK`] `- L220 [`MOCK`] `) as mock_vt:``
- L8853 [`MOCK`] `- L221 [`MOCK`] `mock_vt.return_value = {"malicious": 0}``
- L8854 [`MOCK`] `- L225 [`MOCK`] `mock_vt.assert_called_once_with("")``
- L8855 [`MOCK`] `- L232 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8856 [`MOCK`] `- L233 [`MOCK`] `) as mock_vt:``
- L8857 [`MOCK`] `- L234 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:``
- L8858 [`MOCK`] `- L235 [`MOCK`] `mock_vt.return_value = {"malicious": 3}``
- L8859 [`MOCK`] `- L241 [`MOCK`] `mock_logger.warning.assert_called_once()``
- L8860 [`MOCK`] `- L242 [`MOCK`] `call_args = str(mock_logger.warning.call_args)``
- L8861 [`MOCK`] `- L250 [`MOCK`] `"configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock``
- L8862 [`MOCK`] `- L251 [`MOCK`] `) as mock_vt:``
- L8863 [`MOCK`] `- L252 [`MOCK`] `with patch("configstream.security.honeypot.logger") as mock_logger:``
- L8864 [`MOCK`] `- L253 [`MOCK`] `mock_vt.side_effect = ValueError("Invalid IP")``
- L8865 [`MOCK`] `- L259 [`MOCK`] `mock_logger.error.assert_called_once()``
- L8866 [`MOCK`] `- L260 [`MOCK`] `call_args = str(mock_logger.error.call_args)``
- L8869 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import patch``
- L8870 [`MOCK`] `- L154 [`MOCK`] `# Verify set_event_loop_policy was called (might have been called before mock)``
- L8873 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock``
- L8874 [`MOCK`] `- L43 [`MOCK`] `def mock_storage():``
- L8875 [`MOCK`] `- L44 [`MOCK`] `return MagicMock(spec=QualityStorage)``
- L8876 [`MOCK`] `- L58 [`MOCK`] `def test_metadata_generation(tmp_path, sample_proxies, mock_storage):``
- L8879 [`MOCK`] `- L6 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8882 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L8883 [`MOCK`] `- L48 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8884 [`MOCK`] `- L49 [`MOCK`] `MockHistory.return_value.get_history.return_value = []``
- L8885 [`MOCK`] `- L62 [`MOCK`] `with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:``
- L8886 [`MOCK`] `- L63 [`MOCK`] `MockHistory.return_value.get_history.return_value = []``
- L8887 [`MOCK`] `- L105 [`MOCK`] `patch("configstream.generators.singbox.to_singbox_outbound") as mock_conv,``
- L8888 [`MOCK`] `- L109 [`MOCK`] `mock_conv.return_value = {"type": "vless", "tag": "vless-out"}``
- L8889 [`MOCK`] `- L131 [`MOCK`] `patch("configstream.output_logic.ProxyWasher") as MockWasher,``
- L8890 [`MOCK`] `- L140 [`MOCK`] `patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory,``
- L8891 [`MOCK`] `- L141 [`MOCK`] `):  # Mock history to return serializable data``
- L8892 [`MOCK`] `- L143 [`MOCK`] `# Configure mock history to return empty list (serializable)``
- L8893 [`MOCK`] `- L144 [`MOCK`] `history_instance = MockHistory.return_value``
- L8894 [`MOCK`] `- L147 [`MOCK`] `MockWasher.return_value.wash_batch.return_value = ([], set(), {})``
- L8897 [`PLACEHOLDER`] `- L244 [`PLACEHOLDER`] `config="revived://placeholder",``
- L8900 [`MOCK`] `- L246 [`MOCK`] `from unittest.mock import patch``
- L8903 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import AsyncMock, patch, MagicMock``
- L8904 [`MOCK`] `- L12 [`MOCK`] `def mock_work_queue():``
- L8905 [`MOCK`] `- L18 [`MOCK`] `def mock_tester():``
- L8906 [`MOCK`] `- L19 [`MOCK`] `tester = MagicMock(spec=SingBoxTester)``
- L8907 [`MOCK`] `- L20 [`MOCK`] `tester.go_tester = MagicMock()``
- L8908 [`MOCK`] `- L22 [`MOCK`] `tester.test = AsyncMock(``
- L8909 [`MOCK`] `- L36 [`MOCK`] `def mock_quality_tracker():``
- L8910 [`MOCK`] `- L37 [`MOCK`] `tracker = MagicMock()``
- L8911 [`MOCK`] `- L38 [`MOCK`] `tracker.should_fetch = MagicMock(return_value=True)``
- L8912 [`MOCK`] `- L43 [`MOCK`] `def mock_concurrency():``
- L8913 [`MOCK`] `- L44 [`MOCK`] `cm = MagicMock()``
- L8914 [`MOCK`] `- L45 [`MOCK`] `cm.get_semaphore = MagicMock(return_value=AsyncMock())``
- L8915 [`MOCK`] `- L46 [`MOCK`] `cm.get_semaphore.return_value.__aenter__ = AsyncMock()``
- L8916 [`MOCK`] `- L47 [`MOCK`] `cm.get_semaphore.return_value.__aexit__ = AsyncMock()``
- L8917 [`MOCK`] `- L48 [`MOCK`] `cm.start_tuner = MagicMock()``
- L8918 [`MOCK`] `- L49 [`MOCK`] `cm.stop_tuner = AsyncMock()``
- L8919 [`MOCK`] `- L50 [`MOCK`] `cm.record = AsyncMock()``
- L8920 [`MOCK`] `- L56 [`MOCK`] `mock_work_queue, mock_tester, mock_quality_tracker, mock_concurrency``
- L8921 [`MOCK`] `- L62 [`MOCK`] `# Mock dependencies``
- L8922 [`MOCK`] `- L63 [`MOCK`] `scheduler = MagicMock()``
- L8923 [`MOCK`] `- L64 [`MOCK`] `scheduler.should_retest = MagicMock(return_value=True)``
- L8924 [`MOCK`] `- L66 [`MOCK`] `test_cache = MagicMock()``
- L8925 [`MOCK`] `- L67 [`MOCK`] `test_cache.get = MagicMock(return_value=None)``
- L8926 [`MOCK`] `- L69 [`MOCK`] `geoip = MagicMock()``
- L8927 [`MOCK`] `- L70 [`MOCK`] `geoip.lookup = AsyncMock(``
- L8928 [`MOCK`] `- L71 [`MOCK`] `return_value=MagicMock(``
- L8929 [`MOCK`] `- L76 [`MOCK`] `tracker = MagicMock()``
- L8930 [`MOCK`] `- L77 [`MOCK`] `tracker.phase = MagicMock(``
- L8931 [`MOCK`] `- L78 [`MOCK`] `return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())``
- L8932 [`MOCK`] `- L82 [`MOCK`] `raw_lines = ["vmess://eyJaddfqwefqwe..."]  # Mock line``
- L8933 [`MOCK`] `- L84 [`MOCK`] `await mock_work_queue.put((source, raw_lines))``
- L8934 [`MOCK`] `- L85 [`MOCK`] `await mock_work_queue.put(None)  # Signal end``
- L8935 [`MOCK`] `- L87 [`MOCK`] `# Mock parse_config to return a proxy``
- L8936 [`MOCK`] `- L111 [`MOCK`] `mock_work_queue,``
- L8937 [`MOCK`] `- L115 [`MOCK`] `mock_tester,``
- L8938 [`MOCK`] `- L118 [`MOCK`] `mock_concurrency,``
- L8939 [`MOCK`] `- L122 [`MOCK`] `mock_quality_tracker,``
- L8940 [`MOCK`] `- L123 [`MOCK`] `MagicMock(),  # history``
- L8943 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L8944 [`MOCK`] `- L26 [`MOCK`] `# Mocks``
- L8945 [`MOCK`] `- L27 [`MOCK`] `mock_tester = MagicMock()``
- L8946 [`MOCK`] `- L28 [`MOCK`] `mock_tester.go_tester.available = False  # Use Python path``
- L8947 [`MOCK`] `- L29 [`MOCK`] `mock_tester.test = MagicMock()``
- L8948 [`MOCK`] `- L31 [`MOCK`] `# Mock result for test() must be awaitable``
- L8949 [`MOCK`] `- L32 [`MOCK`] `async def mock_test_result(p):``
- L8950 [`MOCK`] `- L37 [`MOCK`] `mock_tester.test.side_effect = mock_test_result``
- L8951 [`MOCK`] `- L39 [`MOCK`] `mock_scheduler = MagicMock(spec=SmartRetestScheduler)``
- L8952 [`MOCK`] `- L40 [`MOCK`] `mock_scheduler.should_retest.return_value = True``
- L8953 [`MOCK`] `- L42 [`MOCK`] `mock_cache = MagicMock(spec=TestResultCache)``
- L8954 [`MOCK`] `- L43 [`MOCK`] `mock_cache.get.return_value = None``
- L8955 [`MOCK`] `- L45 [`MOCK`] `mock_concurrency = MagicMock(spec=ConcurrencyManager)``
- L8956 [`MOCK`] `- L46 [`MOCK`] `# mock get_semaphore must return an async context manager``
- L8957 [`MOCK`] `- L48 [`MOCK`] `mock_concurrency.get_semaphore.return_value = asyncio.Semaphore(10)``
- L8958 [`MOCK`] `- L49 [`MOCK`] `mock_concurrency.record = MagicMock()  # awaitable? record is async def``
- L8959 [`MOCK`] `- L51 [`MOCK`] `async def mock_record(*args):``
- L8960 [`MOCK`] `- L55 [`MOCK`] `mock_concurrency.start_tuner = MagicMock()``
- L8961 [`MOCK`] `- L59 [`MOCK`] `mock_concurrency.stop_tuner = MagicMock(return_value=f)``
- L8962 [`MOCK`] `- L61 [`MOCK`] `mock_concurrency.record.side_effect = mock_record``
- L8963 [`MOCK`] `- L63 [`MOCK`] `from unittest.mock import AsyncMock``
- L8964 [`MOCK`] `- L65 [`MOCK`] `mock_geoip = MagicMock()``
- L8965 [`MOCK`] `- L66 [`MOCK`] `mock_geoip.lookup = AsyncMock(``
- L8966 [`MOCK`] `- L67 [`MOCK`] `return_value=MagicMock(country_code="US", city="Test", asn="AS1", org="Org")``
- L8967 [`MOCK`] `- L71 [`MOCK`] `mock_quality = MagicMock(spec=SourceQualityTracker)``
- L8968 [`MOCK`] `- L73 [`MOCK`] `# Need to mock parse_config or ensure "vmess://test" parses``
- L8969 [`MOCK`] `- L74 [`MOCK`] `with patch("configstream.consumer.parse_config") as mock_parse:``
- L8970 [`MOCK`] `- L77 [`MOCK`] `mock_parse.return_value = p``
- L8971 [`MOCK`] `- L79 [`MOCK`] `# We also need to mock validate_batch_configs to just return the list``
- L8972 [`MOCK`] `- L80 [`MOCK`] `with patch("configstream.consumer.validate_batch_configs") as mock_validate:``
- L8973 [`MOCK`] `- L81 [`MOCK`] `mock_validate.side_effect = lambda batch, policy: batch``
- L8974 [`MOCK`] `- L88 [`MOCK`] `tester=mock_tester,``
- L8975 [`MOCK`] `- L89 [`MOCK`] `scheduler=mock_scheduler,``
- L8976 [`MOCK`] `- L90 [`MOCK`] `test_cache=mock_cache,``
- L8977 [`MOCK`] `- L91 [`MOCK`] `concurrency=mock_concurrency,``
- L8978 [`MOCK`] `- L92 [`MOCK`] `geoip=mock_geoip,``
- L8979 [`MOCK`] `- L95 [`MOCK`] `quality_tracker=mock_quality,``
- L8980 [`MOCK`] `- L96 [`MOCK`] `history=MagicMock(),``
- L8983 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L8984 [`MOCK`] `- L10 [`MOCK`] `def mock_proxies():``
- L8985 [`MOCK`] `- L34 [`MOCK`] `async def test_pipeline_dry_run(tmp_path, mock_proxies):``
- L8986 [`MOCK`] `- L35 [`MOCK`] `# Create a callable that returns mock_proxies to avoid fixture timing issues``
- L8987 [`MOCK`] `- L36 [`MOCK`] `def filter_unique_mock(*args, **kwargs):``
- L8988 [`MOCK`] `- L37 [`MOCK`] `return list(mock_proxies)``
- L8989 [`MOCK`] `- L40 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L8990 [`MOCK`] `- L43 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L8991 [`MOCK`] `- L44 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L8992 [`MOCK`] `- L45 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L8993 [`MOCK`] `- L46 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L8994 [`MOCK`] `- L49 [`MOCK`] `side_effect=filter_unique_mock,``
- L8995 [`MOCK`] `- L56 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,``
- L8996 [`MOCK`] `- L59 [`MOCK`] `new=MagicMock(spec=ProxyWasher),``
- L8997 [`MOCK`] `- L60 [`MOCK`] `) as MockWasher,``
- L8998 [`MOCK`] `- L67 [`MOCK`] `# Configure mocked tester to be awaitable on close``
- L8999 [`MOCK`] `- L68 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L9000 [`MOCK`] `- L69 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L9001 [`MOCK`] `- L71 [`MOCK`] `# Configure EventStream mock``
- L9002 [`MOCK`] `- L72 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L9003 [`MOCK`] `- L74 [`MOCK`] `history = MagicMock()``
- L9004 [`MOCK`] `- L78 [`MOCK`] `MockHistory.return_value = history``
- L9005 [`MOCK`] `- L80 [`MOCK`] `# Mocking washer methods correctly``
- L9006 [`MOCK`] `- L81 [`MOCK`] `washer_instance = MockWasher.return_value``
- L9007 [`MOCK`] `- L82 [`MOCK`] `washer_instance.fetch_clean_ips = AsyncMock()``
- L9008 [`MOCK`] `- L83 [`MOCK`] `washer_instance.wash_batch = MagicMock(return_value=([], set(), {}))``
- L9009 [`MOCK`] `- L99 [`MOCK`] `final_proxies.extend(mock_proxies)``
- L9010 [`MOCK`] `- L100 [`MOCK`] `stats.working = len(mock_proxies)``
- L9011 [`MOCK`] `- L110 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L9012 [`MOCK`] `- L111 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L9013 [`MOCK`] `- L117 [`MOCK`] `proxies=mock_proxies,``
- L9014 [`MOCK`] `- L128 [`MOCK`] `async def test_pipeline_pareto_sort(tmp_path, mock_proxies):``
- L9015 [`MOCK`] `- L131 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L9016 [`MOCK`] `- L134 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L9017 [`MOCK`] `- L135 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L9018 [`MOCK`] `- L136 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L9019 [`MOCK`] `- L137 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L9020 [`MOCK`] `- L140 [`MOCK`] `new=AsyncMock(return_value={}),``
- L9021 [`MOCK`] `- L142 [`MOCK`] `patch("configstream.pipeline.ProxyHistoryTracker") as MockHistory,``
- L9022 [`MOCK`] `- L144 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L9023 [`MOCK`] `- L145 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L9024 [`MOCK`] `- L147 [`MOCK`] `# Configure EventStream mock``
- L9025 [`MOCK`] `- L148 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L9026 [`MOCK`] `- L150 [`MOCK`] `# Mock history to prefer the higher latency one (reliability > latency scenario)``
- L9027 [`MOCK`] `- L151 [`MOCK`] `history = MagicMock()``
- L9028 [`MOCK`] `- L152 [`MOCK`] `MockHistory.return_value = history``
- L9029 [`MOCK`] `- L164 [`MOCK`] `final_proxies.extend(mock_proxies)``
- L9030 [`MOCK`] `- L171 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L9031 [`MOCK`] `- L172 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L9032 [`MOCK`] `- L180 [`MOCK`] `# Since we mock consumer to just append proxies, they are unsorted initially.``
- L9033 [`MOCK`] `- L182 [`MOCK`] `# We can't easily assert sort order here without mocking the sort function or checking result side effects``
- L9034 [`MOCK`] `- L187 [`MOCK`] `async def test_pipeline_adapter_export_fail(tmp_path, mock_proxies):``
- L9035 [`MOCK`] `- L189 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as MockTester,``
- L9036 [`MOCK`] `- L192 [`MOCK`] `patch("configstream.pipeline.EventStream") as MockEventStream,``
- L9037 [`MOCK`] `- L193 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new=AsyncMock()),``
- L9038 [`MOCK`] `- L194 [`MOCK`] `patch("configstream.pipeline.source_producer") as mock_producer,``
- L9039 [`MOCK`] `- L195 [`MOCK`] `patch("configstream.pipeline.processing_consumer") as mock_consumer,``
- L9040 [`MOCK`] `- L198 [`MOCK`] `new=AsyncMock(side_effect=Exception("Export Fail")),``
- L9041 [`MOCK`] `- L202 [`MOCK`] `MockTester.return_value.close = AsyncMock()``
- L9042 [`MOCK`] `- L203 [`MOCK`] `MockTester.return_value.go_tester.available = False``
- L9043 [`MOCK`] `- L205 [`MOCK`] `# Configure EventStream mock``
- L9044 [`MOCK`] `- L206 [`MOCK`] `MockEventStream.return_value.aclose = AsyncMock()``
- L9045 [`MOCK`] `- L223 [`MOCK`] `mock_producer.side_effect = fake_producer``
- L9046 [`MOCK`] `- L224 [`MOCK`] `mock_consumer.side_effect = fake_consumer``
- L9049 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, AsyncMock, patch``
- L9050 [`MOCK`] `- L14 [`MOCK`] `"configstream.pipeline.source_producer", new_callable=AsyncMock``
- L9051 [`MOCK`] `- L15 [`MOCK`] `) as mock_prod,``
- L9052 [`MOCK`] `- L17 [`MOCK`] `"configstream.pipeline.processing_consumer", new_callable=AsyncMock``
- L9053 [`MOCK`] `- L18 [`MOCK`] `) as mock_cons,``
- L9054 [`MOCK`] `- L21 [`MOCK`] `new_callable=AsyncMock,``
- L9055 [`MOCK`] `- L22 [`MOCK`] `) as mock_gen,``
- L9056 [`MOCK`] `- L23 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),``
- L9057 [`MOCK`] `- L24 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,``
- L9058 [`MOCK`] `- L26 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,``
- L9059 [`MOCK`] `- L29 [`MOCK`] `mock_tester = mock_tester_cls.return_value``
- L9060 [`MOCK`] `- L30 [`MOCK`] `mock_tester.go_tester = MagicMock()``
- L9061 [`MOCK`] `- L31 [`MOCK`] `mock_tester.go_tester.available = False``
- L9062 [`MOCK`] `- L32 [`MOCK`] `mock_tester.close = AsyncMock()``
- L9063 [`MOCK`] `- L34 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()``
- L9064 [`MOCK`] `- L47 [`MOCK`] `assert mock_prod.called, "source_producer should have been called"``
- L9065 [`MOCK`] `- L48 [`MOCK`] `assert mock_cons.called, "processing_consumer should have been called"``
- L9066 [`MOCK`] `- L49 [`MOCK`] `assert mock_gen.called, "generate_pipeline_outputs should have been called"``
- L9067 [`MOCK`] `- L58 [`MOCK`] `patch("configstream.pipeline.source_producer", new_callable=AsyncMock),``
- L9068 [`MOCK`] `- L59 [`MOCK`] `patch("configstream.pipeline.processing_consumer", new_callable=AsyncMock),``
- L9069 [`MOCK`] `- L62 [`MOCK`] `new_callable=AsyncMock,``
- L9070 [`MOCK`] `- L64 [`MOCK`] `patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),``
- L9071 [`MOCK`] `- L65 [`MOCK`] `patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,``
- L9072 [`MOCK`] `- L68 [`MOCK`] `patch("configstream.pipeline.EventStream") as mock_event_stream,``
- L9073 [`MOCK`] `- L71 [`MOCK`] `mock_tester = mock_tester_cls.return_value``
- L9074 [`MOCK`] `- L72 [`MOCK`] `mock_tester.go_tester = MagicMock()``
- L9075 [`MOCK`] `- L73 [`MOCK`] `mock_tester.go_tester.available = False``
- L9076 [`MOCK`] `- L74 [`MOCK`] `mock_tester.close = AsyncMock()``
- L9077 [`MOCK`] `- L75 [`MOCK`] `mock_event_stream.return_value.aclose = AsyncMock()``
- L9080 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import MagicMock, patch, AsyncMock``
- L9081 [`MOCK`] `- L13 [`MOCK`] `def mock_dependencies():``
- L9082 [`MOCK`] `- L15 [`MOCK`] `quality = MagicMock()``
- L9083 [`MOCK`] `- L17 [`MOCK`] `anomaly = MagicMock()``
- L9084 [`MOCK`] `- L20 [`MOCK`] `tester = MagicMock()``
- L9085 [`MOCK`] `- L22 [`MOCK`] `tester.test = AsyncMock()  # For python fallback``
- L9086 [`MOCK`] `- L23 [`MOCK`] `tester.test_batch = AsyncMock()  # For go tester``
- L9087 [`MOCK`] `- L25 [`MOCK`] `scheduler = MagicMock()``
- L9088 [`MOCK`] `- L28 [`MOCK`] `test_cache = MagicMock()``
- L9089 [`MOCK`] `- L31 [`MOCK`] `concurrency = MagicMock()``
- L9090 [`MOCK`] `- L32 [`MOCK`] `concurrency.start_tuner = MagicMock()``
- L9091 [`MOCK`] `- L33 [`MOCK`] `concurrency.stop_tuner = AsyncMock()``
- L9092 [`MOCK`] `- L34 [`MOCK`] `concurrency.get_semaphore.return_value = AsyncMock()``
- L9093 [`MOCK`] `- L35 [`MOCK`] `concurrency.record = AsyncMock()``
- L9094 [`MOCK`] `- L38 [`MOCK`] `sem = AsyncMock()``
- L9095 [`MOCK`] `- L43 [`MOCK`] `geoip = MagicMock()``
- L9096 [`MOCK`] `- L44 [`MOCK`] `geoip.lookup = AsyncMock(``
- L9097 [`MOCK`] `- L45 [`MOCK`] `return_value=MagicMock(``
- L9098 [`MOCK`] `- L50 [`MOCK`] `tracker = MagicMock()``
- L9099 [`MOCK`] `- L51 [`MOCK`] `tracker.phase.return_value = MagicMock()``
- L9100 [`MOCK`] `- L55 [`MOCK`] `history = MagicMock()``
- L9101 [`MOCK`] `- L56 [`MOCK`] `history.record_test_result = MagicMock()``
- L9102 [`MOCK`] `- L83 [`MOCK`] `async def test_source_producer_supplied_proxies(mock_dependencies):``
- L9103 [`MOCK`] `- L84 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9104 [`MOCK`] `- L91 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9105 [`MOCK`] `- L92 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9106 [`MOCK`] `- L104 [`MOCK`] `async def test_source_producer_local_files(mock_dependencies):``
- L9107 [`MOCK`] `- L105 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9108 [`MOCK`] `- L108 [`MOCK`] `with patch("configstream.producer.read_multiple_files_async") as mock_read:``
- L9109 [`MOCK`] `- L109 [`MOCK`] `mock_read.return_value = [("sources/batch_1.txt", "vmess://file")]``
- L9110 [`MOCK`] `- L115 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9111 [`MOCK`] `- L116 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9112 [`MOCK`] `- L128 [`MOCK`] `async def test_source_producer_remote_urls(mock_dependencies):``
- L9113 [`MOCK`] `- L129 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9114 [`MOCK`] `- L137 [`MOCK`] `# Mock fetcher``
- L9115 [`MOCK`] `- L138 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:``
- L9116 [`MOCK`] `- L139 [`MOCK`] `mock_fetch.return_value = {``
- L9117 [`MOCK`] `- L144 [`MOCK`] `# Mock read_multiple_files_async to prevent it from trying to read ss:// as file and logging warnings``
- L9118 [`MOCK`] `- L153 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9119 [`MOCK`] `- L154 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9120 [`MOCK`] `- L181 [`MOCK`] `async def test_source_producer_anomaly_block(mock_dependencies):``
- L9121 [`MOCK`] `- L182 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9122 [`MOCK`] `- L185 [`MOCK`] `mock_dependencies["anomaly"].is_safe.return_value = (False, "Malicious")``
- L9123 [`MOCK`] `- L187 [`MOCK`] `with patch("configstream.producer.fetch_multiple_sources") as mock_fetch:``
- L9124 [`MOCK`] `- L188 [`MOCK`] `mock_fetch.return_value = {``
- L9125 [`MOCK`] `- L196 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9126 [`MOCK`] `- L197 [`MOCK`] `anomaly_detector=mock_dependencies["anomaly"],``
- L9127 [`MOCK`] `- L210 [`MOCK`] `async def test_processing_consumer_basic_flow(mock_dependencies):``
- L9128 [`MOCK`] `- L211 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9129 [`MOCK`] `- L220 [`MOCK`] `# Mock parse_config to return a valid proxy``
- L9130 [`MOCK`] `- L223 [`MOCK`] `# Mock tester to succeed``
- L9131 [`MOCK`] `- L229 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9132 [`MOCK`] `- L231 [`MOCK`] `# Mock validate_batch_configs``
- L9133 [`MOCK`] `- L241 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9134 [`MOCK`] `- L242 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9135 [`MOCK`] `- L243 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9136 [`MOCK`] `- L244 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9137 [`MOCK`] `- L245 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9138 [`MOCK`] `- L246 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9139 [`MOCK`] `- L248 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9140 [`MOCK`] `- L249 [`MOCK`] `history=mock_dependencies["history"],``
- L9141 [`MOCK`] `- L259 [`MOCK`] `assert final_proxies[0].country_code == "US"  # From GeoIP mock``
- L9142 [`MOCK`] `- L263 [`MOCK`] `async def test_processing_consumer_cached_hit(mock_dependencies):``
- L9143 [`MOCK`] `- L264 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9144 [`MOCK`] `- L278 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False``
- L9145 [`MOCK`] `- L279 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = cached_p``
- L9146 [`MOCK`] `- L291 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9147 [`MOCK`] `- L292 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9148 [`MOCK`] `- L293 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9149 [`MOCK`] `- L294 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9150 [`MOCK`] `- L295 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9151 [`MOCK`] `- L296 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9152 [`MOCK`] `- L298 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9153 [`MOCK`] `- L299 [`MOCK`] `history=mock_dependencies["history"],``
- L9154 [`MOCK`] `- L313 [`MOCK`] `async def test_processing_consumer_cache_miss(mock_dependencies):``
- L9155 [`MOCK`] `- L314 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9156 [`MOCK`] `- L325 [`MOCK`] `mock_dependencies["scheduler"].should_retest.return_value = False``
- L9157 [`MOCK`] `- L326 [`MOCK`] `mock_dependencies["test_cache"].get.return_value = None``
- L9158 [`MOCK`] `- L331 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9159 [`MOCK`] `- L343 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9160 [`MOCK`] `- L344 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9161 [`MOCK`] `- L345 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9162 [`MOCK`] `- L346 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9163 [`MOCK`] `- L347 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9164 [`MOCK`] `- L348 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9165 [`MOCK`] `- L350 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9166 [`MOCK`] `- L351 [`MOCK`] `history=mock_dependencies["history"],``
- L9167 [`MOCK`] `- L365 [`MOCK`] `async def test_processing_consumer_go_tester(mock_dependencies):``
- L9168 [`MOCK`] `- L366 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9169 [`MOCK`] `- L377 [`MOCK`] `mock_dependencies["tester"].go_tester.available = True``
- L9170 [`MOCK`] `- L379 [`MOCK`] `# Mock test_batch updates objects in place``
- L9171 [`MOCK`] `- L385 [`MOCK`] `mock_dependencies["tester"].test_batch.side_effect = side_effect``
- L9172 [`MOCK`] `- L397 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9173 [`MOCK`] `- L398 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9174 [`MOCK`] `- L399 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9175 [`MOCK`] `- L400 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9176 [`MOCK`] `- L401 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9177 [`MOCK`] `- L402 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9178 [`MOCK`] `- L404 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9179 [`MOCK`] `- L405 [`MOCK`] `history=mock_dependencies["history"],``
- L9180 [`MOCK`] `- L418 [`MOCK`] `async def test_processing_consumer_filters(mock_dependencies):``
- L9181 [`MOCK`] `- L419 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9182 [`MOCK`] `- L429 [`MOCK`] `# Mock Python tester returns working but HIGH latency``
- L9183 [`MOCK`] `- L433 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9184 [`MOCK`] `- L445 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9185 [`MOCK`] `- L446 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9186 [`MOCK`] `- L447 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9187 [`MOCK`] `- L448 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9188 [`MOCK`] `- L449 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9189 [`MOCK`] `- L450 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9190 [`MOCK`] `- L452 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9191 [`MOCK`] `- L453 [`MOCK`] `history=mock_dependencies["history"],``
- L9192 [`MOCK`] `- L466 [`MOCK`] `async def test_processing_consumer_country_filter(mock_dependencies):``
- L9193 [`MOCK`] `- L467 [`MOCK`] `queue = mock_dependencies["queue"]``
- L9194 [`MOCK`] `- L480 [`MOCK`] `mock_dependencies["tester"].test.return_value = res``
- L9195 [`MOCK`] `- L483 [`MOCK`] `mock_dependencies["geoip"].lookup = AsyncMock(``
- L9196 [`MOCK`] `- L484 [`MOCK`] `return_value=MagicMock(country_code="US", city="", asn="", org="")``
- L9197 [`MOCK`] `- L497 [`MOCK`] `tester=mock_dependencies["tester"],``
- L9198 [`MOCK`] `- L498 [`MOCK`] `scheduler=mock_dependencies["scheduler"],``
- L9199 [`MOCK`] `- L499 [`MOCK`] `test_cache=mock_dependencies["test_cache"],``
- L9200 [`MOCK`] `- L500 [`MOCK`] `concurrency=mock_dependencies["concurrency"],``
- L9201 [`MOCK`] `- L501 [`MOCK`] `geoip=mock_dependencies["geoip"],``
- L9202 [`MOCK`] `- L502 [`MOCK`] `tracker=mock_dependencies["tracker"],``
- L9203 [`MOCK`] `- L504 [`MOCK`] `quality_tracker=mock_dependencies["quality"],``
- L9204 [`MOCK`] `- L505 [`MOCK`] `history=mock_dependencies["history"],``
- L9207 [`MOCK`] `- L8 [`MOCK`] `from unittest.mock import MagicMock``
- L9208 [`MOCK`] `- L19 [`MOCK`] `quality = MagicMock()``
- L9211 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L9212 [`MOCK`] `- L15 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9213 [`MOCK`] `- L35 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9214 [`MOCK`] `- L63 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9215 [`MOCK`] `- L82 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9216 [`MOCK`] `- L106 [`MOCK`] `p = MagicMock(spec=Proxy)``
- L9219 [`MOCK`] `- L5 [`MOCK`] `from unittest.mock import MagicMock``
- L9220 [`MOCK`] `- L15 [`MOCK`] `self.cache = MagicMock(spec=TestResultCache)``
- L9221 [`MOCK`] `- L62 [`MOCK`] `# Mock: p1 needs test, p2 does not``
- L9222 [`MOCK`] `- L63 [`MOCK`] `self.scheduler.should_retest = MagicMock(side_effect=[True, False])``
- L9225 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch, MagicMock, AsyncMock``
- L9226 [`MOCK`] `- L11 [`MOCK`] `def mock_blocklist_file(tmp_path):``
- L9227 [`MOCK`] `- L25 [`MOCK`] `async def test_is_blocked_logic(mock_blocklist_file):``
- L9228 [`MOCK`] `- L28 [`MOCK`] `# Mock the CACHE_FILE path and content loading``
- L9229 [`MOCK`] `- L29 [`MOCK`] `mock_blocklist_file.write_text("1.2.3.4/32\n5.6.7.0/24")``
- L9230 [`MOCK`] `- L31 [`MOCK`] `with patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file):``
- L9231 [`MOCK`] `- L40 [`MOCK`] `async def test_update_blocklist(mock_blocklist_file):``
- L9232 [`MOCK`] `- L44 [`MOCK`] `patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file),``
- L9233 [`MOCK`] `- L45 [`MOCK`] `patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,``
- L9234 [`MOCK`] `- L47 [`MOCK`] `mock_resp = MagicMock()``
- L9235 [`MOCK`] `- L48 [`MOCK`] `mock_resp.status_code = 200``
- L9236 [`MOCK`] `- L49 [`MOCK`] `mock_resp.raise_for_status = MagicMock()``
- L9237 [`MOCK`] `- L50 [`MOCK`] `mock_resp.content = b"9.9.9.9/32\n10.10.10.0/24"``
- L9238 [`MOCK`] `- L52 [`MOCK`] `mock_get.return_value = mock_resp``
- L9239 [`MOCK`] `- L56 [`MOCK`] `if not mock_blocklist_file.exists():``
- L9240 [`MOCK`] `- L59 [`MOCK`] `print("File content:", mock_blocklist_file.read_text())``
- L9241 [`MOCK`] `- L80 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,``
- L9242 [`MOCK`] `- L82 [`MOCK`] `mock_resp = MagicMock()``
- L9243 [`MOCK`] `- L83 [`MOCK`] `mock_resp.status = 200``
- L9244 [`MOCK`] `- L88 [`MOCK`] `mock_resp.json = async_json``
- L9245 [`MOCK`] `- L89 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp``
- L9246 [`MOCK`] `- L99 [`MOCK`] `patch("aiohttp.ClientSession.get") as mock_get,``
- L9247 [`MOCK`] `- L101 [`MOCK`] `mock_resp = MagicMock()``
- L9248 [`MOCK`] `- L102 [`MOCK`] `mock_resp.status = 200``
- L9249 [`MOCK`] `- L107 [`MOCK`] `mock_resp.json = async_json``
- L9250 [`MOCK`] `- L108 [`MOCK`] `mock_get.return_value.__aenter__.return_value = mock_resp``
- L9253 [`ASSUMING`] `- L21 [`ASSUMING`] `# Assuming it checks for basic validity.``
- L9256 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch``
- L9257 [`MOCK`] `- L18 [`MOCK`] `# Mocking _is_address_safe to simulate failure``
- L9258 [`MOCK`] `- L58 [`MOCK`] `# Mock validator to fail the second one with a non-fatal reason``
- L9259 [`MOCK`] `- L61 [`MOCK`] `) as mock_val:``
- L9260 [`MOCK`] `- L62 [`MOCK`] `mock_val.side_effect = [(True, "ok"), (False, "tls_required")]``
- L9263 [`ASSUMING`] `- L54 [`ASSUMING`] `# Assuming we want it to fail, but current logic allows it.``
- L9266 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import patch``
- L9267 [`MOCK`] `- L58 [`MOCK`] `# Mock FileResponse to return content from disk (simulating server behavior)``
- L9268 [`MOCK`] `- L77 [`MOCK`] `def mock_output_dir(tmp_path):``
- L9269 [`MOCK`] `- L78 [`MOCK`] `"""Mock the output directory and create dummy files."""``
- L9270 [`MOCK`] `- L113 [`MOCK`] `def mock_frontend_dir(tmp_path):``
- L9271 [`MOCK`] `- L114 [`MOCK`] `"""Mock the frontend directory."""``
- L9272 [`MOCK`] `- L124 [`MOCK`] `async def test_health_check(mock_output_dir, async_client):``
- L9273 [`MOCK`] `- L125 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9274 [`MOCK`] `- L134 [`MOCK`] `async def test_get_stats(mock_output_dir, async_client):``
- L9275 [`MOCK`] `- L135 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9276 [`MOCK`] `- L144 [`MOCK`] `mock_output_dir, async_client, monkeypatch``
- L9277 [`MOCK`] `- L155 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9278 [`MOCK`] `- L169 [`MOCK`] `mock_output_dir, async_client, monkeypatch``
- L9279 [`MOCK`] `- L171 [`MOCK`] `(mock_output_dir / "proxies.old.json").write_text(``
- L9280 [`MOCK`] `- L175 [`MOCK`] `(mock_output_dir / "proxies.json").write_text(``
- L9281 [`MOCK`] `- L188 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9282 [`MOCK`] `- L203 [`MOCK`] `async def test_get_proxies_all(mock_output_dir, async_client):``
- L9283 [`MOCK`] `- L204 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9284 [`MOCK`] `- L211 [`MOCK`] `async def test_get_proxies_by_country(mock_output_dir, async_client):``
- L9285 [`MOCK`] `- L212 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9286 [`MOCK`] `- L224 [`MOCK`] `async def test_get_proxies_by_protocol(mock_output_dir, async_client):``
- L9287 [`MOCK`] `- L225 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9288 [`MOCK`] `- L237 [`MOCK`] `async def test_download_subscription(mock_output_dir, async_client):``
- L9289 [`MOCK`] `- L238 [`MOCK`] `with patch("configstream.server.OUTPUT_DIR", mock_output_dir):``
- L9290 [`MOCK`] `- L391 [`MOCK`] `async def test_frontend_serving(mock_frontend_dir, async_client):``
- L9291 [`MOCK`] `- L392 [`MOCK`] `with patch("configstream.server.FRONTEND_DIR", mock_frontend_dir):``
- L9292 [`MOCK`] `- L415 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9293 [`MOCK`] `- L420 [`MOCK`] `side_effect=mock_test,``
- L9294 [`MOCK`] `- L438 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9295 [`MOCK`] `- L443 [`MOCK`] `side_effect=mock_test,``
- L9296 [`MOCK`] `- L460 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9297 [`MOCK`] `- L465 [`MOCK`] `side_effect=mock_test,``
- L9298 [`MOCK`] `- L513 [`MOCK`] `async def mock_test(config, timeout=15.0):``
- L9299 [`MOCK`] `- L518 [`MOCK`] `side_effect=mock_test,``
- L9302 [`MOCK`] `- L49 [`MOCK`] `# But since we mocked/created dummy files in previous steps or they exist in repo...``
- L9305 [`MOCK`] `- L41 [`MOCK`] `# Mock Path.cwd to point to a clean temp directory``
- L9308 [`MOCK`] `- L7 [`MOCK`] `from unittest.mock import MagicMock``
- L9309 [`MOCK`] `- L15 [`MOCK`] `def _setup_history_mock(self, proxies, reliability_map=None, uptime_map=None):``
- L9310 [`MOCK`] `- L16 [`MOCK`] `history = MagicMock()``
- L9311 [`MOCK`] `- L40 [`MOCK`] `history = MagicMock()``
- L9312 [`MOCK`] `- L54 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.9}, {proxy.id: 95.0})``
- L9313 [`MOCK`] `- L78 [`MOCK`] `history = self._setup_history_mock(``
- L9314 [`MOCK`] `- L108 [`MOCK`] `history = self._setup_history_mock(``
- L9315 [`MOCK`] `- L145 [`MOCK`] `history = self._setup_history_mock(``
- L9316 [`MOCK`] `- L173 [`MOCK`] `history = self._setup_history_mock(``
- L9317 [`MOCK`] `- L203 [`MOCK`] `history = self._setup_history_mock(``
- L9318 [`MOCK`] `- L234 [`MOCK`] `# Manually create mock to handle missing key logic``
- L9319 [`MOCK`] `- L235 [`MOCK`] `history = MagicMock()``
- L9320 [`MOCK`] `- L269 [`MOCK`] `history = self._setup_history_mock(``
- L9321 [`MOCK`] `- L295 [`MOCK`] `history = self._setup_history_mock(``
- L9322 [`MOCK`] `- L321 [`MOCK`] `history = self._setup_history_mock(``
- L9323 [`MOCK`] `- L351 [`MOCK`] `history = self._setup_history_mock(``
- L9324 [`MOCK`] `- L383 [`MOCK`] `history = self._setup_history_mock(``
- L9325 [`MOCK`] `- L410 [`MOCK`] `history = self._setup_history_mock(``
- L9326 [`MOCK`] `- L442 [`MOCK`] `history = self._setup_history_mock(``
- L9327 [`MOCK`] `- L465 [`MOCK`] `history = self._setup_history_mock(proxies, {proxy.id: 0.6}, {proxy.id: 70.0})``
- L9330 [`MOCK`] `- L2 [`MOCK`] `from unittest.mock import patch, MagicMock``
- L9331 [`MOCK`] `- L37 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9332 [`MOCK`] `- L39 [`MOCK`] `mock_cdll.assert_not_called()``
- L9333 [`MOCK`] `- L72 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9334 [`MOCK`] `- L73 [`MOCK`] `mock_lib = MagicMock()``
- L9335 [`MOCK`] `- L74 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9336 [`MOCK`] `- L75 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9337 [`MOCK`] `- L77 [`MOCK`] `# Force reload lib (reset global in module is hard, so we mock where it's used)``
- L9338 [`MOCK`] `- L81 [`MOCK`] `mock_lib.verify_shadowsocks.assert_called()``
- L9339 [`MOCK`] `- L90 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9340 [`MOCK`] `- L91 [`MOCK`] `mock_lib = MagicMock()``
- L9341 [`MOCK`] `- L92 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0  # Invalid``
- L9342 [`MOCK`] `- L93 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9343 [`MOCK`] `- L105 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9344 [`MOCK`] `- L106 [`MOCK`] `mock_lib = MagicMock()``
- L9345 [`MOCK`] `- L107 [`MOCK`] `mock_lib.verify_shadowsocks.side_effect = Exception("FFI Error")``
- L9346 [`MOCK`] `- L108 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9347 [`MOCK`] `- L120 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9348 [`MOCK`] `- L121 [`MOCK`] `mock_lib = MagicMock()``
- L9349 [`MOCK`] `- L122 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9350 [`MOCK`] `- L123 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9351 [`MOCK`] `- L131 [`MOCK`] `call_args = mock_lib.verify_shadowsocks.call_args``
- L9352 [`MOCK`] `- L150 [`MOCK`] `with patch("configstream.security.ss_ffi.logger") as mock_logger:``
- L9353 [`MOCK`] `- L154 [`MOCK`] `assert mock_logger.warning.called``
- L9354 [`MOCK`] `- L163 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9355 [`MOCK`] `- L164 [`MOCK`] `mock_lib = MagicMock()``
- L9356 [`MOCK`] `- L165 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9357 [`MOCK`] `- L166 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9358 [`MOCK`] `- L187 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9359 [`MOCK`] `- L188 [`MOCK`] `mock_lib = MagicMock()``
- L9360 [`MOCK`] `- L189 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9361 [`MOCK`] `- L190 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9362 [`MOCK`] `- L204 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9363 [`MOCK`] `- L205 [`MOCK`] `mock_lib = MagicMock()``
- L9364 [`MOCK`] `- L206 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0``
- L9365 [`MOCK`] `- L207 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9366 [`MOCK`] `- L243 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9367 [`MOCK`] `- L244 [`MOCK`] `mock_lib = MagicMock()``
- L9368 [`MOCK`] `- L245 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9369 [`MOCK`] `- L248 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 1``
- L9370 [`MOCK`] `- L253 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = 0``
- L9371 [`MOCK`] `- L258 [`MOCK`] `mock_lib.verify_shadowsocks.return_value = -1``
- L9372 [`MOCK`] `- L269 [`MOCK`] `with patch("ctypes.CDLL") as mock_cdll:``
- L9373 [`MOCK`] `- L270 [`MOCK`] `mock_lib = MagicMock()``
- L9374 [`MOCK`] `- L271 [`MOCK`] `mock_cdll.return_value = mock_lib``
- L9375 [`MOCK`] `- L277 [`MOCK`] `mock_cdll.assert_called_once()``
- L9376 [`MOCK`] `- L279 [`MOCK`] `assert hasattr(mock_lib, "verify_shadowsocks")``
- L9379 [`MOCK`] `- L4 [`MOCK`] `from unittest.mock import patch``
- L9382 [`MOCK`] `- L26 [`MOCK`] `# Force fail by making directory read-only or mocking``
- L9383 [`MOCK`] `- L27 [`MOCK`] `# Using mock for stability``
- L9384 [`MOCK`] `- L28 [`MOCK`] `from unittest.mock import patch``
- L9386 [`PLACEHOLDER`] `##### `tests/unit/test_validate_frontend_placeholders.py``
- L9387 [`PLACEHOLDER`] `- L2 [`PLACEHOLDER`] `"""Tests for frontend production placeholder validation."""``
- L9388 [`PLACEHOLDER`] `- L8 [`PLACEHOLDER`] `from scripts.validate_frontend_placeholders import (``
- L9389 [`PLACEHOLDER`] `- L10 [`PLACEHOLDER`] `validate_frontend_placeholders,``
- L9390 [`PLACEHOLDER`] `- L22 [`PLACEHOLDER`] `'const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";\n',``
- L9391 [`PLACEHOLDER`] `- L27 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_detects_public_and_stego_keys(``
- L9392 [`PLACEHOLDER`] `- L32 [`PLACEHOLDER`] `errors = validate_frontend_placeholders(tmp_path, strict=True)``
- L9393 [`PLACEHOLDER`] `- L34 [`PLACEHOLDER`] `assert any("PUBLIC_KEY placeholder" in error for error in errors)``
- L9394 [`PLACEHOLDER`] `- L35 [`PLACEHOLDER`] `assert any("STEGO_KEY placeholder" in error for error in errors)``
- L9395 [`PLACEHOLDER`] `- L38 [`PLACEHOLDER`] `def test_inject_frontend_keys_replaces_placeholders(tmp_path: Path) -> None:``
- L9396 [`PLACEHOLDER`] `- L50 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=True) == []``
- L9397 [`PLACEHOLDER`] `- L59 [`PLACEHOLDER`] `def test_validate_frontend_placeholders_allows_missing_stego_when_not_strict(``
- L9398 [`PLACEHOLDER`] `- L69 [`PLACEHOLDER`] `assert validate_frontend_placeholders(tmp_path, strict=False) == []``
- L9401 [`PLACEHOLDER`] `- L27 [`PLACEHOLDER`] `def test_validate_workflows_requires_pages_frontend_placeholder_guard(``
- L9404 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock, patch``
- L9405 [`MOCK`] `- L103 [`MOCK`] `# Mock _get_clean_endpoint and _get_consistent_exit to ensure success path``
- L9406 [`MOCK`] `- L104 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("1.1.1.1", 2408))``
- L9407 [`MOCK`] `- L137 [`MOCK`] `# Mock helpers``
- L9408 [`MOCK`] `- L138 [`MOCK`] `washer_stats_fixture._get_clean_endpoint = MagicMock(return_value=("2.2.2.2", 2408))``
- L9409 [`MOCK`] `- L164 [`MOCK`] `washer_stats_fixture.get_warp_config = MagicMock(``
- L9412 [`MOCK`] `- L17 [`MOCK`] `async def test_test_dns_mock():``
- L9413 [`MOCK`] `- L20 [`MOCK`] `# Basic existence check since we can't easily mock network calls without respx/aioresponses``
- L9414 [`MOCK`] `- L21 [`MOCK`] `# and aiodns is tricky to mock fully in this context without real networking``
- L9417 [`MOCK`] `- L3 [`MOCK`] `from unittest.mock import MagicMock``
- L9418 [`MOCK`] `- L5 [`MOCK`] `# Mock OpenSSL if not present``
- L9419 [`MOCK`] `- L6 [`MOCK`] `sys.modules["OpenSSL"] = MagicMock()``
- L9420 [`MOCK`] `- L7 [`MOCK`] `sys.modules["OpenSSL.crypto"] = MagicMock()``
- L9421 [`MOCK`] `- L12 [`MOCK`] `def test_cert_generation_mock():``
- L9422 [`MOCK`] `- L13 [`MOCK`] `# Since we mocked OpenSSL, we just check if the function runs without import error``
- L9423 [`MOCK`] `- L14 [`MOCK`] `# and tries to access the mocked object.``
- L9424 [`MOCK`] `- L19 [`MOCK`] `pass  # Expected due to mock return values not being full objects``

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
