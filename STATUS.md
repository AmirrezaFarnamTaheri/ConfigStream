# ConfigStream Project Status

**Last updated:** 2026-05-09
**Version:** v3.0.2
**Status:** Remediation in progress. Not production-ready and not ready to publish as a final public release.

The active source of truth is [ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md](ConfigStream_Master_Audit_Report%20-%20Main%20SOURCE%20OF%20TRUTH.md). That report supersedes older status, finalization, and roadmap claims when they conflict.

## Current Verdict

ConfigStream has a substantial architecture and a large test base, but the repository is currently being brought back into a single, verifiable production contract. Until the P0/P1 audit items are closed, public-facing claims must be treated as remediation targets rather than completed guarantees.

Current blockers:

- Workflow syntax was repaired locally, but workflow behavior still needs full CI validation.
- Public artifact contracts need canonical schemas and deploy smoke tests.
- Runtime metrics, frontend labels, schemas, and docs still need parity work.
- Security defaults for degraded public output still need hardening; admin APIs, production CORS, WebSocket lifecycle, the lab live-test endpoint, and fetch redirect handling have focused guardrails in place.
- Frontend deployment must be made canonical: either tested Vite output or raw static output, not both as competing truths.
- Legacy, duplicate, and stale documents still need cleanup after each implementation step.

## Recently Restored

