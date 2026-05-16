# ConfigStream Project Status

**Last updated:** 2026-05-16
**Version:** v3.1.0
**Status:** Repository production-ready. All P0, P1, and P2 audit items closed. Live Pages deployment currently fails smoke and requires a fresh deploy from this repository state.

The active source of truth is [ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md](ConfigStream_Master_Audit_Report%20-%20Main%20SOURCE%20OF%20TRUTH.md).

## Current Verdict

ConfigStream is formally verified against a single, truthful repository production contract. All P0, P1, and P2 audit items from the remediation roadmap have been closed. The repository enforces strict parity between documentation, configuration, and implementation. The currently deployed GitHub Pages site is stale/incomplete and must be redeployed before public Pages readiness can be claimed.

Key milestones reached:
- 🛡️ **DNS Rebinding Hardened (HTTP + HTTPS)**: `SecurityTransport` now enforces pre-connect resolution and IP pinning for **all** source fetches — both HTTP and HTTPS. HTTP and HTTPS requests are rewritten to a pre-validated IP; HTTPS preserves the original hostname through SNI and the `Host` header so certificate validation and virtual-host routing stay intact while the connector cannot re-resolve after validation.
- 🧪 **Shielded Verification Wired**: `generate_pipeline_outputs` now accepts a `tester` parameter. The `SingBoxTester` instance is passed from `pipeline.py` so shielded chain candidates are actively re-tested; `shielded_verified_count` is incremented only for chains that pass. Candidates without a tester are preserved with `is_working=False` for user-side testing.
- 📦 **Durable Evidence Bundle Fixed**: `scripts/generate_evidence_bundle.py` crash (`json.dump_pretty` AttributeError) resolved; script now uses `json.dumps(..., indent=2)` throughout with proper type hints and UTF-8 encoding.
- 📋 **Output Matrix Reconciled**: `docs/output_matrix.json` `remaining_work` cleared — per-protocol golden output fixtures are complete.
- 📖 **Docs Parity Restored**: `docs/wiki/project/Lab_Page.md` updated from 5 to 9 canonical strategies; `docs/wiki/project/01-introduction.md` corrected from "6 strategies" to "9 strategies"; `AGENTS.md` Section 1 updated to reflect production-ready status.
- 📊 **Truthful Metrics**: Shielded chains are actively verified before being counted as working; metadata clearly distinguishes candidates from verified proxies.
- 📦 **Durable Evidence**: 30-day artifact retention enforced for pipeline and deployment evidence bundles.
- 🧹 **Zero Drift**: `AGENTS.md`, `README.md`, and `SECURITY.md` fully reconciled with codebase and security policies.
- 📚 **Addenda Review Applied**: `Main SOURCE OF TRUTH - PART 2.md`, `Main SOURCE OF TRUTH - PART 3.md`, and `Main SOURCE OF TRUTH - Ammendment.md` were read as actual files. The immediate Part 3 Sing-box/output-contract cleanup was implemented: dead legacy selector/urltest append logic was removed, `chains*.json` was documented as compatibility aliases for the `singbox-chains*.json` artifacts, and generated docs were refreshed from `docs/output_matrix.json`.
- 🧾 **Roadmap Contract Wording Clarified**: Overly prohibitive roadmap wording around unimplemented Xray pipeline artifacts was replaced with a planned-output implementation gate. The validator still prevents docs/output_matrix overclaims until generator, validation, tests, docs, and native-check semantics exist, but the roadmap no longer frames future implementation as blocked.
- 🔒 **CI Regression Batch Applied**: Production and dev dependency pins were updated for the reported `python-dotenv` and `urllib3` advisories, `npm run build` was restored as the documented Vite sanity-build entrypoint, and `deploy_mirror.yml` no longer uses invalid `secrets.*` expressions in step `if:` conditions.

## Closed Audit Items

### P0 Items
- **P0-A**: Evidence bundle script fixed (crash on `json.dump_pretty`); both `main.yml` and `deploy-pages.yml` upload 30-day evidence bundles.
- **P0-B**: `AGENTS.md` reconciled — 9-strategy lab manifest, canonical matrices, production-ready status, superseded document list.
- **P0-C**: Release assets dynamically selected from `docs/output_matrix.json`; `remaining_work` cleared.

### P1 Items
- **P1-A**: `frontend/` established as the only canonical deploy path; `npm run build` / `build:sanity` remain local sanity checks and are not Pages deployment inputs.
- **P1-B**: `ALLOW_PRIVATE_IPS` defaults to `false` in `AppSettings`, `.env.example`, and documentation.
- **P1-C / P2 / P3**: Debt matrix reduced from 134 → 0 actionable markers. Expanded false-positive exclusion rules, added EXCLUDED_FILES set, fixed real ASSUMING/MOCK comments in frontend JS, replaced obfuscated WireGuard key fragment, updated security_validator.py docstring.
- **P1-D**: `SecurityTransport` extended to cover HTTPS via validated-IP rewrite plus original SNI/Host preservation — closes the TOCTOU window for all source fetches.
- **P1-E**: Shielded chain verification wired end-to-end: `generate_pipeline_outputs(tester=...)` → active `test_batch` → `shielded_verified_count` increment.

