# ConfigStream Master Source Of Truth

**Last updated:** 2026-05-28  
**Version:** v3.1.0  
**Scope:** Current project truth, release gates, current evidence, and non-negotiable contracts.  
**Repository state:** Production-ready as code. Repository publish gate is closed. Live GitHub Pages gate remains open until a fresh deploy passes live smoke.

This file and `STATUS.md` are the two current human-readable source-of-truth files. Detailed historical ledgers were moved to `docs/history/source-of-truth/` so they remain auditable without competing with current status.

## Executive Verdict

ConfigStream is production-ready at repository level. The codebase, validators, matrices, CI/release guardrails, source hygiene, dependency audits, frontend smoke coverage, artifact contract, and security checks have been reconciled for v3.1.0.

The live GitHub Pages site is not yet public-ready. It is stale relative to the repository and must be redeployed from current `main`; then the live deployment verifier must pass before any public Pages readiness claim is made.

The core distinction is:

- **Repository publish-ready:** closed.
- **Generated Pages artifact contract:** closed when run against a fresh `output/` tree.
- **Live public Pages readiness:** open until redeploy and live smoke pass.

## Truth Hierarchy

Use this hierarchy whenever status surfaces disagree:

1. `ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md`
2. `STATUS.md`
3. Canonical machine-readable contracts:
   - `docs/output_matrix.json`
   - `docs/protocol_matrix.json`
   - `docs/claim_ledger.json`
   - `docs/capability_registry.json`
   - `docs/core_compatibility_report.json`
   - `docs/module_ownership.json`
   - `docs/DEBT_MATRIX.md`
4. `CHANGELOG.md` for chronological implementation history.
5. `docs/history/source-of-truth/` for archived audit/evidence ledgers.

Archived history is evidence, not current operational truth. If an archived ledger conflicts with this file, `STATUS.md`, or canonical matrices, the current files win.

## Gate Matrix

| Gate | State | Current proof expectation |
|---|---|---|
| Repository production gate | Closed | Tests, validators, security scans, dependency audits, docs/matrix parity, and release workflow guards pass. |
| Public artifact contract | Closed for fresh generated artifacts | `scripts/validate_pages_artifact.py output` passes after output generation and frontend runtime-config injection. |
| Live Pages deployment | Open | Fresh GitHub Pages deploy from current `main`, then `scripts/verify_pages_deployment.py` passes against the public URL. |
| Public serialization safety | Closed | Root and categorized public proxy JSON use safe serialization and do not emit raw source URLs or internal-only fields. |
| Source/token hygiene | Closed for tracked content | Tracked source lists are scrubbed and `.gitleaks.toml` no longer allowlists source files. CI runs gitleaks/source-token checks; the working tree scans clean, so the only remaining step is removing `continue-on-error: true` from the CI gitleaks step (a one-line maintainer change requiring `workflows` permission). |
| Generated artifact hygiene | Closed | `output/`, `data/`, `invvest/`, and `Latest Outputs to investigate/` are ignored and not tracked. |
| Debt matrix reproducibility | Closed | `scripts/generate_debt_matrix.py --check` is non-mutating and excludes generated mirrors. |
| Dependency audit gate | Closed for reported direct advisories | Frontend lockfile and production direct dependency pins were refreshed; direct `pip-audit --no-deps` passes. |
| Mirror deployment parity | Closed | Vercel deploy runs from `output/`, matching the Pages/Netlify artifact shape. |
| Lab export safety | Closed for reported issues | Generated runners require preinstalled binaries and use safer config transport; auto-download/extract paths removed. |

## Concrete Project Map

This snapshot grounds the source of truth in the current repository shape as of 2026-05-28. Counts are descriptive, not eternal policy; if they drift, update this section or replace it with generated inventory.

### Repository Inventory

Current tracked inventory:

| Area | Count | Role |
|---|---:|---|
| `frontend/` | 385 | Raw static Pages application, frontend runtime, assets, service worker, Lab, analytics, public UI. |
| `tests/` | 183 | Unit, scenario, E2E, fuzz, and fixture coverage. |
| `src/` | 138 | Python package, pipeline, fetcher, parsers, output generation, server, security, washer, testing engines. |
| `docs/` | 59 | Machine-readable matrices, generated docs, historical ledgers, governance evidence. |
| `scripts/` | 48 | Validators, release gates, artifact checks, frontend smoke, source maintenance, mirror helpers. |
| `sources/` | 34 | Current tracked public source shards plus source documentation and backup state slated for cleanup. |
| `tools/` | 15 | Local/operator tooling, Lab helpers, worker examples, diagnostics. |
| `.github/` | 7 | CI, Pages deploy, release, retest, and mirror workflows. |

Current total tracked files: 909.

### Core Code Boundaries

| Boundary | Current canonical files | Contract |
|---|---|---|
| Pipeline orchestration | `src/configstream/pipeline.py`, `producer.py`, `consumer.py`, `pipeline_stats.py` | Streaming producer/consumer pipeline; bounded queues; no early output exit on zero working proxies; shutdown must close anomaly/test resources. |
| Fetch and source safety | `fetcher.py`, `fetcher_worker.py`, `http_client.py`, `security/transport.py`, `security_validator.py` | Remote source fetches are untrusted; defend against private-network fetches, redirect abuse, oversized payloads, hostile encodings, and log leaks. |
| Parsing and protocol normalization | `parsers/`, `converters/`, `models.py`, `docs/protocol_matrix.json` | Parser support, schema support, frontend support, and client export support are separate claims. |
| Output generation | `output_logic.py`, `output_handler.py`, `output_transport.py`, `generators/`, `serialize.py` | Public output must use safe serialization, atomic writes, manifest/hash tracking, degraded-valid semantics, and schema/client validators. |
| Testing engines and revival | `testers/`, `test_cache.py`, `intelligence/washer/core.py`, `tools/vwarp.py`, `warp_scanner.py` | Native sidecar/Python checks are authoritative; browser checks are hints; revived/shielded candidates must be counted honestly. |
| Public API/server | `server.py` | Serves public static/API/filter surfaces; API semantics must stay aligned with output matrix and public schemas. |
| Trust and publication | `signer.py`, `stego.py`, `scripts/validate_pages_artifact.py`, `scripts/verify_pages_deployment.py` | Public artifacts need freshness, hash, manifest, runtime-config, placeholder, and live-smoke proof. |
| Governance | `docs/*.json`, `docs/DEBT_MATRIX.md`, `STATUS.md`, this file | Human-readable truth and machine-checkable matrices must agree. |

Large modules that remain maintainability targets:

- `src/configstream/output_logic.py` is the main output-generation concentration point.
- `src/configstream/adapters.py`, `server.py`, `output_handler.py`, `consumer.py`, `fetcher.py`, and `producer.py` are large enough that future edits should prefer local extraction over more growth.
- `frontend/assets/js/i18n.js`, `lab.js`, `analytics.js`, `statistics.js`, and `proxies.js` are the largest frontend runtime files and should be split only behind tests/smoke coverage.

### Machine-Readable Contract Snapshot

| Contract | Current shape | Required upkeep |
|---|---|---|
| Protocol matrix | 38 entries: 21 canonical, 8 aliases, 5 schema-only, 4 internal. 29 public parser paths. 22 Sing-box export paths. 13 Clash export paths. | Any parser/export/frontend/schema change must update `docs/protocol_matrix.json` and relevant tests. |
| Output matrix | 42 output entries across universal, control, Sing-box, Clash, chains, chosen, side-products, frontend, API aliases, categorized API, analytics, docs, DNS-safe, DNS-hardened, and VPN families. | Any generated artifact addition/removal/semantic change must update `docs/output_matrix.json` and artifact validation. |
| Capability registry | 7 entries: 6 stable, 1 planned. | A stable capability requires owner, proof, docs, and tests. Planned entries must not be marketed as shipped. |
| Module ownership | 23 ownership rows. | New major modules, removed replacements, or import-boundary changes must update `docs/module_ownership.json`. |
| Schemas | `proxy`, `metadata`, `health`, and `artifact_manifest`. | Public JSON behavior must validate against schema or have an explicit validator family. |

### Frontend Surface Map

Current raw Pages entry points:

- `frontend/index.html`
- `frontend/proxies.html`
- `frontend/analytics.html`
- `frontend/lab.html`
- `frontend/lab-offline.html`
- `frontend/wiki.html`
- `frontend/about.html`
- `frontend/service-worker.js`
- `frontend/manifest.json`

Frontend runtime contracts:

1. Pages deploy copies raw `frontend/` into `output/` and injects generated runtime config. Vite build output is not the Pages source of truth.
2. Each HTML entry point must work with same-origin static data and explicit degraded states.
3. Large optional features such as globe, charts, analytics, Lab exporters, QR, and strategy data should be lazy or page-scoped when practical.
4. CSP tightening is a continuing objective. `unsafe-eval` is removed; remaining inline requirements should be retired through static bootstraps/templates.
5. `innerHTML` usage is allowed only where content is static, sanitized, or tightly controlled. New UI should prefer DOM builders or safe templating helpers.

### Workflow And Gate Map

| Workflow | Role | Critical truth |
|---|---|---|
| `.github/workflows/ci.yml` | Pull request and push checks | Runs Python matrix, dependency audit, Bandit, gitleaks action, validators, tests, flake8, mypy, black, frontend build/smoke. The gitleaks step is blocking-ready (working tree clean) and only needs `continue-on-error: true` removed to become a hard secret gate. |
| `.github/workflows/main.yml` | Data pipeline and artifact production | Keeps `ALLOW_ACTIVE_SCANNING=false`, prepares output, validates placeholders, validates Pages artifact, and uploads/deploys data artifacts. |
| `.github/workflows/deploy-pages.yml` | Pages publication | Injects runtime config, validates artifact, deploys Pages, then runs live deployment smoke. |
| `.github/workflows/release.yml` | Software release guard | Runs version/capability/compatibility/ownership validations before release activity. |
| `.github/workflows/deploy_mirror.yml` | Optional mirror deploys | Must deploy the validated `output/` shape, not repo root. |
| `.github/workflows/retest.yml` | Retest workflow | Must preserve active-scanning policy and not mutate source truth unexpectedly. |

