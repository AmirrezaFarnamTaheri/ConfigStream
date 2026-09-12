import asyncio
import json
import threading
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.testers.python import PythonTester
from configstream.models import Proxy


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.TEST_URLS = {"google": "http://google.com"}
    settings.CANARY_URL = None
    return settings


@pytest.mark.asyncio
async def test_python_tester_direct_http(mock_settings):
    tester = PythonTester(mock_settings)
    proxy = Proxy(
        config="http://1.1.1.1:80", protocol="http", address="1.1.1.1", port=80
    )

    # Patch at the module level where PythonTester imports aiohttp, not the
    # global aiohttp namespace — previous patch target was wrong.
    with patch("configstream.testers.python.aiohttp.ClientSession") as MockSession:
        session = MockSession.return_value
        session.__aenter__.return_value = session

        # Mock successful response
        resp = MagicMock()
        resp.status = 200
        resp.__aenter__.return_value = resp
        session.get.return_value = resp

        result = await tester.test_direct(proxy)
        assert result.is_working
        assert result.latency is not None


@pytest.mark.asyncio
async def test_python_tester_direct_fail(mock_settings):
    tester = PythonTester(mock_settings)
    proxy = Proxy(
        config="http://1.1.1.1:80", protocol="http", address="1.1.1.1", port=80
    )

    # Patch at the correct module level (same fix as test_python_tester_direct_http).
    with patch("configstream.testers.python.aiohttp.ClientSession") as MockSession:
        session = MockSession.return_value
        session.__aenter__.return_value = session

        # _measure_latency_robust tries each URL twice, catching every exception
        # internally and returning None. The None propagates to test_direct
        # which sets is_working=False — no exception reaches the outer except
        # block, so details['error'] is NOT set in this code path.
        session.get.side_effect = Exception("Connection refused")

        result = await tester.test_direct(proxy)
        assert not result.is_working
        assert result.details.get("error") is None


@pytest.mark.asyncio
async def test_python_tester_singbox_missing_factory(mock_settings):
    with patch("configstream.testers.python._get_singbox_factory", return_value=None):
        tester = PythonTester(mock_settings)
        proxy = Proxy(
            config="vmess://...",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="uuid",
        )

        result = await tester.test_via_singbox(proxy)
        assert not result.is_working


@pytest.mark.asyncio
async def test_python_tester_no_config(mock_settings):
    tester = PythonTester(mock_settings)
    proxy = Proxy(config="", protocol="vmess", address="1.1.1.1", port=443, uuid="uuid")
    result = await tester.test_via_singbox(proxy)
    assert not result.is_working


@pytest.mark.asyncio
async def test_python_tester_wires_wrapper_readiness_port(mock_settings):
    """A supplied sing-box config must expose the same port the wrapper polls."""
    tester = PythonTester(mock_settings)
    proxy = Proxy(
        config="vless://example",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="00000000-0000-0000-0000-000000000001",
    )
    captured = {}

    class Instance:
        http_proxy_url = "http://127.0.0.1:12345"

        def stop(self):
            return None

    def factory(config_path, *, http_port, socks_port):
        captured["config"] = json.loads(Path(config_path).read_text(encoding="utf-8"))
        captured["http_port"] = http_port
        captured["socks_port"] = socks_port
        return Instance()

    with (
        patch("configstream.testers.python._get_singbox_factory", return_value=factory),
        patch("configstream.testers.python._reserve_loopback_port", return_value=43123),
        patch("configstream.testers.python.aiohttp.ClientSession") as MockSession,
    ):
        session = MockSession.return_value
        session.__aenter__.return_value = session
        response = MagicMock(status=204)
        response.__aenter__.return_value = response
        session.get.return_value = response
        result = await tester.test_via_singbox(proxy)

    assert result.is_working
    assert captured["http_port"] == 43123
    assert captured["socks_port"] is False
    assert captured["config"]["inbounds"] == [
        {
            "type": "http",
            "tag": "http-in",
            "listen": "127.0.0.1",
            "listen_port": 43123,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("abandon", ["timeout", "cancel"])
async def test_startup_cleans_late_process_and_retains_config(abandon):
    from configstream.testers.python import _start_instance

    entered = threading.Event()
    release = threading.Event()
    stopped = threading.Event()
    observed = {}

    class Instance:
        def stop(self):
            stopped.set()

    def factory(config_path, **kwargs):
        observed["path"] = Path(config_path)
        entered.set()
        assert release.wait(5), "test did not release startup worker"
        observed["config"] = json.loads(Path(config_path).read_text())
        return Instance()

    task = asyncio.create_task(
        _start_instance(
            factory,
            '{"outbounds": []}',
            43123,
            timeout=0.1 if abandon == "timeout" else 5,
        )
    )
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        if abandon == "cancel":
            task.cancel()
        with pytest.raises(
            asyncio.TimeoutError if abandon == "timeout" else asyncio.CancelledError
        ):
            await task
        assert observed["path"].exists()
    finally:
        release.set()
    assert await asyncio.to_thread(stopped.wait, 5)
    assert observed["config"] == {"outbounds": []}
    assert not observed["path"].exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "protocol,tls", [("https", False), ("http", True), ("socks5", False)]
)
async def test_direct_connector_preserves_auth_and_proxy_tls(
    mock_settings, protocol, tls
):
    import ssl
    from aiohttp_socks import ProxyConnector

    tester = PythonTester(mock_settings)
    proxy = Proxy(
        config="http://example",
        protocol=protocol,
        address="2001:db8::1",
        port=443,
        details={"username": "user/name", "password": "p/a:ss@word", "tls": tls},
    )
    connectors = []
    original = ProxyConnector.from_url

    def create(url, **kwargs):
        connector = original(url, **kwargs)
        connectors.append(connector)
        return connector

    try:
        with (
            patch(
                "configstream.testers.python.ProxyConnector.from_url",
                side_effect=create,
            ),
            patch("configstream.testers.python.aiohttp.ClientSession"),
            patch.object(
                tester, "_measure_latency_robust", AsyncMock(return_value=12.0)
            ),
        ):
            result = await tester.test_direct(proxy)
        assert result.is_working
        connector = connectors[0]
        assert connector._proxy_host == "2001:db8::1"
        assert connector._proxy_username == "user/name"
        assert connector._proxy_password == "p/a:ss@word"
        if protocol == "https" or tls:
            assert connector._proxy_ssl.verify_mode == ssl.CERT_REQUIRED
            assert connector._proxy_ssl.check_hostname
        else:
            assert connector._proxy_ssl is None
    finally:
        for connector in connectors:
            await connector.close()