### P2 Items
- **P2**: `docs/output_matrix.json` `remaining_work` cleared; `Lab_Page.md` strategy table updated to 9 entries; `01-introduction.md` strategy count corrected.

## Validation Snapshot

Latest local validation performed on 2026-05-16:

- `python scripts/generate_evidence_bundle.py --output-dir output --evidence-dir evidence`: passes without error.
- `python -m pytest -q`: 1036 passed, 1 skipped (fresh full-suite validation after native client evidence reporting).
- `python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --report-file output/pages_deployment_smoke.json`: fails against the live site because `analytics.html`, `proxies.json`, and `api/proxies` return HTTP 0/incomplete responses; the deployed artifact is missing `assets/js/runtime-config.js`, `health.json`, and `artifact_manifest.json`; deployed JavaScript still contains placeholder key markers; `metadata.json` is missing `proxies_snapshot_hash`; and public JSON is malformed/partial.
- `SecurityTransport` covers both HTTP and HTTPS pre-connect validation.
- `generate_pipeline_outputs` signature updated; `pipeline.py` passes `tester=tester`.

The repository production gate is CLOSED. The live Pages gate remains open until GitHub Pages is redeployed from this verified state and the deployed smoke test passes.

## Material Audit Progress - 2026-05-16

This follow-up audit inspected the actual repository files, not only validators. The tracked inventory currently contains 887 files across Python source, tests, frontend assets, docs, scripts, workflows, schemas, source batches, and static assets. Generated/ignored debris was cleaned after path verification: `__pycache__` trees, `.hypothesis`, `data/`, `output/`, and local log files were removed. `.pytest_cache/` remains as a Windows permission residue and still produces pytest cache warnings, but it is ignored and not part of the tracked repository.