Blocking vs advisory rule:

- **Blocking gates** must fail CI/release/deploy if violated.
- **Advisory checks** may run in CI but cannot be cited as blocking proof.
- If a check uses `continue-on-error`, this file must describe it as advisory or transitional, not closed blocking proof.

### Validation Command Catalog

Use these as the concrete local proof commands for bookkeeping/source-truth changes:

```bash
py -3.13 -m black --check .
py -3.13 scripts/validate_status.py
py -3.13 scripts/generate_debt_matrix.py --check
py -3.13 scripts/validate_claim_ledger.py
py -3.13 scripts/validate_capability_registry.py
py -3.13 scripts/validate_module_ownership.py
py -3.13 scripts/validate_output_matrix.py
py -3.13 scripts/validate_protocol_matrix.py
py -3.13 scripts/validate_workflows.py
py -3.13 -m pytest tests/unit/test_documentation_hygiene.py tests/unit/test_validate_status.py tests/unit/test_debt_matrix.py tests/unit/test_validate_claim_ledger.py -q
```

Use these for publish/artifact work:

```bash
npm ci
npm run build:sanity
npm run test:frontend:no-network
npm run test:frontend:degraded
py -3.13 scripts/validate_frontend_placeholders.py --inject-env --strict output
py -3.13 scripts/validate_pages_artifact.py --refresh-contract output
py -3.13 scripts/verify_pages_deployment.py <public-pages-url> --timeout 120 --report-file output/pages_deployment_smoke.json
```

Use these for security/release hardening:

```bash
bandit -r src/configstream scripts tools frontend/assets/js -q
gitleaks detect --config .gitleaks.toml --source .
pip-audit -r requirements-prod.txt --format json
npm audit --audit-level=moderate
py -3.13 scripts/check_dependency_drift.py
```

If a command cannot be run locally, the status update must say so explicitly and name the missing environment requirement.

### Definition Of Done By Work Type

Use this table to keep future changes from creating hidden documentation or contract drift.

| Work type | Must update | Must prove |
|---|---|---|
| Parser/protocol change | Parser tests, `docs/protocol_matrix.json`, schema if public fields change, frontend/Lab docs if user-visible. | Golden URI/config cases, malformed input cases, credential fallback cases, protocol alias normalization, export compatibility where claimed. |
| Public proxy field change | `schema/proxy.schema.json`, `serialize.py`, output matrix notes if artifact semantics change, frontend consumers, changelog. | Root `proxies.json`, `api/proxies`, `countries/*.list.json`, and `protocols/*.list.json` all validate and mask secrets consistently. |
| Output artifact change | `docs/output_matrix.json`, `scripts/validate_pages_artifact.py`, docs/wiki/README if user-facing, release workflow if deployed. | Artifact exists or is explicitly optional, degraded behavior is valid, manifest/hash entries are correct, aliases match canonical files. |
| Frontend page/runtime change | Raw `frontend/` files, frontend smoke tests, CSP if scripts/styles/network behavior change, runtime-config/placeholder validator if deploy-time data changes. | `npm run build:sanity`, same-origin smoke, degraded/no-JS smoke where relevant, no placeholder leaks, no unexpected external network calls. |
| Lab import/export/diagnostic change | `frontend/assets/js/lab.js` or future Lab modules, Lab strategy data, CSP, export tests, safety docs. | User-clicked diagnostics only, no silent active scanning, no unverified binary install, safe script interpolation, QR/export secrets handled locally. |
| Pipeline/fetch/tester change | Unit/scenario tests, timeout/concurrency tests, logs, stats/metadata if counters change. | No event-loop blocking in async paths, bounded queue behavior, graceful timeout/degraded outputs, sanitized logs, cache/daemon lifecycle correctness. |
| Security policy change | `.gitleaks.toml`, Bandit/pip/npm audit config, CI workflow, `SECURITY.md` or docs if operator-facing. | Scan passes locally or CI evidence exists, allowlists are narrow, advisory vs blocking status is declared honestly. |
| Release/deploy workflow change | Workflow validator, output matrix if artifact shape changes, status/master if gates change. | Fresh artifact validation, optional mirror parity, Pages deploy smoke for public readiness, no conflation of data and software releases. |
| Documentation/source-truth change | This file, `STATUS.md`, changelog if completed work moved there, historical archive links if files move. | `validate_status`, debt check, claim ledger validation, documentation hygiene tests. |
| Cleanup/pruning change | Ownership map if module boundaries move, tests imports, docs links, changelog. | Removed files are not imported, generated mirrors are not tracked, behavior remains covered by tests. |

### Current Gap Register

These are not all release blockers. They are the concrete gaps or cleanup fronts that still deserve explicit tracking so they do not turn into hidden drift.

| Gap | Severity for repository publish | Why it matters | Desired closure |
|---|---|---|---|
| Live GitHub Pages freshness | Blocks public Pages readiness | Public site can remain stale even when repository and artifact validators pass. | Fresh deploy from current `main`, then `verify_pages_deployment.py` passes against the public URL. |
| Gitleaks blocking flip | Hardening gap (one line) | The scan is wired and the working tree scans clean, but `continue-on-error: true` keeps it non-fatal in CI. | A maintainer with `workflows` permission removes `continue-on-error: true` from the `ci.yml` gitleaks step; automation agents cannot edit workflow files. |
| Source-list truth split | Maintainability/security cleanup | `consolidated_sources.txt`, `sources/batch_*.txt`, and `sources/backup_dynamic/` create avoidable ownership ambiguity. | Choose one authored source manifest/list, generate shards/backups, keep private overrides ignored. |
| Large output module | Maintainability cleanup | `output_logic.py` concentrates many unrelated output families and makes contract drift harder to review. | Extract public lists, native client configs, metadata/health, side-products, chosen outputs, and manifest helpers behind tests. |
| Large Lab runtime | Frontend/security cleanup | Lab parsing, strategy building, diagnostics, exporters, QR, UI state, and safety-sensitive script generation are mixed. | Split into parser, strategies, diagnostics, exporters, and UI modules with targeted tests. |
| Frontend inline/CSP debt | Security hardening | Remaining `unsafe-inline` and broad dynamic DOM construction keep XSS review cost high. | Move inline bootstraps/styles to static files and prefer safe DOM builders/templates. |
| Duplicated docs/wiki surfaces | Documentation cleanup | Mirrored docs trees can drift silently. | Keep one authored doc tree and generate mirrors, with docs-sync validation. |
| Release gate duplication | CI maintainability cleanup | Multiple workflows repeat similar validator sequences with slightly different semantics. | Centralize release/page/data gate orchestration in a small script or reusable action. |
| Native-core proof depth | Evidence hardening | Static validators prove structure but not full native runtime acceptance under every client. | Add pinned native dry-run/check jobs for Sing-box and any future first-class native output. |
| Full dependency audit sensitivity | Environment caution | Direct `pip-audit --no-deps` can pass while full resolution depends on supported Python matrix and resolver state. | Keep full audit in CI matrix and document any accepted transitive advisories with expiry. |

### Blocking Gate Maturity Levels

Every validator/check should be assigned one of these maturity levels in docs and CI comments:

| Level | Meaning | May support readiness claim? |
|---|---|---|
| Informational | Runs manually or produces reports only. | No. It can guide work but cannot prove readiness. |
| Advisory CI | Runs in CI but is non-fatal or allowed to fail. | Only as supporting evidence, never as a blocking proof. |
| Blocking CI | Fails pull request/push/release when violated. | Yes, for the surface it covers. |
| Deploy blocking | Fails artifact deployment or release publication. | Yes, for the deploy/release surface it gates. |
| Live proof | Runs against the public deployed URL/artifact. | Yes, for public-readiness claims only when fresh and retained. |

Current maturity notes:

- Bandit expanded scan is blocking in CI.
- `pip-audit -r requirements-prod.txt --format json` is blocking in CI.
- Gitleaks is blocking-ready: the working tree scans clean and PR runs scan the bounded PR commit range, so removing `continue-on-error: true` is a safe one-line maintainer flip to make it a blocking gate.
- Pages artifact validation is deploy blocking.
- Live Pages smoke is live proof and is the only gate that can close public Pages readiness.

## Non-Negotiable Contracts

### Release And Deployment

1. Public Pages readiness requires live proof for `health.json`, `metadata.json`, `artifact_manifest.json`, `base64.txt`, `chosen/base64.txt`, `proxies.json`, `api/proxies`, `api/stats`, frontend rendering, placeholder absence, manifest/hash parity, and deployment freshness.
2. Raw local `output/`, generated Pages artifacts, live Pages, software releases, and data releases are different states. Passing one does not imply the others pass.
3. Raw static `frontend/` is the canonical Pages input. Vite remains a local build/sanity check unless the output contract is deliberately changed.
4. Runtime frontend secrets/config are generated during artifact preparation; placeholder keys must not ship.
5. Optional mirrors are optional, secret-gated, and must deploy the same validated `output/` artifact shape.

### Security And Privacy

