# ConfigStream Project Status

**Last updated:** 2026-05-06
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
- Source fetching now rejects source URL credentials, localhost/internal hostnames, and private/non-global IP literals by default; redirects are followed manually only after validating each target and respecting `FETCH_MAX_REDIRECTS`.
- Pages deploy now injects `CS_PUBLIC_KEY`/`STEGO_KEY` into copied frontend assets and fails before upload if frontend public-key or stego placeholders remain; workflow validation enforces this guard.
- Public artifact validation now rejects unknown top-level control schema keys and verifies that `api/proxies` and `api/stats` match `proxies.json` and `metadata.json`; README now documents `proxies.json` as a JSON array, not a metadata envelope.
- Laboratory chain strategies now have a canonical 9-strategy manifest, UI/JS/docs parity, Vwarp MASQUE and AtomicNoize build branches, and a fail-loud unsupported-strategy path.
- Laboratory QR export no longer sends proxy or chain payload material to an external QR service; the Lab now renders an offline copyable payload panel and keeps a scannable local QR renderer as an optional follow-up.
- Laboratory manual clean-IP rows now render with DOM text nodes instead of `tr.innerHTML`, and manual clean-IP input is validated before storage.
- `/api/stats` and `/api/diff/proxies` now read and parse JSON artifacts through `asyncio.to_thread()` so route handlers do not block the event loop on artifact disk reads.
- The unused `test_budget` semaphore wiring was removed from the pipeline and consumer; `ConcurrencyManager` remains the canonical Python fallback test limiter.
- Producer backpressure accounting no longer calls source-quality failure reporting when runner queue pressure prevents any chunks from being queued.
- Logging hardening now masks proxy endpoints, source URLs, source tokens, DNS failure host/error material, Vwarp subprocess/tunnel output, security-rule address logs, honeypot reputation logs, test-cache endpoint logs, parser drop/error logs, and converter logs; high-risk static logging policy tests and `SECURITY.md` logging policy documentation are in place.
- Frontend runtime assets are local-first with parity tracking: critical JS/CSS/fonts/globe textures/flags and Lab helper downloads are same-origin, CSP no longer needs broad remote runtime hosts, and `frontend/assets/vendor-manifest.json` records mirrored sources.
- Test execution is split into explicit profiles: `unit`, `integration`, `frontend-browser`, and `production-smoke`. The CI `frontend-browser` job installs Python Playwright Chromium and runs with `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` so missing browser coverage fails instead of silently skipping.

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

Latest local validation performed on 2026-05-06:

- `python scripts/validate_workflows.py`: passed for 6 workflow files
- `python scripts/validate_versions.py`: passed
- `python -m pytest tests/unit/test_validate_versions.py -q`: 3 passed
- `pytest -q tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py`: 18 passed
- `pytest -q tests/unit/test_documentation_hygiene.py tests/unit/test_validate_pages_artifact.py tests/unit/test_output.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py`: 22 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py`: 41 passed
- `pytest -q tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py`: 34 passed
- `pytest -q tests/unit/test_validate_frontend_placeholders.py tests/unit/test_validate_workflows.py`: 6 passed
- `pytest -q tests/unit/test_validate_pages_artifact.py tests/unit/test_documentation_hygiene.py`: 17 passed
- `pytest -q tests/unit/test_lab_strategy_parity.py`: 5 passed
- `pytest -q tests/unit/test_concurrency_contract.py tests/unit/test_pipeline_stages.py tests/unit/test_consumer.py tests/unit/test_pipeline_coverage.py tests/unit/test_pipeline_deep.py`: 16 passed
- `pytest -q tests/unit/test_producer_quality_accounting.py tests/unit/test_pipeline_stages.py`: 12 passed
- `pytest -q tests/unit/test_logging_sanitization_policy.py tests/unit/test_output.py`: 15 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py`: 66 passed
- `pytest -q tests/unit/test_server.py tests/unit/test_server_new.py tests/unit/test_fetcher.py tests/unit/test_fetcher_config.py tests/unit/test_fetcher_resilience.py tests/unit/test_fetcher_retries.py tests/unit/test_fetcher_advanced.py tests/unit/fetcher/test_fetcher_core.py tests/unit/test_output.py tests/unit/test_validate_pages_artifact.py tests/unit/test_analytics_output.py tests/unit/test_merge_batches.py tests/unit/test_documentation_hygiene.py tests/unit/test_validate_workflows.py tests/unit/test_validate_versions.py tests/unit/test_validate_frontend_placeholders.py tests/unit/test_lab_strategy_parity.py tests/unit/test_concurrency_contract.py tests/unit/test_producer_quality_accounting.py tests/unit/test_logging_sanitization_policy.py`: 127 passed
- `npm run build`: passed
- `npm run test:frontend:no-network`: passed, including same-origin no-JS smoke
- `npm run test:frontend:degraded`: passed
- `python -m pytest -q`: 900 passed, 5 skipped

Browser skip visibility:

- The 5 local skips are the Python Playwright frontend e2e tests when the Python browser bundle is not installed.
- `CONFIGSTREAM_REQUIRE_PLAYWRIGHT=1` converts that condition into a hard failure for the `frontend-browser` profile and CI job.
- The Node Playwright same-origin and no-JS smokes run locally through npm and passed in this checkpoint.

The full production gate remains open until the complete audit roadmap is implemented and the full local/CI/deploy verification matrix passes.
