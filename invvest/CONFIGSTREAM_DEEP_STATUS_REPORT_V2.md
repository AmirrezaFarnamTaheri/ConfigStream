# ConfigStream Deep Status Report V2

Audit date: 2026-05-19  
Workspace: `C:\Users\ACER\Documents\GitHub\ConfigStream`  
Scope: first-hand repository material, source code, tests, workflows, schemas, docs, local logs, and extracted production artifacts under `invvest/extracted/`.

## Executive Verdict

The tracked repository is far stronger than the failed public artifact, but the present end-to-end release state is not clean production-ready. The codebase has many real guardrails: bounded producer/consumer architecture, protocol parsers, schema validators, output matrices, Pages contract checks, frontend runtime-config injection, evidence bundles, and a broad unit test suite. However, the material audit found several line-level defects and contract mismatches that explain the recent CI failures and expose additional release risk beyond those two failures.

The most important conclusion: the repository status documents say "repository production-ready", but the current generated artifact and current workflow wiring do not satisfy that claim. This is not only a deploy freshness issue anymore. The extracted `pipeline-output` artifact contains schema-invalid public proxy records, duplicated accounting semantics, and missing hidden deploy control files. The workflow can race the WASM artifact. The validator only samples the first 50 proxy records. The source-of-truth addendum still contains older unresolved-roadmap statements, and the debt matrix generator still detects markers inside that addendum even though the tracked debt matrix says 0 actionable items.

## Material Actually Read

This pass did not stop at tests or keyword checks. I created first-hand reading bundles in `invvest/` from the actual files:

- `read_four_source_of_truth_parts_material.txt`: 607,519 bytes from the master report, Part 2, Part 3, and the amendment.
- `read_all_src_code_material.txt`: 1,202,649 bytes from all `src` Python and Go source files.
- `read_all_tests_material.txt`: 736,632 bytes from all test files.
- `read_workflows_scripts_tools_material.txt`: 451,698 bytes from workflows, scripts, and tools.
- `read_frontend_schema_docs_material.txt`: 994,741 bytes from frontend, schemas, matrix docs, and project docs.
- `read_generated_artifact_evidence_material.txt`: 6,119,509 bytes from extracted artifact/evidence reports and generated audit summaries.
- `read_local_configstream_log_material.txt`: local `configstream.log`.

Inventory from this pass, excluding heavy/generated folders such as `.git`, `node_modules`, `.venv`, `frontend-dist`, and `invvest`: 1,065 files / 332,971,498 bytes. Key source areas:

- `src`: 138 files / 1,313,460 bytes.
- `scripts`: 48 files / 314,337 bytes.
- `tools`: 15 files / 346,744 bytes.
- `docs`: 59 files / 478,792 bytes.
- `frontend`: 385 files / 17,754,123 bytes.
- `tests`: 181 files / 719,065 bytes.
- `.github`: 7 files / 50,137 bytes.
- `schema`: 4 files / 34,618 bytes.
- `sources`: 34 files / 169,249 bytes.

## P0 / Release Blockers

### 1. Public artifact schema is invalid because runtime enrichment writes keys forbidden by schema

`src/configstream/consumer.py:551` writes `p.details["lat"] = geo_data.lat`; `src/configstream/consumer.py:553` writes `p.details["lng"] = geo_data.lng`. The public proxy schema closes protocol-specific `details` objects with `additionalProperties: false` at multiple locations, including `schema/proxy.schema.json:554`, `663`, `755`, `816`, `903`, `983`, `1026`, `1101`, and `1104`.

That exactly matches the CI #680 failure:

- `proxies.json[49].details contains unknown schema key: lat`
- `proxies.json[49].details contains unknown schema key: lng`
- same for `api/proxies`.

Artifact-wide impact is much larger than index 49. In extracted `pipeline-output/proxies.json`, 2,598 of 8,612 proxy records contain `details.lat` and `details.lng`. This is not a one-record data anomaly; it is a generator/schema contract mismatch.

Required direction: either move coordinates to top-level schema fields or add an explicit shared geo-details schema allowance. Do not keep arbitrary protocol-specific details pollution.

### 2. Public artifact schema is invalid because revived chain IDs are serialized as UUIDs

`src/configstream/intelligence/washer/core.py:1160` creates `VWARP-REVIVE-{relay.id[:8]}`. `src/configstream/intelligence/washer/core.py:1163` creates `WARP-REVIVE-{relay.id[:8]}`. `src/configstream/intelligence/washer/core.py:1292` then sets `uuid=chain_id`.