1. Public JSON must not expose raw source URLs, source tokens, proxy credentials, UUID secrets, deployment secrets, local paths, or internal-only fields.
2. Public root proxy JSON and categorized country/protocol list JSON must use the same safe serializer contract.
3. Logs must be sanitized for source URLs, proxy credentials, UUIDs, tokens, endpoints, DNS errors, subprocess output, parser drops, tester/cache endpoints, and converter failures.
4. Active scanning is disabled in CI and default automation. Scanner and Laboratory diagnostics are user-initiated, opt-in local tooling.
5. CI security coverage must include `src/configstream`, `scripts`, `tools`, frontend JavaScript, source files, and release workflows.

### Output Semantics

1. The pipeline must generate artifacts even when zero proxies test as working.
2. Metadata and UI must distinguish working proxies, candidates, revived candidates, shielded candidates, and retested shielded proxies.
3. Untested shielded chains are candidates and must not inflate working totals.
4. `docs/output_matrix.json` is the public artifact inventory. Every public artifact family must be represented or explicitly generated under a validated family rule.
5. `countries/*.list.json` and `protocols/*.list.json` are public API surfaces and must remain schema-compatible with `proxies.json`.

### Governance

1. A feature claim is complete only when implementation, tests, docs, matrices, generated artifacts, CI/deploy workflows, changelog, and evidence describe the same contract.
2. Historical completion claims are not current truth unless they are restated in this file, `STATUS.md`, or canonical matrices.
3. Completed implementation detail belongs in `CHANGELOG.md`; current status files should explain the present contract and proof state.
4. The source-of-truth layer must stay clean: no duplicate root ledgers, no competing roadmaps, no unresolved historical claims mixed into current status.
5. Roadmap prose is advisory until it becomes a registered capability, issue, matrix entry, or tested implementation.
6. Each public/user-facing feature needs an explicit owner surface: backend behavior, frontend behavior, CLI/tooling behavior, API/output contract, docs, tests, and release gate.

## Absorbed Source Ledgers

This section is the explicit absorption pass over the four original source-of-truth files. It records what survives as current policy and what stays archived as historical detail.

### Original Master Audit Report

Archived file:

- `docs/history/source-of-truth/ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.full.md`

Durable value absorbed:

1. **Completion doctrine.** A feature is not complete because code exists. It is complete only when implementation, tests, schemas, generated artifacts, frontend wording, CI/deploy workflows, docs, changelog, and evidence all describe the same behavior.
2. **Separate readiness states.** Repository readiness, generated artifact readiness, live Pages readiness, software release readiness, data release readiness, and mirror readiness are distinct gates.
3. **Canonical matrix model.** Protocol, output, claim, capability, compatibility, module ownership, and debt matrices are the machine-checkable truth under the human-readable master/status layer.
4. **Degraded-output honesty.** Zero-working or failed network runs may still publish candidate artifacts, but metadata and UI must not inflate or mislabel those candidates as verified working capacity.
5. **Frontend deploy reality.** Raw static `frontend/` remains the Pages input; Vite is a sanity/build check unless the output contract is intentionally changed.
6. **Active-scanning boundary.** CI and scheduled automation must not perform project-operated active scanning of third-party infrastructure; scanner/Lab diagnostics are user-run and opt-in.
7. **Debt discipline.** The debt matrix must distinguish real production/frontend/tooling debt from accepted tests, docs/history text, and false positives.
8. **Pages proof chain.** Public readiness requires live proof of runtime config, health, manifest, metadata freshness/hash fields, API aliases, frontend rendering, placeholder absence, and hash parity.

Archived only:

- Old inventory counts, old pass counts, old closure dates, stale live Pages observations, and old "all closed" phrasing where those details conflict with the current 2026-05-28 status.
- Long item-by-item remediation transcripts that are now implementation history rather than current operating policy.

### Part 2 Expansion Ledger

Archived file:

- `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 2.md`

Durable value absorbed:

1. **Feature-contract-first rule.** New work must start by defining the user-facing behavior, output/API shape, degraded behavior, security posture, test profile, docs impact, matrix updates, and rollback/deprecation plan.
2. **Capability registry.** Stable/partial/planned/experimental/deprecated capabilities must be explicit and proof-backed. This is now enforced through `docs/capability_registry.json`.
3. **Module ownership map.** Major modules, public APIs, removed-module replacements, and import boundaries must be explicit. This is now enforced through `docs/module_ownership.json`.
4. **Source ingestion safety.** Source acquisition remains one of the highest-risk areas. Fetch policy must defend against private-network access, redirect abuse, oversized payloads, decompression hazards, hostile encodings, binary junk, and secret leakage.
5. **Parser contract.** Parsers handle hostile/malformed input, record drop statistics where appropriate, recover credentials only through documented fallbacks, and keep import/export support distinct per protocol.
6. **Protocol/export parity.** "Supported protocol" does not mean "exported to every client." Parse support, validation support, Sing-box export support, Clash export support, URI support, and Lab support must remain separate matrix fields.
7. **Secret and credential safety.** Proxy configs contain secrets by design. They must not leak through logs, public JSON, screenshots, browser exports, QR generation, release bundles, or debug/evidence artifacts.
8. **Tester abstraction.** Go sidecar, Python fallback, browser/WASM reachability checks, and future test engines have different authority levels. Native sidecar/Python test results are authoritative for real proxy behavior; browser checks are environmental hints.
9. **Revival lifecycle model.** Revived, washed, shielded, candidate, verified, and working are separate states. Untested or failed-retest chains can remain useful candidates but must not count as working.
10. **DNS/evasion hardening.** DNS cache, private-IP policy, evasion profiles, and WARP/Vwarp chain behavior must remain policy-bound rather than ad hoc.
11. **Output transaction model.** Public artifact generation should be atomic, schema-backed, and manifest/hash tracked. Partial outputs must be explicit rather than silently published as complete.
12. **Signed manifests and trust labels.** Public users need freshness, integrity, and trust-state signals; the UI must distinguish signed, unsigned, stale, degraded, candidate, and verified states.
13. **Lab safety and usability.** Lab sessions, guided wizard behavior, visual chain building, config linting, export packs, local QR generation, live-test sandboxing, and explainable failures are valuable but must remain bounded by privacy/security policy.
14. **Offline/degraded UX.** Offline Lab and static Pages behavior are first-class constraints; loading JSON strategy data or heavy assets must not break the no-server/static-file baseline without an explicit fallback.
15. **Observability taxonomy.** Reports should distinguish fetch policy blocks, parser drops, validation drops, tester failures, timeout classes, source quality, and degraded output reasons.
16. **Release/data-release split.** Software releases and data releases have different contracts. A tag or package release does not prove the current data artifact, and a data artifact does not prove the software release.
17. **Testing profiles.** Unit, parser, output-contract, frontend, security, release, live-smoke, native-core, visual, and full gates should remain named profiles rather than one vague "tests passed" claim.
18. **Future roadmap shaping.** High-value future work should be grouped into contracts, pipeline correctness, quality/intelligence, Lab, outputs, performance/robustness, security/release maturity, and docs/governance.

Archived only:

- Specific proposed features that are not currently implemented or registered as stable capabilities, including broad plugin architecture, recommendation engine, personal profile generator, community source submission flow, and other expansion ideas.
- Old build-order text when it conflicts with the current status or matrices.

### Part 3 Client-Config Ledger

Archived file:

- `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 3.md`

Durable value absorbed:

1. **Dataset vs native config distinction.** `proxies.json` is the canonical public dataset array, not a Sing-box config and not an Xray config.
2. **Sing-box namespace.** Sing-box uses top-level `route`, `inbounds`, `outbounds`, `dns`, and outbound `type` semantics. It must not be described with Xray's `routing`/`protocol` model.
3. **Xray namespace.** Xray uses top-level `routing`, outbound `protocol`, `settings`, and `streamSettings`. Xray JSON is not a first-class pipeline output until it has dedicated generator, validator, matrix entries, native checks, docs, and release artifacts.
4. **Core output families.** Sing-box and Clash are current pipeline output families. Xray is currently a Lab/export surface unless promoted through the full output-family contract.
5. **Remote rule-set caution.** Native client config validation must account for remote rule-set/network assumptions; semantic/static validation is useful but not complete native-core proof.
6. **Naming clarity.** Files named `chains.json`, `singbox-chains.json`, `proxies.json`, `api/proxies`, and client configs must remain semantically distinct in docs and UI.
7. **Protocol caveats.** Some parsed protocols cannot be exported to every client config family. The protocol matrix must show those limits instead of flattening them into generic support.
8. **Validator requirements.** Sing-box, Clash, dataset JSON, categorized list JSON, and any future Xray output need separate validators appropriate to their real format.

Archived only:

- Any statement that claims Xray is already a public pipeline output family.
- Old "immediate action" wording already superseded by current output-matrix and serializer work.

### Amendment Ledger

Archived file:

- `docs/history/source-of-truth/Main SOURCE OF TRUTH - Ammendment.md`

Durable value absorbed:

1. **Do not overclaim readiness.** Public-readiness language must follow live evidence, not optimism or local-only validation.
2. **Evidence state model.** A "latest output folder" is not automatically a deployable artifact. The audit must distinguish source tree, Actions artifact, Pages-mutated artifact, live deployment, optional mirrors, screenshots, and retained reports.
3. **Artifact retention caution.** Short-retention CI artifacts and local folders are useful evidence only while available; durable public claims need durable manifests/reports or live smoke.
4. **Screenshot/UI evidence caution.** Frontend screenshots are supportive proof, not current truth unless generated from the same artifact/deploy state being claimed.
5. **Document hierarchy.** Root truth, status, matrices, changelog, wiki/docs, and historical evidence must have different jobs. Competing root truth files are a maintenance hazard.
6. **Debt as a blocker class.** Debt markers are not cosmetic when they occur in production/frontend/tooling paths. The scanner must classify and reproduce the debt state.
7. **Private IP policy split.** Fetch-source private-network protections and proxy-validation compatibility settings are different controls and must be documented separately.
8. **Release workflow ambiguity.** Scheduled data releases, Pages deploys, package releases, Docker/native artifacts, and mirrors must not be merged into one undifferentiated release claim.
9. **Trust-state correction.** Failed/zero-working outputs, revived candidates, shielded candidates, and verified working proxies must be rendered differently.
10. **One-chain rule.** The project should maintain one source-of-truth chain, one output contract, one frontend deploy path, one release policy, one durable latest-output evidence model, and one live deployment proof chain.

