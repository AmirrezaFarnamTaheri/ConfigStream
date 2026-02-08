import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.workers.scanner import WarpScannerWorker

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
    worker = WarpScannerWorker("/bin/true")
    worker.available = True

    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True

        # Mock subprocess
        proc = AsyncMock()
        proc.returncode = 0
        proc.communicate.return_value = (
            b'{"ip":"162.159.192.1", "port":2408, "latency":50}\n{"ip":"162.159.192.2", "port":2408, "latency":1000}',
            b""
        )

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ips = await worker.scan_endpoints(limit=2, max_latency=800)
            assert len(ips) == 1
            assert "162.159.192.1" in ips
            assert "162.159.192.2" not in ips  # Latency 1000 > 800

@pytest.mark.asyncio
async def test_scan_endpoints_execution_failure():
    worker = WarpScannerWorker("/bin/false")
    worker.available = True

    with patch("configstream.config.AppSettings") as MockSettings:
        MockSettings.return_value.ALLOW_ACTIVE_SCANNING = True

        proc = AsyncMock()
        proc.returncode = 1
        proc.communicate.return_value = (b"", b"Error")

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ips = await worker.scan_endpoints()
            assert ips == []
