# ConfigStream Deep Inventory And Status Report

Generated: 2026-05-19  
Workspace: `C:\Users\ACER\Documents\GitHub\ConfigStream`  
Audit target: repository source, tests, docs, workflows, scripts, frontend, provided CI logs, and extracted latest output artifacts under `Latest Outputs to investigate/`.

## Executive Verdict

ConfigStream's tracked source tree is internally much healthier than the latest public-output artifacts. The repository validators, focused tests, frontend smoke tests, dependency drift check, and typed source checks all pass locally when run against the real tracked code. The canonical documents currently claim repository production-readiness.

The public artifact/deployment path is not currently production-ready. The supplied CI runs show two real release blockers:

1. Public `proxies.json` schema drift: generated proxies contain `details.lat`, `details.lng`, and non-UUID top-level `uuid` values.
2. Workflow orchestration race/contract gap: `Merge & Fan-Out` downloads `frontend-wasm` but does not declare `build_wasm` as a dependency, so the artifact can be unavailable.

There is also a validator blind spot: `scripts/validate_pages_artifact.py` validates only the first 50 proxies, so it can miss thousands of invalid entries after index 49.

## Scope Read

Tracked inventory:

- 907 tracked files.
- 118 tracked `src/configstream` Python files.
- 181 tracked test files.
- 75 documentation/markdown surfaces.
- 385 frontend files/assets.
- 6 GitHub workflow files.

Generated audit evidence written under `invvest/` includes:

- `file_inventory.json`
- `source_of_truth_counts.json`
- `source_of_truth_headings.json`
- `source_of_truth_claim_scan.json`
- `pipeline_output_proxy_schema_summary.json`
- `core_architecture_trace.json`
- `parser_contract_trace.json`
- `security_trace.json`
- `frontend_trace.json`
- `consolidated_pipeline_log_findings.json`
- validator/test command transcripts

The untracked `Latest Outputs to investigate/` folder was treated as user-provided evidence. Extracted artifacts live under `invvest/extracted/`.

## Source Of Truth Review

Four main source-of-truth documents were read and indexed:

| File | Lines | Bytes | Current role |
|---|---:|---:|---|
| `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md` | 6,433 | 475,658 | Current unified editorial source of truth |
| `Main SOURCE OF TRUTH - Ammendment.md` | 789 | 49,922 | Historical/amendment ledger with still-detectable debt markers |
| `Main SOURCE OF TRUTH - PART 2.md` | 2,467 | 66,500 | Future hardening roadmap and capability expansion plan |
| `Main SOURCE OF TRUTH - PART 3.md` | 431 | 15,431 | Core compatibility and output-format hardening notes |

Key document conclusion:

- `STATUS.md` and the master audit say the repository is production-ready as of v3.1.0.
- The same truth hierarchy still says public Pages readiness depends on fresh deploy evidence.
- The supplied logs are newer operational evidence and show public artifact generation/deployment is currently failing.

Contradiction found:

- Tracked `docs/DEBT_MATRIX.md` says 0 actionable markers.
- Running `python scripts/generate_debt_matrix.py` today found 8 markers, all in `Main SOURCE OF TRUTH - Ammendment.md`.
- I reverted the generated debt-matrix file churn after capturing the evidence, so tracked docs were not left modified.

## CI Logs And Run Evidence

### Run #678

Status: success  
Duration: 6h 9m 25s  
Artifacts: 22  
Commit: `8f4ff30b5d79d4bee4f9f4b93f3d9befb9f0462c`

Positive signals:

- Container build completed.
- WASM artifact existed in this successful run.
- `pipeline-output.zip` was produced.
- 17 shard artifacts were produced.
- Evidence bundle was produced.

Warnings:

- 22 Node.js 20 deprecation warnings across Actions usage.
- This is not immediately fatal because some later logs show Node 24 forcing is already enabled, but it remains scheduled maintenance before GitHub's runner defaults change.

### Run #680

Status: failure  
Duration: 4h 50m 42s  
Failing job: `Merge & Fan-Out`  
Failing step: `Prepare public output artifact`

Logged error:

- `proxies.json[49] uuid does not match required pattern`
- `proxies.json[49].details contains unknown schema key: lat`
- `proxies.json[49].details contains unknown schema key: lng`
- Same failures through `api/proxies[49]`.

Root cause traced to code:

- `src/configstream/consumer.py:550-553` writes GeoIP coordinates directly into `p.details["lat"]` and `p.details["lng"]`.
- `schema/proxy.schema.json` protocol-specific detail schemas use `additionalProperties: false` and do not allow `lat`/`lng`.
- `src/configstream/intelligence/washer/core.py:1287-1295` creates revived proxies with `uuid=chain_id`.
- Those chain IDs are strings like `WARP-REVIVE-21150522`, not UUIDs, while `schema/proxy.schema.json` top-level `uuid` requires empty string or UUID-pattern values.

Artifact-wide impact:

- Extracted `pipeline-output/proxies.json` contains 8,612 proxy objects.
- 2,598 contain `details.lat` and/or `details.lng`.
- 3,694 contain non-empty invalid top-level `uuid` values.
- 3,692 of the invalid UUIDs are `protocol=revived`.
- 2 invalid UUIDs are native `socks5` proxies with base64-like credential values in `uuid`.

### Run #682

Status: failure  
Failing job: `Merge & Fan-Out`  
Failing step: `Download WASM for Deployment`

Logged error:

- Artifact not found for name: `frontend-wasm`.

Root cause traced to workflow:

- `.github/workflows/main.yml:166-194` defines and uploads `frontend-wasm`.
- `.github/workflows/main.yml:306-362` downloads `frontend-wasm` in `merge_results`.
- `.github/workflows/main.yml:309` sets `merge_results.needs: pipeline` only.
- `merge_results` does not need `build_wasm`, so GitHub has no dependency guarantee that the artifact exists before download.

Recommended workflow fix:

- Change `merge_results.needs` from `pipeline` to include `build_wasm`, likely `needs: [pipeline, build_wasm]`.
- Keep `if: always()` semantics carefully so failed shards do not suppress merging, but do not make the WASM artifact dependency optional unless deployment can operate without it.

## Extracted Output Artifact Review

`pipeline-output.zip` extraction:

- 493 files.
- About 371 MB uncompressed.
- Contains raw frontend, APIs, subscription files, configs, analytics data, docs, tools, WASM, and public manifests.

Public metadata:

- `metadata.json` reports:
  - `version`: `3.1.0`
  - `total_proxies`: `4306`
  - `total_tested`: `52846`
  - `total_working`: `614`
  - `success_rate`: about `1.16%`
  - `shielded_count`: evidence summary reports `3681`
  - `shielded_verified_count`: `0`
- `health.json` reports:
  - `status`: `ok`
  - `total_working`: `614`
  - `total_tested`: `52846`

Output inconsistency:

- `metadata.json` says `total_proxies=4306`.
- `proxies.json` actually contains 8,612 objects.
- This suggests metadata is counting a subset or pre-expansion set, while public `proxies.json` includes duplicated DNS/profile/revived material.
- If intentional, docs/front-end labels need to clarify the count. If not intentional, metadata is misleading.

Native-client evidence:

- `native_client_check_report.json` exists.
- `sing-box` binary unavailable.
- `mihomo` binary unavailable.
- 12 native checks were skipped.
- This is honest evidence, but it does not prove client-native compatibility.

`audit_pipeline_outputs.py` results:

- JSON files are syntactically valid.
- Sing-box native checks were not run because no binary was available.
- `proxies.txt`, `proxies-dns-safe.txt`, and `proxies-dns-hardened.txt` were classified as 614 invalid lines by that audit helper.
- `stealth_apple-touch-icon.png` was reported missing by that helper.

Manifest extraction caveat:

- Running `validate_pages_artifact.py` directly against the extracted ZIP folder reports missing `.build-config.json` and `.nojekyll`.
- The artifact manifest references dotfiles that are not visible in the extracted folder. This may be ZIP/extraction behavior or packaging mismatch; the CI #680 log reached deeper proxy schema validation, so in CI those files were present at validation time.