Archived only:

- Old pre-remediation status language from before repository remediation closed.
- Old PR references, old line counts, old debt marker counts, and stale examples retained only to explain why the current contracts exist.

## Granular Operating Contracts

This section turns the absorbed ledgers into practical operating rules for future work. It is intentionally detailed: it should prevent the same classes of drift from returning.

### Source And Ingestion Contract

Current rules:

1. Tracked source lists must never contain live-looking user tokens, subscription credentials, bearer tokens, private query strings, or provider-specific secrets.
2. User-provided private feeds belong in local ignored inputs, CI secrets, or documented operator inputs, not in tracked repository source lists.
3. Fetching remote sources is separate from validating proxy endpoints. Fetch safety defaults protect the runner from SSRF/private-network/redirect abuse even if proxy validation later allows private or insecure proxy candidates for compatibility.
4. Source fetch logs must identify sources by sanitized label, hash, or host-level summary. They must not print full URLs with query strings.
5. Source quality metrics should be aggregate and privacy-preserving: success rate, parse yield, drop reasons, freshness, timeout rate, and last-seen summary are acceptable; raw subscription URLs are not.
6. Batch shards should be treated as distribution artifacts unless explicitly chosen as the canonical source-list truth.

Recommended target shape:

- one authored source list or source manifest,
- generated shards for CI load balancing,
- ignored local/private source override files,
- CI source-token scan over every tracked source-like file,
- documentation that explains how users add private feeds without committing secrets.

### Parser And Protocol Contract

Current rules:

1. Parsers accept hostile input and fail closed per line, not per file. One malformed record must not crash a batch.
2. Credential fallback is protocol-specific and must be tested. For VLESS, VMess, Trojan, and Shadowsocks, fallback from path/userinfo/query fields is allowed only where the protocol parser explicitly supports it.
3. Missing required credentials remain fatal after fallback attempts.
4. Drop statistics are part of observability. Parser changes should preserve reason categories where practical.
5. Protocol aliases must normalize to canonical protocol names before public output.
6. The protocol matrix must distinguish at least these concepts:
   - parse support,
   - validation support,
   - URI/link export support,
   - Sing-box export support,
   - Clash export support,
   - Lab import/export support,
   - native dry-run proof where available.
7. Claims like "20+ protocols" mean matrix-backed parse/support coverage, not universal native output parity.

### Public Serialization Contract

Current rules:

1. `serialize_proxy()` is the public proxy record contract.
2. Root `proxies.json`, `api/proxies`, `countries/*.list.json`, and `protocols/*.list.json` must serialize through the same public contract.
3. Public `source` is a sanitized label/ref, not the raw source URL.
4. Internal-only details, exact source URLs, source query strings, local file paths, and raw credential material must not enter public dataset JSON.
5. Invalid internal UUID/password shapes may exist transiently only before validation/serialization. Public JSON must satisfy the published schema.
6. Adding a public field requires:
   - schema update,
   - output matrix update if artifact semantics change,
   - frontend compatibility check,
   - regression test,
   - changelog entry if user-visible.

Regression expectations:

- tokenized source URL serializes without query token leakage,
- country and protocol list records match root proxy public shape,
- empty/invalid UUID internals do not produce schema-invalid public JSON,
- `details` remains contract-bounded and does not collect accidental model internals.

### Output Family Contract

Public output families are not interchangeable.

Dataset/API outputs:

- `proxies.json`
- `api/proxies`
- `countries/*.list.json`
- `protocols/*.list.json`
- `metadata.json`
- `health.json`
- `artifact_manifest.json`
- `api/stats`

Subscription text outputs:

- `base64.txt`
- `proxies.txt`
- `chosen/base64.txt`
- `chosen/proxies.txt`

Native client config outputs:

- Sing-box JSON families,
- Clash YAML families,
- any future Xray output only after promotion through generator, validator, matrix, native proof, docs, and release artifact rules.

Rules:

1. Dataset/API JSON validates against dataset schemas, not native client schemas.
2. Native client configs validate against their own native semantics where possible.
3. Degraded runs may produce empty text subscriptions, but control JSON and manifests must remain coherent.
4. `chosen/*` is a selected subset family and must not be mistaken for full dataset output.
5. Country/protocol files include all matching proxies unless the output matrix explicitly changes that contract.
6. Every public artifact path must be covered directly or by a documented family rule in `docs/output_matrix.json`.

### Pages And Mirror Contract

Pages artifact assembly must be deterministic enough to audit.

Required Pages artifact ingredients:

- raw static frontend files,
- generated runtime config,
- public output files,
- API aliases,
- `health.json`,
- `metadata.json`,
- `artifact_manifest.json`,
- no placeholder key material,
- no generated cache/private debug files,
- no source-token-bearing artifacts.

Live Pages readiness requires:

1. artifact validation before deploy,
2. deploy from the validated artifact,
3. public smoke after deploy,
4. manifest/hash parity against public files,
5. freshness checks based on metadata/health, not stale local assumptions,
6. frontend render smoke that catches stale/degraded mislabeling.

Mirror rules:

- Netlify, Vercel, IPFS, Hugging Face, Google Drive, Telegram, or any other mirror must either deploy the same validated `output/` shape or document a narrower validated mirror contract.
- Optional mirrors are not readiness blockers unless they are advertised as current public surfaces.
- Mirror workflows must not publish the repository root by accident.

### Frontend And Lab Contract

Frontend current contract:

1. The public site is a raw-static app. It must not require a server-rendered framework to load.
2. Vite build sanity can catch frontend regressions, but Vite output is not the Pages source.
3. CSP should move toward no `unsafe-inline`; any temporary inline allowance must stay deliberate and tested.
4. `innerHTML` use must be treated as high-review code, even when content is controlled.
5. Trust and freshness labels must not imply live verification when data is stale, degraded, unsigned, candidate-only, or locally loaded.

Lab current contract:

1. Lab diagnostics are user-clicked and environment-specific. They are not authoritative proxy validation.
2. Browser/WASM checks are browser-limited reachability checks.
3. Sidecar/Python test results remain authoritative for real proxy behavior.
4. Generated runners must avoid shell injection, unsafe temp-file patterns, unverified archive extraction, and silent binary installation.
5. QR generation must be local and must not send configs to third-party QR services.
6. Lab exports may include secrets because client configs require secrets; the UI and docs must make that explicit.
7. Lab strategies are governed by `frontend/assets/data/lab_strategies.json`.
8. The Lab should be split into parser, strategy, diagnostics, export, and UI modules when next touched substantially.

### Security And Supply-Chain Contract

Required coverage:

1. Bandit or equivalent static checks cover Python code under `src/configstream`, `scripts`, and `tools`.
2. Frontend generator and export logic are included in security review because generated scripts are user-run code.
3. Gitleaks/source-token scanning covers source lists and source-like templates.
4. Dependency audits run for the frontend lockfile and production Python dependencies.
5. Direct and transitive dependency findings must be tracked separately when environment resolution differs.
6. CI must not rely on local pre-commit hooks for mandatory security gates.
7. Allowlist rules must be narrow, documented, and reviewed. Broad allowlists for high-risk source directories are not acceptable.

Supply-chain posture:

- zero-budget dependencies are acceptable only if they do not introduce paid infrastructure assumptions,
- vendored browser libraries must be documented and hash/provenance tracked where practical,
- generated runners must prefer preinstalled trusted binaries or explicit user-managed installation,
- remote binary auto-install requires checksum/signature validation and safe archive extraction before it can return.

### Documentation Contract

The documentation set has distinct jobs:

1. Master source of truth: current gates, contracts, evidence model, durable policy.
2. `STATUS.md`: latest checkpoint and concise current state.
3. `CHANGELOG.md`: completed implementation history.
4. Matrices: machine-readable claims and artifact/protocol/capability truth.
5. Wiki/docs: user/operator guidance and architecture explanation.
6. `docs/history/source-of-truth/`: archived evidence only.

Rules:

- Do not put long remediation transcripts back into root truth files.
- Do not delete archived evidence just because it is stale; label it and keep it out of current status.
- Do not cite archived claims as current unless they are restated in active files.
- When source truth changes, update `AGENTS.md` and `README.md` if their status banners would otherwise drift.
- Completed work should move to `CHANGELOG.md`; open gates should stay in Master/STATUS.

### Maintainability And Pruning Contract

The highest-value cleanup should reduce future review burden without changing user-visible behavior accidentally.

Priority pruning targets:

1. duplicate source-list surfaces,
2. tracked source backups,
3. historical ignore tombstones,
4. large monolithic output generation logic,
5. monolithic Lab JavaScript,
6. large shared CSS without clear design layers,
7. repeated CSP/script lists across HTML pages,
8. inline bootstraps that force `unsafe-inline`,
9. broad `innerHTML` render patterns,
10. test files organized by historical incident rather than enduring contract.

Pruning rules:

- remove or move only after identifying the owner and current proof surface,
- keep behavior-preserving changes separate from contract changes,
- add or update validators when deleting a class of artifact/drift,
- prefer generated artifacts over duplicated hand-maintained mirrors,
- keep archived historical evidence but exclude it from scanners that measure current debt.

