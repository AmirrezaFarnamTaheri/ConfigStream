import pytest
from unittest.mock import MagicMock, patch
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
