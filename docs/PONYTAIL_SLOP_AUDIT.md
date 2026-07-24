# Ponytail & Slop Clean-up Audit

## Executive Summary & Target
**Net Lines Cut Target:** `net: -850 lines possible`

After auditing `src/configstream/` according to `/ponytail-review` and `/ai-slop-cleaner` principles, several instances of extreme over-engineering, hand-rolled utilities, and pass-through wrappers were identified. The codebase features numerous "Enterprise" patterns (Circuit Breakers, Adaptive Loaders, SQLite-backed Anomaly Detectors) that solve problems better handled by standard Python paradigms or simple constants. By leveraging native Python capabilities and deleting theoretical scaling abstractions, we can drastically simplify the pipeline without losing core functionality.

## Specific Findings Table

| Location | Smell Tag | What to Cut | Replacement |
|---|---|---|---|
| `anomaly.py` | `over-engineering` | 388-line SQLite DB tracking fetch history & Z-score/Isolation Forest logic | Delete entirely or replace with a simple running memory counter for the session |
| `adaptive_timeout.py` | `over-engineering` | 140-line dynamic timeout calculator with JSON persistence | Static timeout constant (`timeout = 10.0`) or simple inline fallback |
| `adaptive_workers.py` | `over-engineering` | 75-line `psutil` memory-checking worker calculator | `min(150, multiprocessing.cpu_count() * 15)` |
| `circuit_breaker.py` | `slop` | 92-line Half-Open/Open Circuit Breaker state machine | Simple exponential backoff or inline retry counter |
| `cache_warming.py` | `over-engineering` | 75-line module solely to sort an array by a "health score" | `list.sort(key=...)` directly where needed |
| `async_file_ops.py` | `wrapper-slop` | 67-line pass-through wrappers for `aiofiles` and `Path.mkdir` (`ensure_directory`) | Direct `Path(x).mkdir()` and `aiofiles.open()` usage |
| `async_utils.py` | `stdlib: duplication` | 38-line `safe_wait_for` wrapper handling missing tasks | Native `asyncio.wait_for` |
| `utils/__init__.py` | `native: duplication` | Hand-rolled `_FileLock` with `fcntl`/`msvcrt` and `BoundedConcurrencyManager` | Standard `filelock` package and standard `asyncio.Semaphore` |

## Masking Fallbacks vs. Grounded Compatibility Inventory
Many of these systems mask failures rather than addressing them cleanly:
- **`anomaly.py` DB fallback**: Catches broad DB errors to "fail open" anyway, rendering the complex SQLite database setup a silent liability.
- **`safe_wait_for` fallback**: Tries to manually schedule futures when no active task exists, instead of correctly managing event loops at the application edge.
- **Cross-Platform locks**: `_FileLock` in `utils/__init__.py` attempts manual `msvcrt` and `fcntl` imports wrapped in broad `except Exception` blocks, swallowing native OS limitations. Standard `filelock` or `asyncio` file operations would enforce compatibility correctly.

## Prioritized Cleanup Plan

- **Pass 1: Dead code and Theoretical Slop**
  - Delete `circuit_breaker.py` (Theoretical Enterprise slop).
  - Delete `cache_warming.py` (Unnecessary abstraction for a native list sort).
  - Delete `adaptive_timeout.py` (Delete stateful JSON tracking, use fixed timeouts).
- **Pass 2: Duplication and Standard Library Alignment**
  - Remove `async_file_ops.py` and replace with direct `pathlib` and `aiofiles`.
  - Remove `async_utils.py` and replace `safe_wait_for` with `asyncio.wait_for`.
  - Refactor `utils/__init__.py` to remove `_FileLock` and replace `BoundedConcurrencyManager` with standard `asyncio.Semaphore`.
- **Pass 3: Naming & Refactoring**
  - Simplify `adaptive_workers.py` into a 3-line inline function where workers are allocated.
  - Replace `anomaly.py`'s heavy SQLite logic with a simple dictionary-based session validator.
- **Pass 4: Test reinforcement**
  - Ensure remaining logic properly handles networking timeouts natively rather than relying on custom retry/circuit-breaker logic.
  - Clean up test files that stubbed these over-engineered components.
