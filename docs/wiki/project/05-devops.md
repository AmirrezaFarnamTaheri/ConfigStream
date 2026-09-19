# 05. DevOps & Infrastructure

ConfigStream v3.2.0 is a conditional release candidate. `docs/readiness.json` is the machine-readable release authority and `STATUS.md` is generated from it. Workflow YAML remains the executable contract, but production readiness requires exact-head CI, a sealed artifact, and a live deployment smoke for the same commit and digest.

GitHub Pages is the core zero-budget publication target. External mirrors are optional and secret-gated; their absence must not fail the core pipeline or Pages deployment.

## 1. Workflow Inventory

| Workflow | File | Purpose |
| :--- | :--- | :--- |
| CI | `.github/workflows/ci.yml` | Pull request and push validation, including workflow syntax validation. |
| Config's Stream | `.github/workflows/main.yml` | Scheduled/manual production pipeline, sharded batch execution, merge, output generation, native validation, release gating, promotion, and canonical `pipeline-output` publication. |
| Retest | `.github/workflows/retest.yml` | Retests the latest successful canonical `pipeline-output` without running a full source-ingestion cycle. Its output is diagnostic/retest evidence and is **not** an approved Pages release source. |
| Deploy to GitHub Pages | `.github/workflows/deploy-pages.yml` | Deploys a successful canonical `Config's Stream` `pipeline-output` to GitHub Pages after trust-policy, artifact, rollback, and live-verification gates. |
| Release | `.github/workflows/release.yml` | Tagged package release, Python distributions, native binaries, attestations, PyPI publish, and GitHub release assets. |

Every external `uses:` reference must match the tag-to-commit resolution in
`config/github-action-pins.json`. A 40-character value alone is insufficient:
blob object IDs and arbitrary commits are rejected unless the action name,
version comment, and verified commit SHA match that manifest.

## 2. Trigger and Concurrency Model

The main pipeline runs on schedule, manual dispatch, and pushes to `main`. Source reshard commits under `sources/batch_*.txt` and `sources/backup_dynamic/**` are ignored so automated source optimization cannot recursively trigger a full expensive pipeline.

Current concurrency rules:

- `main.yml`: one run per workflow/ref; non-main refs can cancel in progress. A dedicated preemption workflow cancels obsolete different-SHA main runs. If a cron request targets the exact commit already being processed, the new scheduled duplicate is cancelled so completed shard work on the active same-SHA run is preserved.
- `retest.yml`: one active retest per workflow/ref. Its schedule is offset between main cycles, and any queued/running main pipeline has priority; when a main run is requested, the preemption workflow cancels queued/running Retest work so production validation never competes with it.
- `deploy-pages.yml`: one Pages deployment at a time.

Any workflow that writes, deploys, or republishes output must keep an explicit concurrency policy. Any workflow that commits resharded source files must also ignore those source paths on push.

## 3. Pipeline Shape

The production pipeline uses dynamic source batch discovery:

1. `schedule_gate` checks cooldown rules for scheduled runs.
2. `build_container` builds and publishes the container used by batch jobs.
3. `setup_data` restores runtime intelligence data and GeoIP inputs.
4. `build_wasm` refreshes the browser WASM tester artifact.
5. `setup_matrix` discovers `sources/batch_*.txt`; if discovery fails, it falls back to batches 1 through 17.
6. `pipeline` runs one shard per discovered batch and uploads `shard-run-${sha}-${batch}` artifacts.
7. `merge_results` downloads shard artifacts, prepares docs, merges outputs, runs release/native validation and promotion, uploads a single canonical `pipeline-output`, and optionally publishes external mirrors/releases when configured.

The deploy workflow must consume exactly one canonical `pipeline-output` artifact from exactly one successful `Config's Stream` run on `main`. It must not assemble mixed artifacts from multiple runs, accept `Retest` as a release producer, or accept pull-request/fork workflow output. Retest can regenerate an output contract after rechecking proxies, but it does not execute the full production release-gate/native/promotion sequence and is therefore intentionally non-deployable.

Before deployment the workflow snapshots the currently served, policy-verified release. On a true first deployment, an exact HTTP 404 for `artifact_manifest.json` from the trusted Pages origin is recorded as machine-readable `missing_manifest` evidence and may bootstrap the rollback gate; other snapshot failures remain blocking. The candidate and rollback uploads use distinct Pages artifact names; a failed candidate smoke triggers restoration and still leaves the workflow failed closed.

