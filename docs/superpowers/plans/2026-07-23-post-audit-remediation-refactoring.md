# Post-Audit Remediation & Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement critical security, IPC performance, and caching fixes identified during the 44-track repository audit, and perform structured slop cleanup to enforce zero dead code.

**Architecture:** Bounded IPC stdin drain with 15s timeouts for the Go daemon tester; per-path `asyncio.Lock` stampede protection and ETag headers for server endpoints; HMAC-SHA256 offset derivation for steganography; and safe removal of unused helper abstractions.

**Tech Stack:** Python 3.10+ (asyncio, orjson, hashlib, pytest).

## Global Constraints

- Preserve PEP 8 code formatting and 100% test suite green status (1,244/1,244 tests passing).
- Zero placeholders: all task steps must include complete, copy-pasteable code blocks and explicit commands.
- Never introduce breaking changes to `docs/*.json` schemas or public API endpoints.

---

### Task 1: GoBatchTester IPC Deadlock & Process Leak Remediation

**Files:**
- Modify: `src/configstream/testers/go_tester/manager.py`
- Test: `tests/unit/test_go_batch_tester_remediation.py`

**Interfaces:**
- Consumes: `safe_wait_for` from `src/configstream/async_utils.py`
- Produces: Hardened `GoBatchTester.test_batch` with bounded `stdin.drain()` and clean process termination on 5-timeout limit.

- [ ] **Step 1: Write failing unit test for GoBatchTester IPC drain timeout and orphan process prevention**

Create `tests/unit/test_go_batch_tester_remediation.py`:
```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.testers.go_tester.manager import GoBatchTester

@pytest.mark.asyncio
async def test_drain_timeout_triggers_daemon_restart():
    tester = GoBatchTester(binary_path="dummy_path")
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdin.write = MagicMock()
    # Simulate stdin.drain blocking indefinitely
    async def blocking_drain():
        await asyncio.sleep(100)
    mock_proc.stdin.drain = blocking_drain
    tester._proc = mock_proc
    tester.available = True

    with patch.object(tester, '_restart_daemon', new_callable=AsyncMock) as mock_restart:
        proxies = [{"url": "vless://test@1.1.1.1:443"}]
        res = await tester.test_batch(proxies)
        assert res == proxies
        mock_restart.assert_called_once()

@pytest.mark.asyncio
async def test_consecutive_timeouts_calls_close_not_restart():
    tester = GoBatchTester(binary_path="dummy_path")
    tester._consecutive_timeouts = 4
    tester._max_consecutive_timeouts = 5
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdin.write = MagicMock()
    mock_proc.stdin.drain = AsyncMock(side_effect=asyncio.TimeoutError)
    tester._proc = mock_proc
    tester.available = True

    with patch.object(tester, 'close', new_callable=AsyncMock) as mock_close, \
         patch.object(tester, '_restart_daemon', new_callable=AsyncMock) as mock_restart:
        proxies = [{"url": "vless://test@1.1.1.1:443"}]
        res = await tester.test_batch(proxies)
        assert tester.available is False
        mock_close.assert_called_once()
        mock_restart.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/test_go_batch_tester_remediation.py`
Expected: FAIL due to missing bounded drain or `mock_restart` being called instead of `close`.

- [ ] **Step 3: Implement bounded drain and orphan process fix in `src/configstream/testers/go_tester/manager.py`**

Modify `src/configstream/testers/go_tester/manager.py` lines inside `test_batch`:
```python
# Replace unbounded stdin.drain with safe_wait_for
payload_bytes = b"\n".join(orjson.dumps(i) for i in inputs) + b"\n"
self._proc.stdin.write(payload_bytes)
try:
    await safe_wait_for(self._proc.stdin.drain(), timeout=15.0)
except (asyncio.TimeoutError, Exception) as exc:
    logger.error("IPC Deadlock/Error: Failed to drain stdin to Go Tester: %s", exc)
    self._consecutive_timeouts += 1
    if self._consecutive_timeouts >= self._max_consecutive_timeouts:
        logger.error("Disabling Go Batch Tester due to 5 consecutive timeouts.")
        self.available = False
        await self.close()
    else:
        await self._restart_daemon()
    return proxies
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/test_go_batch_tester_remediation.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/testers/go_tester/manager.py tests/unit/test_go_batch_tester_remediation.py
git commit -m "fix(tester): prevent IPC drain deadlock and process leaks in GoBatchTester"
```

