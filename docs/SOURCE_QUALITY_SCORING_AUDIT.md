# Source Quality Scoring & Score Decay Audit

## 1. Source Quality Tracker Architecture Flowchart

```ascii
      [ StreamingProducer / Pipeline ]
                     |
                     v
             (should_fetch, update, report_success, report_failure)
                     |
        +-----------------------------------+
        |       SourceQualityTracker        |
        |      (source_quality.py)          |
        |  - In-Memory Cache (sources)      |
        |  - State & Status Derivation      |
        +-----------------------------------+
                     | (Inherits)
                     v
        +-----------------------------------+
        |          QualityStorage           |
        |       (quality/storage.py)        |
        |  - Threading Lock & Local Conn    |
        |  - CRUD: upsert_stats, record_run |
        +-----------------------------------+
                     |
                     v
           [ SQLite Database ]
      (source_stats, source_runs, proxy_history)
```

## 2. Score Decay & Latency Penalty Algorithm Verification Table

| Component | Code implementation | Verification / Discrepancy |
| --------- | ------------------- | -------------------------- |
| **Trust Score Calculation** | `calculate_trust_score` computes based on reliability (50%), diversity (30%), consistency (20%), and subtracts jitter penalty. | **Unused/Hardcoded**: `SourceQualityTracker.update()` hardcodes `trust_score = 50.0` instead of calling `calculate_trust_score()`. |
| **Cooldown Hours** | `calculate_cooldown_hours` implements exponential backoff. | **Discrepancy**: Comment says `1 failure -> 1h`, but `pow(2, 1) = 2h`. **Unused**: `should_fetch()` uses static `UPDATE_INTERVAL_HOURS` for probation, completely ignoring the backoff logic. |
| **Permanent Failures** | `_is_permanent_failure` jumps to `PERMANENT_FAILURE_SENTINEL` (100) on 404/410. | **Verified**: Logic correctly ensures permanent failure sources are never resurrected in `should_fetch()`. |
| **Diversity Score** | `calculate_diversity_score` uses Gini-Simpson Index. | **Verified**: Logic correctly penalizes single-country distributions, but relies on accurate `country_code` in upstream Proxies. |

## 3. Storage Persistence & Thread Safety Audit Findings

*   **Thread Safety Model**: Uses a hybrid of `threading.local()` for connections and a global `threading.Lock()` `self._lock` wrapping all CRUD operations.
*   **Contention Risk**: Since every single operation (`execute_write`, `execute_write_many`, `get_source_state`, `upsert_stats`) acquires the same global instance `_lock`, all DB access across the application is strictly serialized. While this prevents SQLite locked database errors, it can cause a significant bottleneck in a highly concurrent streaming pipeline.
*   **Merge Operation Risk**: `merge_from()` opens independent DB connections while holding the global lock, iterating over tables. This will pause the entire pipeline relying on `SourceQualityTracker` while the merge executes.
*   **Integrity**: Schema handles default values well, and migration gracefully adds columns.

## 4. Source Threshold Filtering Performance Assessment

*   **Source Stall Prevention**: `should_fetch()` provides immediate O(1) circuit breaking. Dead sources are correctly ignored until `SOURCE_RESURRECTION_HOURS` (168 hours) pass.
*   **Worst Performers Optimization**: `get_worst_performing()` queries the DB and sorts by failures and reliability. However, this method queries `reliability_score < 50 OR consecutive_failures > 0` directly. For large tables, this could be slow unless there are indexes on `reliability_score` and `consecutive_failures` (which currently do not exist).
*   **Ineffective Caching**: `SourceQualityTracker` initializes `self.sources` as an in-memory cache, but never uses it. Operations read directly from the SQLite database via `get_source_state()`.

## 5. Code Hardening Recommendations

1.  **Integrate Trust Score Algorithm**: Replace the hardcoded `trust_score = 50.0` in `SourceQualityTracker.update()` with the actual invocation of `calculate_trust_score()` to provide accurate source ranking.
2.  **Use Exponential Backoff**: Update `should_fetch()` for `probation` status to utilize `calculate_cooldown_hours()` rather than falling back to static polling intervals. Fix the formula if 1 hour is desired for 1 failure (e.g., `math.pow(2, failures - 1)`).
3.  **Fix Database Indexing**: Add SQLite indexes on `reliability_score` and `consecutive_failures` in `QualityStorage._init_db()` to accelerate `get_worst_performing()` queries.
4.  **Optimize Thread Synchronization**: Investigate removing the global instance `_lock` for read operations (`get_source_state`), relying instead on WAL journal mode and SQLite's internal thread-safe reading.
5.  **Remove or Utilize In-Memory Cache**: Either implement dictionary-backed caching to reduce DB hits in `should_fetch()`, or remove the unused `self.sources` field entirely.
