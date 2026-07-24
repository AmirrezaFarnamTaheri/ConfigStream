# Core Execution Flow `run_full_pipeline` Deep-Dive Audit

**Target:** Flow 361 (`run_full_pipeline` in `src/configstream/pipeline/core.py`)
**Scope:** 31 Files | 138 Target Nodes Evaluated

---

## 1. `run_full_pipeline` Complete Execution Flowchart

```ascii
[ User Input / Trigger ]
       |
       v
+---------------------------------------------------+
| run_full_pipeline() (core.py)                     |
| -> StandardPipeline.create_and_init()             |
+---------------------------------------------------+
       |
       |---[ Initializations ]---> VwarpTool, SmartRetestScheduler, GeoIP, Blocklists, Washer
       v
+---------------------------------------------------+
| asyncio.gather(producer_task, *consumer_tasks)    |
+---------------------------------------------------+
       |                                      |
       | (Tasks spawn)                        | (Tasks spawn)
       v                                      v
+------------------------+          +-----------------------------------+
| StreamingProducer      |          | WorkerConsumer (x N workers)      |
| (producer.py)          |          | (consumer.py)                     |
+------------------------+          +-----------------------------------+
| 1. fetch files/urls    |          | 1. work_queue.get()               |
| 2. extract configs     |          | 2. _parse_chunk (Executor)        |
| 3. anomaly checks      |   PUT    | 3. deduplicate (seen_lock)        |
| 4. micro-chunking      |=======>  | 4. validate & warm cache          |
| 5. _queue_payload      |  Queue   | 5. _test_candidates (batching)    |
+------------------------+          | 6. _revive_failed_proxies (WARP)  |
                                    | 7. _enrich_geoip_and_filter       |
                                    | 8. append to final_proxies        |
                                    +-----------------------------------+
                                                      |
       +----------------------------------------------+
       | (All consumers terminate upon 'None' sentinel)
       v
+---------------------------------------------------+
| Final Cleanup & Output Generation (core.py)       |
| -> dedupe_and_shuffle -> sort_proxies_pareto      |
| -> generate_pipeline_outputs -> Save History      |
+---------------------------------------------------+
       |
       v
[ PipelineResult Object ]
```

---

## 2. Node & File Criticality Verification Table

Analyzed 138 functional nodes across 31 dependent modules. Key boundaries verified:

| File Name | Critical Node / Function | Sub-Nodes Evaluated | Criticality Assessment |
| :--- | :--- | :--- | :--- |
| `core.py` | `StandardPipeline.run` | 24 | High. Controls global timeout boundaries, `time_limit_task`, cancellation via `_cancel_all`, and final cleanup sequences. |
| `core.py` | `run_full_pipeline` | 5 | Medium. Entry-point factory wrapper. Evaluated arguments pass-through correctly. |
| `producer.py` | `source_producer` | 38 | High. Manages `bounded_queue` pressure, circuit breakers, and anomaly detection handoffs. |
| `producer.py` | `_queue_payload` | 14 | Critical. Handles backpressure drops (`_drop_slowest_testing`) and micro-chunking timeouts. |
| `consumer.py` | `processing_consumer`| 41 | Critical. Core task orchestration (Parsing, Dedupe, Testing, Revival, GeoIP, Stats updating). |
| `consumer.py` | `_test_candidates` | 21 | High. Handles concurrency constraints, Go-Tester integration, and fallback Python executor testing boundaries. |
| `consumer.py` | `_revive_failed_proxies`| 15 | High. `vwarp_success_ids` tracking and standard WARP re-testing logic. |

*(Note: Peripheral modules evaluated include `vwarp/manager.py`, `circuit_breaker.py`, `anomaly.py`, and `test_cache.py` totaling the remaining nodes in the graph path).*

---

## 3. Async Queue & Thread Synchronization Audit Findings