The public schema requires top-level `uuid` to be empty or a UUID pattern at `schema/proxy.schema.json:73-76`. `src/configstream/serialize.py:75` serializes `"uuid": proxy.uuid` directly.

Extracted artifact impact:

- 3,694 invalid non-empty top-level UUID values.
- 3,692 are revived `WARP-REVIVE-*` / `VWARP-REVIVE-*` records.
- 2 are native `socks5` records with base64-looking usernames (`Og==`, `VDJjbE0wUWxNMFE6Og==` class).

Required direction: separate `id`, `chain_id`, and protocol credential fields. Top-level `uuid` should not be a generic identity field unless the schema is deliberately changed. For non-UUID protocols, credentials belong in protocol-specific `details`.

### 3. Generic HTTP/SOCKS parsing abuses `uuid` for usernames

`src/configstream/parsers/generic.py:166` and `src/configstream/parsers/generic.py:199` set `uuid=parsed.username or ""` for generic and naive proxy URLs. This is how non-UUID credentials leak into the top-level UUID slot and later fail the public schema. The `Proxy.id` property in `src/configstream/models.py` also treats `uuid` as the preferred stable credential/identifier, which makes this field carry too many meanings.

Required direction: keep username in `details.username` or a protocol-specific field, and make stable IDs separate from credential fields.

### 4. Pages artifact validator samples only first 50 proxies

`scripts/validate_pages_artifact.py:636` iterates `payload[:50]`, so only the first 50 records are schema-validated. The CI #680 failure happened because record 49 already had bad data. If malformed records appear after index 49, the validator will incorrectly pass. In the extracted artifact, invalid UUIDs begin around index 193 and continue for thousands of records; these would be missed if the first 50 were clean.

Required direction: validate every proxy record, or validate all records with a bounded error-report limit. Sampling is not acceptable for a deploy gate whose purpose is contract enforcement.

### 5. Main workflow can race or skip `frontend-wasm`

`.github/workflows/main.yml:189-191` uploads `frontend-wasm`. `.github/workflows/main.yml:358-361` downloads it in `Merge & Fan-Out`. But `.github/workflows/main.yml:309` declares `needs: pipeline`, not `needs: [pipeline, build_wasm]`.

That exactly matches CI #682:

- `Unable to download artifact(s): Artifact not found for name: frontend-wasm`

Required direction: make `merge_results` depend on `build_wasm`, or make the download conditional with an explicit fallback that still leaves the frontend contract truthful.

### 6. Extracted pipeline artifact is missing hidden deploy files

The extracted `pipeline-output` artifact has 493 files but lacks `.nojekyll` and `.build-config.json`. The workflow creates `output/.nojekyll` at `.github/workflows/main.yml:413-414` and uploads `pipeline-output` at `.github/workflows/main.yml:433-436` via `actions/upload-artifact@v4`.

This matters because `scripts/validate_pages_artifact.py` requires `.build-config.json` and `.nojekyll` for a complete Pages-shaped artifact. The run #680 log validated before upload and therefore reached proxy schema errors, but any later consumer downloading `pipeline-output` may receive a shape different from the directory that was validated.

Required direction: ensure hidden files are included in reusable artifacts, or do not treat `pipeline-output` downloads as equivalent to the validated Pages directory.

## P1 / High Risk

### 7. Metadata count semantics are internally inconsistent

Extracted `pipeline-output`:

- `proxies.json` length: 8,612.
- `metadata.json.total_proxies`: 4,306.
- `metadata.json.total_working`: 614.
- Actual `is_working == true` count in public JSON: 1,228.
- Native count: 614.
- Revived count: 3,692.
- Records with `details.is_chain`: 4,306.

This strongly suggests the artifact emits paired rows or chain-expanded records while metadata counts a different logical unit. That may be intentional internally, but it is confusing and public-facing. Frontend users and downstream API consumers will naturally compare `metadata.total_proxies` to `proxies.json.length`.

Required direction: either document and expose separate `logical_proxy_count`, `public_record_count`, `chain_record_count`, and `working_public_record_count`, or make `total_proxies` match the public array.

### 8. Native client compatibility evidence is honest but weak

The evidence bundle records native checks, but `native_client_check_report.json` shows `sing-box` and `mihomo` unavailable/skipped. The source of truth correctly calls pinned/reproducible native binary validation future hardening, but the current claim ledger can be read as stronger than the evidence. This is not a failing test; it is a proof gap.