## Current Remediation State By Area

### Document Consolidation And Historical Evidence

Current shape:

- Root current truth is limited to this file and `STATUS.md`.
- Long historical ledgers are preserved under `docs/history/source-of-truth/`.
- Completed implementation details belong in `CHANGELOG.md`.
- Machine-verifiable claims belong in matrices and ledgers under `docs/`.

What changed in this bookkeeping pass:

- The previous root addenda files were moved out of the project root:
  - `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 2.md`
  - `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 3.md`
  - `docs/history/source-of-truth/Main SOURCE OF TRUTH - Ammendment.md`
- The previous long-form master report was archived as:
  - `docs/history/source-of-truth/ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.full.md`
- The new root master keeps current truth, release gates, proof expectations, closed/open classes, and next cleanup work.

Why this matters:

The old documents were useful but mixed current truth, historical evidence, resolved findings, future roadmap items, and stale warnings. Keeping all of that at root made it too easy to re-open closed issues mentally or accidentally cite old status as current. The new layout keeps depth available while making the operational truth unambiguous.

### Completion Doctrine

The original master report's most important rule remains active:

> Do not add feature claims faster than the project can prove them.

In current terms, a capability is complete only when all applicable proof surfaces align:

- implementation paths exist and are owned,
- unit/integration/frontend/native checks exist where relevant,
- generated artifacts match schemas and output matrix semantics,
- frontend labels match backend metadata semantics,
- release/deploy workflows enforce the same contract,
- docs and `CHANGELOG.md` describe the same behavior,
- live public evidence exists when a public deployment claim is made.

This doctrine applies especially to output formats, security claims, Lab capabilities, active scanning boundaries, Pages readiness, optional mirrors, and native client compatibility.

### Artifact State Model

The archived amendment repeatedly warned that "latest output" is not one thing. That warning remains current policy.

ConfigStream has at least five artifact states:

1. **Source tree:** tracked repository files.
2. **Raw pipeline output:** local or CI-generated `output/` before Pages mutation.
3. **Pages artifact:** raw `frontend/` plus generated API aliases, runtime config, health, manifest, and public output files.
4. **Live Pages deployment:** what users actually fetch after GitHub Pages deploy/cache behavior.
5. **Optional mirrors:** Netlify, Vercel, IPFS, Hugging Face, Google Drive, Telegram, or other secret-gated mirrors.

Required rule:

- A pass in one state does not prove any other state.
- Live public readiness requires live public smoke, not only local validators.
- Optional mirrors must publish the same validated artifact shape as Pages unless they have a documented, validated alternate contract.

### Pages Readiness Contract

Live Pages can be marked ready only after the public URL passes all required smoke checks. The live smoke must verify:

- primary HTML entry points load,
- `assets/js/runtime-config.js` exists and contains non-placeholder runtime key material when required,
- `health.json` exists and identifies the run,
- `artifact_manifest.json` exists and hashes required public artifacts,
- `metadata.json` includes freshness and `proxies_snapshot_hash`,
- `proxies.json` parses and follows public schema,
- `api/proxies` is an alias-compatible public API response,
- `api/stats` is present and coherent,
- `base64.txt` and `chosen/base64.txt` follow degraded-output rules,
- placeholder markers are absent from deployed JavaScript,
- manifest hash parity holds for tracked public files,
- frontend renders without stale/degraded mislabeling.

Current state:

- Repository-side artifact preparation and validation exist.
- Live public site is still stale/incomplete until a fresh deploy proves otherwise.

### Protocol And Client-Config Boundary

Part 3's core correction remains a live contract:

- `proxies.json` is a ConfigStream dataset/API artifact.
- `proxies.json` is not a native Sing-box config.
- `proxies.json` is not a native Xray config.
- Sing-box uses top-level `route` and outbound objects with `type`.
- Xray uses top-level `routing` and outbound objects with `protocol`, `settings`, and `streamSettings`.
- Sing-box, Clash, Xray, and dataset JSON must not be described as interchangeable.

Current state:

- Sing-box and Clash pipeline artifacts are stable output families.
- Xray remains a planned/non-pipeline output family unless and until generator, validator, native proof, docs, and output matrix semantics are added.
- Lab-only exports must not be overclaimed as pipeline-public output families.
- `docs/core_compatibility_report.json` is the machine-readable compatibility truth.

### Capability And Ownership Governance

Part 2's governance items were not just roadmap prose. They are now active contracts:

- `docs/capability_registry.json` tracks stable, partial, planned, experimental, deprecated, and removed capabilities.
- `scripts/validate_capability_registry.py` prevents stable capabilities from lacking proof.
- `docs/module_ownership.json` maps major modules, ownership boundaries, public APIs, internal APIs, removed-module replacements, tests, and docs.
- `scripts/validate_module_ownership.py` prevents removed modules and stale removed-module imports from returning.
- `docs/claim_ledger.json` links implemented claims to proof surfaces.

Current implication:

Future cleanup should update these machine contracts whenever ownership, output families, public capabilities, or removed-module boundaries change.

### Public Serialization And Output Contract

Closed:

- `serialize_proxy()` no longer publishes raw `details._source` values into public `source`.
- Country list and protocol list JSON now use the safe serializer rather than raw `model_dump()`.
- `docs/output_matrix.json` includes categorized public API families for country and protocol list JSON.
- Artifact validation covers categorized list schema parity.

Why this matters:

The previous risk was a split public contract: root `proxies.json` could be safe while `countries/*.list.json` or `protocols/*.list.json` leaked internal fields or schema-invalid credential shapes. The repository contract now treats all public proxy-list JSON as one public serializer surface.

### Source Hygiene

Closed:

- Tracked source lists were scrubbed of tokenized subscription query values.
- `.gitleaks.toml` no longer allowlists source lists as a blind spot.
- CI includes source-token/secret scanning. The gitleaks workflow step is blocking-ready; flipping it to blocking only requires removing `continue-on-error: true` from `ci.yml`.
- Source leakage through public serialized output is blocked by serializer sanitization.

Current cleanup opportunity:

The repo still has two source-list truth surfaces: sharded `sources/batch_*.txt` and `consolidated_sources.txt`. It also keeps `sources/backup_dynamic/` tracked. These are not current P0 blockers, but they are prime maintainability cleanup targets.

Desired final shape:

- one canonical source-list input,
- generated shards or mirrors if needed,
- runtime/CI backups ignored or archived as CI artifacts,
- source-token scan covering all tracked source-like files.

### Generated Artifact Hygiene

Closed:

- Stale tracked output mirrors and ZIPs were removed from version control.
- Generated artifact paths are ignored.
- Debt scanning excludes generated/mirror artifact trees.
- Repo inventory is no longer polluted by old `invvest/` and latest-output mirrors.

Current cleanup opportunity:

`.gitignore` still contains many specific historical artifact entries under broader ignored directories. It can be collapsed to improve readability after confirming ignore coverage remains equivalent.

Generated artifacts must never become source-of-truth evidence by being committed back into the repository. Durable evidence should be small, structured, hash-addressed, and retained as CI artifacts or summarized reports.

### Debt Matrix

Closed:

- `scripts/generate_debt_matrix.py --check` is a real non-mutating check mode.
- Generated artifact mirrors are excluded.
- Current debt matrix claims are reproducible.

Current cleanup opportunity:

The debt scanner carries many false-positive rules because old status/history text used to be scanned. With history moved and current truth cleaned, the exclusion set can be simplified in a follow-up.

Debt categories that remain useful:

- production defect,
- frontend/user-facing defect,
- tooling defect,
- docs/history marker,
- accepted test mock,
- accepted placeholder text,
- false positive.

The "zero actionable debt" claim must continue to mean zero production/frontend/tooling blockers, not zero occurrences of words like placeholder or mock anywhere in historical evidence.

### Frontend And Lab

Closed:

- Lab CSP allows the intended external diagnosis probes.
- `unsafe-eval` was removed from primary frontend CSP definitions.
- Lab generated Bash/Python runners no longer auto-download and extract unverified binaries.
- Generated runner config transport was hardened.
- Standalone Lab runner no longer silently installs remote binaries.
- Frontend dependency advisories from the review batch were addressed.

Still open:

- `unsafe-inline` remains and should be removed through static bootstraps/templates.
- Broad `innerHTML` usage remains in Lab, Proxies, Analytics, and shared UI code. Most usage is controlled/static or sanitized, but the review burden is high.
- The Lab is still a large single feature surface and should be modularized into parser, strategy, diagnostics, export, and UI modules.
- Large frontend assets should be lazy-loaded or reduced for constrained networks.

Frontend product contract:

- Pages must remain usable as raw static files.
- Offline/degraded paths must be explicit in UI state.
- Lab diagnostics must be user-clicked and documented as browser/network-environment checks, not authoritative proxy validation.
- Browser WASM checks are browser-limited reachability checks; sidecar/Python test results remain authoritative for real proxy behavior, with native sidecar checks preferred when available.
- Frontend trust labels must distinguish signed, unsigned local, stale, degraded, candidate, revived, shielded candidate, and verified states where applicable.

### CI, Release, And Mirrors

Closed:

- Bandit scan scope covers `src/configstream`, `scripts`, `tools`, and frontend JavaScript.
- The expanded Bandit gate passes.
- Gitleaks/source token scanning is wired in CI with a source-token rule set and is blocking-ready; removing `continue-on-error: true` from `ci.yml` is the one-line change that makes it a hard blocking gate.
- Vercel mirror deploy runs from `output/`, matching Pages/Netlify artifact shape.
- Workflow validation guards the release/deploy semantics.