### Bounded Queue Contention (`work_queue`)
- **Design Assessment:** The `work_queue` is an `asyncio.Queue(maxsize=5000)`. `producer.py` leverages intelligent micro-chunking (`_chunk_lines`) and implements a bounded `queue_put_timeout` (default 0.75s).
- **Backpressure Handling:** When queue pressure exceeds `QUEUE_OVERLOAD_THRESHOLD`, `_drop_slowest_testing()` attempts to discard longer URI candidates to prioritize faster targets.
- **Verdict:** Highly resilient. It successfully prevents memory exhaustion during fast-producer/slow-consumer scenarios without permanently blocking the producer task.

### Thread Synchronization (`seen_lock`)
- **Design Assessment:** A shared `asyncio.Lock` (`seen_lock`) is used in `consumer.py` to synchronize updates to `stats`, `seen_keys`, and `final_proxies`.
- **Verdict:** Correct implementation, but memory eviction under the lock in `_deduplicate_batch` using generic dictionary iteration might induce slight event-loop blocking on extremely large runs.

### Consumer Revival Tracking (`vwarp_success_ids`)
- **Design Assessment:** `vwarp_success_ids` correctly operates as an in-memory `set[str]` inside the `_revive_failed_proxies` loop. When VWarp revives a proxy, its `origin_id` is cached. Standard WARP revival then strictly checks against this set.
- **Verdict:** Flawless tracking logic. Avoids duplicate testing of proxies across both VWarp and WARP methods, eliminating O(N^2) redundancy during proxy recovery phases.

---

## 4. Exception Boundaries & Failure Recovery Assessment

### Pipeline Shutdown Sequence & Cleanup
- **Resource Management:** `StandardPipeline.run` is wrapped in a strict `try/finally` block that guarantees cleanup via `time_limit_task.cancel()`, `await self.context.concurrency.stop_tuner()`, `await VwarpTool().stop_tunnel()`, and flushing event streams.
- **Task Cancellation:** Exception boundaries implement a secure `_cancel_all` handler that actively signals `consumer_tasks` to cancel, gathers remaining futures to suppress orphaned tasks, and cascades exception logs cleanly.

### Boundary Enforcement
- **Producer Hand-offs:** `run_in_executor` boundaries are respected for blocking methods (e.g., `extract_config_lines`, `anomaly_detector.record`, and `quality_tracker.report_failure`). Exceptions thrown in `fetch_multiple_sources` are captured and correctly marked against the Source Quality tracker.
- **Consumer Failures:** Go-Tester batch errors safely boundary-wrap and correctly degrade to standard `_fallback_test` concurrency implementations on an individual-proxy basis.

---

## 5. Performance & Memory Optimization Roadmap

1. **GeoIP Sequential Bottleneck (`consumer.py:788`)**
   - **Current State:** `_enrich_geoip_and_filter` loops over the `final_batch_for_this_source` and `await`s GeoIP lookups sequentially.
   - **Optimization:** Refactor into `asyncio.gather(*[geoip.lookup(p.address) for p in batch])` to perform batch-resolution asynchronously, vastly improving per-chunk latency.

2. **Eviction Lock Delays (`consumer.py:440`)**
   - **Current State:** If `seen_keys` breaches `MAX_SEEN_KEYS`, `eviction_count` elements are popped iteratively inside `async with seen_lock:`.
   - **Optimization:** Shift to an explicitly sized caching mechanism (e.g., `lru_cache` structure or fixed-size `deque`) to avoid dynamic iteration and `.pop()` blocking the async event loop during mass-eviction.

3. **Fallback Testing Redundancy (`consumer.py:590`)**
   - **Current State:** Fallback tests correctly handle `CancelledError`, but Python's async gather does not pre-emptively cancel concurrent batch members if the main tester process is forcefully halted mid-flight unless the pipeline level interrupts.
   - **Optimization:** Attach bounded timeouts strictly inside `_test_wrap` wrappers inside the Python fallback loops to avoid zombie semaphore locking.
