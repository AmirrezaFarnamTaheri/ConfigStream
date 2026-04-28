# ConfigStream Master Audit Report

**Date:** 2026-04-28  
**Subject:** `AmirrezaFarnamTaheri/ConfigStream` repository, public deployment, documentation, CI/CD, backend, frontend, output contracts, security posture, and roadmap.  
**Status:** Final consolidated audit report. The source material has been merged, deduplicated, reconciled, and polished into one coherent document.

---

## 0. Method and Evidence Rules

This report consolidates the audit corpus into a single unified assessment. The inputs did not have the same evidence quality. Several were access-limited public-surface audits based on repository listings, rendered documentation, GitHub Pages output, and sampled public artifacts. Others claimed direct inspection of workflow, server, configuration, and source snippets. One source went further into deep-systems and adversarial analysis; those items are preserved as useful threat-model and design-review material, but many must be verified in a local checkout before being treated as confirmed defects.

This report therefore uses four evidence levels:

- **Confirmed public evidence:** repeated across reports or observed from public frontend/output/repository inventory.
- **Reported source evidence:** asserted by an input audit that claims it retrieved workflow/source snippets, but not re-executed in this consolidation.
- **Needs source verification:** plausible, important, and actionable, but dependent on source inspection, runtime tests, or CI logs.
- **Strategic or speculative risk:** a useful design warning, threat-model concern, or roadmap idea that should not be labeled as a current bug until verified.

The consolidation rule is simple: duplicate findings are merged, but their unique details are retained. If one report gives evidence, another gives impact, and a third gives a concrete test or fix, the final finding includes all three. When reports conflict, this report preserves the conflict and gives the safest interpretation.

---

## 1. Executive Summary

ConfigStream is presented as a zero-budget, GitHub-hosted anti-censorship configuration platform. Its intended pipeline fetches public proxy sources, parses many protocols, normalizes and validates configurations, tests proxies with Go/Python engines, revives or "washes" failed candidates through WARP/Vwarp strategies, ranks results, generates many client-compatible outputs, and publishes static artifacts plus a frontend dashboard/laboratory through GitHub Pages.

Across the eight reports, the strongest consolidated conclusion is that ConfigStream has a genuinely broad and ambitious product architecture, but it is held back by serious drift between promises, public output state, CI/CD controls, implementation evidence, documentation, and user-facing trust signals. The most urgent work is not adding more evasion features; it is making the existing pipeline, outputs, metadata, CI/CD, security posture, and frontend states truthful, validated, and self-consistent.

The highest-impact themes are:

1. **Audit completeness risk.** Several reports say a complete file-by-file audit was blocked because source archives or raw files were unavailable. Other reports make direct source-level claims. A final authoritative audit still requires a fixed commit SHA, a full checkout/archive, and reproducible build/test runs.
2. **CI/CD correctness risk.** Multiple reports identify malformed GitHub Actions YAML, self-triggering scheduled pipelines, broad workflow permissions, root container execution despite non-root claims, late/non-blocking validation, and too much work concentrated in release/deploy workflows.
3. **Public output trust problem.** Public outputs were reported as collapsed or degraded: `base64.txt`, `chosen/base64.txt`, and DNS-safe Base64 output reportedly decoded to the same single SOCKS5 URI in one sample. A side-product archive was reported as suspiciously small. The site reportedly claims freshness and richness while public artifacts may be sparse.
4. **Frontend degraded-state problem.** The public homepage, analytics, wiki, and lab surfaces reportedly expose placeholders, zero counters, "checking" states, and weak no-JS/static rendering. For an anti-censorship tool, degraded and script-hostile environments are first-class use cases, not edge cases.
5. **Output and metadata contract drift.** The reports repeatedly call for canonical manifests and schemas: `artifact_manifest.json`, `output_manifest.json`, `metadata.schema.json`, `lab_strategies.json`, and a protocol/tester/output compatibility matrix. Without these, README tables, server routes, frontend cards, CI checks, generated files, and schemas drift independently.
6. **Backend/API risks.** Repeated findings include a `/api/diff/proxies` schema mismatch, optional admin auth when `ADMIN_API_KEY` is unset, broad GitHub Pages CORS trust, WebSocket lifecycle risks, synchronous file/JSON work inside async routes, path containment concerns, and public config pack secret exposure.
7. **Pipeline/concurrency risks.** The documents highlight shard-local deduplication, missing or weak semaphores, `TIME_WAIT`/ephemeral port exhaustion, cancellation during sync writes, unbounded `seen_keys`, queue shedding that poisons source quality, and fragile historical identity.
8. **Security and abuse boundaries.** Risks include SSRF after DNS resolution, stored XSS through untrusted proxy fields, scanner safety, active probing/honeypot concerns, dependency/action pinning gaps, root containers, WARP/Cloudflare anti-abuse, Rust FFI panic boundaries, and optional external services that may undermine zero-budget guarantees.
9. **Documentation and feature-claim drift.** Reports repeatedly flag Python version drift, Chain Laboratory strategy-count drift, protocol support drift, stale module references, overclaiming around autonomous intelligence, WASM browser testing, steganographic delivery, smart routing, and WARP/Vwarp revival.
10. **Testing governance gap.** The project appears to have many tests, but the reports warn of missing required PR quality gates, non-blocking schema validation, insufficient deployed-site smoke tests, missing golden output tests, docs drift tests, and possible test sprawl.

The practical remediation sequence is:

1. Validate and repair workflows.
2. Stop self-triggering and overlapping release pipelines.
3. Establish artifact/output/metadata/lab/protocol manifests.
4. Make public degraded states honest and useful.
5. Make security controls executable and align docs with reality.
6. Add regression tests around parser/tester/output/frontend contracts.
7. Separate core zero-budget functionality from optional experimental features.
8. Clean stale docs, duplicate paths, empty files, and legacy claims.

---

## 2. Consolidated Project Understanding

The intended ConfigStream system model is:

```text
source lists
  -> fetch with adaptive timeouts, redirects policy, circuit breakers, and hostile-input controls
  -> parse and extract proxy configurations across many protocols
  -> normalize protocol aliases and required fields
  -> validate against security constraints and blocklists
  -> deduplicate locally and, ideally, globally across shards
  -> test via Go sidecar and Python fallback
  -> classify, score, rank, tag, and preserve history
  -> revive or wash failed candidates through WARP/Vwarp or chain strategies
  -> generate subscription and client outputs
  -> publish static artifacts, metadata, and frontend pages
```

The intended output surface includes `base64.txt`, `chosen/base64.txt`, `base64-dns-safe.txt`, `clash.yaml`, `singbox.json`, `singbox-vpn.json`, `singbox-chains.json`, `revived.json`, `proxies.json`, DNS-safe and DNS-hardened variants, protocol-specific outputs, side-product archives, and possible client-specific profiles for Mihomo/Clash.Meta, Shadowrocket, Surge, Loon, Quantumult X, Xray, SIP008, WireGuard, OpenVPN, and related clients.

The project has three product surfaces:

1. **Pipeline product:** scheduled ingestion, parsing, testing, ranking, revival, output generation, and publication.
2. **User-facing static site:** homepage, proxy list, analytics, lab/offline lab, wiki/about pages, and direct downloads.
3. **Developer/API/data product:** JSON artifacts, metadata, WebSocket/API endpoints, lab test endpoints, output routes, schemas, and manifests.