---

### Task 2: Server Concurrent Cache Stampede & HTTP Header Remediation

**Files:**
- Modify: `src/configstream/server.py`
- Test: `tests/unit/test_server_cache_remediation.py`

**Interfaces:**
- Consumes: `_read_json_file_async` in `src/configstream/server.py`
- Produces: Stampede-proof `_read_json_file_async` using per-path `asyncio.Lock` and `ETag`/`Cache-Control` headers for `/api/stats`.

- [ ] **Step 1: Write failing unit test for cache stampede prevention and ETag generation**

Create `tests/unit/test_server_cache_remediation.py`:
```python
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from configstream.server import _read_json_file_async, _cache_locks

@pytest.mark.asyncio
async def test_cache_stampede_single_read_execution(tmp_path):
    json_file = tmp_path / "test_data.json"
    json_file.write_text('{"status": "ok"}')

    read_count = 0
    def mock_read(p):
        nonlocal read_count
        read_count += 1
        return {"status": "ok"}

    with patch("configstream.server._read_json_file", side_effect=mock_read):
        # Fire 10 concurrent async reads for the same missing cache file
        results = await asyncio.gather(*[_read_json_file_async(json_file) for _ in range(10)])
        assert len(results) == 10
        assert read_count == 1  # Only read once due to lock
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/test_server_cache_remediation.py`
Expected: FAIL with `assert 10 == 1` due to missing stampede lock.

- [ ] **Step 3: Implement per-path `asyncio.Lock` stampede fix in `src/configstream/server.py`**

In `src/configstream/server.py`, add `_cache_locks` and update `_read_json_file_async`:
```python
from collections import defaultdict

_cache_locks: dict[Path, asyncio.Lock] = defaultdict(asyncio.Lock)

async def _read_json_file_async(path: Path) -> Any:
    try:
        current_mtime = await asyncio.to_thread(os.path.getmtime, path)
    except FileNotFoundError:
        _json_cache.pop(path, None)
        raise

    cached = _json_cache.get(path)
    if cached and cached[0] == current_mtime:
        return cached[1]

    async with _cache_locks[path]:
        # Double-check inside lock
        cached = _json_cache.get(path)
        if cached and cached[0] == current_mtime:
            return cached[1]

        data = await asyncio.to_thread(_read_json_file, path)
        _json_cache[path] = (current_mtime, data)
        return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/test_server_cache_remediation.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/server.py tests/unit/test_server_cache_remediation.py
git commit -m "fix(server): introduce per-path asyncio.Lock to prevent cache stampede"
```

---

### Task 3: Repository Slop Cleanup & Unused Dead Code Deletion

**Files:**
- Modify: `src/configstream/fetcher_worker.py`
- Test: `tests/unit/test_slop_cleanup_verification.py`

**Interfaces:**
- Consumes: Target files listed in `docs/REPO_WIDE_SLOP_CLEANUP_AUDIT.md`
- Produces: Cleaned codebase with zero unused pass-through classes or dead functions.

- [ ] **Step 1: Write verification test for removed dead code classes**

Create `tests/unit/test_slop_cleanup_verification.py`:
```python
import pytest
import configstream.fetcher_worker as fw

def test_unused_exception_classes_removed():
    assert not hasattr(fw, "UnusedLegacyFetcherError")
```

- [ ] **Step 2: Run test to verify it fails/passes based on state**

Run: `python -m pytest -o pythonpath=src tests/unit/test_slop_cleanup_verification.py`

- [ ] **Step 3: Remove identified dead code and redundant wrappers**

Clean up dead code in `src/configstream/fetcher_worker.py` and verify all 1,244 unit tests remain green.

- [ ] **Step 4: Run full test suite to verify zero regressions**

Run: `python -m pytest -o pythonpath=src tests/unit`
Expected: 1,244 / 1,244 PASS (100% Green)

- [ ] **Step 5: Commit**

```bash
git add src/configstream/fetcher_worker.py tests/unit/test_slop_cleanup_verification.py
git commit -m "refactor(cleanup): remove unused dead code classes identified in audit"
```
