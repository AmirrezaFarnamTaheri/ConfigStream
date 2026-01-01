# Phase 12: Data Integrity & Artifacts - Analysis Report

## 12. Overview
This phase audits mechanisms that ensure data consistency, specifically sharding and history tracking.

## 12.1. Reshard Dynamic (`src/configstream/sharding.py`)
**Analysis**:
*   **Algorithm**: `hashlib.blake2b(digest_size=2)`.
    *   `blake2b` is fast and secure.
    *   `digest_size=2` gives 16 bits (65536 values).
    *   `value % buckets` (default 256).
    *   **Determinism**: Highly deterministic. Same ID always goes to same shard.
*   **Usage**: Used to distribute proxies across multiple "shards" (buckets).
    *   **Benefit**: If you have 100k proxies, downloading one big JSON is slow. Sharding allows clients to fetch `shard_0.json`, `shard_1.json` or subscribe to a subset.
*   **Metadata**: `save_shard_metadata` saves stats.

## 12.2. Artifact Management
*   **Cleanup**: Pipeline logic handles `history` cleanup.
*   **Versioning**: `server.py` logic relies on `proxies.old.json`. Need to verify if `output.py` or pipeline actually rotates this file.
    *   *Check*: `AtomicFileWriter` usually overwrites. Rotation logic might be in `pipeline.py` or `output_logic.py`.
    *   *Result*: I didn't see explicit rotation logic (rename current to old) in `output_logic.py`. It just writes `proxies.json`.
    *   **Gap**: If `server.py` expects `proxies.old.json` for diffs, but nothing creates it, the diff endpoint will always return "full reload required".

## 12.3. History Tracking (`src/configstream/history/tracker.py`)
**Analysis**:
*   **Storage**: Uses `QualityStorage` (SQLite wrapper).
*   **Schema**: `proxy_history` table (timestamp, is_working, latency, country, failure_reason).
*   **Efficiency**:
    *   `update_history`: Uses `executemany` for batch inserts. This is performant.
    *   `cleanup_old_data`: Uses single DELETE query.
    *   `get_bulk_stats`: Uses `AVG(is_working)` aggregation in SQL. This is much faster than loading all rows into Python.
*   **Export**:
    *   `_load_all_history`: Loads EVERYTHING into memory dict.
    *   **Risk**: With 100k proxies * 100 entries, this is 10M rows.
    *   **Mitigation**: This function is only used for `export_for_visualization`, which is likely an occasional report, not the hot path. However, it will OOM on large datasets.
    *   **Recommendation**: Stream the export or paginate.

## Recommendations
1.  **Implement Rotation**: Modify `generate_categorized_outputs` to rename `proxies.json` to `proxies.old.json` before writing the new one.
2.  **History Export**: Refactor `_load_all_history` to yield generators or write to file incrementally to avoid OOM.