The repository inventory described across reports includes `.github/`, `_includes/`, `docs/`, `frontend/`, `policy/`, `schema/`, `scripts/`, `sources/`, `src/`, `tests/`, and `tools/`, plus root governance/build files such as `README.md`, `AGENTS.md`, `SECURITY.md`, `STATUS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `KNOWN_ISSUES.md`, `QUICKSTART.md`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `package.json`, `requirements.txt`, `render.yaml`, and `vite.config.mjs`.

The audit corpus identifies real strengths. ConfigStream is not merely decorative: it has a broad multi-format output concept, parser/tester/security/frontend/lab modules, a multi-runtime architecture, extensive documentation, CI sharding ideas, frontend analytics, historical reliability concepts, source quality concepts, WARP/Vwarp revival ambitions, DNS-safe outputs, and a promising Chain Laboratory. This report treats it as a serious project with governance and correctness debt, not as an empty repository.

---

## 3. Coverage Inventory and Audit Limitations

Several reports were explicitly access-limited. They could inspect public repository listings, README/project intent, public pages, and sampled outputs, but could not clone the repository or fetch raw Python/Go/Rust/JavaScript/YAML source. Those reports could not honestly provide function-level parser bugs, line-level workflow validation, import-level dead-code proof, full frontend behavior, or complete test quality judgments.

Other reports claim they retrieved workflow/source snippets and therefore assert concrete findings such as workflow indentation problems, `/api/diff/proxies` schema mismatch, optional admin auth, CORS regex issues, dependency pinning drift, and output-route duplication. These are high-priority findings, but they must still be checked against the current branch in a real checkout.

The unresolved audit-risk areas are:

- Full `.github/workflows/` syntax, triggers, permissions, concurrency, cache keys, artifact handling, and Pages deployment logic.
- Full `src/configstream/**/*.py` implementation.
- Parser contracts, malformed input handling, protocol aliases, drop reasons, and per-protocol output compatibility.
- Go tester JSON payload shape, timeout behavior, process lifecycle, and WASM build behavior.
- Rust `ss_checker` FFI panic/memory boundaries.
- Frontend JavaScript data fetching, sanitization, DOM rendering, service-worker behavior, lab wiring, and large-data performance.
- Schema contents and whether metadata fields match frontend consumers.
- Test suite quality, actual coverage, and required PR gates.
- WARP/Vwarp scanner/washer retention semantics and safety controls.
- Side-product archive contents and secret scanning.
- Optional external service behavior and zero-budget fallbacks.

Because of this, the final remediation plan must include a real-checkout verification checklist rather than pretending the reports collectively prove every implementation-level claim.

---

## 4. Evidence Conflict Map

The main evidence conflict is between access-limited public-surface audits and stronger source-level claims. Some inputs repeatedly warn that raw source could not be retrieved; others present workflow, API, configuration, and code assertions as direct findings. The deep-systems material is valuable, but several assertions still need direct confirmation in a local checkout.

The safest interpretation is:

- Public frontend/output observations are high-confidence where repeated.
- Workflow/API/config claims are urgent and likely actionable, but should be validated locally before being marked closed.
- Deep systems claims are valuable risk inventory and test-design material, but not all should appear as confirmed bugs.
- Roadmap ideas must be separated from defects so the report does not blur "broken today" with "could be improved later."

---

## 5. Critical Findings

### C1. Full source audit remains incomplete without a repository archive

**Evidence level:** Confirmed public/access-limited evidence.  
**Severity:** Critical.  
**Category:** Audit completeness.

Several reports state that the requested exhaustive, file-by-file audit could not be completed because a source archive or raw source files were not available. Public folder listings, rendered README/docs, public pages, and sampled outputs are useful, but they cannot validate function-level parser behavior, async correctness, workflow YAML, frontend sanitization, test quality, or runtime CI behavior.

**Impact:** Any implementation-level claim may be incomplete or wrong unless rechecked against a full checkout at a fixed commit SHA. This affects parser findings, workflow findings, dead-code claims, security-control claims, and runtime behavior.

**Fix:** Audit a ZIP/tar archive or local checkout at a fixed commit SHA, including `.github`, `src`, `frontend`, `tests`, `docs`, `scripts`, `tools`, `schema`, `policy`, `sources`, generated sample outputs, and CI logs.

**Priority:** P0.

### C2. GitHub Actions YAML may be malformed in multiple workflow files

**Evidence level:** Reported source evidence.  
**Severity:** Critical.  
**Category:** CI/CD correctness.

Multiple reports say workflow files contain invalid or suspicious `env:` indentation, especially around keys such as `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`, `CS_PUBLIC_KEY`, and `CS_IPNS_KEY`. Affected workflows are reported as `main.yml`, `retest.yml`, `ci.yml`, and/or `deploy-pages.yml` depending on the input audit.

If true in committed YAML, this can disable or destabilize the entire GitHub Actions operating model: scheduled runs, sharding, artifact merge, Pages deploy, releases, retests, WASM builds, source optimization, and validation.

**Fix:** Run `actionlint`, parse all workflow files with a YAML parser, manually inspect the affected `env:` blocks in GitHub or a local checkout, normalize formatting, and add workflow syntax validation to CI/pre-commit.

**Priority:** P0.

### C3. Scheduled pipeline can self-trigger through source-shard commits

**Evidence level:** Reported source evidence.  
**Severity:** Critical.  
**Category:** DevOps, cost, reliability.

One source-level audit states that the main workflow runs on push/schedule/manual dispatch and that a merge job can run `scripts/dynamic_reshard.py` and commit changed `sources/batch_*.txt` back to `main`. That push can retrigger the same workflow. A scheduled pipeline can therefore create follow-on runs by mutating source shards.

**Impact:** Wasted GitHub Actions minutes, noisy back-to-back runs, confusing causality, and harder incident analysis. This undermines the zero-budget story.

**Fix:** Move resharding to a manual workflow, publish reshard recommendations as artifacts, push only to a branch excluded from expensive workflows, add strict path filters, and define workflow `concurrency` rules.

**Priority:** P0.

### C4. Deployment can fail closed when outputs are empty or sparse

**Evidence level:** Reported source evidence plus public-output concern.  
**Severity:** Critical/High.  
**Category:** Reliability, product contract.

Reports say the README promises useful outputs even when no proxies pass live testing, but workflows treat empty or missing files such as `singbox.json`, `clash.yaml`, `singbox-vpn.json`, `base64.txt`, logs, chain outputs, side products, trend data, and docs artifacts as critical failures. That is a fail-closed release policy, while the product promise is degraded-but-useful publication.

**Impact:** During censorship spikes or network failures, the pipeline may block publication exactly when users need stale or degraded-but-valid artifacts. Users may receive no update or misleading state instead of an honest degraded output.

**Fix:** Publish schema-valid minimal outputs, stale-known-good artifacts, and `health.json`/`degraded.json` metadata. Gate on validity, provenance, and explicit status, not non-emptiness alone.

**Priority:** P0/P1.

### C5. Public frontend renders placeholders, zeros, and ambiguous loading states

**Evidence level:** Confirmed public evidence across several reports.  
**Severity:** High/Critical for product trust.  
**Category:** Frontend, accessibility, degraded operation.

The public frontend reportedly exposes unresolved placeholders such as `{sources}` and `{hours}`, zeroed counters, "Fetching latest configurations...", and "Last updated: checking..." in static/no-JS text. Analytics and wiki/docs pages were also reported as weak or JavaScript-dependent in accessible rendering.

**Impact:** For a hostile-network anti-censorship project, JavaScript failure, blocked assets, low-power browsers, privacy browsers, text previews, link unfurlers, and no-JS users are realistic. Broken static fallback reduces trust and can make the project look empty or stale even if data exists elsewhere.

**Fix:** Pre-render static fallback metadata, download links, last-known status, safety guidance, and clear degraded states at build time. Use JavaScript only for enhancements such as live refresh, filtering, charts, and lab interactions.

**Priority:** P0/P1.

### C6. Public Base64/chosen outputs appear collapsed and not observably distinct

**Evidence level:** Confirmed public-output sample in multiple reports.  
**Severity:** High.  
**Category:** Output generation, product reliability.

Several reports state that sampled public outputs `base64.txt`, `chosen/base64.txt`, and `base64-dns-safe.txt` decoded to the same single SOCKS5 URI. This conflicts with documentation that implies broad, curated, DNS-safe, and top-selection outputs.

This may be an acceptable degraded state only if it is explicitly labeled. Without health metadata, users cannot tell whether the pipeline is healthy, stale, sparse, fallback-only, or broken.

**Fix:** Add output-count regression tests and a public `health.json` or `artifact_manifest.json` that includes source count, parsed count, tested count, working count, chosen count, per-output byte size/hash, generated time, stale/degraded status, and reason codes.

**Priority:** P0/P1.

### C7. `/api/diff/proxies` appears incompatible with documented `proxies.json` schema

**Evidence level:** Reported source evidence.  
**Severity:** High.  
**Category:** API/data contract.

Reports state that the README documents `proxies.json` as an envelope with `metadata` and `proxies`, while `/api/diff/proxies` treats loaded `proxies.json` as an iterable list of proxy dictionaries. If the endpoint iterates the envelope object directly, it sees keys like `metadata` and `proxies` rather than proxy records, causing errors, incorrect diffs, or full reload fallback.

**Impact:** Differential updates become unreliable. Large datasets may be re-downloaded, damaging frontend performance and undermining the advertised update model.

**Fix:** Normalize accepted shapes before diffing. Support both legacy list and public envelope schemas during migration. Use distinct names such as `shard-proxies.jsonl` for shard intermediates and `proxies.json` for public envelope output.

**Priority:** P1.

### C8. Admin update endpoint can be unauthenticated if `ADMIN_API_KEY` is unset

**Evidence level:** Reported source evidence.  
**Severity:** High.  
**Category:** API security.

Reports say the admin notify endpoint enforces API-key validation only when `ADMIN_API_KEY` exists, while the README treats that key as optional production hardening. In a misconfigured public deployment, unauthenticated callers could trigger update broadcasts.

**Impact:** Client confusion, forced refresh storms, misleading update state, and avoidable availability risk.

**Fix:** Fail closed in production. Allow unauthenticated admin behavior only in explicit development/test/CI modes or behind an explicit `ALLOW_UNAUTH_ADMIN=true` flag.

**Priority:** P1.

### C9. Security documentation overstates automation hardening

**Evidence level:** Reported source evidence plus documentation drift.  
**Severity:** High.  
**Category:** Security governance.

Reports state that `SECURITY.md` claims minimal token permissions, pinned dependencies, non-root container operation, DOMPurify integration, and hardened frontend behavior, while workflows may grant broad permissions, containers may run as root, dependencies/actions may not be fully pinned, and frontend sanitization assets may not be evident in the inventory.

**Impact:** Security-sensitive users and contributors are told a stronger story than automation and shipped assets may enforce.

**Fix:** Turn security claims into executable checks: job-scoped workflow permissions, non-root runtime validation, lockfiles, action SHA pinning, frontend sanitizer presence checks, unsafe DOM API checks, gitleaks, dependency audit, and generated security posture docs.

**Priority:** P1.

### C10. Documentation and product claims are drifting from implementation and public output

**Evidence level:** Confirmed across reports.  
**Severity:** High.  
**Category:** Documentation, governance, product trust.

The reports repeatedly identify drift: Python version differences between README/About/workflows, Chain Laboratory strategy-count mismatch, shard-count mismatch between docs and source batches, protocol support claims requiring parser proof, stale module references, runtime freshness claims that do not match public outputs, and advanced capability claims that may be aspirational rather than implemented.

**Impact:** Users may choose the wrong outputs, contributors may follow obsolete architecture, and security-sensitive claims may become misleading.

**Fix:** Generate docs from manifests and current tree wherever possible. Mark features as stable, beta, experimental, deprecated, or aspirational. Add docs drift CI.

**Priority:** P1.

---

## 6. High-Priority Findings

### H1. Side-product archive appears suspiciously small

**Evidence level:** Confirmed public-output sample; contents need verification.  
**Severity:** High.  
**Category:** Output/archive health.

One report observed a very small public side-product archive content length, suggesting it may be empty or nearly empty. The docs imply rich side products and native client packs, so a tiny archive may indicate output generation, archive assembly, artifact upload, or Pages deployment failure.

**Fix:** Publish an archive manifest containing file count, byte sizes, checksums, generated time, expected minimums, and secret-scan results. Mark the archive degraded or fail the artifact if it falls below expected thresholds.

### H2. Public output freshness is not trustworthy

**Evidence level:** Confirmed public evidence in multiple reports, root cause needs verification.  
**Severity:** High.  
**Category:** Product reliability.

Reports describe a mismatch between public copy claiming frequent auto-updates and readable outputs that appear sparse, stale, or collapsed. Even if sparse output is intentional fallback behavior, users need explicit freshness and degradation metadata.

**Fix:** Add public badges and machine-readable status: last successful run, last artifact generation, last release, artifact counts, stale status, and error class.

### H3. Chain Laboratory documentation and UI disagree on strategy count

**Evidence level:** Confirmed public/docs drift.  
**Severity:** High/Medium.  
**Category:** Frontend/docs contract.

Reports identify drift between README, AGENTS/docs, and live Chain Laboratory visible strategy buttons. Since the Lab is a central differentiator, strategy count drift signals a missing source of truth.

**Fix:** Introduce `lab_strategies.json` with `id`, `name`, `description`, `stability`, required inputs, safe targets, output formats, and deployment modes. Generate UI buttons, docs, tests, and analytics labels from it.

### H4. Runtime version documentation is inconsistent

**Evidence level:** Confirmed docs/UI drift.  
**Severity:** Medium.  
**Category:** Documentation/runtime.

Reports mention Python version drift, such as README prerequisites saying Python 3.10+ while the public About page describes Python 3.12. This can be valid if 3.10 is minimum and 3.12 is deployed, but it must be stated explicitly.

**Fix:** Maintain one runtime/version manifest and generate README/About/workflow badges from it.

### H5. Dependency pinning and install paths do not match security claims

**Evidence level:** Reported source evidence.  
**Severity:** High.  
**Category:** Supply chain.

Reports say security docs claim pinned dependencies, while CI installs from broad dependency ranges or inconsistent files. `requirements.txt`, `pyproject.toml`, and any lockfile must be aligned.

**Fix:** Use `uv.lock`, `requirements.lock`, Poetry/PDM lockfiles, or compiled requirements. CI should install from the lock, verify the lock is fresh, and fail on drift.

### H6. Production defaults may conflict with the advertised security posture

**Evidence level:** Reported source evidence.  
**Severity:** High/Medium.  
**Category:** Security defaults, product modes.

One source-level audit reports that configuration defaults include `ALLOW_PRIVATE_IPS=True`, `INCLUDE_INSECURE_PROXIES=True`, `USE_VWARP_TUNNEL=True`, and broad GitHub Pages CORS while credentials are allowed. The same report says the README documents `USE_VWARP_TUNNEL=true` as defaulting to false, creating direct config/docs drift.

These settings may be valid for an anti-censorship fail-open mode, but they are not safe as implicit production defaults without clear labeling. Operators may believe private/insecure proxies are excluded when they are retained, or may run Vwarp unexpectedly.

**Fix:** Introduce explicit operating profiles: `strict-consumer-safe`, `anti-censorship-fail-open`, `development`, and `ci`. Generate docs from actual defaults and publish the active profile in metadata.

### H7. PR quality gates are missing or not clearly required

**Evidence level:** Reported source evidence and governance gap.  
**Severity:** High.  
**Category:** CI/testing.

Reports warn that quality checks may be concentrated in release workflows rather than a separate required PR workflow. Release validation is too late if broken code can merge first.

**Fix:** Add a required `ci.yml` for PRs with workflow linting, Python lint/type/tests, frontend tests, schema validation, manifest drift checks, security checks, and artifact fixture validation.

### H8. Frontend build story is unclear

**Evidence level:** Reported source/docs evidence.  
**Severity:** Medium.  
**Category:** Frontend tooling, documentation drift.

One report notes a documentation/tooling mismatch: the project is described as Vanilla JS/no-build in some places, while `package.json` and Vite-related files indicate a build/test toolchain exists. This may be acceptable if Vite is only for tests or optional development, but the docs must state the truth.

**Fix:** Document whether Vite is required for production, optional for development, or used only for tests/build checks. Add a frontend build manifest if generated assets are published.

### H9. Retest/schema validation appears non-blocking

**Evidence level:** Reported source evidence.  
**Severity:** High.  
**Category:** Release integrity.

Reports say schema validation is non-blocking in retest or release contexts. Public artifacts should not be published if they fail schema validation.

**Fix:** Make schema validation blocking for public release artifacts. Allow warnings only on exploratory/nightly branches.

---

## 7. CI/CD, GitHub Actions, Releases, and Deployment

### D1. Split release pipeline from PR quality gates

The reports repeatedly argue that CI does too much in the main release workflow. The pipeline should separate PR validation, scheduled aggregation, manual retest, Pages deploy, mirror deploy, and release packaging. Each workflow should have narrow permissions and a clear artifact contract.

**Required checks:** `actionlint`, YAML parsing, Python unit tests, parser fixtures, output schema validation, frontend fixture rendering, docs drift checks, dependency drift checks, and security scans.

### D2. Add workflow concurrency controls

Scheduled runs should not overlap. Push-triggered follow-on runs should not race with scheduled runs. Use workflow `concurrency` with an explicit queue/cancel policy, and avoid committing generated source-shard changes from the production aggregation job.

### D3. Make artifact expectations machine-checked

Shard count, expected artifacts, output filenames, side-product archive contents, Pages deploy inputs, and release assets should be recorded in a run manifest. The merge job should fail or mark degraded if expected shard artifacts are missing or corrupt.

### D4. Reduce merge and artifact I/O chokepoints

Reports warn that merging many SQLite files or uploading many artifacts from simultaneous matrix jobs can become a GitHub Actions bottleneck. Intermediate formats such as JSONL or Parquet may be safer for shard outputs. At minimum, record checksums and use robust merge validation.

### D5. Avoid rebuilding and repackaging too much on every schedule

Container builds, WASM builds, release packages, mirrors, and heavy front-end rebuilds should be keyed to input changes. Scheduled proxy aggregation should not rebuild unrelated assets unless their source changed.

### D6. Pin actions by SHA and narrow permissions per job

Using mutable tags such as `actions/checkout@v4` is common but weaker than immutable SHA pinning for a security-sensitive project. Top-level broad permissions should be replaced with job-scoped minimal permissions.

---

## 8. Backend, API, FastAPI Runtime, and WebSockets

### B1. Synchronous file and JSON parsing inside async routes can block the event loop

**Evidence level:** Needs source verification; reported by Gemini and consolidated reports.  
**Severity:** Medium/High.

`/api/diff/proxies` reportedly uses synchronous file reads and standard `json.loads()` on potentially large `proxies.json` payloads. For large datasets, this can block the FastAPI event loop and delay unrelated requests and WebSocket heartbeats.

**Fix:** Use `aiofiles` for file reads, `orjson` for faster parsing, ETag/If-None-Match where possible, and precomputed static patch artifacts when feasible.

### B2. WebSocket receive loops can leak or hang without heartbeat timeouts

**Evidence level:** Needs source verification.  
**Severity:** Medium.

Reports warn that an infinite `await websocket.receive_text()` loop can keep dead clients open if the network drops without TCP FIN. Broadcast loops can also be delayed by slow clients.

**Fix:** Add ping/pong heartbeat, `asyncio.wait_for` receive timeouts, per-client send timeouts, stale connection cleanup, and bounded message size.

### B3. Path resolution should use resolved containment

**Evidence level:** Needs source verification.  
**Severity:** Medium.

Reports mention path handling that uses character filters and `os.path.commonpath`, which can be fragile around symlinks or future directory changes.

**Fix:** Use `Path.resolve()` for both base and target, then require `target.resolve().is_relative_to(base.resolve())`.

### B4. Output routing needs a canonical manifest

**Evidence level:** Confirmed structural risk.  
**Severity:** High.

Output names are reportedly duplicated across README tables, server route maps, `/subscribe` aliases, generator scripts, CI release assets, and frontend cards.

**Fix:** Create `output_manifest.json` with filename, route, MIME type, subscription alias, client compatibility, schema, generator owner, docs label, and expected health fields. Generate server maps, docs tables, frontend cards, and CI checks from it.

### B5. Native side products may expose secrets

**Evidence level:** Needs source/policy verification.  
**Severity:** Medium/High.

WireGuard/OpenVPN/native packs can accidentally include inherited keys, endpoints, or user-provided secrets. Public publication requires secret scanning and clear policy.

**Fix:** Add archive secret scanning, redaction tests, and explicit public/private artifact boundaries.

One report specifically says the WireGuard side-product generator may build `.conf` files containing `PrivateKey` when available. That may be a legitimate client-export feature for private/local runs, but it is dangerous if the same artifact path is published publicly. The final policy should define which generated packs may contain secrets, which are public-safe, and which are local-only.

### B6. Pydantic settings mutation may bypass validation

**Evidence level:** Needs source verification; asserted by deep-systems review.  
**Severity:** Medium.

Gemini reports a Pydantic anti-pattern in which a dictionary defined at class level is overwritten in `model_post_init`, potentially bypassing schema validation for computed security settings such as blocked countries. If invalid environment values fail silently or crash later, configuration safety becomes brittle.

**Fix:** Verify the settings model. Prefer `@field_validator` or `@model_validator` for derived settings, and add tests for valid/invalid `BLOCKED_COUNTRIES`, private-IP flags, Vwarp flags, and security profile combinations.

### B7. Precomputed diff/patch artifacts may be better than dynamic server diffs

**Evidence level:** Strategic optimization from deep-systems review.  
**Severity:** Medium.

Several reports already identify the dynamic diff endpoint as risky. Gemini adds a concrete optimization: compute a JSON Patch/RFC 6902 or equivalent `proxies-patch.json` during the build pipeline, then serve it statically. This avoids server CPU and event-loop pressure.

**Fix:** Consider build-time patch generation only after the public schema is stabilized. Validate patch application against old/current fixture datasets.

---

## 9. Pipeline, Async Execution, State, Caching, and Concurrency

### P1. Synchronous history/cache saves in async pipeline

Reports warn that `history.save()` or `test_cache.save()` may run synchronously near pipeline shutdown while other cleanup is offloaded to an executor. Slow disk writes or SQLite commits can stall shutdown and event streams.

**Fix:** Make persistent writes explicit, bounded, and cancellation-safe. Use executor/off-thread writes or async-safe storage APIs consistently.

### P2. `seen_keys` smart eviction may be documented but not implemented

A deep-systems review states that docs describe smart eviction of `seen_keys`, while code allegedly initializes a basic dictionary with no eviction. If true, large runs can grow memory until CI OOM.

**Fix:** Verify implementation. If missing, implement bounded LRU/ordered eviction or a tested Bloom/filter strategy with memory ceilings.

### P3. Shard-local Bloom filters cause redundant testing

Reports warn that per-shard dedupe cannot prevent different matrix jobs from testing the same proxy if duplicated across source batches.

**Fix:** Add pre-flight global deduplication or a merge-aware dedupe strategy. At minimum, measure duplicate rate across shards and feed that back into source batching.

### P4. Missing tester semaphore can exhaust file descriptors and ports

Gemini reports that a missing `test_budget` semaphore can allow thousands of Python fallback sockets. Even with semaphores, high churn can exhaust ephemeral ports due to `TIME_WAIT`.

**Fix:** Enforce global socket budgets, per-protocol concurrency, rate limits, TCP lifecycle tuning where safe, and CI stress tests for `Too many open files` and `EADDRNOTAVAIL`.

### P5. Cancellation and hard timeouts can corrupt state

Reports warn that cancelling consumers during synchronous DB/file writes can leave history/cache databases corrupt.

**Fix:** Shield critical writes, use atomic temp-file replacement, WAL/integrity checks, and resumable state formats.

### P6. Queue shedding can poison source quality metrics

If overloaded queues drop a random portion of parsed configs, a good source can appear to have poor yield during runner/network spikes.

**Fix:** Track dropped counts separately from failed validation/testing. Do not penalize sources for queue pressure or global runner anomalies.

### P7. Adaptive concurrency can misread runner/network noise

**Evidence level:** Strategic risk from deep-systems review.  
**Severity:** Medium/High.

Gemini warns that adaptive timeout/worker logic can mistake noisy GitHub Actions runner networking for proxy failure. If adjacent-tenant load or Azure network jitter spikes latency, the adaptive worker pool may throttle too aggressively or mark healthy proxies as failed.

**Fix:** Separate runner-health signals from proxy-health signals. Track global latency anomalies, source-wide failure spikes, DNS/API failures, and runner network health before penalizing proxies or sources.

### P8. Artifact upload throttling can break matrix merges

**Evidence level:** Strategic CI risk from deep-systems review.  
**Severity:** Medium/High.

If 14-17 matrix shards finish at roughly the same time and upload artifacts concurrently, GitHub artifact APIs may throttle or fail. This can create partial merge state even when shard processing succeeded.

**Fix:** Stagger uploads, retry with backoff, record expected artifacts in `run_manifest.json`, and make the merge job distinguish missing, corrupt, late, and empty artifacts.

---

## 10. Data Model, Identity, History, and Source Quality

### M1. Proxy identity may be too fragile for historical reliability

Reports warn that an ID based on protocol, host, port, and credential resets history when public providers rotate UUIDs/passwords. That loses reliability data.

**Fix:** Consider separating stable node identity from credential identity. Track `(protocol, host/asn, port, transport, sni/path)` plus credential revisions.

### M2. Proxy identity may collapse multi-transport nodes

Reports warn that VLESS/VMess/Trojan can share host, port, and credential but differ by transport, path, SNI, gRPC service name, HTTPUpgrade, or network type. If ID excludes these, one config can overwrite another.

**Fix:** Include transport and routing-critical details in uniqueness keys and output IDs.

### M3. SourceQualityTracker can be poisoned by adversarial timing

An adversary can temporarily block high-quality sources only during scheduled CI windows. The quality tracker may mark those sources as bad, weaponizing the project against itself.

**Fix:** Detect global network anomalies when many historically good sources fail simultaneously. Quarantine failures during runner/network anomalies and use EWMA/recency weighting.

### M4. Historical trust should decay toward recent behavior

**Evidence level:** Strategic risk from deep-systems review.  
**Severity:** Medium/High.

Gemini warns that static historical averages can be dangerous if a previously trustworthy source is seized or starts publishing honeypots. A long history of good behavior can mask recent malicious behavior.

**Fix:** Use EWMA or another recency-weighted model. Keep long-term reputation, but let the last 24-72 hours strongly affect source trust, honeypot suspicion, and quarantine state.

---

## 11. Fetching, SSRF Boundaries, DNS, GeoIP, and External Services

### F1. Source fetching needs SSRF-grade validation

The project fetches hostile public sources. Reports call for private-range blocking, redirect validation, credential masking, response-size caps, timeout ceilings, binary payload handling, and sanitized logs.

**Fix:** Validate URLs before fetch and after redirects. Resolve DNS and reject loopback, private, link-local, multicast, metadata endpoints, Docker bridge ranges, and bogon addresses.

### F2. DNS cache poisoning and post-resolution bogon filtering

Scraped configs may use domain names that resolve to private or local addresses. Validation must happen after DNS resolution as well as before fetch.

**Fix:** Add post-DNS bogon/RFC1918 filters and malicious-source accounting.

### F3. GeoIP RAM duplication can hurt CI runners

If GeoIP databases are loaded separately in many processes, memory can balloon.

**Fix:** Use memory-mapped MaxMind readers and shared process initialization where possible.

### F4. Optional external APIs need hard zero-budget fallbacks

VirusTotal, Cloudflare, Google Drive, Hugging Face, IPFS, Telegram, or GeoIP enrichments must be optional, rate-limited, and disabled safely.

**Fix:** Publish external-service state in metadata as required/optional/disabled/degraded.

---

## 12. Parsers, Protocol Coverage, Normalization, and Drop Reasons

### PR1. Parser contracts need adversarial fixtures

Reports call for fixtures covering bad Base64, trailing garbage, percent-encoded credentials, invalid UUIDs, empty passwords, alias schemes, huge lines, private hosts, malicious remarks, and malformed query parameters.

**Fix:** Define a parser contract: accepted schemes, required fields, normalized output model, drop reason taxonomy, max field lengths, and malicious input handling.

### PR2. Protocol support claims require generated proof

README and public pages claim broad protocol support, but visible parser filenames only prove a subset. Other protocols may live in `others.py` or generic parsing, but this needs tests.

**Fix:** Generate a protocol matrix from tests: parser support, tester support, converter support, output support, known losses, and docs labels.

### PR3. `others.py` can become a protocol graveyard

If many high-value protocols are concentrated in a miscellaneous parser, ownership and tests become unclear.

**Fix:** Split high-value protocols into dedicated modules or maintain a registry mapping schemes to parser/tester/converter owners.

---

## 13. Tester Stack: Go, Python, Rust, WASM, and Contract Drift

### T1. Tester implementations need one contract

The reports identify Go sidecar, Python fallback, Lab tester, WASM assets, Rust `ss_checker`, and possible uTLS helpers. These can drift in payload format, timeout behavior, protocol coverage, and error taxonomy.

**Fix:** Define one input JSON schema, output JSON schema, error taxonomy, timeout model, and protocol support matrix. Run every tester implementation against shared fixtures.

### T2. Go tester JSON-array payload must be regression-tested

Reports call out a known issue class: subprocess input must be a valid JSON array, not concatenated JSON objects or partial streams.

**Fix:** Unit-test stdin payload shape for zero, one, and many proxies.

### T3. Browser WASM cannot test arbitrary raw TCP/UDP proxies

Gemini strongly argues that browser WASM cannot open arbitrary TCP/UDP sockets. Browser-side testing is limited to HTTP(S), WebSocket, WebTransport, WebRTC, or worker-mediated paths subject to CORS and browser sandboxing.

**Fix:** Mark raw browser testing claims as unsupported unless bridged by a Worker/server. Lab docs should distinguish browser-local parsing/export from actual connectivity testing.

### T4. Rust FFI panic boundaries need verification

Reports warn that Rust panics across FFI can crash Python with undefined behavior or segmentation faults.

**Fix:** Wrap Rust exports with `catch_unwind`, return error codes, expose explicit free APIs, and fuzz malformed configs at the FFI boundary.

### T5. Go sidecar IPC optimization is a roadmap idea, not a current fix

**Evidence level:** Strategic enhancement from deep-systems review.  
**Severity:** Low/Medium.

Gemini suggests compiling the Go tester as a C-shared library and using `ctypes`/`cffi` to reduce IPC overhead. This may improve performance, but it also increases FFI risk and operational complexity.

**Fix:** Treat this as a later optimization only after JSON/NDJSON tester contracts, timeouts, process lifecycle, and output correctness are stable. If adopted, require FFI fuzzing and panic boundaries similar to the Rust checker.

---

## 14. WARP/Vwarp, Washing, Revival, Active Scanning, and Abuse Risk

### W1. Revival retention semantics need tests

Reports repeatedly say WARP/Vwarp revival is central but unverified. The system must prove that failed proxies can be washed, retested, tagged, retained, and published correctly.

**Fix:** Add E2E tests for failed proxy -> WARP wash -> retest success, failed proxy -> Vwarp fallback -> revived output, WARP unavailable -> degraded metadata.

### W2. Cloudflare WARP anti-abuse can false-fail revived proxies

GitHub Actions runner IPs may trigger Cloudflare anti-abuse if they register or handshake many WARP tunnels. The pipeline may misclassify Cloudflare rate limiting as proxy failure.

**Fix:** Rotate WARP endpoints, back off registration, distinguish WARP endpoint failure from proxy failure, and publish WARP health separately.

### W3. Vwarp subprocess lifecycle can leave orphan processes

Gemini reports a risk that `vwarp` subprocesses may outlive the parent on timeout/crash and keep ports open.

**Fix:** Bind child lifecycle to parent, use process groups, cleanup traps, timeout enforcement, and post-run port checks.

### W4. Active scanners must be bounded and opt-in

Reports warn that clean-IP discovery and scanner-like tools must be explicitly bounded.

**Fix:** Add user consent, dry-run mode, rate limits, target allowlists, no private/reserved ranges, legal/ToS warnings, randomized traversal where appropriate, and scanner guardrail tests.

### W5. VirusTotal lookups can disclose evasion nodes

Reports warn that submitting live evasion nodes to third-party reputation services may disclose infrastructure.

**Fix:** Disable VT for live candidates by default. Prefer offline blocklists or local datasets for sensitive paths.

### W6. Canary proxies and active-probing detection are experimental

**Evidence level:** Strategic roadmap idea.  
**Severity:** Strategic.

One roadmap proposal suggests controlled canary proxies to detect censor active probing and dynamically update blocklists. This could be valuable, but it changes the project from passive aggregation into active threat instrumentation.

**Fix:** Keep this out of stable docs unless implemented with owned infrastructure, legal review, clear user disclosure, and strict separation from public user-submitted proxy lists.

---

## 15. Output Generation, Client Formats, Archives, and Compatibility

### O1. Artifact manifest is the central missing contract

The most repeated remediation is a public artifact manifest containing every output file, schema, byte size, checksum, generated time, source stats, stale/degraded state, and reason codes.

**Fix:** Publish `artifact_manifest.json` and make deploy/release validation depend on it.

### O2. Converter/generator duplication needs clear ownership

Both converter and generator packages reportedly contain Clash and sing-box logic. This may be intentional, but it needs a boundary.

**Fix:** Define converters as model-to-client-object mappers and generators as serializers/writers. Add snapshot tests for every emitted format.

### O3. Clash vs Mihomo compatibility must be loss-aware

Reports warn that standard Clash may not support VLESS/Reality/Hysteria2 the way Mihomo/Clash.Meta does.

**Fix:** Generate `clash.yaml` and `mihomo.yaml` separately, with explicit protocol inclusion/exclusion and warnings.

### O4. Output cache busting and freshness must be visible

Users and clients need to know whether a file is fresh, stale, generated from fallback, or sparse.

**Fix:** Add generated comments where client formats allow them; otherwise rely on manifest metadata, stable ETags, versioned URLs, and public badges.

### O5. Config Forge and protocol mutation claims need proof

**Evidence level:** Strategic/docs critique from deep-systems review.  
**Severity:** Medium for docs truthfulness.

Gemini argues that docs around a "Config Forge" or mutation engine may imply active protocol hardening, TLS fingerprint mutation, padding, or obfuscation wrapping, while converters may simply perform static schema translation. If true, this is a documentation-truth problem.

**Fix:** Split claims into what converters do today and what future mutation features might do. If mutation is implemented, add tests showing actual changes to output fingerprints, transport settings, padding, fragmentation, and client compatibility.

---

## 16. Metadata, Schemas, Manifests, and Frontend/Data Contracts

The reports converge on one architectural fix: make contracts explicit and generated.

Required contracts:

- `artifact_manifest.json`: every artifact, size, hash, schema, generated time, degradation state.
- `output_manifest.json`: output names, routes, MIME types, aliases, client compatibility, docs labels.
- `metadata.schema.json`: every backend-produced field and every frontend-consumed field.
- `lab_strategies.json`: Chain Lab strategies and safety metadata.
- `protocol_matrix.json`: parser/tester/converter/output support by protocol.
- `tester_contract.schema.json`: tester input/output/error taxonomy.
- `run_manifest.json`: workflow run metadata, shard counts, artifact counts, deploy SHA, Pages URL.

These manifests should generate README tables, frontend cards, server routes, CI expectations, and docs fragments. Manual lists should become the exception.

---

## 17. Frontend, Static Fallbacks, UX, Accessibility, and Trust Signals

### FE1. Static/no-JS UX must be useful

The static site should show direct downloads, latest known status, generated time, stale/degraded labels, and safe fallback text without requiring JavaScript.

### FE2. Wiki/docs should not be JavaScript-dependent

Documentation must be readable offline and with scripts disabled. Search and navigation can be progressive enhancements.

### FE3. Frontend must treat proxy/source data as hostile

Remarks, SNI, paths, tags, source URLs, and country labels may be attacker-controlled.

**Fix:** Avoid raw `innerHTML`, add sanitizer utilities, enforce field length/character constraints, test malicious fixture rendering, and use CSP where possible.

### FE4. Trust/status badges should be first-class

Recommended badges: `fresh`, `stale`, `degraded`, `fallback`, `tested`, `untested`, `revived`, `dns-safe`, `chain`, `experimental`, `manual verification recommended`.

### FE5. Frontend smoke tests should fail on specific placeholder strings

The complete audit names concrete production strings that should never leak after build or hydration: `{sources}`, `{hours}`, `...`, `checking...`, all-zero loaded metric cards, and ambiguous "Last updated: checking..." states.

**Fix:** Add static and hydrated DOM tests that fail if these strings appear in production output outside explicitly documented fallback text.

---

## 18. Chain Laboratory, Offline Lab, Scanner UX, and Browser Limits

The Chain Laboratory is repeatedly described as a strong product idea with visible drift and safety risk. The final report should treat it as important but requiring contract discipline.

Required Lab contracts:

- Strategy manifest.
- Local-only vs transmitted secret labels.
- Scanner consent and rate-limit policy.
- Offline fixture tests for parse -> clean IP discovery -> chain build -> test -> export.
- Clear distinction between browser-local operations and backend/Worker-mediated network testing.

The exact live strategy names reported by the audit-prep and complete-audit reports should be preserved until a manifest replaces them: WARP Tunnel, Vwarp Masque, Vwarp AtomicNoize, Double WARP, WARP+Psiphon, Relay Chain, TLS Fragment, CDN Worker Relay, and Custom Chain.

Roadmap ideas from the reports include visual topology builders, latency/traceroute widgets, survival-rate charts, evasion efficacy matrices, and interactive evasion tuning. These should be kept as roadmap items, not mixed with P0 defects.

---

## 19. Security, Secrets, CORS, XSS, Supply Chain, and Container Posture

### S1. CORS policy is too broad if credentialed/admin APIs exist

Reports mention a regex like `https://.*\.github\.io`, which trusts arbitrary GitHub Pages origins.