## 4. Pages Artifact Contract & Deployment Dependency Closure

`deploy-pages.yml` downloads the canonical `pipeline-output`, applies the configured Pages signature policy without mutating the sealed artifact, validates frontend/artifact contracts, snapshots a last-known-good rollback candidate, and then deploys the exact verified candidate.

The core pre-deploy checks include:

```bash
python scripts/validate_pages_signature_policy.py output
python scripts/validate_frontend_placeholders.py --strict output
python scripts/validate_pages_artifact.py output
```

`validate_pages_signature_policy.py` is secure by default:

- a signed artifact always requires a valid configured `CS_PUBLIC_KEY` and cryptographic manifest verification;
- a signed artifact can never be downgraded to unsigned treatment;
- genuinely unsigned Pages publication is rejected unless repository Variable `ALLOW_UNSIGNED_PAGES=true` is explicitly configured;
- the same signed/explicit-unsigned policy is applied to the candidate, last-known-good snapshot, deployed candidate, and restored rollback release.

### 4.1 Dependency Closure & Fail-Closed Publication
- **Validator Runtime Dependencies**: `scripts/validate_frontend_placeholders.py` imports `configstream.security_validator` $\rightarrow$ `configstream.config`, which relies on `pydantic-settings` and `pydantic`; signature/deployment verification also relies on `cryptography`, `httpx`, and `PyYAML`.
- **Dependency Isolation Rule**: The `deploy-pages.yml` runner must install the complete verifier dependency set declared by the workflow/production constraints before qualification.
- **Fail-Closed Security**: If a validator dependency is missing, the Pages trust policy rejects the artifact, the artifact contract fails, or live verification fails, `DEPLOY_READY` remains `false`. The workflow terminates without accepting the candidate as healthy; failed post-deploy smoke invokes the last-known-good rollback path when available.
- **Differentiating True Success vs Skipped Runs**: A GitHub Actions workflow run marked "Success" may indicate only a qualification/no-op path. True deployment success requires the `deploy` job to execute with green qualification and live verification and to update the GitHub Pages environment.

The public output contract includes:

- `metadata.json`: pipeline metrics and frontend analytics source.
- `health.json`: compact public status, generated time, run identity fields, and degraded/ok state.
- `artifact_manifest.json`: file inventory with relative paths, sizes, SHA-256 hashes, categories, run identity fields, and optional Ed25519 manifest signature.
- `pipeline_events.jsonl`: sanitized append-only pipeline event telemetry; each line is a timestamped JSON object and must be covered by the manifest.

The current contract includes schema-backed artifact validation, API alias parity, refreshed manifests, deployed-site smoke, screenshots, and evidence-bundle retention. Future workflow changes must preserve those gates or update the authority docs and validators in the same change.

## 5. Local Validation

Use these commands before changing workflow or deployment behavior:

```bash
python scripts/validate_workflows.py
python scripts/validate_release_controls.py
python scripts/validate_action_pins.py
python scripts/validate_versions.py
pytest -q tests/unit/test_validate_workflows.py tests/unit/test_pages_deploy_workflow.py tests/unit/test_pages_signature_policy.py tests/unit/test_validate_pages_artifact.py tests/unit/test_validate_versions.py
```

The repository production gate remains broader than this quick checklist: Python tests, linting, typing, frontend build, artifact schema checks, browser smoke tests, security checks, workflow validators, suppression/skip governance, and deployed artifact verification are tracked in the master report and `STATUS.md`.

## 6. Cleanup Rule

Every workflow or deployment change must update all affected surfaces in the same step:

- workflow YAML
- validator scripts
- tests
- README or wiki docs
- `STATUS.md`
- `CHANGELOG.md`
- master audit status, if an item is closed or materially changed

Remove legacy branches, stale comments, old artifact names, duplicate validation arrays, and obsolete docs as soon as the new contract is in place.

---

## 7. Container Optimization & Security Hardening (`/elite-devops-architect`)

> **Target-state roadmap.** The current image is a multi-stage Python slim
> image with a non-root runtime user. The items below are proposed hardening
> work and must not be interpreted as current controls until verified.

### 7.1 Multi-Stage Build & Layer Caching Optimization
The target production Docker build will isolate build dependencies from runtime binaries:
1. **Dependency Stage:** Copy package manifests and use BuildKit cache mounts where the build environment supports them.
2. **Build Stage:** Compiles the Go tester binary (`CGO_ENABLED=0 go build -ldflags="-s -w"`) and WASM modules.
3. **Runtime Stage:** Evaluate a minimal runtime image after compatibility and CVE validation; strip compilers and build tools.

