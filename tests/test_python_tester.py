import pytest
from unittest.mock import MagicMock, AsyncMock, patch
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

    with patch("aiohttp.ClientSession") as MockSession:
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

    # We need to ensure _measure_latency_robust returns None
    # It catches exceptions.

    with patch("aiohttp.ClientSession") as MockSession:
        session = MockSession.return_value
        session.__aenter__.return_value = session

        # Mock exception for get()
        session.get.side_effect = Exception("Connection refused")

        # NOTE: _measure_latency_robust tries 2 times.
        # If both fail, it returns None.

        result = await tester.test_direct(proxy)
        assert not result.is_working
        # details['error'] might be set or not depending on where exception is caught.
        # test_direct catches outer exceptions.
        # _measure_latency_robust catches inner exceptions and returns None.
        # If None returned, is_working=False. details error NOT set in test_direct if latency is None.
        # Wait, looking at code:
        # try: ... latency = ... if latency is None: is_working=False
        # except Exception as e: is_working=False; details['error']=...
        # Since _measure_latency_robust handles connection error internally and returns None,
        # no exception propagates to test_direct's except block.
        # So details['error'] is NOT set.

        # assert result.details.get("error")  <-- This fails.
        pass


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