**Fix:** Use exact allowed origins for credentialed endpoints. Separate public static artifact access from credentialed APIs.

### S2. Rate limiting by IP can punish censored-region users behind CGNAT

Subscription downloads should generally be static/CDN-served rather than dynamically rate-limited by source IP.

### S3. Dependency and action pinning are insufficient

Use lockfiles and pin third-party GitHub Actions to immutable SHAs for high-trust release paths.

### S4. Root container execution contradicts non-root posture

If the workflow runs containers as root, security docs must say so or the workflow must stop doing it.

### S5. AES-GCM nonce and steganography claims need reality checks

Gemini raises nonce entropy and LSB image/CDN optimization concerns. These should be verified with code and deployment tests before docs claim robust encrypted/steganographic delivery.

Gemini specifically warns that LSB image payloads can be destroyed by CDN/image optimization, EXIF stripping, recompression, or any lossy transformation. If steganographic delivery remains documented, it needs deployed-artifact integrity tests that fetch through the real CDN and verify the payload can still be extracted and authenticated.

### S6. Security contact placeholders must be removed

The audit corpus flags placeholder security contact information in `SECURITY.md`. Security-sensitive projects need a real contact, disclosure process, and response expectation. Placeholder text weakens trust and can delay vulnerability reporting.

**Fix:** Provide a valid security email, GitHub Security Advisory process, or documented issue-label process, and make sure the policy is current.

