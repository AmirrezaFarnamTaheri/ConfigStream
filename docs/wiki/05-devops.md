# 05. DevOps & Infrastructure

ConfigStream's DevOps strategy is centered around the "Zero Budget" constraint. We treat GitHub Actions not just as a CI tool, but as a distributed serverless compute platform.

## The Pipeline Workflow (`.github/workflows/pipeline.yml`)

### Triggers
1.  **Schedule**: Runs every 6 hours (`0 */6 * * *`).
2.  **Dispatch**: Manual trigger via GitHub UI.
3.  **Push**: On commits to `main` (for testing).

### The Matrix Strategy
We split the workload to bypass the 6-hour timeout limit of a single runner and to maximize concurrency.

```yaml
strategy:
  matrix:
    batch: [1, 2, 3, 4, 5, 6]
```
*   **Job 1**: Processes `sources/batch_1.txt`
*   **Job 2**: Processes `sources/batch_2.txt`
*   ...

### Artifact Lifecycle

1.  **Setup**:
    *   Job restores `actions/cache` containing `data/history.db` and `data/source_quality.db`.
2.  **Execution**:
    *   Each matrix job runs independently.
    *   Each produces a local `output/` directory and a `data/` delta.
3.  **Upload**:
    *   Each job uploads its results as an artifact: `batch-results-1`, `batch-results-2`, etc.
4.  **Merge**:
    *   The final `merge_results` job downloads **all** artifacts.
    *   It runs `scripts/merge_batches.py` to combine the databases (SQL Merge) and the proxy lists (De-duplication).
5.  **Deploy**:
    *   The combined `output/` is pushed to `gh-pages`.

## Caching Strategy

We use a sophisticated caching key structure to ensure we always get the latest valid DB but don't fail if it's missing.

```yaml
key: configstream-data-${{ github.run_id }}
restore-keys: |
  configstream-data-
```
*   We use `sqlite3`'s WAL mode to ensure database integrity even if a process crashes.
*   The DBs are "Vacuumed" periodically to keep size small.

## Security Scanning

### Secrets
*   **Pre-commit**: We use `gitleaks` locally to prevent committing API keys.
*   **GitHub**: Secret Scanning is enabled on the repo.

### Dependencies
*   **Dependabot**: configured to check `pip` and `go` dependencies weekly.
*   **Pinning**: We pin versions in `requirements.txt` to avoid supply-chain attacks or breaking changes.

## Deployment Targets

1.  **GitHub Pages**: The primary static host. Served via Fastly CDN.
2.  **Cloudflare Pages**: A mirror configured via a separate workflow (or pull-based).
3.  **Hugging Face**: We treat Hugging Face Datasets as an "Immutable Backup."
    *   Script: `scripts/upload_hf.py`
    *   Why? HF has massive bandwidth and is rarely blocked.

## Local Development (Docker)

To replicate the CI environment locally:

```bash
# Start the full stack
docker compose up --build

# Run a specific command inside the container
docker compose exec web configstream run --sources sources/batch_1.txt
```

*   **Volumes**: `output/` and `data/` are mounted to the host, so you can see the results immediately.
*   **Network**: The container runs in a constrained network mode to simulate CI limits.
