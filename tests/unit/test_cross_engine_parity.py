# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.models import Proxy
from configstream.testers.python import PythonTester
from configstream.testers.go import GoBatchTester


@pytest.mark.asyncio
async def test_go_and_python_tester_verdict_parity():
    """Verify that both GoBatchTester and PythonTester map verdicts consistently for the same outcomes."""
    # Create sample proxies
    proxy_ok = Proxy(
        protocol="http",
        address="1.1.1.1",
        port=80,
        config="http://1.1.1.1:80",
    )
    proxy_fail = Proxy(
        protocol="http",
        address="2.2.2.2",
        port=80,
        config="http://2.2.2.2:80",
    )

    # 1. Setup Python Tester Mock Response
    settings = MagicMock()
    settings.TEST_URLS = {"google": "http://google.com"}
    settings.CANARY_URL = None
    py_tester = PythonTester(settings)

    # Mock ClientSession and ProxyConnector for PythonTester
    with (
        patch("configstream.testers.python.ProxyConnector.from_url") as mock_from_url,
        patch("aiohttp.ClientSession") as MockSession,
    ):

        def make_mock_connector(url):
            connector = MagicMock()
            connector._proxy_url = url
            return connector

        mock_from_url.side_effect = make_mock_connector

        def session_factory(*args, **kwargs):
            connector = kwargs.get("connector")
            proxy_url = getattr(connector, "_proxy_url", "")

            session = MagicMock()
            session.__aenter__.return_value = session

            resp_ok = MagicMock()
            resp_ok.status = 200
            resp_ok.__aenter__.return_value = resp_ok

            def get_side_effect(url, **kwargs):
                if "2.2.2.2" in str(proxy_url):
                    raise Exception("Connection Refused")
                return resp_ok

            session.get.side_effect = get_side_effect
            return session

        MockSession.side_effect = session_factory

        py_res_ok = await py_tester.test_direct(proxy_ok)
        py_res_fail = await py_tester.test_direct(proxy_fail)

    # Assert Python Tester outputs
    assert py_res_ok.is_working is True
    assert py_res_fail.is_working is False

    # 2. Setup Go Tester Mock Process Response
    proc = MagicMock()
    proc.returncode = None
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    proc.wait = AsyncMock()
    proc.terminate = MagicMock()
    proc.kill = MagicMock()

    proc.stdout = MagicMock()
    proc.stdout.at_eof.return_value = False
    proc.stderr = MagicMock()
    proc.stderr.at_eof.return_value = False
    proc.stderr.readline = AsyncMock(return_value=b"")

    responses_queue = asyncio.Queue()

    async def mock_readline():
        return await responses_queue.get()

    proc.stdout.readline = mock_readline

    def side_effect_write(data):
        import json

        lines = data.decode().strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            req = json.loads(line)
            req_id = req["id"]
            # 1.1.1.1 is working, 2.2.2.2 is not
            is_working = "1.1.1.1" in req.get("config", "")
            resp = {
                "id": req_id,
                "is_working": is_working,
                "latency": 150 if is_working else 0,
                "error": None if is_working else "connection refused",
            }
            responses_queue.put_nowait(json.dumps(resp).encode() + b"\n")

    proc.stdin.write.side_effect = side_effect_write

    import sys

    with (
        patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)),
        patch(
            "configstream.testers.go_tester.secure_manager.GoBatchTester._initialize_binary_identity"
        ),
        patch(
            "configstream.testers.go_tester.secure_manager.GoBatchTester._verify_binary_integrity",
            return_value=True,
        ),
        patch.object(GoBatchTester, "self_test", new=AsyncMock(return_value=True)),
    ):
        go_tester = GoBatchTester(binary_path=sys.executable)
        go_tester.available = True
        await go_tester.start()

        batch = [proxy_ok, proxy_fail]
        go_results = await go_tester.test_batch(batch)

        responses_queue.put_nowait(b"")
        await go_tester.close()

    assert len(go_results) == 2
    go_res_ok = go_results[0]
    go_res_fail = go_results[1]

    # Verify verdict parity:
    # 1. Working proxy must have is_working=True on both engines
    assert go_res_ok.is_working == py_res_ok.is_working
    # 2. Failed proxy must have is_working=False on both engines
    assert go_res_fail.is_working == py_res_fail.is_working