### S7. Public proxy safety copy should be explicit

The audit-prep report notes that the homepage correctly warns against using public proxies for sensitive accounts, but the product framing can still sound broadly "secure." Public proxies are untrusted transports.

**Fix:** Add a privacy model: public proxies may help reach blocked content, but they are not safe for credentials, banking, private accounts, or sensitive personal data unless end-to-end encryption and user threat model support that use.

---

## 20. Documentation Drift, Governance, Dead Code, and Cleanup

Reported cleanup targets include:

- Empty root files such as `NL` and `US`.
- Empty or stale `docs/DEBT_MATRIX.md`.
- Duplicate `docs/encyclopedia` and `docs/wiki/encyclopedia` paths.
- Multiple Home page docs.
- Historical references to removed paths such as `pipeline_core`, `fetcher_core`, `output_handler.py`, or vendored frontend libraries.
- Drift between README, AGENTS, STATUS, CHANGELOG, architecture/devops/frontend/API wiki pages, About page, and live outputs.
- Test families with overlapping names such as old/new/comprehensive/coverage-boost variants.
- Security contact placeholders in `SECURITY.md`.
- Root or generated-looking files such as `consolidated_sources.txt`, `NL`, `US`, and output-related files whose ownership is unclear.

**Fix:** Establish a canonical architecture map generated from the current tree, archive historical docs, enforce removed-file guard lists, and add docs drift CI.