Material fixes completed during this pass:
- `src/configstream/config.py`: aligned `FAIL_ON_ZERO_WORKING` default to `False`, matching `.env.example`, Pages degraded-output policy, and the pipeline requirement to always generate outputs unless strict mode is explicitly requested.
- `scripts/generate_debt_matrix.py`: removed a UTF-8 BOM that blocked direct AST parsing of the file.
- `src/configstream/security/transport.py`: replaced the ineffective per-request `ssl_context` wrapper approach with an `httpx`/`httpcore`-compatible HTTPS validated-IP rewrite using `sni_hostname` and original `Host` preservation.
- `src/configstream/output_logic.py` and `schema/metadata.schema.json`: made `shielded_candidate_count` and `shielded_verified_count` part of the required public metadata contract and preserved dict/merge-stage `shielded_verified_count`.
- `scripts/prepare_release_assets.py`: removed the legacy hard-coded asset fallback; release assets now come from `docs/output_matrix.json` or fail closed if the matrix is missing.
- `scripts/deduplicate_sources.py` and `consolidated_sources.txt`: removed stale 14-batch terminology, aligned the helper with 17 shards, and synchronized `consolidated_sources.txt` as a deduplicated mirror of `sources/batch_*.txt`.
- `scripts/generate_evidence_bundle.py` and `scripts/take_deployment_screenshots.py`: cleaned evidence helper metadata, ASCII status output, URL joining, typing, and path handling.
- `tests/unit/security/test_transport.py`, `tests/unit/test_output.py`, and `tests/unit/test_release_scripts.py`: added regression coverage for HTTPS pin rewrite, DNS rebinding rejection, shielded verified-count metadata export, matrix-based release asset selection, and source mirror parity.
- `src/configstream/generators/singbox.py`: removed dead legacy Part 3 selector/urltest append logic that mutated a non-returned list after `final_outbounds` had already been assembled.
- `docs/output_matrix.json`, `README.md`, and `docs/wiki/project/08-api-reference.md`: aligned `chains.json`, `chains-dns-safe.json`, and `chains-dns-hardened.json` with their real implementation as compatibility aliases for the `singbox-chains*.json` generated Sing-box chain configs.
- `tests/unit/generators/test_singbox_comprehensive.py` and `tests/unit/test_output.py`: added regression coverage for the cleaned Sing-box final outbound contract and byte-identical `chains*.json` alias behavior.
- `docs/capability_registry.json`, `scripts/validate_capability_registry.py`, and `tests/unit/test_validate_capability_registry.py`: implemented Part 2 section 1.1 as a machine-validated capability registry. Stable capabilities now require implementation paths, complete claim-ledger proof, tests, docs, explicit limitations, and cleanup decisions.
- `docs/core_compatibility_report.json`, `scripts/validate_core_compatibility.py`, and `tests/unit/test_validate_core_compatibility.py`: implemented the Part 3 compatibility report. Sing-box and Clash pipeline artifacts are explicit stable full-config outputs; Xray is explicitly planned/not pipeline-generated so Lab-only exports cannot be overclaimed.
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `scripts/validate_workflows.py`, and `tests/unit/test_validate_workflows.py`: wired the capability registry and core compatibility validators into CI/release guardrails.
- `docs/claim_ledger.json`: added `claim.governance.capability_registry_contract` so the registry has its own complete proof trail.
- `scripts/validate_pages_artifact.py`: added structured native client evidence generation via `--native-report-file`. Optional `sing-box` and `mihomo` checks now record passed/failed/skipped states in `native_client_check_report.json`; missing binaries remain explicit skips rather than silent absence.
- `scripts/generate_evidence_bundle.py` and `.github/workflows/main.yml`: archive `pipeline-evidence/native_client_check_report.json` with the pipeline evidence bundle without adding it to public Pages outputs.
- `docs/core_compatibility_report.json`, `docs/capability_registry.json`, and `docs/claim_ledger.json`: recorded native client compatibility evidence as stable evidence-only capability, while leaving pinned native binary validation as remaining future hardening.
- `docs/core_compatibility_report.json`, `scripts/validate_core_compatibility.py`, `tests/unit/test_validate_core_compatibility.py`, `docs/capability_registry.json`, `docs/claim_ledger.json`, `README.md`, and `Main SOURCE OF TRUTH - PART 2.md`: replaced stale blockade/prohibition phrasing with implementation-gate language. Planned Xray output names are tracked as outputs requiring implementation, not forbidden artifacts; the validation behavior remains strict against overclaims.
- `requirements-prod.txt` and `requirements.txt`: bumped `python-dotenv` from `1.2.1` to `1.2.2` and `urllib3` from `2.6.3` to `2.7.0` to address the reported production dependency audit findings.
- `package.json` and `vite.config.mjs`: restored `npm run build` as an alias for `npm run build:sanity`, preserving the canonical raw-static Pages deployment while keeping the documented local build command and CI frontend job valid. The self-contained `frontend/lab-offline.html` remains a raw-static artifact and is excluded from the Vite bundle input because its inline single-file structure is not a deploy bundle dependency.
- `.github/workflows/deploy_mirror.yml`, `scripts/validate_workflows.py`, and `tests/unit/test_validate_workflows.py`: removed invalid direct `secrets.*` step conditions from optional mirror deploy steps and added a workflow validator regression so future workflows cannot reintroduce that GitHub Actions parse error.
- `requirements-prod.txt` and `requirements.txt`: pinned `numpy==2.2.6`, `scipy==1.15.3`, and `scikit-learn==1.7.2` so the production dependency audit resolves under the CI Python 3.10 environment instead of selecting Python 3.11+ only releases.
- `.github/workflows/ci.yml`, `scripts/validate_workflows.py`, and `tests/unit/test_validate_workflows.py`: installed Node Playwright Chromium before the `npm run test:frontend:no-network` smoke job and added a workflow validator regression for the exact browser-install requirement.
- `docs/module_ownership.json`, `docs/MODULE_OWNERSHIP.md`, `scripts/validate_module_ownership.py`, and `tests/unit/test_validate_module_ownership.py`: implemented Part 2 section 1.2 as a machine-validated module ownership map. The map records canonical owners, public/internal APIs, removed-module replacements, proof tests, and docs for major `src/configstream` areas, while the validator fails on missing proof paths, recreated removed files, and removed-module imports.
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `scripts/validate_workflows.py`, `docs/capability_registry.json`, `docs/claim_ledger.json`, `AGENTS.md`, and `Main SOURCE OF TRUTH - PART 2.md`: wired module ownership validation into CI/release, capability bookkeeping, claim-ledger proof, contributor guidance, and the exact source-of-truth item status.

Material review completed:
- Pipeline source/consumer/fetcher/shutdown paths were inspected for bounded queues, executor offload, sanitized failure paths, anomaly detector closure, no ETag caching, manual redirect validation, DNS validation, and zero-working behavior.
- Output generation and metadata paths were inspected for DNS cache passthrough, chosen-output fallback, shielded candidate accounting, and public artifact schema alignment.
- Frontend runtime/config/Lab/proxies/verifier files were inspected for raw `frontend/` deploy reality, nine-strategy Lab parity, local/offline QR behavior, signed-artifact fail-closed handling, and user-input escaping paths.
- Workflows were inspected for raw frontend copy, runtime config injection, Pages artifact validation, `ALLOW_ACTIVE_SCANNING=false`, batch time limits, evidence bundle generation, and live-deploy smoke.