- GitHub workflow YAML now parses locally through `scripts/validate_workflows.py`.
- Workflow validation is wired into CI and pre-commit.
- Source reshard commits are guarded by `paths-ignore` checks to reduce self-trigger loops.
- Pages artifact validation is centralized in `scripts/validate_pages_artifact.py`.
- Output generation now writes `health.json` and `artifact_manifest.json` so public deployments have a canonical status file and file inventory.
- Pages validation now checks manifest file coverage, file sizes, SHA-256 hashes, manifest totals, metadata required keys, proxy array shape, and health required fields.
- Pages deployment refreshes the public contract after all deploy-time mutations so the manifest describes the exact uploaded artifact.
- `scripts/validate_versions.py` now uses explicit UTF-8 reads and ASCII-safe output for Windows compatibility, with a cp1252-stdout regression test.
- `pyproject.toml` now classifies the project as Beta during remediation instead of Production/Stable.
- README TLS fragmentation language now matches implementation: fragmentation is disabled in current sing-box outputs.
- Shielded chain candidates no longer inflate `total_working`; metadata now exposes `shielded_candidate_count` and `shielded_verified_count`.
- Production admin update notifications now fail closed unless `ADMIN_API_KEY` is configured and supplied; the endpoint is rate-limited, and server startup fails in production if the key is absent.
- Production CORS now uses explicit origins only: wildcard origin regex is empty by default, credentialed CORS is disabled by default, and production startup rejects `ALLOWED_ORIGIN_REGEX`.
- WebSocket update connections now have bounded connection count, idle timeout, send timeout, stale cleanup, and connection/drop stats.
- Lab live chain testing is disabled by default in production; when explicitly enabled, it requires `ADMIN_API_KEY`, enforces a `30/minute` rate limit, rejects oversized configs, validates submitted outbound shape/type/hosts, blocks private/internal destinations, and keeps the frontend manual fallback path available.
- Laboratory Step 4 now exposes visible live-test/manual-test mode state: backend-capable hosting keeps the live endpoint path, while GitHub Pages/file-style static hosting is labeled for manual sing-box testing.
- Source fetching now rejects source URL credentials, localhost/internal hostnames, and private/non-global IP literals by default; redirects are followed manually only after validating each target and respecting `FETCH_MAX_REDIRECTS`.
- Pages deploy now injects `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets and fails before upload if frontend public-key or stego placeholders remain; workflow validation enforces this guard.
- Public artifact validation now rejects unknown top-level control schema keys and verifies that `api/proxies` and `api/stats` match `proxies.json` and `metadata.json`; README now documents `proxies.json` as a JSON array, not a metadata envelope.
- Laboratory chain strategies now have a canonical 9-strategy manifest, UI/JS/docs parity, Vwarp MASQUE and AtomicNoize build branches, and a fail-loud unsupported-strategy path.
- The same-origin frontend browser smoke now checks the rendered Laboratory strategy dropdown against the canonical 9-strategy manifest.
- Laboratory QR export no longer sends proxy or chain payload material to an external QR service; the Lab now renders an offline copyable payload panel and keeps a scannable local QR renderer as an optional follow-up.
- Laboratory manual clean-IP rows now render with DOM text nodes instead of `tr.innerHTML`, and manual clean-IP input is validated before storage.
- Laboratory result messages now escape dynamic user/API values before inserting trusted helper markup, covering local proxy input, parsed proxy remarks, custom JSON parse errors, unsupported strategy names, live-test latency/exit IP/error text, and export format labels.
- The same-origin frontend browser smoke now exercises Lab XSS payloads for local proxy input, parsed proxy remarks, custom JSON errors, live-test API errors/successes, and offline QR export while blocking external network requests.
- `/api/stats` and `/api/diff/proxies` now read and parse JSON artifacts through `asyncio.to_thread()` so route handlers do not block the event loop on artifact disk reads.
- The unused `test_budget` semaphore wiring was removed from the pipeline and consumer; `ConcurrencyManager` remains the canonical Python fallback test limiter.
- Producer backpressure accounting no longer calls source-quality failure reporting when runner queue pressure prevents any chunks from being queued.
- Logging hardening now masks proxy endpoints, source URLs, source tokens, DNS failure host/error material, Vwarp subprocess/tunnel output, security-rule address logs, honeypot reputation logs, test-cache endpoint logs, parser drop/error logs, and converter logs; high-risk static logging policy tests and `SECURITY.md` logging policy documentation are in place.
- Frontend runtime assets are local-first with parity tracking: critical JS/CSS/fonts/globe textures/flags and Lab helper downloads are same-origin, CSP no longer needs broad remote runtime hosts, and `frontend/assets/vendor-manifest.json` records mirrored sources.
- Optional IPFS/IPNS frontend failover is now covered by local tests: the frontend probes a same-origin static asset, skips placeholder IPNS keys, preserves the current leaf page/query/hash when building gateway URLs, normalizes gateway bases, and prevents repeated redirect attempts within the same session.
- Test execution is split into explicit profiles: `unit`, `integration`, `frontend-browser`, and `production-smoke`. The CI `frontend-browser` job installs Python Playwright Chromium and runs with `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` so missing browser coverage fails instead of silently skipping.
- Shadowsocks-Rust FFI validation is explicitly optional: it runs only with a local platform binary and matching `SS_LIB_SHA256`; otherwise Python validation remains authoritative, and configured hash mismatches fail closed.
- Frontend WASM verification is labeled as browser-limited reachability only. Unsupported transports keep Go sidecar/Python results authoritative, and invalid browser-check URLs fail explicitly before `WebSocket` construction.
- Encyclopedia documentation now has one canonical source: `docs/wiki/encyclopedia`. The root `docs/encyclopedia` tree is a synced mirror guarded by `scripts/validate_docs_sync.py`.
- Debt matrix artifacts are portable: generated paths are repo-relative, generated debt files are excluded from self-scans, and marker summaries separate production/frontend/tooling/docs debt from test-only mocks.
- Optional external publishing is separated from the zero-budget core: GitHub Pages is the core publication target, while IPFS/Pinata, Hugging Face, Google Drive, and Telegram are optional secret-gated mirrors guarded by `scripts/validate_optional_mirrors.py`.
- The first canonical claim ledger now lives at `docs/claim_ledger.json`, with `scripts/validate_claim_ledger.py` guarding required proof fields and preventing complete claims without tests/docs/changelog evidence.
- Protocol claims now have a canonical inventory in `docs/protocol_matrix.json`; `scripts/validate_protocol_matrix.py` checks schema enum coverage, parser-export references, README protocol claims, and frontend display capability. `tests/unit/test_protocol_output_golden.py` now checks every public canonical protocol fixture against the matrix's Sing-box/Clash export flags, generated subscription outputs, the real frontend `processProxyData()` normalizer after parser ingestion, and representative malformed inputs that must fail closed for every public canonical parser. `scripts/frontend_same_origin_smoke.cjs` also serves browser fixture `proxies.json` data for every public canonical protocol and verifies the rendered Proxies page table badges plus protocol filter options in Chromium. The protocol-matrix inventory claim is complete; deeper protocol-specific fuzzing remains tracked as separate parser hardening.
- Parser hardening now drops additional missing-credential edge cases for TUIC, Snell, Brook, and SSH while preserving anonymous Hysteria/Hysteria2 and unauthenticated generic HTTP/SOCKS behavior where the existing parser contract allows it.
- VLESS/VMess credential-boundary proof now locks the intended split between compatibility parsing and strict validation: VLESS query-parameter UUID recovery is covered, VMess missing/empty IDs are covered as malformed parser inputs, public golden UUID fixtures use schema-compatible UUIDv4 values, and the security validator proves missing VMess/VLESS UUIDs remain fatal even when insecure proxy retention is enabled.
- Shadowsocks credential recovery now preserves intended compatibility by parsing host-side query parameters before the empty-password fallback decision, so links such as `ss://method:@host:port/?password=...` recover the password instead of being dropped prematurely.
- Clash JSON import parsing now fails closed for missing VMess/VLESS UUIDs, missing Trojan/Shadowsocks credentials, invalid Shadowsocks methods, invalid ports, empty WireGuard private keys, and unknown Clash `type` values while preserving valid imported entries.
- Public output claims now have a canonical inventory in `docs/output_matrix.json`; `scripts/validate_output_matrix.py` checks that every Pages-required artifact is listed, nonempty flags match the deploy validator, core control artifacts keep schema validation, degraded outputs remain explicitly valid, side-product required ZIP members mirror the deploy validator, and optional OpenVPN/WireGuard member patterns match the generator contract. Pages validation checks side-product ZIP integrity, safe member paths, the required `proxies.txt` member, deploy-secret markers inside ZIP members without blocking normal proxy credentials, and Sing-box/Clash reference semantics for selectors, detours, route/DNS outbounds, groups, and rule policies. When `--native-client-check` is requested, Pages validation also runs local `sing-box` and `mihomo`/Clash config checks if those binaries are available, while missing binaries remain a clean skip. `scripts/generate_output_docs.py` renders the README/API output tables from the matrix and production-smoke checks they are current. `tests/unit/test_output.py` now builds a deterministic public artifact directory from the real output generator and validates it with the Pages contract. `tests/unit/test_protocol_output_golden.py` adds per-protocol generator/export fixtures and parser-to-frontend normalizer fixtures for every public canonical protocol, and the Node frontend smoke verifies browser-rendered protocol badges/filter options. The public output artifact contract claim is complete for current Pages-required outputs.