---

## 21. Testing Strategy and Regression Matrix

### P0 tests

- Workflow YAML parsing and `actionlint`.
- Output manifest validation.
- Metadata schema validation.
- Public degraded-state frontend fixture.
- Empty/sparse output publication.
- `/api/diff/proxies` envelope/list compatibility.
- Admin auth fail-closed.
- Artifact count/byte-size/hash validation.
- Parser hostile-input fixtures.
- Go tester JSON-array payload shape.
- XSS fixture rendering.

### P1 tests

- Shard count and source-batch consistency.
- Lab strategy manifest drift.
- Protocol support matrix generation.
- WARP/Vwarp degraded behavior.
- Side-product archive manifest and secret scan.
- Dependency lock drift.
- Action SHA pinning check.
- CORS exact-origin check.
- SSRF post-DNS bogon filtering.

### P2/P3 tests

- Large-output frontend performance budgets.
- GeoIP memory mapping behavior.
- Rust FFI fuzzing.
- Ephemeral port exhaustion stress tests.
- Chain generation snapshots.
- Clash/Mihomo compatibility snapshots.
- Optional external-service degradation fixtures.

---

## 22. Refactor and Architecture Roadmap

### Phase 0: Stop the bleeding

Fix workflow syntax, self-triggering, deploy gating, admin auth, public degraded state, and manifest absence.