Still open:

- Live Pages freshness is not closed until a real deploy and public smoke pass.
- Gitleaks/source token scanning should become a blocking CI gate after one confirmed-clean run proves the rule set is stable.
- Workflow commands can still be simplified into a smaller release-gate runner to reduce duplicated CI logic.

Release command families that should remain guarded:

- status validation,
- workflow validation,
- output matrix validation,
- protocol matrix validation,
- claim ledger validation,
- capability registry validation,
- module ownership validation,
- debt matrix check,
- dependency audit/drift check,
- frontend placeholder/runtime-config validation,
- Pages artifact validation,
- live Pages smoke after deploy.

### Dependencies

Closed for reported batch:

- Frontend advisories for Vite/PostCSS/Picomatch were addressed by lockfile refresh.
- Production direct advisories for Starlette/FastAPI/wasmtime were addressed with updated pins.
- Direct `pip-audit -r requirements-prod.txt --no-deps` passes in the recorded verification.

Remaining caution:

The full resolving audit remains CI-environment-sensitive and should continue running in the supported Python matrix.

### Documentation And Source-Of-Truth

Closed in this bookkeeping pass:

- Root source-of-truth surface is reduced to two current files: this file and `STATUS.md`.
- Historical long-form ledgers are archived under `docs/history/source-of-truth/`.
- Current truth no longer depends on the old root addenda files.

Current cleanup opportunity:

There is still duplication between some docs trees and generated/user docs. Future cleanup should keep canonical authored docs in one place and generate mirrors where needed.

Documentation ownership rule:

- This file explains current truth and release gates.
- `STATUS.md` gives the latest checkpoint.
- `CHANGELOG.md` records completed implementation details.
- `README.md` introduces users/operators to the product.
- Wiki docs explain usage and architecture.
- Matrices and ledgers carry machine-readable claims.
- Historical audit prose stays archived.

## Detailed Chunk Absorption

This section is the deeper chunk pass over the four archived source ledgers. It exists to preserve the live engineering contracts that were easy to lose when the old reports were compressed.

### Original Master: Closure Rules, Evidence, And Known Limitations

Still alive:

1. **Cross-surface parity gate.** A claim is valid only when code, tests, generated artifacts, frontend labels, matrices, docs, changelog, and CI/deploy workflows agree. A fix in one surface is incomplete if another public surface still says or emits the old behavior.
2. **No split-brain contracts.** There must be one public output contract, one frontend deploy contract, one source-of-truth chain, one release policy, and one latest-output evidence model. Duplicated ledgers, duplicate generated output copies, duplicate source lists, or duplicate validators are risks unless one is explicitly generated from the other.
3. **No permanent compatibility debt.** Temporary shims are allowed only with a named owner, tests, and a retirement path. Backward compatibility must not become a reason to keep two incompatible truth models alive forever.
4. **Concurrency and race-safety gate.** Pipeline shutdown, queue draining, timeout handling, anomaly database closure, source-quality writes, resharding, tester daemon restarts, and output generation must be race-safe. Time-limited runs should still produce coherent degraded artifacts.
5. **Changelog discipline.** Completed implementation work belongs in `CHANGELOG.md`. Current truth files should not become a chronological dump of everything ever fixed.
6. **Known limitation tracking.** Browser/WASM testing is limited by browser networking and cannot replace sidecar/native proof. Mobile layout, static asset loading, country flags, WASM MIME handling, frontend trust labels, Vwarp/chain stats, and stale deployment evidence all require explicit validation when touched.
7. **Evidence is scoped.** A local passing validator, a CI artifact, a screenshot, a release asset, and a live public deploy each prove different things. Reports must name which surface was tested.
8. **Durable proof beats prose.** Current status language should point to validators, matrices, manifests, hashes, and smoke reports rather than relying on narrative closure claims.

Archived-only details:

- Old remediation transcripts, old inventory counts, old line-number references, old pass/fail snapshots, and old closure phrasing remain useful only as historical context.

### Part 2: Architecture, Expansion, And Feature Completeness

Still alive:

1. **Feature definition checklist.** Every meaningful feature must answer: who uses it, what behavior changes, what data/API shape it exposes, what safety boundary it crosses, how it behaves degraded/offline, which tests prove it, which docs/matrices change, and how it rolls back or deprecates.
2. **Feature flags for risky work.** Experimental, network-active, high-blast-radius, or compatibility-sensitive behavior should be guarded by explicit flags or clearly local-only commands until stable.
3. **Source provider abstraction.** Long-term source ingestion should separate authored source manifests, generated shards, local/private overrides, source quality scoring, scheduling, and operator-provided feeds. Source scheduler decisions should be explainable and reproducible enough to debug.
4. **Fetcher sandbox.** Fetching source content must defend against redirect abuse, private-network access, credentials in URLs, oversized payloads, decompression hazards, hostile encodings, binary junk, and unexpected content types before data reaches parsers.
5. **Parser result richness.** Parser behavior should eventually expose structured success/drop reasons rather than only `Proxy | None`, especially for high-volume diagnostics and source-quality feedback.
6. **Endpoint reputation and tester profile.** A single successful probe is not the whole quality story. Test cache keys should include relevant profile/engine information, and quality signals should distinguish timeout, DNS, TLS, captive portal, blocked target, chain failure, and engine unavailable.
7. **WARP/Vwarp key and chain lifecycle.** WARP keys, key health, per-key failure counters, rotation policy, chain generation, chain retesting, and candidate retention must be observable and bounded. Failed retests can produce useful candidates, but only retested successes count as verified.
8. **DNS/evasion policy.** DNS-safe and DNS-hardened modes need explicit rewrite rules, SNI/Host preservation, private-IP safeguards, poisoning heuristics where available, and fail-open/fail-safe behavior by artifact family.
9. **Lab safety boundary.** The Lab can guide users, parse configs, build strategies, export scripts, render QR, and run user-clicked diagnostics. It must not hide third-party requests, default to broad scanning, auto-install unverified binaries, or imply browser checks are authoritative proxy tests.
10. **Offline-first frontend contract.** Static Pages, local file use, no-JS/degraded states, cached assets, runtime config, and local-only Lab flows are product constraints, not afterthoughts.
11. **Observability taxonomy.** Reports should separate source fetch policy blocks, source network failures, parser drops, security validation drops, tester failures, timeout classes, revival results, output-generation degradation, and deploy freshness.
12. **Versioned public API.** Public JSON schemas should evolve additively when possible. Breaking output/API changes require matrix updates, docs, compatibility notes, and versioning or explicit migration.
13. **Snapshot identity.** Public data snapshots need durable identity through manifest hash, generated timestamp, source commit/ref, or equivalent metadata. Frontend trust labels should show stale/unsigned/degraded states clearly.
14. **Threat-model ownership.** Malicious source content, SSRF, secret leakage, XSS, dependency compromise, unverified binary downloads, artifact tampering, replay/stale deploy, and operator misuse all need mitigations, tests, and residual-risk notes where they touch product behavior.
15. **Supply-chain posture.** Runtime CDN dependencies should be avoided or justified. Vendored frontend assets, dependency lockfiles, binary checksums/signatures where binaries are downloaded, SBOM/release attestations where practical, and scheduled audits form the long-term target.
16. **Release split.** A software release, data release, Pages deploy, mirror deploy, package publish, and native/browser sidecar artifact are separate release products. Status must not let one imply another.
17. **Named test profiles.** Keep separate profiles for fast unit, parser golden, output contract, frontend static smoke, frontend browser smoke, security, dependency audit, chaos/degraded mode, native-core proof, release gate, and live deployment smoke.
18. **Roadmap intake.** Future expansion ideas are not current truth until registered in capability/matrix/docs/tests. The right path is contract first, then implementation, then proof.

Archived-only details:

- Broad expansion ideas such as plugin ecosystems, community source portals, recommendation engines, personal profile generators, and advanced analytics remain roadmap candidates only when separately scoped and registered.

### Part 3: Native Client Semantics And Output Namespaces

Still alive:

1. **Dataset JSON is not client JSON.** `proxies.json`, `api/proxies`, country lists, and protocol lists are public datasets. They must not contain top-level Sing-box or Xray config structures.
2. **Sing-box contract.** Sing-box configs use `route`, `inbounds`, `outbounds`, `dns`, `log`, `experimental`, outbound `type`, valid outbound tags, valid route references, and Sing-box-specific transport/security fields.
3. **Xray contract.** Xray configs use `routing`, `inbounds`, `outbounds`, outbound `protocol`, `settings`, `streamSettings`, and Xray-specific policy/stats/API semantics. Xray must not be described as first-class pipeline output until it has generator, schema/static validator, native proof, matrix rows, docs, tests, and release artifacts.
4. **Namespace rejection.** Validators should actively reject cross-core mixing, such as Xray `routing` inside Sing-box configs, Sing-box outbound `type` inside Xray outbounds, or dataset fields masquerading as native config keys.
5. **Output naming clarity.** A file name that says Sing-box should be a complete valid Sing-box config or explicitly documented as a partial/library artifact. `chains.json`, `singbox-chains.json`, `proxies.json`, and `api/proxies` must not be used interchangeably.
6. **Remote rule-set caution.** Native validation must account for remote rule-set assumptions. Static/schema validation is valuable, but native-core proof should use pinned clients where feasible and document network-dependent checks separately.
7. **Protocol export caveats.** A parsed protocol may be accepted into datasets while being unsupported or partially supported in Sing-box, Clash, URI, Lab, or future Xray exports. The protocol matrix must preserve those distinctions.
8. **Validator families.** Dataset, categorized public lists, Sing-box, Clash, Lab exports, worker examples, and any future Xray output need validators that match their real format and runtime expectations.

