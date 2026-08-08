# 05. DevOps & Infrastructure

ConfigStream v3.2.0 is a conditional release candidate. `docs/readiness.json` is the machine-readable release authority and `STATUS.md` is generated from it. Workflow YAML remains the executable contract, but production readiness requires exact-head CI, a sealed artifact, and a live deployment smoke for the same commit and digest.

GitHub Pages is the core zero-budget publication target. External mirrors are optional and secret-gated; their absence must not fail the core pipeline or Pages deployment.

## 1. Workflow Inventory

| Workflow | File | Purpose |
| :--- | :--- | :--- |
| CI | `.github/workflows/ci.yml` | Pull request and push validation, including workflow syntax validation. |
| Config's Stream | `.github/workflows/main.yml` | Scheduled/manual production pipeline, sharded batch execution, merge, output generation, and optional secret-gated mirrors/releases. |
| Retest | `.github/workflows/retest.yml` | Retests the latest successful `pipeline-output` artifact without running a full source ingestion cycle. |
| Deploy to GitHub Pages | `.github/workflows/deploy-pages.yml` | Deploys one completed `pipeline-output` artifact to GitHub Pages after validation. |
| Deploy Mirror | `.github/workflows/deploy_mirror.yml` | Optional secret-gated mirror deployment from the latest successful `pipeline-output`. |
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
- `deploy_mirror.yml`: one mirror deployment per workflow/ref, canceling stale in-progress mirror runs.

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

## 4. Pages Artifact Contract

`deploy-pages.yml` prepares the Pages directory by merging frontend files into `output/`, creating API-compatible aliases, and running:

```bash
python scripts/validate_pages_artifact.py output
```

That validator is the current deploy-side artifact gate. It checks required files, non-empty files, JSON parseability, JSONL pipeline telemetry shape, ZIP integrity, path containment, `artifact_manifest.json` inventory coverage, and `health.json` status.

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