### Phase 1: Stabilize contracts

Introduce artifact, output, metadata, lab, protocol, tester, and run manifests. Generate docs/server/frontend/CI expectations from them.

### Phase 2: Separate stages and reduce coupling

Clarify fetch, parse, validate, test, rank, revive, convert, generate, publish boundaries. Separate converters from generators and core pipeline from optional mirrors/bots/labs.

### Phase 3: Tier optional and experimental features

Mark WARP/Vwarp, steganography, WASM testing, BYOW, domain fronting, autonomous intelligence, Rust FFI, and active scanning as stable/beta/experimental/deprecated with explicit tests and safety limits.

### Phase 4: Clean and enforce governance

Archive stale docs, remove empty files, rationalize tests, enforce removed-file guards, and make documentation drift fail CI.

---

## 23. Product, UX, and Advanced Feature Roadmap

Immediate product trust improvements:

- Current run health panel.
- Output freshness badges.
- Degraded/fallback reason codes.
- Recommended safe output guidance.
- Static no-JS download page.
- Public status manifest.

Frontend/Lab improvements:

- Lab strategy manifest.
- Local-only secret handling.
- Safer scanner UX.
- Offline mocked lab workflow tests.
- Large-output pagination/virtualization.
- Survival-rate and output-health charts.

Advanced roadmap ideas to keep explicitly experimental:

- Visual topology builder.
- Real-time traceroute/latency visualization.
- Evasion efficacy matrix by ASN/technique.
- Dynamic routing or Smart Chains v2.
- BYOW provisioning.
- Canary/honeypot detection.
- Protocol translation/Config Forge.
- WebRTC/WebTransport-based limited browser verification.
- Threat-hunting dashboards.

These are not prerequisites for stabilizing the current product.

---

## 24. Prioritized Remediation Plan

### Fix first

1. Validate and fix all workflow YAML.
2. Stop workflow self-trigger loops and add concurrency.
3. Replace fail-closed empty-output deploy checks with schema-valid degraded outputs.
4. Add artifact/output/metadata manifests.
5. Fix `/api/diff/proxies` schema compatibility.
6. Make admin auth fail closed in production.
7. Pre-render honest static frontend fallback.
8. Add public health/degraded metadata.
9. Align security docs with actual controls.
10. Add required PR quality gates.

### Highest ROI next

1. Generate README/server/frontend/CI output lists from `output_manifest.json`.
2. Generate Lab UI/docs/tests from `lab_strategies.json`.
3. Generate protocol support docs from tests.
4. Add parser/tester/frontend malicious fixtures.
5. Split core zero-budget mode from optional integrations.
6. Clean empty files and duplicate docs.
7. Rationalize test suites.

### Must verify in a real checkout

1. Workflow indentation and permissions.
2. `/api/diff/proxies` implementation.
3. Admin auth implementation.
4. CORS configuration.
5. Parser support matrix.
6. Go/Python/Rust/WASM tester contracts.
7. WARP/Vwarp retention and subprocess lifecycle.
8. Frontend sanitizer and DOM rendering.
9. Side-product archive contents.
10. Docker root/non-root behavior.

---

## 25. Real-Checkout Verification Checklist

- Run `actionlint` and YAML parser over all workflows.
- Run `git grep`/AST checks for output filename duplication.
- Run schema validation for public `proxies.json`, `metadata.json`, and all generated artifacts.
- Decode and compare `base64.txt`, `chosen/base64.txt`, and DNS-safe outputs.
- Inspect side-product archive file count and secret scan.
- Run a sparse-output/zero-working-proxy dry deploy.
- Run frontend static fixture tests with JS disabled.
- Run Playwright fixture tests for healthy, stale, empty, malformed, and degraded metadata.
- Run parser adversarial fixtures.
- Run tester contract fixtures across Go/Python/Rust/WASM where applicable.
- Run SSRF/DNS bogon tests.
- Run CORS/admin auth tests.
- Run WARP/Vwarp unavailable tests.
- Run docs drift and manifest generation checks.

---

## 26. End-to-End Workflow Verification Matrix

This matrix consolidates the end-to-end workflow checklist into regression targets. These workflows should become executable fixtures, not only documentation.

| Workflow | Current consolidated status | Verification target |
| --- | --- | --- |
| Source ingestion -> parsing -> validation -> testing -> ranking -> outputs | Needs source and runtime verification. Public counters suggest either pipeline degradation or frontend metadata failure. | Run a local shard with fixture sources and assert counts at each stage. |
| Failed proxy -> WARP/Vwarp washing -> retesting -> revived output | Needs source verification. Public revived/WARP/VWARP counters reportedly show zero or placeholders without reason. | Mock WARP/Vwarp success, failure, and unavailable states; assert tags, retained candidates, and metadata. |
| Valid proxy -> smart chain generation -> chain output | Needs source verification. Docs mention chain outputs while public chain counters are weak/zero. | Use fixture proxies to generate chain output and validate client schemas. |
| DNS-safe output generation | Needs source verification. Public docs advertise DNS-safe/hardened profiles without clear artifact health. | Generate DNS-safe outputs from mixed host/IP fixtures and validate expected inclusion/exclusion. |
| CI shard processing -> partial artifacts -> merge -> Pages deploy | Not verified in this consolidation. | Inspect workflow matrix, shard count, artifact upload/download, merge rules, deploy directory, and Pages URL. |
| Local Docker run | Not verified. | Build and run Docker image with fixture inputs; confirm non-root behavior and output paths. |
| Local native run | Not verified. | Run CLI/package entry points from a clean environment and compare outputs to fixture snapshots. |
| Frontend dashboard loading metadata and outputs | Publicly broken or degraded according to several reports. | Render healthy, stale, missing, malformed, and degraded metadata fixtures with JavaScript enabled and disabled. |
| Proxies page loading, filtering, exporting | Not verified. | Test large `proxies.json`, filtering, export, virtual scrolling/pagination, and empty states. |
| Analytics page reading stats | Not verified; public/static view reportedly shows zero stats. | Test analytics with full, sparse, stale, and failed-run metadata. |
| Laboratory parse -> clean IP discovery -> chain build -> test -> export | Partially verified from UI only. | Run offline Lab fixture with mocked clean IPs and mocked tester responses. |
| Offline lab/scanner/runner | Partially verified from route/UI only. | Confirm downloads, local-only behavior, scanner guardrails, and no unsafe default scanning. |
| Error/empty-output workflow | Publicly weak. | Simulate no sources, malformed sources, parsed-but-none-working, tester unavailable, and WARP unavailable. |
| Tester unavailable workflow | Needs source verification. | Disable Go tester and assert Python fallback or explicit degraded metadata. |
| WARP/Vwarp unavailable workflow | Needs source verification. | Disable WARP/Vwarp and assert outputs remain valid with clear reason codes. |

---

## 27. Detailed Verification Backlog

This backlog is the actionable verification queue for a follow-up source audit. It is deliberately explicit so future code-audit work can check items off without rediscovering them.

### 29.1 Repository and Governance Files

- Verify `.env.example` documents every required and optional environment variable.
- Verify `.gitleaks.toml` is current and CI-enforced.
- Verify `.pre-commit-config.yaml` runs the same checks as CI, or document the difference.
- Verify `AGENTS.md` reflects the current architecture and removed-file guard list.
- Verify `CHANGELOG.md` is historical, not the current architecture source of truth.
- Verify `CONTRIBUTING.md` commands match current package scripts and CI.
- Verify `KNOWN_ISSUES.md` matches current known public failures.
- Verify `QUICKSTART.md` works from a clean checkout.
- Verify `README.md` output lists, protocol lists, shard count, runtime version, schedule, and security claims are generated or checked.
- Verify `SECURITY.md` has real contact details, accurate permissions, accurate dependency-locking claims, and current frontend sanitizer claims.
- Verify `STATUS.md` does not overclaim production readiness, audit status, security posture, or output health.
- Verify `Dockerfile` and `docker-compose.yml` run as non-root where claimed and match local/CI paths.
- Verify `render.yaml` is optional and documented as outside the zero-budget GitHub Pages reference deployment.
- Verify `package.json`, `package-lock.json`, and `vite.config.mjs` define whether the frontend is buildless, Vite-built, or test-only.
- Verify `pyproject.toml`, `requirements.txt`, and `requirements-prod.txt` have lockfile parity and no silent dependency drift.
- Verify `mypy.ini`, lint configs, and pytest config are actually enforced in required PR checks.

### 29.2 Workflow and Deployment Files

- Validate `ci.yml`, `deploy-pages.yml`, `deploy_mirror.yml`, `main.yml`, `release.yml`, and `retest.yml` with `actionlint` and a YAML parser.
- Check every `env:` block for indentation, especially keys such as `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`, `CS_PUBLIC_KEY`, and `CS_IPNS_KEY`.
- Confirm workflow schedules match the documented "every 4 hours" behavior.
- Confirm comments do not mention stale "3-hour" or alternating schedules.
- Confirm push triggers cannot be caused by production source-shard commits.
- Confirm workflow `concurrency` prevents overlapping scheduled runs.
- Confirm job permissions are least privilege and not broad at top level unless necessary.
- Confirm Pages deployment publishes the exact directory the frontend expects.
- Confirm merge jobs fail or mark degraded on missing/corrupt shard artifacts.
- Confirm release assets match `artifact_manifest.json`.
- Confirm retest schema validation is blocking for public artifacts.
- Confirm mirror deploys are optional and cannot break the core Pages output.
- Confirm Docker/image/WASM builds are cached or only run when relevant inputs change.

### 29.3 Backend/API Routes