Archived-only details:

- Old recommendations already implemented by the current output matrix and serializer work are preserved as historical justification, not open action.

### Amendment: Evidence Boundaries And Anti-Overclaiming

Still alive:

1. **Current branch matters.** Open PRs, local branches, unmerged patches, and review drafts are not current repository truth until merged into the active branch being audited.
2. **Latest output is a state, not a folder name.** A directory named latest-output is not trusted by itself. Trust requires artifact validation, manifest/hash parity, timestamp/source identity, and deploy/smoke context.
3. **CI artifact retention is weak evidence.** Short-lived workflow artifacts prove historical runs only while available. Durable status claims need committed reports, retained release assets, signed manifests, or live smoke results.
4. **Screenshots are supportive only.** UI screenshots prove visual state for a captured build, not live deployment freshness or API correctness unless tied to the same artifact and timestamp.
5. **Live Pages proof checklist.** The live gate specifically needs runtime config, health, artifact manifest, metadata freshness/hash fields, API aliases, parseable public JSON, frontend placeholder absence, expected MIME behavior, and public URL fetch success.
6. **Private-network policy split.** Blocking private-network source fetches and allowing users to validate private proxy candidates are separate controls. They must not share ambiguous config names or docs.
7. **Source resharding caution.** Any scheduled source reshuffling or source-quality feedback loop must avoid self-trigger loops, racey commits, token reintroduction, and unexplained source churn.
8. **Generated artifacts are not source.** Large output mirrors, ZIPs, extracted release bundles, screenshots, cache trees, `frontend-dist/`, and local `output/` trees belong in ignored paths or release artifacts, not as source-truth evidence in git.
9. **Trust-state rendering.** Stale, failed, degraded, unsigned, local-only, candidate, revived, shielded, and verified states must be visually and semantically different in frontend and metadata.
10. **Docs must retire old claims.** When a claim is superseded, it should move to history or changelog. Leaving old root files beside current truth is itself a product risk because maintainers will eventually read the wrong file.

Archived-only details:

- Old "missed/skipped" phrasing, dated counts, stale branch/PR references, old latest-output examples, and older release-roadmap statements are historical evidence only.

## Current Open Work

### Required Before Public Pages Readiness

1. Generate or confirm a fresh Pages artifact from current `main`.
2. Run artifact validation against that output tree.
3. Deploy GitHub Pages from the validated artifact.
4. Run live deployment smoke:

```bash
python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --timeout 120 --report-file output/pages_deployment_smoke.json
```

5. Only after the live smoke passes, change the live Pages gate from open to closed.

### High-Value Maintainability Cleanup

1. Flip the CI gitleaks step to blocking by removing `continue-on-error: true` (working tree already scans clean; requires `workflows` permission).
2. Make one source-list truth and generate shards/mirrors/backups.
3. Stop tracking source backups; keep them as ignored runtime files or CI artifacts.
4. Collapse historical `.gitignore` artifact tombstones into broad directory ignores.
5. Split `output_logic.py` by output family.
6. Split `frontend/assets/css/style.css` by design layer and page.
7. Modularize `frontend/assets/js/lab.js`.
8. Move repeated HTML shell/CSP/script lists into a raw-static-compatible template step.
9. Move i18n dictionaries out of `i18n.js` into loadable JSON.
10. Lazy-load heavy analytics and WASM assets.
11. Reorganize tests by contract area.

## Pruning And Simplification Roadmap

This roadmap is adopted from the deeper pruning review. These items are not current publish blockers unless a later validator marks them so. They are the preferred sequence for making the repository easier to read, maintain, audit, and ship.

### Highest-Value Cleanup

1. **Remove tracked source backups**

   Current concern:

   - `sources/backup_dynamic/` looks like operational backup state rather than source truth.
   - Keeping backup batches tracked increases source churn, review noise, and token-exposure surface.
   - Workflows/tests may reference it, so removal needs a dependency check first.

   Desired state:

   - Move backup source snapshots to ignored runtime output, CI artifacts, or explicitly named historical fixtures.
   - Keep only the current source truth in tracked files.
   - Add/update tests so workflows fail if they rely on mutable backup state.

   Risk: medium. The cleanup touches source ownership and possible workflow assumptions.

2. **Choose one source-list truth**

   Current concern:

   - `consolidated_sources.txt` and `sources/batch_*.txt` can represent the same logical source inventory.
   - Two maintained surfaces create split-brain ownership and make token hygiene harder.

   Desired state:

   - Choose either one canonical manifest/list or canonical shards.
   - Generate the other representation.
   - Document local private source overrides separately.
   - Keep source-token scanning over every tracked source-like file.

   Risk: medium. It affects resharding, CI batch inputs, and operator docs.

3. **Shorten `.gitignore` artifact tombstones**

   Current concern:

   - `.gitignore` contains many specific historical artifact paths even when broad directory ignores already cover them.
   - Long tombstone lists make it harder to see the actual ignore policy.

   Desired state:

   - Collapse redundant `invvest/`, latest-output, generated artifact, cache, and build-output entries into clear directory-level rules.
   - Keep explicit exceptions only where needed.
   - Verify with `git status --ignored` or equivalent targeted checks before/after.

   Risk: low if verified carefully.

4. **Split `output_logic.py` by output family**

   Current concern:

   - `src/configstream/output_logic.py` is large and mixes metadata, manifests, subscriptions, categorized lists, native client configs, and artifact contract helpers.
   - The public serializer and categorized API fixes are easier to preserve if the code is organized by output family.

   Desired state:

   - Extract modules for public lists, subscriptions, metadata/health, manifests, native client configs, and shared utilities.
   - Keep public APIs stable or add compatibility wrappers.
   - Preserve output matrix and artifact validator semantics.

   Risk: medium-high. This should be behavior-preserving and heavily tested.

5. **Make categorized API generation first-class**

   Current concern:

   - Country/protocol JSON is public API behavior but historically sat inside broader output generation.
   - That made serializer drift easier to miss.

   Desired state:

   - Add a dedicated module such as `public_lists.py`.
   - Centralize country/protocol grouping, safe serialization, schema validation expectations, and artifact paths.
   - Keep tests for root/country/protocol schema parity.

   Risk: medium. It is related to public API output.

6. **Centralize release/artifact script helpers**

   Current concern:

   - `scripts/validate_pages_artifact.py`, `scripts/verify_pages_deployment.py`, and `scripts/deploy_artifact_smoke.py` repeat path, report, URL, subprocess, and JSON-check patterns.
   - Duplication increases Bandit noise and makes validator behavior drift more likely.

   Desired state:

   - Add `scripts/lib/` helpers for safe subprocess calls, report writing, artifact path traversal, URL-scheme checks, and JSON loading.
   - Keep CLI behavior stable.
   - Add focused tests for the helper layer.

   Risk: medium. The validators are release-critical.

7. **Unify workflow release gates**

   Current concern:

   - Main, release, deploy-pages, and mirror workflows duplicate validation intent.
   - When a gate is added in one workflow but not another, readiness becomes subjective again.

   Desired state:

   - Add a single command family, for example `scripts/run_release_gate.py ci|pages|release|mirror`.
   - Workflows call the command rather than hand-maintaining long command chains.
   - `scripts/validate_workflows.py` checks that the canonical gate runner is present.

   Risk: medium. This affects CI/release workflows but should reduce future drift.

8. **Collapse duplicated documentation trees**

   Current concern:

   - `docs/encyclopedia/**` and `docs/wiki/encyclopedia/**` appear mirrored.
   - Mirrored docs create review noise and stale-copy risk.

   Desired state:

   - Keep one authored source tree.
   - Generate the mirrored/wiki tree if needed.
   - Add a docs-generation or parity check.

   Risk: low-medium. Verify publishing expectations before deleting mirrors.

9. **Keep historical truth docs under `docs/history/`**

   Current state:

   - Done for the four long source-of-truth ledgers.

   Maintenance rule:

   - Do not move historical ledgers back to root.
   - Add new historical audit transcripts under `docs/history/source-of-truth/` or another clearly named history folder.
   - Promote only distilled current policy into the root master/status files.

10. **Keep the Master Report as current truth plus appendices**

   Current state:

   - Done in this pass: the root master is no longer a huge raw transcript.

   Maintenance rule:

   - The root master should remain a detailed current contract and evidence index.
   - Long raw evidence belongs in dated appendices/history.
   - If a future audit adds many findings, absorb the durable policy and move completed implementation detail to `CHANGELOG.md`.

### Frontend And UI Cleanup

11. **Template repeated HTML shells**

   Current concern:

   - `index.html`, `lab.html`, `proxies.html`, and other pages repeat CSP, icons, CSS, scripts, nav, and common shell structure.

   Desired state:

   - Use a tiny static prebuild/template step that emits raw HTML for Pages.
   - Keep raw static Pages compatibility.
   - Generate CSP/script tags consistently.

   Risk: medium. CSP and script ordering are user-visible.

12. **Split the large stylesheet**

   Current concern:

   - `frontend/assets/css/style.css` is large and mixes tokens, layout, components, page-specific rules, and utilities.

   Desired state:

   - Split into tokens, base, layout, components, utilities, and page-specific files.
   - Keep load order explicit.
   - Use visual smoke tests around high-risk pages.

   Risk: medium. UI regressions are easy if ordering changes.

13. **Modularize Lab JavaScript**

   Current concern:

   - `frontend/assets/js/lab.js` mixes parsing, diagnostics, strategy building, export generation, QR behavior, and UI state.

   Desired state:

   - Split into modules such as:
     - `lab/parser.js`
     - `lab/diagnostics.js`
     - `lab/strategies.js`
     - `lab/exporters.js`
     - `lab/qr.js`
     - `lab/ui.js`
   - Keep the current public workflow stable.
   - Add click-path tests for diagnosis/export.

   Risk: medium-high. Lab is large and security-sensitive.

