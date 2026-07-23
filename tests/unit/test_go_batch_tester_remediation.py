# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for GoBatchTester IPC drain timeout and orphan process prevention.

Task 1 of the Post-Audit Remediation Plan.

Strategy: import the base streaming class directly from manager.py (bypassing
the binary-identity verification in secure_manager.py), and patch
_ensure_process to a no-op so test_batch can reach the drain() path.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the *base* streaming class to avoid binary discovery in secure_manager
from configstream.testers.go_tester.manager import GoBatchTester as _BaseTester
from configstream.models import Proxy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proxy(address: str = "1.1.1.1", port: int = 443) -> Proxy:
    """Build a minimal valid Proxy for testing."""
    return Proxy(
        config=f"vless://00000000-0000-0000-0000-000000000001@{address}:{port}",
        protocol="vless",
        address=address,
        port=port,
        uuid="00000000-0000-0000-0000-000000000001",
    )


def _make_tester() -> _BaseTester:
    """Construct a BaseTester with all required instance state, no side-effects."""
    tester = object.__new__(_BaseTester)
    tester.workers = 20
    tester.timeout = 10
    tester.binary_path = "dummy_binary"
    tester.available = True
    tester._proc = None
    tester._lock = asyncio.Lock()
    tester._pending_futures: dict = {}
    tester._stopping = False
    tester._consecutive_timeouts = 0
    tester._max_consecutive_timeouts = 5
    tester._canary_url = None
    tester._check_honeypot = False
    tester._reader_task = None
    return tester


# Minimal outbound dict returned by mock to_singbox_outbound
_MOCK_OUTBOUND = {"type": "vless", "server": "1.1.1.1", "server_port": 443}


# ---------------------------------------------------------------------------
# Test 1: blocking drain -> daemon restart
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_drain_timeout_triggers_daemon_restart():
    """A drain() that blocks indefinitely must time out and restart the daemon."""
    tester = _make_tester()

    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdin.write = MagicMock()
    mock_proc.stdin.is_closing = MagicMock(return_value=False)

    async def blocking_drain():
        await asyncio.sleep(9999)

    mock_proc.stdin.drain = blocking_drain
    tester._proc = mock_proc

    proxy = _make_proxy()

    async def instant_timeout(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        raise asyncio.TimeoutError

    with patch.object(tester, "_ensure_process", new_callable=AsyncMock), \
         patch(
             "configstream.testers.go_tester.manager.to_singbox_outbound",
             return_value=_MOCK_OUTBOUND,
         ), \
         patch.object(tester, "_restart_daemon", new_callable=AsyncMock) as mock_restart, \
         patch.object(tester, "close", new_callable=AsyncMock), \
         patch(
             "configstream.testers.go_tester.manager.safe_wait_for",
             side_effect=instant_timeout,
         ):
        result = await tester.test_batch([proxy])

    mock_restart.assert_called_once()
    assert result == [proxy]


# ---------------------------------------------------------------------------
# Test 2: 5th consecutive drain timeout -> close() called, available=False
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fifth_consecutive_drain_timeout_disables_tester():
    """On the 5th consecutive drain timeout the tester must be disabled via close()."""
    tester = _make_tester()
    tester._consecutive_timeouts = 4  # next timeout hits the threshold

    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdin.write = MagicMock()
    mock_proc.stdin.is_closing = MagicMock(return_value=False)
    tester._proc = mock_proc

    proxy = _make_proxy(address="2.2.2.2")

    async def instant_timeout(coro, timeout):
        try:
            coro.close()
        except Exception:
            pass
        raise asyncio.TimeoutError

    with patch.object(tester, "_ensure_process", new_callable=AsyncMock), \
         patch(
             "configstream.testers.go_tester.manager.to_singbox_outbound",
             return_value=_MOCK_OUTBOUND,
         ), \
         patch.object(tester, "close", new_callable=AsyncMock) as mock_close, \
         patch.object(tester, "_restart_daemon", new_callable=AsyncMock) as mock_restart, \
         patch(
             "configstream.testers.go_tester.manager.safe_wait_for",
             side_effect=instant_timeout,
         ):
        result = await tester.test_batch([proxy])

    assert tester.available is False
    mock_close.assert_called_once()
    mock_restart.assert_not_called()
    assert result == [proxy]