### 7.2 Container Security & Hardening Matrix
- **Non-Root Execution:** Keep the runtime user unprivileged; add `cap_drop: ALL` only in deployment manifests that support it.
- **Secrets Management:** Secrets are mounted via BuildKit secrets or environment variables injected at runtime, never baked into container image layers.
- **Healthcheck Probes:** Keep an active healthcheck and record its final interval, timeout, and retry values in the Dockerfile.

---

## 8. QA & TDD Systematic Verification Framework (`/qa-tdd-architect`)

### 8.1 The Iron Law of TDD
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```
All feature additions and bugfixes must strictly execute the **Red-Green-Refactor** cycle:
- **RED:** Write a minimal failing test proving the behavior or bug exists. Watch it fail with the expected error.
- **GREEN:** Implement the minimal production code to pass the test.
- **REFACTOR:** Simplify and optimize code structure while maintaining passing tests.

### 8.2 Smart Error Grouping & Triage Hierarchy
When diagnosing broken test runs or CI pipeline failures, engineers must prioritize repairs in sequence:
1. **Infrastructure Failures:** Missing environment variables, broken action pins, network timeouts.
2. **API Contract Mismatches:** Function signature drift, NDJSON schema changes.
3. **Logic Errors:** Algorithmic calculation bugs, edge-case regressions.

### 8.3 Test Coverage Targets
- **Current enforced source threshold:** $\ge 80\%$.
- **Proposed branch target:** $\ge 75\%$, after a branch-coverage reporter and CI gate are added.
- **Critical-path objective:** Add scenario coverage for parsers, protocol encryption, and NDJSON serialization; define measurable coverage thresholds per subsystem before gating releases.

---

## 9. Progressive Disclosure Documentation Architecture (`/elite-skill-architect`)

Documentation and agent skills across ConfigStream follow the **3-Level Progressive Disclosure** model:
1. **Metadata Tier:** Frontmatter headers and high-level abstracts loaded into context on demand (~100 words).
2. **Instruction Body:** Core workflows, executable commands, and essential patterns kept lean (<500 lines).
3. **Bundled Deep References:** Comprehensive encyclopedias, protocol specs, and troubleshooting guides loaded selectively.

---

## 10. Pages Publication Integrity and Freshness Runbook

### 10.1 Why Green Backend Runs Can Leave Pages Stale

A successful production pipeline run only proves that it produced a candidate artifact. Retest success is not a production-release signal and is never a Pages source.

Pages changes only after the separate qualification workflow downloads the exact canonical `Config's Stream` candidate, installs every dependency required by its validators, validates its source/trust/artifact contract, and deploys it. A missing transitive validator dependency, missing canonical artifact, failed trust-policy check, or failed qualification leaves the previously served Pages artifact intact.

The deploy workflow must install its verifier environment from a pinned, complete dependency definition rather than an ad-hoc subset. A preflight must execute the same validator-import path used in deployment before the candidate is accepted.

### 10.2 Live Candidate Identity Gate

Internal manifest consistency is insufficient: a consistently old site can pass self-hash checks. A successful live verification must bind the response to the candidate by checking all of the following after propagation polling and cache-bypassed fetches:

1. Expected source commit or immutable candidate identifier.
2. Expected workflow run identifier and manifest digest. In signed mode, the detached/manifest signature must verify against configured `CS_PUBLIC_KEY`. A signed artifact without that trust anchor is invalid. Genuinely unsigned Pages publication is allowed only when `ALLOW_UNSIGNED_PAGES=true` is explicitly configured.
3. Metadata generation time against the configured freshness policy.
4. Required route/bootstrap asset hashes, including runtime configuration.

The verifier must catch transport failures and always write a machine-readable report; an exception is a failed verification, not missing evidence.

The verifier CLI should accept the expected source commit, run identifier, and candidate manifest digest as explicit inputs. Its regression suite must serve a valid-but-old artifact and prove that the live check rejects it.

### 10.3 Static Artifact Lifetime Policy

Artifact authenticity and operational freshness are separate controls. The signature lifetime must accommodate queued deployment, propagation, rollback, and verification. The frontend must use artifact metadata to warn about stale data; it must not use a short signature-expiry window or the visitor clock as a proxy for artifact freshness.
