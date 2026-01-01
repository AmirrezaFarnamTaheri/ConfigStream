# Phase 2: Core Pipeline Orchestration - Analysis Report

## 2. Overview
Phase 2 analyzes `src/configstream/pipeline.py` and its supporting modules. This ecosystem orchestrates data ingestion (sources), processing (cleaning, deduplication), testing (via `SingBoxTester`), and output generation.

## 2.1. Concurrency & Event Loop Management

### 2.1.1. Blocking Calls
**Analysis**:
*   `shutil.which` and `os.path.exists` are synchronous file system operations. They are fast but technically blocking.
*   `subprocess.Popen` in the Vwarp startup block is non-blocking (it just spawns).
*   **Startup Loop**:
    ```python
            for _ in range(20):  # Try for 2 seconds (20 * 0.1)
                await asyncio.sleep(0.1)
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT),
                        timeout=0.2,
                    )
    ```
    This loop correctly uses `asyncio` to wait for the port.
*   **Shutdown**: `vwarp_proc.terminate()` and `vwarp_proc.wait()` (synchronous version of `wait` on Popen object).
    *   **Issue**: `subprocess.Popen.wait` is BLOCKING. It will block the event loop.
    *   **Recommendation**: Use `asyncio.create_subprocess_exec` instead of `subprocess.Popen` to get an awaitable process object, or use `await loop.run_in_executor(None, vwarp_proc.wait)`.
*   **Output Handler Blocking**: `output_handler.py` uses `shutil.copy2` for log rotation and `history.export_*` methods synchronously. These can block the loop significantly when files are large.
    *   **Action**: Wrap these calls in `loop.run_in_executor`.

### 2.1.2. Task Management
**Analysis**:
*   `consumer_tasks` are created and gathered properly.
*   **Exception Handling**: The `try...except` block around `asyncio.gather` handles `CancelledError` and others, explicitly cancelling tasks.
    ```python
            for t in consumer_tasks:
                t.cancel()
            producer_task.cancel()
            await asyncio.gather(*consumer_tasks, return_exceptions=True)
    ```
    This is robust.

### 2.1.3. Queue Bounding
**Analysis**:
*   `work_queue = asyncio.Queue(maxsize=5000)`.
*   This prevents memory explosion if consumers are slow.

### 2.1.4. Deduplication
**Analysis**:
*   `seen_keys` and `seen_lock` are passed to consumers.
*   The actual deduplication logic resides in `processing_consumer` (not shown here, but referenced).
*   `filter_unique_endpoints` is called at the end.

### 2.1.5. Dynamic Concurrency (`concurrency_manager.py`)
**Analysis**:
*   **AIMD**: Implements Additive Increase/Multiplicative Decrease based on error rates.
    *   `error_threshold = 0.1` (10% errors triggers backoff).
    *   `backoff_factor = 0.7`.
*   **Safety**:
    *   Uses `_stats_lock` (AsyncLock) to protect deque updates (`record`, `_adjust`).
    *   Uses `_lifecycle_lock` (AsyncLock) to protect `start_tuner`/`stop_tuner`. This prevents race conditions if start/stop are called rapidly.
*   **Resizable Semaphore**: `utils.BoundedConcurrencyManager` (not read, but inferred) allows resizing via `set_limit`.

### 2.1.6. Adaptive Workers (`adaptive_workers.py`)
**Analysis**:
*   **Logic**: `optimal = cpu_count * 15`.
*   **Memory Check**: Uses `psutil` (if available) to cap workers based on RAM (`available_mb / 20`).
    *   Assumes 20MB per worker. This is a reasonable heuristic for Python async tasks + parsing overhead.
*   **Limits**: Clamps between 10 and 200.

## 2.2. Error Handling & Resilience

### 2.2.1. Exception Swallowing
**Analysis**:
*   The `finally` block handles Vwarp cleanup.
*   `except Exception as e` in the main block logs with `logger.exception`, so stack traces are preserved.
*   Server notification swallows errors (`logger.debug`) which is appropriate (fire-and-forget).

### 2.2.2. Graceful Shutdown
**Analysis**:
*   The `try...finally` block ensures `tester.close()`, `concurrency.stop_tuner()`, and `event_stream.aclose()` are called.
*   **Vwarp Issue**: As mentioned, `vwarp_proc.wait(timeout=2)` is blocking.

## 2.3. Resource Management

### 2.3.1. Subprocess Leaks
**Analysis**:
*   Vwarp process is terminated/killed in `finally`.
*   However, if `vwarp_proc.wait()` blocks the loop, it might delay shutdown.

### 2.3.2. Worker Scaling
**Analysis**:
*   `optimal_consumers` calculation looks reasonable (`cpu_count * 1.5`).
*   Upper bound clamping (32 or 16) prevents thrashing.

### 2.3.3. Stats Locking (Race Condition)
**Analysis**:
*   In `consumer.py`, updates to `stats.drop_reasons` inside loops are NOW protected by `seen_lock` (verified in deep scan).
*   **New Issue**: `PipelineStats.to_dict()` reads fields without locking. If this is called by an external observer (API) while consumers are running, it may yield inconsistent states (e.g., `drop_reasons` dictionary changing size during iteration).
    *   **Fix**: `PipelineStats` should encapsulate the lock or be accessed only when the pipeline is paused/finished.

### 2.3.4. Producer Throttling
**Analysis**:
*   `src/configstream/pipeline_core/producer.py` uses a hardcoded `asyncio.Semaphore(100)` for URL checking.
*   **Constraint**: This might be a bottleneck on high-bandwidth systems where `max_workers` (consumers) is scaled up to >100.
*   **Recommendation**: Make the producer semaphore dynamic, scaling with `max_workers` or a config setting.

## Recommendations
1.  **Async Subprocess**: Switch Vwarp `subprocess.Popen` to `asyncio.create_subprocess_exec`. This allows `await process.wait()` which doesn't block the loop.
2.  **Server Notification**: Use `aiohttp` instead of `httpx` (since `aiohttp` is already a dep and often lighter) or ensure `httpx` client is closed properly (context manager is used, so it's fine).
3.  **Type Hints**: `seen_keys` is `Dict[tuple, None]`. It works as a set but carries value overhead. `Set[tuple]` would be cleaner if consumers support it.
4.  **Stats Safety**: Apply `seen_lock` to ALL dictionary mutations in `PipelineStats`.
