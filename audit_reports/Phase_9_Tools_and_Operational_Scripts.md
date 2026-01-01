# Phase 9: Tools & Operational Scripts - Analysis Report (Deep Scan)

## 9. Overview
This phase audits the operational scripts, workflows, and CI/CD pipelines.

## 9.1. Workflows (`.github/workflows/pipeline.yml`)

### 9.1.1. Matrix Generation
**Analysis**:
*   **Logic**: Scans `sources/batch_*.txt` using `ls`, `sed`, `jq`.
*   **Fallback**: If no files found, defaults to `["1".."10"]`. This ensures the pipeline runs even if source generation fails (or is fresh).
*   **Robustness**: `jq -R -s -c 'split("\n")[:-1]'` handles newline separation correctly.

### 9.1.2. Job: `pipeline` (The Shard Runner)
**Analysis**:
*   **Container**: Uses `ghcr.io/...:latest`.
    *   **Security**: Credentials passed via `github.actor` / `GITHUB_TOKEN`. Correct.
*   **Cache**: Restores `data/*.db` and `mmdb`.
    *   **Key**: `configstream-data-${{ github.ref }}`. Good for branch isolation.
*   **Run Step**:
    *   `python -m configstream.cli merge`.
    *   **Artifacts**: Prepares `output_batch_${BATCH_NUMBER}/data` with DBs. This allows state persistence across shards?
        *   *Correction*: State (DBs) is copied *from* `data/` *to* output artifact. The *next* run restores it.
    *   **Issue**: `sqlite3` DBs from multiple shards cannot be naively merged by just overwriting. The `merge_results` job must handle DB merging logic (Phase 12 audit confirms `ProxyHistoryTracker.merge` exists).

### 9.1.3. Job: `merge_results` (The Aggregator)
**Analysis**:
*   **Artifact Download**: `merge-multiple: true`. Downloads all shard outputs into one folder.
*   **Go Build**: Compiles `configstream-tester` with tags.
    *   **Optimization**: `mv` to `$GITHUB_WORKSPACE` and adds to PATH. Correct.
*   **Merge Script**: `python -m scripts.merge_batches`.
    *   **Env**: Passes `WARP_KEY_POOL` and `STEGO_KEY`.
*   **Optimization**: `scripts/dynamic_reshard.py` rebalances `sources/`.
*   **Commit**: Pushes optimized sources back to repo.
    *   **Race Condition**: If multiple runs happen, push might fail. `|| echo "Push failed"` handles this gracefully.
*   **Distribution**:
    *   **IPFS**: Uses `publish_ipfs.py`.
    *   **Telegram/HF/GDrive**: Fan-out in parallel (`&` and `wait`). This speeds up the job significantly.

## 9.2. Scripts

### 9.2.1. `run_cycle.sh`
*   **Purpose**: Local execution wrapper.
*   **Logic**: Runs `pipeline` -> `merge` -> `healthcheck`. Mirrors CI.

### 9.2.2. `deduplicate_sources.py` (Source Management)
**Analysis**:
*   **Purpose**: Manages `sources/batch_*.txt` files.
*   **Logic**:
    *   Reads existing sources.
    *   Adds new hardcoded sources (`NEW_SOURCES`).
    *   Filters: Drops duplicates by domain (heuristic `get_domain`).
    *   **Blacklist**: Removes "soroushmirzaei" explicitly.
    *   **Redistribution**: Shuffles URLs into 10 batch files modulo index.
*   **Safety**: Writes to `consolidated_sources.txt` as source of truth.

## 9.3. Backend Core (`src/configstream/pipeline_core/producer.py`)

### 9.3.1. Flow Control
**Analysis**:
*   **Local Files**: Reads immediately.
*   **Remote Sources**:
    *   **Cooldown**: Checks `quality_tracker.should_fetch` (Executor).
    *   **Semaphore**: `sem = asyncio.Semaphore(100)` limits concurrent checks.
*   **Fetching**:
    *   **Batching**: `batch_size = 100`.
    *   **Jitter**: `random.uniform(0.5, 2.0)`. Prevents thundering herd on remote hosts.
    *   **Concurrency**: `max_concurrent=settings.PER_HOST_MAX_CONCURRENCY`.
*   **Processing**:
    *   **Offloading**: `_extract_config_lines` runs in `loop.run_in_executor`. Critical for CPU safety.
    *   **Anomaly Check**: `anomaly_detector.is_safe` runs in executor.
*   **Queueing**: `await work_queue.put`. Matches Consumer.

### 9.3.2. Sorter (`src/configstream/pipeline_core/sorter.py`)
**Analysis**:
*   **Pareto Score**: `(norm_latency * 0.5) + ((1.0 - rel) * 0.3) + ((1.0 - up) * 0.2)`.
*   **Efficiency**: `history.get_bulk_stats(ids)` prevents N+1 DB queries. This is the correct optimization.

## Recommendations
1.  **DB Merging**: Verify `scripts/merge_batches.py` actually calls `history.merge()`. If it just copies the last shard's DB, data is lost.
2.  **Workflow Resilience**: The `git push` in `merge_results` should use `rebase` strategy or retry logic to handle contention.

## 9.4. Operational Scripts Deep Dive (`scripts/`)

### 9.4.1. `clean_security_issues.py`
**Analysis**:
*   **Deprecation**: Prints "WARNING: This script is deprecated" to stderr.
*   **Safety**: If used, it loads JSON, filters list, and atomic writes (`open("w")`).
*   **Issue**: `open("w")` is NOT atomic. It truncates before writing. If `json.dump` fails (disk full), file is corrupted.
    *   **Recommendation**: Use `AtomicFileWriter` or write-to-temp-then-rename pattern if this script is kept.

### 9.4.2. `upload_telegram.py`
**Analysis**:
*   **Timeout**: `timeout=60`. Good.
*   **Error Handling**: Catches `Exception`, prints error, and `sys.exit(1)`.
*   **Hardcoded Files**: Uploads specific filenames (`singbox.json`, etc.). If pipeline output names change, this breaks.

### 9.4.3. `upload_hf.py` (Hugging Face)
**Analysis**:
*   **Repo Creation**: Tries to create repo. Handles `exist_ok`.
*   **Upload**: Uses `api.upload_folder`. Efficient.
*   **Failure**: Logs error but does NOT `sys.exit(1)` (commented out).
    *   **Logic**: "We generally don't want to fail the CI pipeline if the mirror fails". This is a valid operational choice for a mirror.

### 9.4.4. `upload_gdrive.py`
**Analysis**:
*   **Auth**: Expects `GDRIVE_SA_JSON` (Service Account).
*   **Sync Logic**: Checks `get_folder_files` first. If file exists -> `update`. If not -> `create`.
    *   **Benefit**: Preserves File IDs (important for shared links).
*   **Iteration**: `for item in local_path.glob("*")`. Only uploads root files, not recursive.
    *   **Limitation**: If `output/` has subfolders (`data/`, `country/`), they are ignored.
    *   **Action**: Ensure `output_dir` structure matches expectation or implement recursive upload. Currently, the main artifacts are in root, so it's acceptable.
