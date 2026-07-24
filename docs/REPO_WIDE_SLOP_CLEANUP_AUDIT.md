# Repo-Wide Slop Cleanup Audit

## Executive Summary & Net Lines Cut Target
**Target:** `net: -782 lines possible`

A comprehensive review of `src/configstream/` has identified multiple instances of over-engineering, dead code, unused abstractions, and hand-rolled utilities that duplicate standard library or platform capabilities. Cleaning up these redundancies will simplify the codebase, reduce maintenance burden, and slightly improve performance by removing unnecessary abstraction layers.

## Specific Findings Table

| Location | Smell Tag | What to Cut | Replacement | Lines |
|---|---|---|---|---|
| `async_file_ops.py` | Unneeded abstraction | Async wrapper functions (`read_file_async`, `write_file_async`, `ensure_directory`) | Inline `pathlib` or `aiofiles` directly where needed. | 67 |
| `cache_warming.py` | Unneeded abstraction | Over-engineered caching strategy (`warm_cache`, `get_cache_warming_strategy`) | Remove entirely. Just sort proxies inline in `consumer.py` if health sorting is strictly necessary. | 75 |
| `hard_stop.py` | Redundant helper | `HardStopWatcher` class | Inline the bounded graceful shutdown logic directly into the pipeline runner's shutdown routine. | 76 |
| `adaptive_workers.py` | Over-engineering | Entire module (`calculate_optimal_workers`) | Move simple heuristic logic into `pipeline/core.py`. | 75 |
| `adaptive_timeout.py` | Dead abstraction / Over-engineering | Entire module tracking latency history | Use fixed timeout configs or simple backoff algorithms. The `get_timeout` method ignores the source parameter anyway. | 140 |
| `async_utils.py` | Standard library duplication | `safe_wait_for` shadows standard library | `stdlib:asyncio.wait_for`. The fallback workaround is not needed for Python 3.11+. | 38 |
| `dns_utils.py` | Single-caller interface | `normalize_socket_address_host` | Inline into `pipeline/fetcher.py`. | 27 |
| `sorter.py` | Dead code branch | `_compute_and_sort` intended for async offloading but called synchronously | Inline into `sort_proxies_pareto` without the confusing separation. | 34 |
| `utils/__init__.py` | Stdlib/PyPI duplication | `_FileLock`, `AtomicFileWriter`, `BoundedConcurrencyManager` | Use standard `os.replace` with `tempfile`, or PyPI `filelock`. Replace `BoundedConcurrencyManager` with standard `asyncio.Semaphore`. | ~223 |
| `fetcher_worker.py` | Dead code | `RateLimitError`, `parse_retry_after` | Completely unused error classes and helpers. Remove. | 27 |

## Masking Fallbacks vs. Grounded Compatibility Inventory

The audit revealed several places where the project implements custom fallbacks mimicking existing functionality:
- `stdlib:` The `AtomicFileWriter` manually implements what `tempfile.NamedTemporaryFile` + `os.replace` provides. It masks filesystem nuances (retries on Windows `WinError 5`) but introduces 100+ lines of complex logic that could be handled by proven PyPI libraries like `atomicwrites`.
- `stdlib:` The `async_utils.safe_wait_for` creates a shim over `asyncio.wait_for` handling `RuntimeError` for lack of current task. This masks standard Python asyncio usage and isn't needed if tasks are spawned properly.
- `native:` The `_FileLock` implementation falls back to `fcntl` or `msvcrt` manually with manual loops, duplicating the robust features of the `filelock` standard library/PyPI package.

## Prioritized 4-Pass Cleanup Execution Plan

### Pass 1: Dead Code & Ghost Abstractions
*Target: `cache_warming.py`, `hard_stop.py`, `fetcher_worker.py` (partial), `sorter.py` (partial)*
- Delete completely unused code blocks like `RateLimitError` and `parse_retry_after`.
- Remove `cache_warming.py` and its integration in `pipeline/consumer.py`.
- Inline the `hard_stop.py` `HardStopWatcher` logic directly into the pipeline shutdown handler.
- Refactor `sorter.py` to remove the fake `_compute_and_sort` abstraction.

### Pass 2: Duplication & Over-engineering
*Target: `adaptive_workers.py`, `adaptive_timeout.py`, `async_file_ops.py`*
- Delete `adaptive_workers.py` and `adaptive_timeout.py`, replacing them with simpler heuristic bounds in their respective callers.
- Replace `async_file_ops.py` usages with native `aiofiles` / `pathlib`.

### Pass 3: Naming & Single-Caller Inlining
*Target: `dns_utils.py`*
- Move `normalize_socket_address_host` directly into `pipeline/fetcher.py` and delete `dns_utils.py`.

### Pass 4: Core Utility Refactoring (Test Reinforcement)
*Target: `utils/__init__.py`, `async_utils.py`*
- Swap `_FileLock` and `AtomicFileWriter` with `filelock` and standard `os.replace` techniques.
- Replace `safe_wait_for` with `asyncio.wait_for`.
- **Note:** Ensure existing unit tests for file I/O and pipeline concurrency are strictly monitored to verify no regression occurs on Windows filesystems.
