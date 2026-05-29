# ConfigStream Project Status

**Last updated:** 2026-05-29  
**Version:** v3.1.0  
**Status:** Repository production-ready. All repository-side P0, P1, and P2 audit items are closed. Live Pages deployment currently fails smoke and requires a fresh deploy from this repository state.

The active current source of truth is [ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md](ConfigStream_Master_Audit_Report%20-%20Main%20SOURCE%20OF%20TRUTH.md). Detailed historical ledgers are archived under [docs/history/source-of-truth](docs/history/source-of-truth/).

## Current Verdict

The repository publish-ready gate is closed. The generated artifact contract is closed when validated against a fresh `output/` tree. The live public Pages gate remains open until GitHub Pages is redeployed from this repository state and live smoke passes.

This status file is deliberately current-state focused. Completed implementation detail is recorded chronologically in `CHANGELOG.md`; historical audit ledgers remain available under `docs/history/source-of-truth/`.

The master source of truth now includes an explicit one-by-one absorption pass over the four original ledgers. Durable policy from the old master report, Part 2, Part 3, and the amendment has been pulled forward into current contracts; stale counts, old closure language, PR-era examples, and long remediation transcripts remain archived as evidence only.

## Closed Audit Items

The following review/audit classes are closed at repository level:

| Area | Status | Current proof surface |
|---|---|---|
| Public source leakage | Closed | `serialize_proxy()` sanitizes public `source`; public outputs no longer expose raw tokenized source URLs. |
| Categorized JSON serializer drift | Closed | Country/protocol list JSON uses the same safe public serializer as root `proxies.json`. |
| Output matrix coverage | Closed | `docs/output_matrix.json` covers categorized list JSON API families. |
| Source token exposure | Closed for tracked content | Tracked source lists are scrubbed; source files are scanned in CI. |
| Gitleaks allowlist gap | Closed for config; one-line CI flip pending | Source-file allowlisting was removed and custom source-token rules exist. The working tree scans clean; the only remaining step is removing `continue-on-error: true` from the CI gitleaks step (must be applied by a maintainer with `workflows` permission). |
| Tracked generated artifacts | Closed | Generated mirrors/ZIPs were removed and ignored. |
| Debt matrix reproducibility | Closed | `scripts/generate_debt_matrix.py --check` is non-mutating and excludes generated mirrors. |
| Frontend dependency advisories | Closed for reported batch | Lockfile resolves patched Vite/PostCSS/Picomatch versions. |
| Lab diagnosis CSP gap | Closed | External diagnosis endpoints are allowed by Lab CSP. |
| Lab Bash export injection | Closed | Generated Bash runner uses safer config transport. |
| Lab Python export extraction/mktemp risk | Closed | Generated Python runner requires preinstalled `sing-box`; unsafe auto-download/extract behavior removed. |
| Standalone Lab runner auto-install risk | Closed | Remote auto-install path disabled. |
| Python direct dependency audit | Closed for reported batch | Direct production pins updated; direct `pip-audit --no-deps` passes. |
| CI security scan scope | Closed | Bandit and secret scans cover broader risk surfaces. |
| CSP `unsafe-eval` | Closed | `unsafe-eval` removed from primary frontend pages. |
| Vercel artifact-root mismatch | Closed | Vercel deploy runs from `output/`. |
| Code-quality audit (f1-f12 + frontend review) | Closed | Non-security code-quality findings remediated: Loon relay format, fail-closed uTLS checksum, dead-code removal, named permanent-failure sentinel, bounded WARP scan timeout, numeric Vwarp version compare + RUF006 task GC, non-mutating cache `contains()`, atomic `adaptive_timeout`/`stego` writes, mojibake repair, optional per-user Telegram authorization, idempotent trace-id factory, real manifest verification in `verifier.js`, and a bounded Chart.js load poll. See `CHANGELOG.md` Unreleased. |

## Gate Status

| Gate | Status | Notes |
|---|---|---|
| Repository production gate | Closed | Code, tests, validators, workflows, source hygiene, dependency audits, and artifact contract are reconciled. |
| Pages artifact gate | Closed for generated artifacts | Fresh local/generated artifacts must pass `scripts/validate_pages_artifact.py`. |
| Live Pages gate | Open | Public deployment is stale/incomplete until redeployed and verified. |
| Source/token hygiene | Closed for tracked content | Tracked source lists are scrubbed; CI secret scanning covers source files. Working-tree gitleaks scan is clean; flipping the CI step to blocking is a pending one-line maintainer change. |
| Generated artifact hygiene | Closed | Generated output mirrors and ZIPs are ignored and not tracked. |
| Debt reproducibility | Closed | `scripts/generate_debt_matrix.py --check` is non-mutating and excludes generated mirrors. |
| Security scan gate | Mostly closed | Expanded Bandit scope passes; source/token scan is wired in CI. Gitleaks is blocking-ready (working tree clean) and only needs the `continue-on-error` line removed by a maintainer with `workflows` permission. |
| Dependency gate | Closed for reported direct advisories | Frontend and direct production advisories from the audit batch were addressed. |

## Current Open Work

### Public Release

1. Redeploy GitHub Pages from current `main`.
2. Run live Pages smoke:

```bash
python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --timeout 120 --report-file output/pages_deployment_smoke.json
```

3. Mark live Pages gate closed only after the live smoke passes.

### Cleanup And Maintainability

These are not current publish blockers, but they are the next valuable cleanup items:

- Remove remaining frontend `unsafe-inline` through static bootstraps/templates.
- Reduce broad `innerHTML` rendering in Lab, Proxies, and Analytics.
- Choose one canonical source-list truth and generate shards/mirrors/backups.
- Stop tracking `sources/backup_dynamic/` as source truth.
- Modularize output generation by output family.
- Split large frontend CSS and Lab JS surfaces.
- Keep root status files current and detailed, while preserving old evidence only in `docs/history/source-of-truth/`.

## Current Contract Summary

The master file is intentionally more detailed than this status checkpoint. It now carries concrete inventory, gate maturity levels, validation command catalogs, definition-of-done rules by work type, a gap register, and granular operating contracts for source ingestion, parser/protocol handling, public serialization, output families, Pages/mirror deployment, frontend/Lab behavior, security/supply-chain gates, documentation ownership, and pruning rules.

### Repository Contract

- Raw static `frontend/` is the Pages source.
- Vite build is a sanity check, not the deploy source.
- Runtime public config is generated into the artifact.
- Output artifacts are validated through the output matrix and Pages artifact validator.
- Generated artifact mirrors are not source truth.
- `CHANGELOG.md` carries completed implementation details.
- Current status prose must not duplicate historical ledgers.

### Security Contract

- Public outputs must not leak source tokens, raw source URLs, proxy secrets, deployment secrets, or internal-only model fields.
- Logs must remain sanitized.
- Active scanning remains disabled by default and in CI.
- Lab/scanner tooling is opt-in and user-run.
- Source-list files are scanned rather than allowlisted away from secret detection.
- Optional mirrors must remain secret-gated.

### Output Contract

- Zero-working degraded runs still generate artifacts.
- Working/candidate/revived/shielded semantics must remain distinct.
- Public country/protocol list JSON is part of the public API surface.
- `docs/output_matrix.json` is the artifact inventory.
- `proxies.json` is a dataset/API artifact, not a native Sing-box or Xray config.
- Native client config families must be validated as their own formats.

### Governance Contract

- Stable capabilities must be listed in `docs/capability_registry.json` with proof.
- Major module ownership and removed-module boundaries must remain listed in `docs/module_ownership.json`.
- Public claims must remain linked in `docs/claim_ledger.json`.
- Historical evidence must stay under `docs/history/source-of-truth/` unless deliberately promoted back into current truth.

### Evidence Contract

- A local generated output tree proves only that local output tree.
- A CI artifact proves only the retained artifact for the retention window.
- A Pages artifact proves only the exact artifact uploaded to Pages.
- A live Pages smoke proves what public users fetch at that moment.
- Screenshots prove UI rendering only for the artifact or deployment they were captured from.
- Optional mirrors prove only their own published artifact unless parity with Pages is validated.

## Granular Current Area Status

| Area | Current state | Remaining action |
|---|---|---|
| Pipeline/fetch/consumer | Repository contract closed; bounded/fail-open behavior and source-safety guardrails are documented. | Keep source-fetch DNS/private-network protections covered when fetcher changes. |
| Parser/protocol support | Matrix-backed protocol inventory is current. | Add new protocols only with parser/export/frontend/docs proof. |
| Public JSON outputs | Safe serializer and categorized list parity are closed. | Keep schema tests for every public list family. |
| Client config outputs | Sing-box/Clash are stable; Xray pipeline output remains planned. | Add native/pinned proof before claiming new native output families. |
| Frontend | Local static deployment contract is closed; smoke/build pass. | Remove `unsafe-inline`, reduce broad `innerHTML`, modularize Lab. |
| Lab | Export hardening and diagnosis CSP issues are closed. | Split Lab code by concern and add deeper click-path tests around export/diagnosis. |
| CI/security | Bandit, gitleaks/source scans, workflow validators, and audits are wired. | Flip the gitleaks step to blocking (remove `continue-on-error`); keep scans server-side and avoid broad allowlists. |
| Artifacts | Generated mirrors are untracked; artifact validator guards Pages shape. | Redeploy live Pages and keep durable evidence. |
| Docs/source of truth | Current root truth is this file plus Master. | Generate/archive duplicated docs instead of growing root status files. |

## Validation Snapshot

Latest local verification recorded for this status:

- `ruff check src/`: passed (after the code-quality audit remediation).
- `python -m mypy .`: passed for the audited modules.
- `scripts/generate_debt_matrix.py --check`: passed.
- `scripts/validate_output_matrix.py`: passed.
- `scripts/validate_workflows.py`: passed.
- `scripts/validate_changelog.py`: passed.
- `scripts/validate_status.py`: passed.
- `python -m pytest -q tests/unit/test_frontend_security_contract.py tests/unit/test_repo_hygiene.py tests/unit/test_release_scripts.py tests/unit/test_bot_cli.py tests/unit/test_cache_warming.py`: passed.
- `bandit -r src/configstream scripts tools frontend/assets/js -q`: passed.
- `pip_audit -r requirements-prod.txt --no-deps`: passed.
- `npm run build:sanity`: passed.
- Same-origin frontend smoke: passed.
- `python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --timeout 120 --report-file output/pages_deployment_smoke.json`: fails against stale live Pages.

Latest full-suite snapshot:

- `python -m pytest -q`: 1054 passed, 4 skipped.

## Current Source Files

Use these files for current status and proof:

- `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`
- `STATUS.md`
- `docs/output_matrix.json`
- `docs/protocol_matrix.json`
- `docs/claim_ledger.json`
- `docs/capability_registry.json`
- `docs/core_compatibility_report.json`
- `docs/module_ownership.json`
- `docs/DEBT_MATRIX.md`
- `CHANGELOG.md`

Archived evidence lives in `docs/history/source-of-truth/` and must not be treated as current status when it conflicts with the files above.
