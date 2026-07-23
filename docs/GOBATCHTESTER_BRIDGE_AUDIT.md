# GoBatchTester IPC & Daemon Bridge Audit

## GoBatchTester IPC Architecture Flowchart

```text
+--------------------+        JSON over stdin        +---------------------+
|   Python asyncio   | ----------------------------> |   Go Daemon Proc    |
| (GoBatchTester)    |                               | (-workers, -timeout)|
|                    | <---------------------------- |                     |
|  - write/drain     |   JSON over stdout (results)  |  - Proxy testing    |
|  - _read_loop      |                               |                     |
|  - _stderr_loop    | <---------------------------- |  - Logging          |
|  - safe_wait_for   |        stderr (logs)          |                     |
+--------------------+                               +---------------------+
```

## Timeout & Consecutive Failure Threshold Verification Table

| Component / Logic | Configured Threshold | Observation / Vulnerability |
| --- | --- | --- |
| Batch Timeout | `min(300, len(inputs)*2 + 60)` | Scales safely with batch size. Provides sufficient buffer (60s) over Go's internal context timeouts to avoid race conditions. |
| Daemon Restart Await | 30.0s | Synchronous `safe_wait_for(self._restart_daemon(), 30.0)`. Safely prevents the event loop from hanging on zombie processes. |
| Consecutive Timeout | 5 consecutive batches | **Flaw**: Once `self._consecutive_timeouts >= 5`, `self.available` is set to `False`, but the code mistakenly calls `await self._restart_daemon()`. Because `_ensure_process()` doesn't check `self.available`, this spawns a permanent orphaned process that is never used or closed. |
| Daemon Self-Test | 5.0s | Short 5-second check. Properly disables the daemon and calls `await self.close()` on failure, leaving no orphan processes. |

## Daemon Restart Await & Process Pipe IPC Safety Audit

1. **Process Pipe IPC Deadlock Vulnerability**: 
   When writing the batch payload to the daemon (`self._proc.stdin.write(payload_str.encode())`), the code subsequently awaits `self._proc.stdin.drain()`. This `drain()` call is **unbounded**. If the Go process enters a deadlocked state and stops reading from stdin, the OS pipe buffer will fill up. When this happens, `await drain()` will block indefinitely. This completely bypasses the batch timeout logic (which only guards the `asyncio.gather` for futures). 
2. **JSON Serialization Inefficiency**: 
   The `_json_str` helper takes `orjson.dumps` (which outputs `bytes`), decodes it to a string, joins it via string concatenation, and then encodes it back to `bytes` before writing to `stdin`. Joining `bytes` directly is safer and strictly more performant.

## Fallback & Error Boundary Assessment

- **Successful Fallback for Future Batches**: When the daemon is permanently disabled (`self.available = False` after self-test failure or 5 consecutive timeouts), subsequent batches immediately return unmodified proxy lists. The broader ConfigStream framework correctly detects unresolved proxies and falls back to Python-based sequential proxy checking.
- **In-flight Proxies on Crash/Timeout**: If the Go daemon crashes (`BrokenPipeError`) or times out *during* an active batch, the affected proxies are explicitly marked as `is_working = False` with reasons like `DAEMON_CRASHED` or `BATCH_TIMEOUT`. Because they are marked as explicitly failed, they bypass the Python fallback mechanism. If the intent is to gracefully fail over in-flight proxies to Python, their states should be reverted to `None` instead of `False`.

## Code Hardening Patches

### Patch 1: Prevent `drain()` IPC Deadlock & Optimize Serialization
**Target**: `src/configstream/testers/go_tester/manager.py` -> `test_batch` & `test_custom_configs`

```python
# [Before] Unbounded drain and inefficient serialization:
payload_str = "\n".join(_json_str(i) for i in inputs) + "\n"
self._proc.stdin.write(payload_str.encode())
await self._proc.stdin.drain()

# [After] Bounded drain and direct bytes joining:
from ...async_utils import safe_wait_for
import orjson as json

payload_bytes = b"\n".join(json.dumps(i) for i in inputs) + b"\n"
self._proc.stdin.write(payload_bytes)
try:
    await safe_wait_for(self._proc.stdin.drain(), timeout=15.0)
except asyncio.TimeoutError:
    logger.error("IPC Deadlock: Failed to drain stdin to Go Tester")
    await self._restart_daemon()
    return proxies
```

### Patch 2: Fix Orphaned Process Leak on Threshold Reached
**Target**: `src/configstream/testers/go_tester/manager.py` -> `test_batch`

```python
# [Before] Spawns a useless daemon before exiting:
if self._consecutive_timeouts >= self._max_consecutive_timeouts:
    logger.error("... Disabling to preserve pipeline time budget.")
    self.available = False
    await self._restart_daemon()
    return proxies

# [After] Cleanly terminates without spawning orphans:
if self._consecutive_timeouts >= self._max_consecutive_timeouts:
    logger.error("... Disabling to preserve pipeline time budget.")
    self.available = False
    await self.close()  # Properly kill proc and readers
    return proxies
```