Required direction: keep the wording evidence-only, or add pinned native binaries/checks in CI.

### 9. Source-of-truth surfaces still mix current truth with old incompatible truth

Current `STATUS.md:5` says repository production-ready but live Pages fails smoke. `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md:6` and `:13` repeat the same current verdict. The same master report preserves old "not production-ready" sections, with supersession notes around lines `991-1003`.

The amendment is still a live file and contains older contradictory status: `Main SOURCE OF TRUTH - Ammendment.md:12`, `:24`, `:42`, `:63`, `:112`, `:124`, `:185-191`, and repeated later around `:651-706`. It says remediation is not production-final, debt markers are huge, output matrix has remaining work, and open PR state matters. Some of this is intentionally historical, but AGENTS says the four parts are source-of-truth material and the user explicitly asked to read them. As written, they still create ambiguity unless every old claim is clearly fenced as superseded.

Required direction: add a top-level supersession block to Part 2, Part 3, and amendment, or split historical ledgers from current operative truth.

### 10. Debt matrix says 0 actionable markers, but the generator still finds amendment markers

`docs/DEBT_MATRIX.md:6` says the matrix represents actionable debt after filtering historical reports. During the earlier pass, `python scripts/generate_debt_matrix.py` found 8 markers, all in `Main SOURCE OF TRUTH - Ammendment.md`. I reverted the generated file changes immediately, so tracked source was not changed.

This is not a code blocker by itself, but it means the debt scan result depends on whether the amendment is considered active material. The user explicitly treats it as source of truth, so the discrepancy should be clarified.

Required direction: either exclude the amendment as historical in the generator, or update the tracked debt matrix after a deliberate run.

### 11. Local logs show expected fail-open behavior, but also operational proof gaps

`configstream.log` shows:

- Go tester binary missing repeatedly; pipeline falls back to Python tester.
- Vwarp unavailable on Windows and disabled.
- GeoIP database missing locally.
- Source cooldown can result in "ALL remote sources are on cooldown/disabled".
- History storage file-size guard triggers at 105,906,176 bytes.
- Source quality DB errors fail open.
- VirusTotal API key missing / rate limited.

Many of these are expected in local tests and fail-open paths, but they are important status signals. A production-readiness report should not present these as equivalent to live native compatibility and real-network confidence.

## P2 / Design and Maintainability Risks

### 12. `Proxy.uuid` is overloaded across protocol credential, stable ID, user credential, and chain identity

The codebase uses `uuid` for VLESS/VMess identity, Trojan-ish credential compatibility, generic username, cache/history stable identity, and revived chain IDs. This is the common root under multiple artifact failures. The schema wants a UUID; the model wants a stable credential; the pipeline wants an identity key; parsers want protocol credentials.

Recommended model direction:

- `id`: stable generated record identifier.
- `credential_uuid`: UUID only for UUID-based protocols.
- `username` / `password`: protocol-specific auth.
- `chain_id`: revived/smart-chain identity.
- `uuid`: either removed from public top-level or kept only as UUID-compatible alias.

### 13. Public schema is stricter than internal model, but generation does not normalize at the boundary

The internal `Proxy.details` is a free dict. The public schema has protocol-specific closed shapes. That is workable only if serialization normalizes/sanitizes before writing public JSON. `serialize_proxy` currently mostly passes through raw `details`, including chain objects after partial conversion and arbitrary runtime enrichment.

Recommended direction: add a public DTO layer or `serialize_public_proxy()` that strips, moves, or maps internal-only keys before schema validation.

### 14. Workflow validation checks structure, not artifact causality

The workflow validator passed, but the workflow still allowed `merge_results` to download an artifact from a job it did not need. This means `scripts/validate_workflows.py` is not checking job dependency causality for artifacts. It checks that commands exist, but not whether producer jobs are in `needs`.

Recommended direction: add a regression: any job using `actions/download-artifact` with `name: frontend-wasm` must need the job that uploads `frontend-wasm`.

### 15. Frontend is mostly guarded, but DOM construction remains broad

The frontend has runtime config fail-closed paths and same-origin/no-network guardrails. It also uses many `innerHTML` sites. Many are static/trusted templates or sanitized markdown paths, but the master report itself says DOM-builder cleanup remains reasonable hardening. The Lab page in particular includes dynamic HTML builders and export surfaces, so it should continue moving toward DOM APIs or narrowly audited template helpers.

