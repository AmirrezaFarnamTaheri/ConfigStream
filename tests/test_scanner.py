import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
            b'{"ip":"162.159.192.2", "port":2408, "latency":1000}',
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

    assert len(ips) == 1
    assert "162.159.192.1" in ips
    assert "162.159.192.2" not in ips  # Latency 1000 > 800


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