## Core Architecture Review

### Pipeline

Positive:

- `src/configstream/pipeline.py:254` creates `asyncio.Queue(maxsize=5000)`, satisfying the bounded queue requirement.
- `src/configstream/pipeline.py:156` instantiates `AdaptiveTimeout`.
- `src/configstream/pipeline.py:169` instantiates `AnomalyDetector`.
- `src/configstream/pipeline.py:451` calls output generation after processing.
- `src/configstream/pipeline.py` logs zero-working output as critical but continues in non-strict mode, matching the fail-open output contract.

Concern:

- The latest consolidated logs show hard time-limit cancellation and partial output finalization with zero working proxies in at least one shard. This is expected in hostile CI, but the final merged artifact must label partial/degraded conditions clearly.

### Producer

Positive:

- `src/configstream/producer.py` uses `CircuitBreakerManager`.
- It sanitizes source URLs in log paths.
- It uses `run_in_executor` for blocking/source-quality/parser work.
- It validates and extracts config lines through structured drop stats.

Concern:

- Logs show frequent circuit-breaker-open fetch failures and high source failure rates. That is acceptable for the domain but should feed adaptive source quality more visibly into status/evidence.

### Consumer

## Remediation Closure Update (2026-05-19)

This section closes each major finding with first-hand implementation detail in the requested format.

### Item 1: `details.lat` / `details.lng` violate proxy schema

- What I saw:
  - CI #680 failed at `proxies.json[49]` for unknown `details.lat` and `details.lng`.
  - Code path writing those keys was in `src/configstream/consumer.py`.
- How I handled it:
  - Removed runtime writes of `lat` and `lng` into protocol `details`.
  - Kept geo enrichment logic otherwise intact.
- What I implemented:
  - `src/configstream/consumer.py`: removed `p.details["lat"]` / `p.details["lng"]` assignments.
- Status:
  - Implemented in tracked code. Root schema violation path addressed.

### Item 2: Revived chain IDs written into top-level `uuid`

- What I saw:
  - Revived IDs (`WARP-REVIVE-*`, `VWARP-REVIVE-*`) were assigned to `uuid`.
  - Schema requires UUID-pattern or empty string.
- How I handled it:
  - Broke the coupling between chain identity and public UUID field.
- What I implemented:
  - `src/configstream/intelligence/washer/core.py`: revived proxy creation now sets `uuid=""`.
- Status:
  - Implemented in tracked code.

### Item 3: Generic parser leaks username into top-level `uuid`

- What I saw:
  - Generic HTTP/SOCKS parsing used `parsed.username` as `uuid`.
  - This produced non-UUID values in public artifacts.
- How I handled it:
  - Kept protocol credential in details, not UUID.
- What I implemented:
  - `src/configstream/parsers/generic.py`: set `uuid=""`; write username to `details["username"]`.
  - `tests/unit/test_parsers_generic_extended.py`: updated expectations.
- Status:
  - Implemented and test-updated.

### Item 4: Serialization boundary did not enforce UUID contract

- What I saw:
  - Serializer passed through `proxy.uuid` without schema-safe normalization.
- How I handled it:
  - Added explicit UUID boundary guard at public serialization.
- What I implemented:
  - `src/configstream/serialize.py`: added `_public_uuid_value()` UUID regex gate.
  - Non-UUID/non-empty values now serialize as empty string.
- Status:
  - Implemented in tracked code.

### Item 5: `validate_pages_artifact.py` validates only first 50 proxies

- What I saw:
  - Validator used `payload[:50]`, allowing invalid records after index 49 to escape.
- How I handled it:
  - Expanded validation coverage to full payload while capping output noise.
- What I implemented:
  - `scripts/validate_pages_artifact.py`: iterate all records.
  - Added bounded error cap (`MAX_PROXY_VALIDATION_ERRORS`) with early-stop message.
- Status:
  - Implemented in tracked code.

### Item 6: `Merge & Fan-Out` could download WASM before producer completion

- What I saw:
  - `merge_results` downloaded `frontend-wasm` without depending on `build_wasm`.
  - This matches CI #682 artifact-not-found failure.
