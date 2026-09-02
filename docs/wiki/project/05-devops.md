# 05. DevOps & Infrastructure

ConfigStream v3.2.0 is a conditional release candidate. `docs/readiness.json` is the machine-readable release authority and `STATUS.md` is generated from it. Workflow YAML remains the executable contract, but production readiness requires exact-head CI, a sealed artifact, and a live deployment smoke for the same commit and digest.

GitHub Pages is the core zero-budget publication target. External mirrors are optional and secret-gated; their absence must not fail the core pipeline or Pages deployment.

## 1. Workflow Inventory

| Workflow | File | Purpose |
| :--- | :--- | :--- |
| CI | `.github/workflows/ci.yml` | Pull request and push validation, including workflow syntax validation. |
| Config's Stream | `.github/workflows/main.yml` | Scheduled/manual production pipeline, sharded batch execution, merge, output generation,. |
| Retest | `.github/workflows/retest.yml` | Retests the latest successful `pipeline-output` artifact without running a full source ingestion cycle. |
| Deploy to GitHub Pages | `.github/workflows/deploy-pages.yml` | Deploys one completed `pipeline-output` artifact to GitHub Pages after validation. |
| Release | `.github/workflows/release.yml` | Tagged package release, Python distributions, native binaries, attestations, PyPI publish, and GitHub release assets. |

Every external `uses:` reference must match the tag-to-commit resolution in
`config/github-action-pins.json`. A 40-character value alone is insufficient:
blob object IDs and arbitrary commits are rejected unless the action name,
version comment, and verified commit SHA match that manifest.

## 2. Trigger and Concurrency Model

The main pipeline runs on schedule, manual dispatch, and pushes to `main`. Source reshard commits under `sources/batch_*.txt` and `sources/backup_dynamic/**` are ignored so automated source optimization cannot recursively trigger a full expensive pipeline.

Current concurrency rules:

- `main.yml`: one run per workflow/ref; non-main refs can cancel in progress.
- `retest.yml`: one active retest per workflow/ref, with no cancellation of an already-running retest.
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
7. `merge_results` downloads shard artifacts, prepares docs, merges outputs, validates critical release files, uploads a single `pipeline-output`, and optionally publishes external mirrors/releases when configured.

The deploy workflow must consume exactly one `pipeline-output` artifact from exactly one completed run. It must not assemble mixed artifacts from multiple runs.
Before deployment it snapshots the currently served, manifest-verified release.
The candidate and rollback uploads use distinct Pages artifact names; a failed
candidate smoke triggers restoration and still leaves the workflow failed closed.

## 4. Pages Artifact Contract & Deployment Dependency Closure

`deploy-pages.yml` prepares the Pages directory by downloading the canonical `pipeline-output` artifact, merging frontend assets into `output/`, creating API-compatible aliases, and executing the sealed-artifact validation suite:

```bash
python scripts/validate_frontend_placeholders.py --strict output
python scripts/validate_pages_artifact.py output
```

### 4.1 Dependency Closure & Fail-Closed Publication
- **Validator Runtime Dependencies**: `scripts/validate_frontend_placeholders.py` imports `configstream.security_validator` $\rightarrow$ `configstream.config`, which relies on `pydantic-settings` and `pydantic`.
- **Dependency Isolation Rule**: The `deploy-pages.yml` runner must install the complete dependency set (`httpx`, `cryptography`, `pydantic`, `pydantic-settings`) in its verification environment.
- **Fail-Closed Security**: If any validator dependency is missing or if artifact verification fails, `DEPLOY_READY` remains `false`. The workflow terminates without publishing, ensuring compromised or malformed artifacts never overwrite the live site.
- **Differentiating True Success vs Skipped Runs**: A GitHub Actions workflow run marked "Success" may simply indicate that the deployment job was skipped (e.g., triggered on an event with no candidate artifact). True deployment success occurs only when the `deploy` job executes with green verification and updates the GitHub Pages live environment.

The public output contract now includes:

- `metadata.json`: pipeline metrics and frontend analytics source.
- `health.json`: compact public status, generated time, run identity fields, and degraded/ok state.
- `artifact_manifest.json`: file inventory with relative paths, sizes, SHA-256 hashes, categories, and run identity fields.
- `pipeline_events.jsonl`: sanitized append-only pipeline event telemetry; each line is a timestamped JSON object and must be covered by the manifest.

The current contract includes schema-backed artifact validation, API alias parity, refreshed manifests, deployed-site smoke, screenshots, and evidence-bundle retention. Future workflow changes must preserve those gates or update the master/status files and validators in the same change.

## 5. Local Validation

Use these commands before changing workflow or deployment behavior:

```bash
python scripts/validate_workflows.py
python scripts/validate_action_pins.py
python scripts/validate_versions.py
pytest -q tests/unit/test_validate_workflows.py tests/unit/test_validate_pages_artifact.py tests/unit/test_validate_versions.py
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

A successful pipeline run only proves that it produced a candidate artifact.
Pages changes only after the separate qualification workflow downloads that
exact candidate, installs every dependency required by its validators, validates
it, and deploys it. A missing transitive validator dependency, a skipped
`workflow_run` candidate, or a failed qualification leaves the previously
served Pages artifact intact.

The deploy workflow must install its verifier environment from a pinned,
complete dependency definition rather than an ad-hoc subset. Add a preflight
that executes the same validator-import path used in deployment before the
candidate is accepted.

### 10.2 Live Candidate Identity Gate

Internal manifest consistency is insufficient: a consistently old site can
pass self-hash checks. A successful live verification must bind the response to
the candidate by checking all of the following after propagation polling and
cache-bypassed fetches:

1. Expected source commit or immutable candidate identifier.
2. Expected workflow run identifier and manifest digest; verify the detached manifest signature when a public key is configured. A missing optional verification key must not create a new deployment prerequisite.
3. Metadata generation time against the configured freshness policy.
4. Required route/bootstrap asset hashes, including runtime configuration.

The verifier must catch transport failures and always write a machine-readable
report; an exception is a failed verification, not missing evidence.

The verifier CLI should accept the expected source commit, run identifier, and
candidate manifest digest as explicit inputs. Its regression suite must serve a
valid-but-old artifact and prove that the live check rejects it.

### 10.3 Static Artifact Lifetime Policy

Artifact authenticity and operational freshness are separate controls. The
signature lifetime must accommodate queued deployment, propagation, rollback,
and verification. The frontend must use artifact metadata to warn about stale
data; it must not use a short signature-expiry window or the visitor clock as a
proxy for artifact freshness.