14. **Replace generated shell scripts with safer templates**

   Current concern:

   - Generated Bash/Python runners are user-run code and need extra review clarity.

   Desired state:

   - Use dedicated template files.
   - Use tested interpolation/encoding helpers.
   - Keep regression tests for quotes, newlines, command substitution, JSON payloads, and adversarial remarks.

   Risk: medium. Security-sensitive but can be done incrementally.

15. **Move i18n dictionaries to JSON**

   Current concern:

   - `frontend/assets/js/i18n.js` mixes runtime code and translation dictionaries.

   Desired state:

   - Keep runtime loader small.
   - Move dictionaries to `assets/i18n/*.json`.
   - Lazy-load locale-specific data.
   - Keep offline/static fallback behavior.

   Risk: low-medium. Needs fallback handling.

16. **Reduce broad `innerHTML` usage**

   Current concern:

   - `proxies.js`, `analytics.js`, and `lab.js` still contain many HTML sinks.
   - Even controlled/static markup increases XSS/CSP review cost.

   Desired state:

   - Add small DOM-builder/render helpers.
   - Use `textContent` by default.
   - Reserve sanitized `innerHTML` for explicit reviewed cases.

   Risk: medium. UI output changes must be tested.

17. **Lazy-load heavy analytics assets**

   Current concern:

   - Globe textures, `three.min.js`, `globe.gl.min.js`, and `chart.min.js` are heavy for constrained networks.

   Desired state:

   - Load heavy analytics libraries only on analytics pages or after user action.
   - Keep graceful fallback when assets fail.
   - Preserve no-network/frontend smoke behavior.

   Risk: low-medium.

18. **Prune font families and weights**

   Current concern:

   - The frontend carries multiple Latin and Persian font families/weights.

   Desired state:

   - Keep minimum required scripts and weights.
   - Lazy-load locale-specific fonts where practical.
   - Document why each retained font exists.

   Risk: low-medium. Verify Persian/RTL rendering.

19. **Make service/cache/update logic one layer**

   Current concern:

   - `cache-manager.js`, `update-detector.js`, `loading-controller.js`, `state-manager.js`, and service worker logic overlap.

   Desired state:

   - One small runtime state/update layer.
   - Clear ownership of cache freshness, loading status, stale data, and update prompts.

   Risk: medium. This affects perceived freshness and offline behavior.

20. **Turn repeated script chains into page manifests**

   Current concern:

   - HTML pages manually list scripts, making missing/extra script drift likely.

   Desired state:

   - Define per-page script manifests.
   - Generate script tags during static template build.
   - Validate required scripts by page.

   Risk: low-medium.

### Backend And Logic Cleanup

21. **Split `server.py` by API group**

   Current concern:

   - `server.py` mixes Lab routes, public artifact routes, health routes, static helpers, and admin/runtime behavior.

   Desired state:

   - Move route groups into focused modules/routers.
   - Preserve import paths or add compatibility wrappers.
   - Keep admin fail-closed behavior and CORS policy tests.

   Risk: medium-high.

22. **Separate adapters by family**

   Current concern:

   - `adapters.py` carries multiple client/output concerns.

   Desired state:

   - Split by adapter/client/output family.
   - Keep protocol/export matrix alignment.
   - Add focused adapter tests by family.

   Risk: medium.

23. **Sharpen washer/vwarp boundaries**

   Current concern:

   - Washer core and Vwarp tooling mix config building, process execution, result classification, and operational retry logic.

   Desired state:

   - Extract config builders, process runners, failure classifiers, and result models.
   - Keep WARP/Vwarp constants canonical.
   - Preserve chain retesting/candidate accounting semantics.

   Risk: medium-high.

24. **Rename or narrow `backup.py`**

   Current concern:

   - `backup.py` is generic-sounding and appears CLI-referenced.

   Desired state:

   - Rename toward its actual domain or make its public API narrow and documented.
   - Update references and tests.

   Risk: low-medium depending on CLI usage.

25. **Generate docs from matrices**

   Current concern:

   - Protocol/output/capability facts can drift across README, wiki docs, matrices, and status prose.

   Desired state:

   - Generate tables/docs from `protocol_matrix.json`, `output_matrix.json`, and capability registry where possible.
   - Keep authored prose for explanation, not duplicated inventories.

   Risk: low-medium.

### Tests And Quality Cleanup

26. **Reorganize tests by contract**

   Current concern:

   - `tests/unit` is broad and mixes many concerns.

   Desired state:

   - Use directories like:
     - `tests/contracts`
     - `tests/security`
     - `tests/frontend`
     - `tests/pipeline`
     - `tests/release`
   - Keep pytest markers/profiles aligned with CI gates.

   Risk: medium due import/path assumptions.

27. **Create shared test factories**

   Current concern:

   - Tests independently construct proxies, artifacts, workflows, metadata, and fake outputs.

   Desired state:

   - Add `tests/factories/` for canonical proxy records, output trees, workflow snippets, metadata, and manifests.
   - Reduce fixture drift and test length.

   Risk: low-medium.

28. **Retire vague test names**

   Current concern:

   - Names like `coverage_boost`, `deep`, and `extended` hide intent.

   Desired state:

   - Rename tests around behavior and contract, such as pipeline shutdown, fetcher private-network policy, output schema parity, or Lab exporter safety.

   Risk: low if imports are updated carefully.

29. **Make Bandit policy explicit**

   Current concern:

   - Expanded Bandit scans can produce low-value subprocess/import noise unless reviewed policy is encoded.

   Desired state:

   - Use an explicit reviewed Bandit config.
   - Keep true positives visible.
   - Avoid broad blanket exclusions.
   - Add comments or helper wrappers for known-safe subprocess patterns.

   Risk: low-medium.

30. **Promote dependency audits into one command**

   Current concern:

   - `npm audit`, `pip-audit`, `pip check`, and lockfile drift checks are separate readiness signals.

   Desired state:

   - Add one dependency gate command.
   - Report frontend, direct Python, transitive Python, and environment-sensitive findings separately.
   - Let workflows call the same command.

   Risk: low-medium.

### Nice-To-Have Cleanup

31. **Move Worker examples to `examples/workers/`**

   Current concern:

   - Worker scripts under `tools/workers/` can read like core production tooling.

   Desired state:

   - Move optional deployable examples under `examples/workers/`.
   - Keep docs clear that they are optional/user-operated.

   Risk: low-medium.

32. **Compress static image strategy**

   Current concern:

   - Globe/visual textures are attractive but heavy.

   Desired state:

   - Keep one default texture.
   - Load alternatives on demand.
   - Document why retained assets exist.

   Risk: low.

33. **Add a repo map**

   Current concern:

   - New contributors need a quick navigation layer.

   Desired state:

   - Add `docs/REPO_MAP.md` covering core pipeline, frontend, release scripts, docs generation, tests, and local-only tools.

   Risk: low.

34. **Make local-only tooling visibly local-only**

   Current concern:

   - `tools/lab-scanner.py`, `tools/lab-runner.sh`, Worker scripts, and scanner helpers can appear production-adjacent.

   Desired state:

   - Group opt-in local tools away from core production code.
   - Add local-only labels in docs and command help.

   Risk: low-medium.

35. **Use a single readiness dashboard artifact**

   Current concern:

   - Readiness evidence is spread across docs, logs, matrices, and validators.

   Desired state:

   - Generate `docs/readiness.json` or a markdown table from validators.
   - Keep status claims tied to generated proof.
   - Separate repository, artifact, live Pages, release, and mirror readiness.

   Risk: low-medium.

### Recommended Cleanup Sequence

Preferred sequence:

1. Collapse `.gitignore` artifact tombstones.
2. Collapse duplicated documentation trees.
3. Template repeated HTML shells.
4. Split frontend CSS.
5. Modularize Lab JavaScript.
6. Split output generation by output family.
7. Centralize release/artifact script helpers.
8. Then tackle source-list architecture: remove tracked backups and choose one source-list truth.

Why this order:

- The first two items are high-readability and relatively low product risk.
- Frontend template/CSS/Lab cleanup reduces the largest UI review burden.
- Output/script cleanup protects release contracts.
- Source-list cleanup is valuable but should come after the repository has stronger generators and checks, because source ownership affects CI and operators.

## Validation Snapshot

Latest repository-level verification recorded before this bookkeeping pass:

- `python -m black --check .`: passed.
- `python scripts/generate_debt_matrix.py --check`: passed.
- `python scripts/validate_output_matrix.py`: passed.
- `python scripts/validate_workflows.py`: passed.
- `python scripts/validate_status.py`: passed.
- `python -m flake8`: passed.
- `python -m mypy src/configstream`: passed.
- `python -m bandit -r src/configstream scripts tools frontend/assets/js -q`: passed.
- `python -m pip_audit -r requirements-prod.txt --no-deps`: passed.
- `npm audit`: 0 vulnerabilities.
- `npm run build:sanity`: passed.
- `python -m pytest -q`: 1057 passed, 4 skipped in the latest full-suite snapshot.
- `python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --timeout 120 --report-file output/pages_deployment_smoke.json`: fails against stale live Pages.

## Archived Evidence

Archived long-form ledgers:

- `docs/history/source-of-truth/ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.full.md`
- `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 2.md`
- `docs/history/source-of-truth/Main SOURCE OF TRUTH - PART 3.md`
- `docs/history/source-of-truth/Main SOURCE OF TRUTH - Ammendment.md`

These files preserve detail for audit history. They are not current status surfaces.
