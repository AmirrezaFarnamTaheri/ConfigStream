# The Pipeline

The ConfigStream pipeline is the heart of the system. It orchestrates the entire lifecycle of a proxy from discovery to publication.

## Pipeline Stages

### 1. Source Discovery & Sharding
*   **Sources**: Defined in `sources/batch_*.txt`.
*   **Sharding**: To fit within GitHub Actions' 6-hour timeout, sources are split into 10 parallel batches (`matrix.batch_number`).
*   **Dynamic Resharding**: The `scripts/dynamic_reshard.py` script analyzes past run times and rebalances sources across batches to ensure even load.

### 2. The Processing Loop (`processing_consumer`)
Running in `src/configstream/pipeline_core/consumer.py`:

1.  **Fetch**: `orchestrator.fetch_from_source`
    *   Applies User-Agent rotation.
    *   Checks Circuit Breaker.
    *   Enforces per-source timeout (300s).
2.  **Parse**: `auto_detect_and_parse`
    *   Extracts lines.
    *   Sniffs content type (HTML vs Base64).
    *   Converts to `Proxy` objects.
3.  **Validate**: `SecurityValidator`
    *   Checks for blacklisted domains/IPs.
    *   Validates UUIDs/Passwords.
    *   Sanitizes input.
4.  **Test**: `SingBoxTester`
    *   Batches proxies into chunks (e.g., 50).
    *   Sends to Go binary.
    *   Receives `is_working`, `latency`, `error`.
5.  **Quality Update**:
    *   Updates `SourceQualityTracker` with success rates.
    *   Records metrics for `AdaptiveTimeout`.

### 3. Merging (`scripts/merge_batches.py`)
Once all batches finish, the `merge_results` job runs:
1.  **Download**: Artifacts from all batches are downloaded.
2.  **Consolidate**: Proxies are deduplicated by `(protocol, address, port)`.
3.  **Wash**: The `ProxyWasher` identifies working but "dirty" (blocked) proxies and wraps them in WARP chains.
4.  **Retest**: Washed chains are verified again to ensure end-to-end connectivity.
5.  **Rank**: Proxies are sorted by a multi-objective score (Latency, Uptime, Stability).

### 4. Distribution
*   **Output**: Files generated in `output/`.
*   **Publishing**:
    *   **GitHub Pages**: Main hosting.
    *   **Telegram**: Bot upload.
    *   **Hugging Face**: Dataset backup.
    *   **IPFS**: Decentralized pinning.