## Category Status

### Architecture

Strong shape. Producer/consumer separation, bounded queue behavior, adaptive timeout, circuit breaker, quality tracker, event stream, and fail-open outputs are real. The architecture is not the primary problem. The weak point is the boundary between rich internal `Proxy` objects and strict public artifact schemas.

### Parsers

Broad protocol coverage is present. Robustness handling exists for VMess/VLESS/Trojan/SS and generic parsers. The main parser flaw found in this pass is not crashing; it is field semantics: generic/naive HTTP/SOCKS credentials flow into `uuid`, which breaks the public UUID contract.

### Testing

The test suite is broad and useful, but a lot of tests are mocked/dry-run by design. That is acceptable for unit scope, but it does not prove live network, native client, or deploy artifact correctness. Existing tests did not catch the validator sample window or artifact dependency race. Add focused regressions for:

- GeoIP coordinates do not violate public proxy schema.
- Revived records do not put non-UUID IDs in `uuid`.
- Generic SOCKS/HTTP usernames do not populate top-level `uuid`.
- `validate_pages_artifact.py` checks records after index 50.
- `merge_results` depends on `build_wasm`.
- Downloaded `pipeline-output` preserves required hidden files or is not used as Pages-equivalent.

### Workflows

CI has good coverage breadth and Node 24 opt-in environment variables. The logs still show GitHub's Node 20 action deprecation warnings for third-party actions. That is not currently the root cause because GitHub forced Node 24 in parts of the log, but it remains operational noise. The real workflow blocker is the missing `build_wasm` dependency and hidden-file artifact shape.

### Public Outputs

The output family is large and mostly generated, but the extracted public JSON is currently invalid against its own schema. The API aliases match the same bad content, so alias parity works while semantic validity fails. Subscriptions (`proxies.txt`, DNS-safe, DNS-hardened, chosen outputs) contain plausible URI lines, but control JSON is the public contract blocker.

### Frontend

The raw static `frontend/` deploy model is correctly recognized by docs and workflow. Runtime config is generated during deploy and the verifier fails closed when public key material is missing. The frontend likely can consume the artifact once artifact JSON is valid. However, frontend trust labels and counts can be misleading if metadata count semantics remain inconsistent.

### Security

The project has meaningful security work: source URL validation, DNS/private-IP checks, sanitized logging, blocklists, API-key fail-closed behavior for admin routes, and ZIP secret scans. The current defects are more schema/identity/deploy-contract issues than obvious secret leaks. Remaining proof gaps: optional VirusTotal behavior, native binary checks, and broad DOM HTML construction cleanup.

### Documentation and Governance

The docs are unusually detailed and have machine-readable matrices. The problem is that historical ledgers are still easy to read as current truth. The current status should say something like: "repository remediation is mostly complete, but current scheduled/public artifact release is blocked by schema and workflow defects." That is more accurate than "production-ready" today.

## Prioritized Remediation List

1. Stop writing `lat`/`lng` into protocol `details`, or update schema with a deliberate public geo object.
2. Stop serializing revived chain IDs into top-level `uuid`; add `chain_id`/`id` fields or change schema deliberately.
3. Stop using top-level `uuid` for generic/naive usernames.
4. Change `validate_pages_artifact.py` to validate every proxy record, with capped error output.
5. Add `build_wasm` to `merge_results.needs` or make WASM optional with explicit frontend behavior.
6. Ensure hidden files survive `pipeline-output` artifact download if that artifact is reused downstream.
7. Clarify metadata count semantics: public records vs logical proxies vs working native proxies vs chain records.
8. Add workflow dependency validation for artifact producers/consumers.
9. Reconcile the four source-of-truth parts so historical material is fenced off from current operative truth.
10. Expand native-client proof from skipped evidence to pinned/reproducible checks if production claims require it.

## Bottom Line

The repo has a serious amount of remediation already done. But the latest artifact evidence and line-level code reading show the current system is not cleanly production-ready end to end. The immediate blockers are not vague: they are concrete field-contract violations, validator sampling, artifact dependency wiring, and ambiguous readiness claims. Fixing those would convert this from "strong codebase with a broken release edge" into a much more defensible production posture.

## Item-By-Item Implementation Update (2026-05-19)

Below is the explicit closure log for each high-signal item in this report.