## Required Closure Rule

After every change, verify and update all affected surfaces:

- backend implementation
- frontend implementation
- schemas and generated artifacts
- tests and CI workflows
- README, wiki docs, SECURITY, STATUS, and CHANGELOG
- cleanup of deprecated files, old aliases, unused fallbacks, and stale references

No task is closed while any surface still documents or serves the old contract.

## Validation Snapshot

Latest local validation performed on 2026-05-09:

- `python scripts/validate_workflows.py`: passed for 6 workflow files
- `python scripts/validate_versions.py`: passed
- `python -m pytest tests/unit/test_validate_versions.py -q`: 3 passed
- `python -m pytest tests/unit/test_ss_ffi.py -q`: 18 passed
- `python -m pytest tests/unit/test_wasm_browser_semantics.py tests/unit/test_documentation_hygiene.py -q`: 9 passed
- `python scripts/validate_status.py`: passed
- `python -m pytest tests/unit/test_validate_status.py tests/unit/test_documentation_hygiene.py -q`: 9 passed
- `python scripts/validate_docs_sync.py`: passed
- `python -m pytest tests/unit/test_validate_docs_sync.py -q`: 3 passed
- `python -m pytest tests/unit/test_lab_strategy_parity.py tests/unit/test_frontend_failover.py -q`: 9 passed
- `python scripts/validate_debt_matrix.py`: passed
- `python -m pytest tests/unit/test_debt_matrix.py -q`: 5 passed
- `python scripts/validate_assets.py`: passed
- `python -m pytest tests/unit/test_validate_assets.py -q`: 6 passed
- `python scripts/validate_optional_mirrors.py`: passed
- `python -m pytest tests/unit/test_validate_optional_mirrors.py -q`: 3 passed
- `python scripts/validate_claim_ledger.py`: passed
- `python -m pytest tests/unit/test_validate_claim_ledger.py -q`: 4 passed
- `python scripts/validate_protocol_matrix.py`: passed
- `python -m pytest tests/unit/test_validate_protocol_matrix.py -q`: 3 passed
- `python -m pytest tests/unit/test_protocol_output_golden.py tests/unit/test_validate_protocol_matrix.py -q`: 8 passed
- `python scripts/validate_output_matrix.py`: passed
- `python scripts/generate_output_docs.py --check`: passed
- `python -m pytest tests/unit/test_validate_output_matrix.py -q`: 8 passed
- `python -m pytest tests/unit/test_validate_pages_artifact.py tests/unit/test_validate_output_matrix.py -q`: 32 passed
- `python -m pytest tests/unit/test_output.py::test_generated_public_artifact_fixture_matches_pages_contract -q`: 1 passed
- `pytest -q tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py`: 18 passed
- `pytest -q tests/unit/test_documentation_hygiene.py tests/unit/test_validate_pages_artifact.py tests/unit/test_output.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py`: 22 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py`: 41 passed
- `pytest -q tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py`: 34 passed
- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed
- `pytest -q tests/unit/test_validate_pages_artifact.py tests/unit/test_documentation_hygiene.py`: 17 passed
- `pytest -q tests/unit/test_lab_strategy_parity.py`: 7 passed
- `pytest -q tests/unit/test_concurrency_contract.py tests/unit/test_pipeline_stages.py tests/unit/test_consumer.py tests/unit/test_pipeline_coverage.py tests/unit/test_pipeline_deep.py`: 16 passed
- `pytest -q tests/unit/test_producer_quality_accounting.py tests/unit/test_pipeline_stages.py`: 12 passed
- `pytest -q tests/unit/test_logging_sanitization_policy.py tests/unit/test_output.py`: 15 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py`: 66 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed
- `python -m pytest tests/unit/test_protocol_output_golden.py tests/unit/test_security_validator.py tests/unit/test_security_validator_full.py tests/unit/test_proxy_schema.py -q`: 15 passed, 1 skipped
- `python -m pytest tests/unit/parsers/test_parser_fixes.py tests/unit/test_protocol_output_golden.py tests/unit/test_parsers_robustness.py -q`: 58 passed
- `python -m pytest tests/unit/test_parsers_json_yaml.py tests/unit/test_protocol_output_golden.py tests/unit/test_parsers_robustness.py -q`: 49 passed
- `python -m pytest tests/unit/test_frontend_failover.py -q`: 3 passed
- `npm run build`: passed
- `npm run test:frontend:no-network`: passed, including protocol render, Lab XSS, and same-origin no-JS smoke
- `npm run test:frontend:degraded`: passed
- `python scripts/run_test_profile.py production-smoke`: passed, including 82 focused pytest tests
- `python -m pytest -q`: 974 passed, 5 skipped

Browser skip visibility:

- The 5 local skips are the Python Playwright frontend e2e tests when the Python browser bundle is not installed.
- `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` converts that condition into a hard failure for the `frontend-browser` profile and CI job.
- The Node Playwright same-origin and no-JS smokes run locally through npm and passed in this checkpoint.

The full production gate remains open until the complete audit roadmap is implemented and the full local/CI/deploy verification matrix passes.
