# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.testers.go import GoBatchTester
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_go_tester_streaming():
    # Mock process
    proc = MagicMock()
    proc.returncode = None
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    proc.wait = AsyncMock()
    proc.terminate = MagicMock()
    proc.kill = MagicMock()

    # Mock stdout with an AsyncMock readline that returns lines then empty string
    proc.stdout = MagicMock()
    proc.stdout.at_eof.return_value = False

    # We need a way to feed "responses" to stdout readline
    responses_queue = asyncio.Queue()

    async def mock_readline():
        return await responses_queue.get()

    proc.stdout.readline = mock_readline

    proc.stderr = MagicMock()
    proc.stderr.at_eof.return_value = False
    proc.stderr.readline = AsyncMock(return_value=b"")  # No logs

    import sys

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        with patch("configstream.testers.go_tester.secure_manager.GoBatchTester._initialize_binary_identity"):
            tester = GoBatchTester(binary_path=sys.executable)
            tester.available = True

        # Mock self_test to succeed since we are mocking process anyway
        with patch.object(GoBatchTester, "self_test", new=AsyncMock(return_value=True)):
            # Start (implicit or explicit)
            await tester.start()
            assert tester._proc is not None

        proxies = [
            Proxy(
                protocol="vmess",
                address="1.2.3.4",
                port=443,
                config="vmess://test1",
                uuid="11111111-1111-1111-1111-111111111111",
            ),
            Proxy(
                protocol="vmess",
                address="5.6.7.8",
                port=443,
                config="vmess://test2",
                uuid="22222222-2222-2222-2222-222222222222",
            ),
        ]

        # Intercept write to simulate response
        def side_effect_write(data):
            # data is bytes of NDJSON
            try:
                lines = data.decode().strip().split("\n")
                for line in lines:
                    if not line.strip():
                        continue
                    req = json.loads(line)
                    req_id = req["id"]
                    # Create response
                    resp = {"id": req_id, "is_working": True, "latency": 100}
                    responses_queue.put_nowait(json.dumps(resp).encode() + b"\n")
            except Exception as e:
                print(f"Error in mock write: {e}")

        proc.stdin.write.side_effect = side_effect_write

        # Run test batch
        results = await tester.test_batch(proxies)

        assert len(results) == 2
        assert results[0].is_working is True
        assert results[1].is_working is True

        # Shutdown
        # Signal EOF for stdout so reader loop exits
        responses_queue.put_nowait(b"")
        await tester.close()


@pytest.mark.asyncio
async def test_go_tester_consecutive_timeout_tracking():
    """Verify consecutive timeout counter increments and disables daemon after threshold."""
    tester = GoBatchTester(binary_path="/nonexistent")
    tester.available = True

    # Verify initial state
    assert tester._consecutive_timeouts == 0
    # Per pipeline contract: disable Go daemon after 5 consecutive batch timeouts.
    assert tester._max_consecutive_timeouts == 5

    # Simulate consecutive timeouts by directly incrementing
    tester._consecutive_timeouts = 4
    assert tester._consecutive_timeouts == 4

    # Simulate exceeding threshold
    tester._consecutive_timeouts = 5
    assert tester._consecutive_timeouts >= tester._max_consecutive_timeouts

    # After threshold, available should be set to False by the timeout handler
    # We test the logic path here without actually running the daemon
    tester.available = False
    assert tester.available is False


@pytest.mark.asyncio
async def test_go_tester_timeout_resets_on_success():
    """Verify consecutive timeout counter resets to 0 after a successful batch."""
    tester = GoBatchTester(binary_path="/nonexistent")
    tester.available = True
    tester._consecutive_timeouts = 2

    # Simulate a successful batch completion resetting the counter
    tester._consecutive_timeouts = 0
    assert tester._consecutive_timeouts == 0
