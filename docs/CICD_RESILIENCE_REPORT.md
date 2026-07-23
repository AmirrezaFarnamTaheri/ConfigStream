# CI/CD Resilience & Hardening Report

## 1. Security Injection & Hardening Risk Matrix
During the audit of `.github/workflows/`, we identified direct string interpolation of GitHub contexts inside `run` block scripts. This exposes the workflows to bash injection if a malicious actor controls the context values (e.g., branch names, workflow names).

| Workflow | Line(s) | Risk Context | Remediation |
|---|---|---|---|
| `retest.yml` | 47-51 | `${{ github.repository }}` and `${{ github.ref_name }}` directly inside `""` in bash | Map to `env` variables (`GITHUB_REPO`, `GITHUB_REF_NAME`) and reference them as `$GITHUB_REF_NAME`. |
| `deploy-pages.yml` | 46-51 | `${{ github.event.workflow_run.id }}` and `${{ github.event.workflow_run.name }}` directly in bash | Map to `env` variables (`WORKFLOW_RUN_ID`, `WORKFLOW_RUN_NAME`) and use `$WORKFLOW_RUN_ID`. |

*(All other scripts correctly use the `env:` block for secrets and variable passing, e.g., in `ci.yml`).*

## 2. Workflow Concurrency & Least-Privilege Permission Table
The permissions across workflows observe the principle of least privilege well. Job-level scopes correctly isolate token access.

| Workflow | Job | Concurrency Strategy | Permission Scope | Evaluation |
|---|---|---|---|---|
| `main.yml` | global / jobs | `group: ${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true` (non-main) | `contents: read` globally. Specific jobs escalate to `packages: write`, `contents: write`, `id-token: write` respectively. | **Excellent.** Minimal access per job. |
| `retest.yml` | global | `cancel-in-progress: false` | `contents: read`, `actions: read`. | **Excellent.** Queues ONE pending run, preventing API abuse while limiting access. |
| `ci.yml` | global | N/A | `contents: read` globally. | **Excellent.** No write access needed. |
| `release.yml` | jobs | N/A | Scoped `id-token: write` and `attestations: write` per job. | **Excellent.** Secure provenances and Trusted Publishing via OIDC. |
| `deploy-pages.yml`| global | `group: "pages"`, `cancel-in-progress: true` | `pages: write`, `id-token: write`. | **Excellent.** Scoped purely to GitHub Pages deployment. |

## 3. Timeout & Resharding Performance Assessment
- **Timeouts:** 
  - The `pipeline` job in `main.yml` has a `timeout-minutes: 180` boundary, with a container-level `BATCH_TIME_LIMIT_SECONDS: 9000` (150 minutes). This gives a safe 30-minute grace period for post-processing and artifact uploads.
  - The `retest` job in `retest.yml` mirrors the `timeout-minutes: 180` boundary.
- **Resharding Logic:**
  - `setup_matrix` dynamically generates `source-matrix.json` via `scripts/shard_sources.py` with 4 parts (`SOURCE_SHARD_PARTS: "4"`).
  - Parallelism is bounded to `max-parallel: 12`.
  - Dynamic resharding outputs are recorded via `scripts/dynamic_reshard.py`.
  - **Assessment:** Well-bounded and scalable.

## 4. Zero-Artifact Fallback Protection Roadmap
- **Current Behavior:** 
  - Shard artifacts are strictly required (`if-no-files-found: error`).
  - The `merge_validate_publish` job strictly requires `needs.pipeline.result == 'success'`.
  - If a single shard fails, the pipeline fails, and no release/publish occurs.
- **Resilience Roadmap:**
  - **Graceful Degradation:** To support a robust fallback when one shard out of $N$ fails, we recommend changing `merge_validate_publish` to `if: always() && contains(needs.pipeline.result, 'success')` or similar, allowing it to merge surviving shards and issue a partial dataset release with a warning.
  - **Missing Outputs:** `deploy-pages.yml` gracefully handles `Retest` failures where no artifact is produced. It checks `if [ -z "$(ls -A output)" ]` and `exit 0`s to prevent failure noise. 

## 5. Exact YAML Patch Specifications

### Patch for `retest.yml` (Injection Fix)
```diff
@@ -35,19 +35,21 @@
         env:
           FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
           GH_TOKEN: ${{ github.token }}
+          GITHUB_REPO: ${{ github.repository }}
+          GITHUB_REF_NAME: ${{ github.ref_name }}
         run: |
           # Non-schedule triggers always proceed
           if [ "${{ github.event_name }}" != "schedule" ]; then
             echo "proceed=true" >> "$GITHUB_OUTPUT"
             exit 0
           fi
 
           # Query the last completed run of BOTH main and retest workflows on this branch
           MAIN_RUN=$(gh api \
-            "repos/${{ github.repository }}/actions/workflows/main.yml/runs?branch=${{ github.ref_name }}&status=completed&per_page=1" \
+            "repos/${GITHUB_REPO}/actions/workflows/main.yml/runs?branch=${GITHUB_REF_NAME}&status=completed&per_page=1" \
             --jq '.workflow_runs[0] // empty' 2>/dev/null || true)
           RETEST_RUN=$(gh api \
-            "repos/${{ github.repository }}/actions/workflows/retest.yml/runs?branch=${{ github.ref_name }}&status=completed&per_page=1" \
+            "repos/${GITHUB_REPO}/actions/workflows/retest.yml/runs?branch=${GITHUB_REF_NAME}&status=completed&per_page=1" \
             --jq '.workflow_runs[0] // empty' 2>/dev/null || true)
```

### Patch for `deploy-pages.yml` (Injection Fix)
```diff
@@ -41,13 +41,15 @@
         env:
           FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
           GH_TOKEN: ${{ github.token }}
+          WORKFLOW_RUN_ID: ${{ github.event.workflow_run.id }}
+          WORKFLOW_RUN_NAME: ${{ github.event.workflow_run.name }}
         run: |
           # Download artifact from the triggering workflow run using GitHub CLI
-          if ! gh run download ${{ github.event.workflow_run.id }} \
+          if ! gh run download $WORKFLOW_RUN_ID \
               --name pipeline-output \
               --dir output; then
-            if [ "${{ github.event.workflow_run.name }}" = "Retest" ]; then
+            if [ "$WORKFLOW_RUN_NAME" = "Retest" ]; then
               echo "⚠️ No pipeline-output artifact found for Retest run; skipping Pages deploy."
               exit 0
             fi
```
