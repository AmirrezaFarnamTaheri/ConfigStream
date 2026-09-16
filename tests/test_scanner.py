import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.warp_scanner import WarpScannerWorker


@pytest.mark.asyncio
async def test_scanner_ci_disabled():
    # Mock settings to NOT force scanner
    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.FORCE_SCANNER = False
        with patch.dict("os.environ", {"CI": "true"}):
            worker = WarpScannerWorker()
            assert not worker.available


@pytest.mark.asyncio
async def test_scanner_ci_force_enabled():
    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.FORCE_SCANNER = True
        MockSettings.return_value.CONFIGSTREAM_TESTER_BIN = "/bin/ls"  # Dummy path
        with patch.dict("os.environ", {"CI": "true"}):
            with patch("os.path.exists", return_value=True):
                worker = WarpScannerWorker()
                assert worker.available


@pytest.mark.asyncio
async def test_scan_endpoints_disabled_settings():
    worker = WarpScannerWorker("/bin/ls")
    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.ALLOW_ACTIVE_SCANNING = False
        MockSettings.return_value.FORCE_SCANNER = False

        ips = await worker.scan_endpoints()
        assert ips == []


@pytest.mark.asyncio
async def test_scan_endpoints_rejects_invalid_numeric_bounds():
    worker = WarpScannerWorker("/bin/ls")
    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True
        MockSettings.return_value.FORCE_SCANNER = False

        assert await worker.scan_endpoints(limit=0) == []
        assert await worker.scan_endpoints(timeout=0) == []
        assert await worker.scan_endpoints(max_latency=-1) == []


@pytest.mark.asyncio
async def test_scan_endpoints_execution_success():
    identity = SimpleNamespace(path=Path("/bin/true"))

    with (
        patch("configstream.config.AppSettings") as MockSettings,
        patch.dict(os.environ, {"CI": "true"}, clear=False),
    ):
        settings = MockSettings.return_value
        settings.ALLOW_ACTIVE_SCANNING = True
        settings.FORCE_SCANNER = True
        settings.CONFIGSTREAM_TESTER_BIN = "/bin/true"
        worker = WarpScannerWorker("/bin/true")
        assert worker.available

        proc = AsyncMock()
        proc.returncode = 0
        proc.communicate.return_value = (
            b'{"ip":"162.159.192.1", "port":2408, "latency":50}\n'
            b'{"ip":"not-an-ip", "port":2408, "latency":10}\n'
            b'{"ip":"162.159.192.2", "port":2408, "latency":-1}\n'
            b'{"ip":"162.159.192.3", "port":2408, "latency":1000}\n'
            b'{"ip":"162.159.192.4", "port":2408, "latency":60}\n'
            b'{"ip":"162.159.192.5", "port":2408, "latency":70}',
            b"",
        )

        with (
            patch(
                "configstream.testers.go_tester.binary_security.initialize_binary_identity",
                return_value=identity,
            ),
            patch(
                "configstream.testers.go_tester.binary_security.verify_binary_identity",
                return_value=True,
            ),
            patch("asyncio.create_subprocess_exec", return_value=proc),
        ):
            ips = await worker.scan_endpoints(limit=2, max_latency=800)

    assert ips == ["162.159.192.1", "162.159.192.4"]


@pytest.mark.asyncio
async def test_scan_endpoints_execution_failure():
    identity = SimpleNamespace(path=Path("/bin/false"))

    with (
        patch("configstream.config.AppSettings") as MockSettings,
        patch.dict(os.environ, {"CI": "true"}, clear=False),
    ):
        settings = MockSettings.return_value
        settings.ALLOW_ACTIVE_SCANNING = True
        settings.FORCE_SCANNER = True
        settings.CONFIGSTREAM_TESTER_BIN = "/bin/false"
        worker = WarpScannerWorker("/bin/false")
        assert worker.available

        proc = AsyncMock()
        proc.returncode = 1
        proc.communicate.return_value = (b"", b"Error")

        with (
            patch(
                "configstream.testers.go_tester.binary_security.initialize_binary_identity",
                return_value=identity,
            ),
            patch(
                "configstream.testers.go_tester.binary_security.verify_binary_identity",
                return_value=True,
            ),
            patch("asyncio.create_subprocess_exec", return_value=proc),
        ):
            ips = await worker.scan_endpoints()

    assert ips == []


@pytest.mark.asyncio
async def test_scan_timeout_kills_and_reaps_child():
    identity = SimpleNamespace(path=Path("/bin/true"))

    with (
        patch("configstream.config.AppSettings") as MockSettings,
        patch.dict(os.environ, {"CI": "true"}, clear=False),
    ):
        settings = MockSettings.return_value
        settings.ALLOW_ACTIVE_SCANNING = True
        settings.FORCE_SCANNER = True
        settings.CONFIGSTREAM_TESTER_BIN = "/bin/true"
        worker = WarpScannerWorker("/bin/true")

        proc = MagicMock()
        proc.returncode = None
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        proc.wait = AsyncMock(return_value=-9)

        with (
            patch(
                "configstream.testers.go_tester.binary_security.initialize_binary_identity",
                return_value=identity,
            ),
            patch(
                "configstream.testers.go_tester.binary_security.verify_binary_identity",
                return_value=True,
            ),
            patch("asyncio.create_subprocess_exec", return_value=proc),
        ):
            assert await worker.scan_endpoints() == []

    proc.kill.assert_called_once_with()
    proc.wait.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_scan_cancellation_kills_reaps_and_propagates():
    identity = SimpleNamespace(path=Path("/bin/true"))

    with (
        patch("configstream.config.AppSettings") as MockSettings,
        patch.dict(os.environ, {"CI": "true"}, clear=False),
    ):
        settings = MockSettings.return_value
        settings.ALLOW_ACTIVE_SCANNING = True
        settings.FORCE_SCANNER = True
        settings.CONFIGSTREAM_TESTER_BIN = "/bin/true"
        worker = WarpScannerWorker("/bin/true")

        proc = MagicMock()
        proc.returncode = None
        proc.communicate = AsyncMock(side_effect=asyncio.CancelledError)
        proc.wait = AsyncMock(return_value=-9)

        with (
            patch(
                "configstream.testers.go_tester.binary_security.initialize_binary_identity",
                return_value=identity,
            ),
            patch(
                "configstream.testers.go_tester.binary_security.verify_binary_identity",
                return_value=True,
            ),
            patch("asyncio.create_subprocess_exec", return_value=proc),
        ):
            with pytest.raises(asyncio.CancelledError):
                await worker.scan_endpoints()

    proc.kill.assert_called_once_with()
    proc.wait.assert_awaited_once_with()