### P0-1: `details.lat/lng` schema violation
- What I saw:
  - CI #680 exact error on unknown `details.lat`/`details.lng`.
  - Runtime write path in `src/configstream/consumer.py`.
- What I did:
  - Removed these writes from the consumer enrichment path.
- What was implemented:
  - `src/configstream/consumer.py` no longer injects `lat/lng` into protocol details.
- Status:
  - Implemented.

### P0-2: Revived chain IDs in top-level `uuid`
- What I saw:
  - `WARP-REVIVE-*` and `VWARP-REVIVE-*` emitted in `uuid`.
- What I did:
  - Decoupled chain identity from UUID output field.
- What was implemented:
  - `src/configstream/intelligence/washer/core.py` revived proxies now use `uuid=""`.
- Status:
  - Implemented.

### P0-3: Generic HTTP/SOCKS usernames serialized as UUIDs
- What I saw:
  - Generic parser wrote `parsed.username` into `uuid`.
- What I did:
  - Kept credentials in details; kept UUID empty for non-UUID protocols.
- What was implemented:
  - `src/configstream/parsers/generic.py` now stores username in `details["username"]`, `uuid=""`.
  - `tests/unit/test_parsers_generic_extended.py` updated accordingly.
- Status:
  - Implemented + tested.

### P0-4: Validator only checked first 50 proxies
- What I saw:
  - `scripts/validate_pages_artifact.py` used `payload[:50]`.
- What I did:
  - Expanded to full-array validation with bounded error reporting.
- What was implemented:
  - Full iteration across proxy payload plus capped error output.
- Status:
  - Implemented.

### P0-5: WASM artifact race in `main.yml`
- What I saw:
  - `merge_results` downloaded `frontend-wasm` while only needing `pipeline`.
- What I did:
  - Added hard dependency and policy check.
- What was implemented:
  - `.github/workflows/main.yml`: `merge_results.needs` includes `build_wasm`.
  - `scripts/validate_workflows.py`: new dependency-causality validation.
  - `tests/unit/test_validate_workflows.py`: reject/accept coverage added.
- Status:
  - Implemented + guarded by regression tests.

### P0-6: Hidden control files mismatch in downloadable artifact
- What I saw:
  - Evidence extraction can omit hidden control files used by Pages contract checks.
- What I did:
  - Forced artifact upload to include hidden files.
- What was implemented:
  - `.github/workflows/main.yml`: `include-hidden-files: true` on `pipeline-output` upload.
- Status:
  - Implemented.

### P1-7: Metadata/public-count ambiguity
- What I saw:
  - `metadata.total_proxies` diverged from public `proxies.json` row count.
- What I did:
  - Added explicit logical vs public count fields while preserving compatibility.
- What was implemented:
  - `src/configstream/output_handler.py`: returns `public_record_count/public_working_count`.
  - `src/configstream/output_logic.py`: emits logical/public counters separately.
  - `schema/metadata.schema.json`: schema updated for new fields.
- Status:
  - Implemented.

### P1-8: Serializer boundary lacked UUID contract enforcement
- What I saw:
  - Public serialization emitted raw `proxy.uuid`.
- What I did:
  - Added UUID-pattern normalization in serializer boundary.
- What was implemented:
  - `src/configstream/serialize.py`: `_public_uuid_value()` gate.
- Status:
  - Implemented.

### P1-9: Source-of-truth historical documents remained ambiguous
- What I saw:
  - Amendment/Part docs could be interpreted as active truth without explicit fencing.
- What I did:
  - Added supersession notes to mark historical/evidence context.
- What was implemented:
  - Updated:
    - `Main SOURCE OF TRUTH - Ammendment.md`
    - `Main SOURCE OF TRUTH - PART 2.md`
    - `Main SOURCE OF TRUTH - PART 3.md`
- Status:
  - Implemented.

### P1-10: Readiness messaging needed release-edge caveat
- What I saw:
  - Public wording could overstate active deploy readiness.
- What I did:
  - Adjusted wording to reflect gate-based readiness.
- What was implemented:
  - `README.md` language updated.
- Status:
  - Implemented.

### Verification summary for implemented work
- What I saw:
  - Needed post-change contract confidence.
- What I did:
  - Re-ran workflow/output/status/claim validators and focused pytest slices.
- What was implemented:
  - Validation/test evidence produced in the ongoing audit session.
- Status:
  - Completed; no new blocker surfaced in focused suites.