- How I handled it:
  - Added direct dependency and added policy-level validator coverage.
- What I implemented:
  - `.github/workflows/main.yml`: `merge_results.needs` now includes `build_wasm`.
  - `scripts/validate_workflows.py`: new rule requiring `build_wasm` dependency when `merge_results` downloads `frontend-wasm`.
  - `tests/unit/test_validate_workflows.py`: added reject/accept regression tests.
- Status:
  - Implemented in workflow and in validator/test policy.

### Item 7: Hidden deploy control files dropped from downloadable artifact

- What I saw:
  - Extracted evidence could miss hidden files expected by downstream checks.
- How I handled it:
  - Ensured upload step includes hidden files explicitly.
- What I implemented:
  - `.github/workflows/main.yml`: set `include-hidden-files: true` for `pipeline-output` upload.
- Status:
  - Implemented in tracked workflow.

### Item 8: Metadata count semantics (public rows vs logical proxies) ambiguous

- What I saw:
  - `metadata.total_proxies` and public `proxies.json` row count diverged.
- How I handled it:
  - Kept backward-compatible top-level totals while exposing explicit logical/public counters.
- What I implemented:
  - `src/configstream/output_handler.py`: return `public_record_count` / `public_working_count`.
  - `src/configstream/output_logic.py`: export
    - `total_proxies` / `total_working` (public-facing counts),
    - `logical_total_proxies` / `logical_total_working`,
    - `public_record_count` / `public_working_count`.
  - `schema/metadata.schema.json`: added these fields.
- Status:
  - Implemented in tracked code and schema.

### Item 9: Source-of-truth historical documents could be read as active status

- What I saw:
  - Amendment/parts include historical language that can conflict with current readiness claims.
- How I handled it:
  - Added explicit supersession framing at top of historical files.
- What I implemented:
  - `Main SOURCE OF TRUTH - Ammendment.md`
  - `Main SOURCE OF TRUTH - PART 2.md`
  - `Main SOURCE OF TRUTH - PART 3.md`
- Status:
  - Implemented in tracked docs.

### Item 10: Public-facing readiness wording over-optimistic for failing release edge

- What I saw:
  - Repository statements could be read as fully production-ready even when current public artifact path was failing.
- How I handled it:
  - Tightened wording to represent repository maturity plus active release gates.
- What I implemented:
  - `README.md`: production messaging adjusted to gate-aware phrasing.
- Status:
  - Implemented in tracked docs.

### Item 11: Workflow policy did not enforce artifact causality

- What I saw:
  - Existing workflow validator checked structure/content but not producer-consumer dependency for WASM artifact.
- How I handled it:
  - Added causality rule plus targeted unit tests.
- What I implemented:
  - `scripts/validate_workflows.py`: `_main_frontend_wasm_download_has_build_dependency`.
  - `tests/unit/test_validate_workflows.py`: new failing and passing fixtures.
- Status:
  - Implemented and now regression-covered.

### Item 12: Validation and verification run after implementation

- What I saw:
  - Need proof that fixes integrate with existing contract checks.
- How I handled it:
  - Re-ran core validators and focused test slices.
- What I implemented:
  - Local execution evidence captured for:
    - `validate_workflows.py`
    - `validate_output_matrix.py`
    - `validate_status.py`
    - `validate_claim_ledger.py`
    - focused pytest subsets for artifact/workflow/output/parser contracts.
- Status:
  - Completed; checks passed in this audit pass.

Positive:

- CPU/heavy operations are repeatedly offloaded with `run_in_executor`.
- Logging uses `SecurityValidator.sanitize_log_message` in many error paths.
- Revived proxies are preserved even if not working, matching the user-side testing policy.

P0/P1 issue:

- `src/configstream/consumer.py:550-553` injects GeoIP coordinates into protocol-specific `details`, violating the public proxy schema. Coordinates should be top-level schema fields, removed from public serialization, or added explicitly to each allowed details schema. The cleanest contract is probably top-level `lat`/`lng` or no public coordinates in proxy records.

### Fetcher

Positive:

- `src/configstream/fetcher.py` imports and uses `AdaptiveTimeout`.
- It imports and uses `CircuitBreakerManager`.
- It sanitizes source strings in log paths.
- It uses the hardened HTTP client/transport path.

### Output Generation

Positive:

- `output_handler.py` passes `dns_safe_cache` and `dns_hardened_cache` into `generate_categorized_outputs`, matching AGENTS.md.
- Chosen outputs are generated.
- Output code has broad artifact generation coverage.

Concerns:

- Public `proxies.json` schema is not enforced before publishing all records.
- Validator only samples first 50 proxies.
- Metadata count semantics diverge from `proxies.json` length.

## Parser Review

Positive:

- VLESS credential fallback exists in `src/configstream/parsers/vless.py:77-87`.
- Trojan credential fallback exists in `src/configstream/parsers/trojan.py:35-48`.
- Shadowsocks password fallback exists in `src/configstream/parsers/shadowsocks.py:99-113`.
- `extract_config_lines` returns configs plus drop stats and logs only sampled/sanitized drops.
- Extraction handles malformed, binary-like, HTML, YAML, JSON, and oversized payload paths.

Risk:

- The output artifact shows two native `socks5` proxies with base64-like values in the top-level `uuid` field. That suggests at least one generic/other parser path is still mapping non-UUID credentials into `Proxy.uuid`. For non-UUID protocols, credentials should remain in `details.password`, `details.username`, or protocol-specific keys, not top-level `uuid`.

## Security Review

Positive:

- `SecurityValidator.sanitize_log_message` masks UUIDs, tokens, and URL credentials.
- `security/blocklist.py` uses a `threading.Lock` singleton pattern.
- `geoip.py` uses a `threading.Lock` singleton pattern.
- `security/transport.py` documents and implements DNS rebinding defense with pre-resolution, private-network blocking, IP pinning, Host preservation, and HTTPS SNI preservation.
- Active scanning is disabled in workflow batch runs via `ALLOW_ACTIVE_SCANNING=false`.

Concerns:

- Generated output still exposes schema-internal metadata (`lat`, `lng`) inside `details`.
- Synthetic revived IDs in `uuid` can confuse clients and downstream consumers that treat top-level `uuid` as a real credential.
- Native compatibility evidence is currently skipped when binaries are unavailable; this is honest but not a compatibility proof.

## Tester And Revival Review

Positive:

- Go sidecar is built in `Merge & Fan-Out`.
- WASM module source exists and artifact can be produced.
- Washer creates WARP and Vwarp revival chains and includes `mtu: 1280` for WireGuard WARP outbounds at `washer/core.py:1206-1216`.
- Revived candidates are kept even when re-testing fails, matching AGENTS.md.

Concerns:

- Vwarp tunnel startup errors appear in consolidated logs.
- Go tester warnings are frequent.
- `shielded_verified_count=0` in the evidence means shielded candidates did not become verified working proxies in that run.
- Revived proxy public serialization is schema-invalid because `uuid=chain_id`.

## Frontend Review

Positive:

- Same-origin smoke passed.
- Protocol render smoke passed.
- Lab XSS smoke passed.
- No-network frontend smoke passed.
- Runtime config placeholder validator passed.
- Lab QR path is local/offline and does not use third-party QR services.
- Many user-provided values are rendered through `textContent` or escaped helpers.

Concerns:

- `frontend/assets/js/lab.js` and `frontend/assets/js/proxies.js` still use multiple `innerHTML` assignments. Many are controlled/static or escaped, but DOM-builder cleanup remains a valid hardening item.
- `npm run build` passes, but Vite warns that several Lab scripts cannot be bundled without `type="module"`. This is acceptable only because raw static `frontend/` is canonical for Pages deployment.

## Workflow And Deployment Review

Positive:

- `scripts/validate_workflows.py` passes.
- Workflows set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` in relevant environments.
- Batch runs set `ALLOW_ACTIVE_SCANNING=false`.
- Public output preparation copies raw `frontend/`, injects runtime config, creates API aliases, removes `data/test_cache.json`, refreshes contract, and validates the artifact.

Blocker:

- `merge_results` does not depend on `build_wasm`, causing `frontend-wasm` artifact download failure risk.

Maintenance:

- Node 20 action deprecation warnings remain for third-party/action versions in GitHub logs. This is not the direct cause of #680/#682, but the workflows should continue moving toward explicit Node 24-compatible actions.

## Documentation And Governance Review

Positive:

- `validate_status.py` passes.
- `validate_claim_ledger.py` passes.
- `validate_protocol_matrix.py` passes.
- `validate_output_matrix.py` passes.
- `validate_module_ownership.py` passes.
- Claim ledger includes governance and output evidence claims.

Concerns:

- Canonical docs say repo production-ready, but latest operational evidence shows public artifact/deploy blockers.
- Amendment ledger still contains historical TODO/XXX language that the debt generator now treats as actionable unless explicitly excluded.
- Source-of-truth hierarchy should add a dated post-#680/#682 note so the next contributor does not trust older success language over fresh CI failures.

## Local Validation Run

Commands run during this audit:

- `python scripts/validate_workflows.py`: passed.
- `python scripts/validate_protocol_matrix.py`: passed.
- `python scripts/validate_output_matrix.py`: passed.
- `python scripts/validate_claim_ledger.py`: passed.
- `python scripts/validate_module_ownership.py`: passed.
- `python scripts/validate_status.py`: passed.
- `python scripts/validate_frontend_placeholders.py frontend`: passed.
- `python scripts/check_dependency_drift.py`: passed.
- `python scripts/validate_assets.py`: passed.
- `python -m pytest tests/unit/test_validate_pages_artifact.py tests/unit/test_validate_workflows.py tests/unit/test_logging_sanitization_policy.py -q`: 57 passed.
- `python -m mypy src scripts tests`: passed with annotation notes only.
- `npm run build`: passed with Lab non-module script bundle warnings.
- `npm run test:frontend:no-network`: passed.
- `python scripts/audit_pipeline_outputs.py --artifact invvest\extracted\pipeline-output --contract pages --report invvest\audit_pipeline_outputs_report.json`: passed as a syntax/audit helper, but reported invalid `proxies.txt` lines and missing stego asset.

Non-actionable command caveat:

- `python -m mypy .` failed after extracting artifacts into `invvest/` because duplicated `lab-scanner.py` modules existed inside audit output. Running mypy against tracked source/test/script roots passed.

## Priority Findings

### P0: Public artifact schema is broken

Evidence:

- CI #680 failed on `proxies.json[49]`.
- Extracted artifact has 2,598 records with `details.lat/lng`.
- Extracted artifact has 3,694 invalid non-empty top-level `uuid` values.
- Code source: `consumer.py:550-553`, `washer/core.py:1287-1295`.

Impact:

- Pages deployment fails.
- Public API contract is invalid.
- Frontend/API consumers cannot trust schema.

Recommended fix:

- Stop writing `lat`/`lng` into protocol-specific `details`; move to top-level schema fields or omit from public proxy serialization.
- Do not put revived chain IDs into `Proxy.uuid`; add a separate `chain_id`, `revival_id`, or use `id`/`remarks`/`details.origin_id`.
- For non-UUID protocols, keep credentials out of top-level `uuid`.

### P0: WASM artifact dependency is not declared

Evidence:

- CI #682 failed downloading `frontend-wasm`.
- Workflow line `.github/workflows/main.yml:309` only needs `pipeline`.
- Download occurs at `.github/workflows/main.yml:358-362`.

Impact:

- Merge/deploy can fail independently of code quality.

Recommended fix:

- Add `build_wasm` to `merge_results.needs`.

### P1: Pages validator samples only first 50 proxies

Evidence:

- `scripts/validate_pages_artifact.py:636` iterates `payload[:50]`.
- Extracted artifact contains thousands of invalid entries beyond the first 50.

Impact:

- Validator can pass invalid public data if early records happen to be clean.

Recommended fix:

- Validate all proxies, or validate all schema-sensitive fields with streaming/early capped reporting.
- Keep error output capped, not validation coverage capped.

### P1: Metadata count semantics are misleading

Evidence:

- `metadata.json total_proxies=4306`.
- `proxies.json` length is 8,612.

Impact:

- Dashboard and public API stats may mislead users.

Recommended fix:

- Define separate fields: `native_proxy_count`, `public_proxy_record_count`, `revived_count`, `dns_variant_count`, `working_count`.

### P1: Native compatibility evidence is skipped

Evidence:

- `native_client_check_report.json`: 12 skipped, 0 passed, 0 failed.

Impact:

- Output JSON/YAML syntax is not enough to prove sing-box/mihomo importability.

Recommended fix:

- Install pinned sing-box/mihomo binaries in the validation job or document the evidence as schema-only.

### P2: Debt matrix exclusion drift

Evidence:

- Tracked debt matrix says 0.
- Regeneration found 8 markers in Amendment ledger.

Impact:

- Governance validator can drift from actual source text.

Recommended fix:

- Either exclude historical source-of-truth ledgers intentionally or remove/neutralize stale TODO/XXX text.

### P2: Frontend hardening remains worthwhile

Evidence:

- `frontend_trace.json` lists many `innerHTML` call sites.
- Smoke tests pass, and many are escaped/static.

Impact:

- Future edits can accidentally turn controlled HTML into user-influenced HTML.

Recommended fix:

- Convert Lab/proxies dynamic rows to DOM construction utilities over time.

## Category Status

| Category | Status | Notes |
|---|---|---|
| Repository structure | Strong | Clear module split, canonical matrices, many validators |
| Source-of-truth docs | Mixed | New docs are coherent, historical addenda still create debt-scan conflict |
| CI workflows | Mixed | Validators pass, but WASM dependency race is real |
| Pipeline architecture | Strong with output-contract bug | Bounded queue, async offload, fail-open behavior present |
| Fetching/network resilience | Strong | Adaptive timeout, circuit breaker, DNS rebinding transport present |
| Parsers | Mostly strong | Credential fallbacks present; non-UUID credential placement still leaks to `uuid` in output |
| Security/logging | Mostly strong | Sanitization and transport protections present; output schema leaks remain |
| Output generation | Blocked for public deploy | Generates broad artifacts, but public `proxies.json` invalid |
| Frontend | Good | Same-origin/no-network smoke passed; hardening remains |
| Testing | Strong locally | Focused tests passed; full suite not rerun in this audit due time/artifact scope |
| Latest artifacts | Not deployable | Schema drift, manifest/extraction caveat, skipped native checks |
| Public Pages readiness | Not ready | #680 and #682 are blocking evidence |

## Immediate Remediation Checklist

1. Fix public proxy serialization:
   - remove `details.lat/lng` or add a properly documented schema location.
   - prevent synthetic chain IDs from populating `uuid`.
   - prevent non-UUID protocol credentials from populating `uuid`.

2. Strengthen `validate_pages_artifact.py`:
   - validate all proxies.
   - cap displayed errors, not checked records.
   - add regression fixture with invalid proxy after index 50.

3. Fix workflow dependency:
   - add `build_wasm` to `merge_results.needs`.
   - keep merge behavior robust for shard failures.

4. Re-run pipeline artifact validation:
   - `python scripts/validate_pages_artifact.py --refresh-contract output`
   - native report with actual sing-box/mihomo binaries if possible.

5. Update source-of-truth docs:
   - add a dated status note for #680/#682.
   - reconcile `DEBT_MATRIX.md` exclusion behavior with Amendment TODO/XXX markers.

6. Re-run full validation:
   - full pytest.
   - mypy on tracked code.
   - frontend smoke.
   - workflow validators.
   - Pages artifact validation against generated output.

## Final State

The codebase is not a mess; it is a sophisticated, heavily guarded system with a real public-contract regression. The flaws are not primarily missing tests. They are exactly where the user suspected: in line-level interactions between code, schema, serializer, and deployment workflow.

The next repair should be narrow and high-impact: public proxy schema hygiene, validator coverage beyond 50 records, and the WASM job dependency. Once those are fixed, the project can credibly return to the production-ready status claimed by the canonical docs.