- Verify `/api/diff/proxies` supports both legacy list and envelope-shaped `proxies.json`.
- Verify diff implementation does not block the event loop on large files.
- Verify `/api/proxies` supports pagination, projection, protocol/country filters, and does not default to huge full payloads for common UI paths.
- Verify `/api/admin/notify-update` fails closed in production.
- Verify CORS uses exact origins for credentialed/admin endpoints.
- Verify WebSocket connection manager has heartbeat, idle timeout, bounded broadcast concurrency, message-size limits, and cleanup telemetry.
- Verify static page serving uses resolved path containment and safe route allowlists.
- Verify `/api/lab/test-chain` and similar Lab endpoints return useful manual fallback instructions on 503/unavailable.
- Verify output routes and `/subscribe` aliases are generated from `output_manifest.json`.
- Verify dynamic APIs are not required for the static GitHub Pages baseline unless explicitly documented as optional.

### 29.4 Pipeline and State

- Verify producer/consumer queues are bounded and backpressure is intentional.
- Verify CPU-heavy parsing runs in executors or safe workers.
- Verify no blocking file/DB/network calls occur inside hot async paths.
- Verify `history.save()`, `test_cache.save()`, and source-quality writes are cancellation-safe.
- Verify state writes are atomic and recoverable after timeout.
- Verify `seen_keys` or equivalent dedupe state has a real memory ceiling.
- Verify shard-local dedupe does not waste excessive test budget on duplicate proxies.
- Verify queue shedding is source-aware and does not corrupt source-quality scoring.
- Verify global runner/network anomaly detection prevents mass false source penalties.
- Verify cache keys are stable and do not create unbounded per-run cache sprawl.
- Verify partial artifacts are merged with checksums and schema validation.

### 29.5 Fetching and Source Ingestion

- Verify source URL validation blocks loopback, private, link-local, multicast, metadata endpoints, and Docker bridge ranges.
- Verify DNS rebinding and post-resolution private-IP checks.
- Verify redirect handling preserves SSRF constraints.
- Verify response byte limits, streaming reads, binary/non-UTF8 handling, and decompression safety.
- Verify malformed URLs and credentials-in-URL are sanitized in logs.
- Verify timeouts are adaptive but bounded.
- Verify circuit breakers are per-source or per-host and do not suppress unrelated sources.
- Verify retry behavior avoids hammering unreliable public endpoints.
- Verify source failures are represented in metadata and frontend degraded-state messages.
- Verify public/free external APIs are optional and rate-limited.

### 29.6 Parsers and Normalization

- Verify every documented protocol has valid fixtures, malformed fixtures, parser support, normalization support, tester support, converter support, and output support.
- Verify aliases such as `ss`, `shadowsocks`, `vmess`, `vless`, and client-specific variants normalize consistently.
- Verify UUID validation for VMess/VLESS.
- Verify Shadowsocks method validation and credential parsing.
- Verify Base64 decoding tolerates padding errors and trailing garbage safely.
- Verify percent-decoding cannot trigger crashes or injection.
- Verify parser return contracts are uniform.
- Verify parser drop reasons are counted and surfaced in metadata.
- Verify unsupported protocols are rejected with structured reasons rather than silent drops.
- Verify `others.py` is not an untested protocol graveyard.
- Verify parser fields such as remarks, SNI, path, host, service name, ALPN, fingerprint, and tags are length-limited and sanitized.

### 29.7 Tester Stack

- Verify Go tester accepts valid JSON arrays and rejects malformed concatenated payloads.
- Verify Python caller serializes payloads safely and checks tester exit status.
- Verify timeout classification distinguishes network timeout, protocol mismatch, tester crash, DNS failure, WARP failure, and unsupported protocol.
- Verify three-consecutive-timeout or daemon-restart behavior is implemented if documented.
- Verify tester-unavailable mode still generates useful outputs with clear degraded metadata.
- Verify chain testing uses the same schema discipline as native testing.
- Verify Sing-box/Xray/Clash compatibility tests exist.
- Verify WASM/browser tester claims are limited to browser-feasible transports.
- Verify Rust `ss_checker` is active, experimental, or dead; if active, verify FFI panic/memory safety.
- Verify socket and ephemeral-port budgets under high-volume tests.

### 29.8 WARP/Vwarp, Lab, and Scanners

- Verify WARP/Vwarp revival retains failed-but-revived candidates with explicit tags when appropriate.
- Verify WARP unavailable, Vwarp unavailable, bad key, no candidates, and all-failed-candidates cases.
- Verify WARP endpoint rotation and anti-abuse backoff if WARP registration is automated.
- Verify WireGuard MTU handling, especially around MTU 1280 and UDP-heavy protocols.
- Verify Vwarp subprocesses are bound to parent lifecycle and cleaned up on timeout/crash.
- Verify scanner UI requires consent and uses safe default targets.
- Verify scanner code rejects private/reserved ranges and has rate limits.
- Verify Lab secrets are local-only unless explicitly transmitted.
- Verify Lab avoids localStorage for secrets by default.
- Verify Lab logs and errors redact WARP keys, worker URLs, tokens, UUIDs, and passwords.
- Verify offline scanner/runner downloads exist and match docs.

### 29.9 Output Artifacts and Manifests

- Verify `base64.txt`, `chosen/base64.txt`, `base64-dns-safe.txt`, `clash.yaml`, `mihomo.yaml` if added, `singbox.json`, `singbox-vpn.json`, `singbox-chains.json`, `revived.json`, `proxies.json`, protocol-specific outputs, DNS-safe outputs, DNS-hardened outputs, side-product archives, and client adapters.
- Verify universal and chosen outputs are intentionally different or explicitly marked degraded.
- Verify all JSON/YAML outputs parse.
- Verify Base64 outputs decode to valid lines.
- Verify atomic writes prevent half-written artifacts.
- Verify empty-run skeletons exist for every documented output.
- Verify output item counts, byte sizes, hashes, generated times, and schema versions are in `artifact_manifest.json`.
- Verify side-product archive contains expected files and passes secret scanning.
- Verify public WireGuard/OpenVPN packs cannot leak private material unintentionally.
- Verify adapter outputs for Shadowrocket, Surge, Loon, Quantumult X, SIP008, Xray, Clash/Mihomo, and Sing-box are loss-aware.
- Verify standard Clash output drops unsupported VLESS/Reality/Hysteria2 nodes or routes them to Mihomo-only output.

### 29.10 Frontend and UX

- Fail production builds if `{sources}`, `{hours}`, `...`, `checking...`, or all-zero loaded metric states leak outside explicit fallback text.
- Verify homepage, proxies page, analytics page, lab page, offline lab, wiki, and about page work with JavaScript disabled at baseline.
- Verify metadata loader validates schema and transitions through loading, loaded, stale, degraded, failed, and offline states.
- Verify frontend data access is centralized rather than duplicated across pages.
- Verify proxy/source fields render as text, not HTML.
- Verify sanitizer dependency or vendored asset is present if docs claim it.
- Verify CSP policy and unsafe DOM API checks.
- Verify QR generation cannot inject unsafe content.
- Verify large proxy tables use pagination, filtering, lazy loading, or virtualization.
- Verify mobile output cards, copy buttons, download links, focus states, keyboard navigation, and screen reader summaries.
- Verify frontend retries stop or transition state when metadata is missing rather than polling forever.

### 29.11 Documentation and Cleanup

- Generate runtime version docs from a single support manifest.
- Generate protocol support docs from tests.
- Generate output docs from `output_manifest.json`.
- Generate Lab docs from `lab_strategies.json`.
- Generate security posture docs from actual executable controls.
- Archive stale docs that describe removed layouts.
- Remove or justify empty/stub files such as `NL`, `US`, and `docs/DEBT_MATRIX.md`.
- Deduplicate `docs/encyclopedia` and `docs/wiki/encyclopedia` or generate one from the other.
- Add CI checks for docs referencing removed files.
- Add CI checks for env vars used but undocumented.
- Add CI checks for documented outputs not generated.
- Add CI checks for frontend routes without source pages.

### 29.12 Final User-Facing Acceptance Criteria

The project should not be called healthy until all of the following are true:

- Workflows parse and required PR checks run.
- Scheduled runs cannot self-trigger loops.
- Public artifacts are schema-valid and manifest-described.
- Empty/degraded runs still publish honest, safe, valid outputs.
- Public pages do not show unresolved placeholders.
- Users can see freshness, counts, health, and degraded reasons.
- Universal and chosen outputs are either meaningfully distinct or clearly marked as degraded.
- Admin/auth/CORS/security defaults fail closed in production.
- Public docs are readable without JavaScript.
- Lab strategies, scanner safety, and browser limits are explicit.
- Experimental features are not marketed as stable.

---