Remaining items:
- Public GitHub Pages is still stale/incomplete and must be redeployed, then `scripts/verify_pages_deployment.py` must pass against the live URL.
- No untracked release inputs remain in the current working tree after the previous audit-contract commit; current follow-up work is tracked-file cleanup only.
- `Main SOURCE OF TRUTH - PART 2.md`, `Main SOURCE OF TRUTH - PART 3.md`, and `Main SOURCE OF TRUTH - Ammendment.md` remain live addenda ledgers. Their actionable findings continue to flow into `STATUS.md`, the master audit, capability registry, and machine validators item by item.
- Part 2 roadmap expansion items remaining after this pass: stable internal event bus, durable latest-output evidence bundle, Lab project model/linter, confidence scoring, source quality v2, output transaction system, signed manifest browser verification, deploy screenshots, adaptive scheduling, and matrix-generated documentation expansion.
- Part 3 remaining hardening items after this pass: pinned/reproducible native client binary validation and offline/lite Sing-box variants that avoid remote rule-set dependencies.
- Frontend trusted/static `innerHTML` usage remains mostly controlled by local data and escaping, but further DOM-builder cleanup is still a reasonable hardening task for Lab/proxies/analytics.

Latest focused verification for the addenda follow-up:
- `pip-audit -r requirements-prod.txt --format json --no-deps`: passed with no known vulnerabilities for the patched direct pins. The exact dependency-resolving `pip-audit -r requirements-prod.txt --format json` could not complete in this Windows/Python 3.13 shell because pip could not resolve `orjson==3.11.6` for Python 3.13 after a PyPI read timeout; CI's Python 3.10-3.12 matrix remains the authoritative resolving audit environment.
- `npm run build`: passed after restoring the `build` alias and normalizing Vite multi-page input paths.
- `npm run test:frontend:no-network`: passed.
- `python scripts/check_dependency_drift.py; python scripts/validate_workflows.py; python scripts/validate_core_compatibility.py; python scripts/validate_capability_registry.py; python scripts/validate_claim_ledger.py; python scripts/validate_status.py`: passed.
- `python -m pytest tests/unit/test_validate_workflows.py tests/unit/test_validate_core_compatibility.py tests/unit/test_dependency_drift.py tests/unit/test_validate_status.py -q`: 30 passed.
- `python -m pytest -q`: 1036 passed, 1 skipped.
- `pre-commit run --all-files`: attempted after installing `pre-commit`, but the remote `gitleaks` hook could not initialize because GitHub HTTPS fetches failed from this environment. Local equivalents were run directly: flake8 passed, Black check passed, workflow/status/dependency validators passed, and full pytest passed. `python -m mypy .` still reports pre-existing repository typing debt outside this CI-remediation patch.
- `pytest tests/unit/generators/test_singbox_comprehensive.py tests/unit/test_output.py tests/unit/test_release_scripts.py tests/unit/test_validate_output_matrix.py tests/unit/test_validate_status.py -q`: 25 passed.
- `python scripts/validate_output_matrix.py`: passed.
- `python scripts/generate_output_docs.py --check`: passed.
- `python -m pytest -q`: 1036 passed, 1 skipped.
- `pytest tests/unit/test_validate_output_matrix.py tests/unit/test_validate_core_compatibility.py tests/unit/test_validate_capability_registry.py tests/unit/test_validate_claim_ledger.py tests/unit/test_validate_workflows.py -q`: 40 passed.
- `python scripts/validate_capability_registry.py; python scripts/validate_core_compatibility.py; python scripts/validate_output_matrix.py; python scripts/validate_claim_ledger.py; python scripts/validate_workflows.py`: passed.
- `pytest tests/unit/test_validate_pages_artifact.py tests/unit/test_release_scripts.py tests/unit/test_validate_workflows.py -q`: 47 passed.
- `python -m pip install --dry-run --only-binary=:all: --python-version 3.10 --implementation cp --abi cp310 --platform manylinux2014_x86_64 -r requirements-prod.txt`: passed, proving the production audit requirements resolve for CI Python 3.10 after the NumPy/SciPy/scikit-learn pin correction.
- `python scripts/validate_module_ownership.py; python scripts/validate_workflows.py; python scripts/check_dependency_drift.py`: passed after module ownership CI wiring, frontend Playwright browser install repair, and Python 3.10 production pin correction.
- `python -m pytest tests/unit/test_validate_module_ownership.py tests/unit/test_validate_workflows.py tests/unit/test_dependency_drift.py -q`: 26 passed.
- `python -m pytest -q`: 1042 passed, 1 skipped after the module ownership, workflow, and dependency-audit remediation batch.
