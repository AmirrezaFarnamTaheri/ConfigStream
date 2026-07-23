# Dynamic Resharding Performance Audit

## Matrix Resharding & Shard Allocation Flowchart
```ascii
+-----------------------+      +---------------------------+       +------------------------+
| Parse Logs & DB Runs  | ---> | Similarity Analysis       | --->  | Weight Assignment      |
| (Extract Duration/ms) |      | (Remove 90% overlapping)  |       | (Weight=Duration*10)   |
+-----------------------+      +---------------------------+       +------------------------+
                                                                             |
                                                                             v
+-------------------------+     +-------------------------------+   +-----------------------+
| Write batch_*.txt       | <-- | Greedy Load Balancing         |<- | Group by Project      |
| (Atomic write + tmp)    |     | (Min-load bin packing)        |   | (Sort Desc. Weight)   |
+-------------------------+     +-------------------------------+   +-----------------------+
```

## Batch Distribution & Timeout Limits Compliance Table

| Metric / Limit | Target (Seconds) | Implementation in `dynamic_reshard.py` | Compliance Status |
|---|---|---|---|
| **Max Batches** | N/A | `MAX_BATCHES = 17` | Compliant. Total shards hard-capped at 17. |
| **Min Batches** | N/A | `MIN_BATCHES = 14` | Compliant. Will not reduce shards below 14. |
| **Batch Time Limit** | 14400s (4h) | `TARGET_BATCH_SECONDS = 14400` | Compliant. Batches are allocated aiming for <= 4 hours. |
| **Consumer Revival Grace** | 2700s (45m) | Implicit in `TARGET_BATCH_SECONDS` buffer | At Risk. If total workload exceeds `17 * 14400` (244,800s), batches will overflow into the grace period limit. |

## Grace Period & Consumer Revival Timing Assessment
- `dynamic_reshard.py` correctly aims for `14400s` (4 hours) of execution time per batch based on historically observed parsing and fetching lengths.
- Because it hard-caps at `MAX_BATCHES = 17`, if the total cumulative seconds (`total_seconds = sum(weight)/10.0`) exceeds 244,800s, shards will inevitably start exceeding the 4h threshold. 
- This overload will cut directly into the 45m (`2700s`) consumer revival grace period defined globally (`BATCH_TIME_LIMIT_GRACE_SECONDS`), creating a potential timeout risk during workflow execution if pipeline source bloat continues unchecked.

## Source Weight & Latency Balancing Algorithm Findings
- **Weight Assignment**: Base weight is calculated via `weight = int(total_duration * 10)` in deciseconds. Fallbacks use `DEFAULT_WEIGHT = 130` (~13 seconds) for newly added sources.
- **Anti-Affinity**: URLs are clustered by "project key" (domain/repo). The Greedy Bin Packing strategy explicitly avoids assigning sources from the same project into the same batch, mitigating HTTP 429 rate-limiting from target repositories.
- **Empty Batch Handling**: Because `get_current_batch_count()` ensures `num_batches >= max(current_batches, MIN_BATCHES)`, the script never scales down the number of shards. If sources dwindle, it generates "empty" batches containing only comment headers (`# ConfigStream Batch X`). The pipeline handles these safely but wastes overhead on empty consumer shards.
- **Redistribution Safety**: Robust. Shard lists are generated using temporary atomic file replacements (`batch_X.txt.tmp`), and stale leftover batches are correctly unlinked upon success.
- **Metrics Exporting**: Matrix shard performance metrics (`load_balance_ratio`, `max_load`, `std_dev`) are only printed to `stdout` and saved to `data/batch_load_stats.json`. They are **not** actively exported to GHA `$GITHUB_OUTPUT`.

## Performance & Resharding Optimization Roadmap
1. **Adaptive Shard Scaling Down**: Modify the logic to allow batch count to dynamically reduce instead of locking `current_batches` as the historical minimum. This will prevent GitHub Actions from running empty or highly imbalanced shards.
2. **Explicit GitHub Actions Integration**: Output `load_balance_ratio`, `max_load_s`, and `std_dev_s` directly to `$GITHUB_OUTPUT`. This allows workflow steps to trigger warnings or slack alerts dynamically on high shard skew.
3. **Threshold Warning Logs**: Implement logic to emit CI annotations (`::warning::`) if the predicted slow batch execution time crosses `14400s`, directly alerting engineers that the `2700s` grace period is endangered.
4. **Predictive Down-weighting**: Integrate retry logic weights. Currently, chronically failing endpoints might only reflect their "fast-fail" time, resulting in low weight and overloading a shard if the endpoint suddenly revives. Add penalty coefficients for known unstable sources.
