import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Removed nest_asyncio and manual event_loop fixture to rely on pytest-asyncio default behavior.


@pytest.fixture
def mock_singbox_factory(monkeypatch):
    """
    Mocks the SingBoxProxy factory and its instances.
    """
    mock_instance = MagicMock()
    mock_instance.http_proxy_url = "http://127.0.0.1:10809"
    mock_instance.socks_proxy_url = "socks5://127.0.0.1:10808"
    mock_instance.stop = MagicMock()

    # Create a factory that returns this mock instance
    # The factory in production code is synchronous: singbox_factory(config_path) -> instance
    mock_factory = MagicMock(return_value=mock_instance)

    monkeypatch.setattr("configstream.testers.singbox_factory", mock_factory)
    return mock_factory


@pytest.fixture(autouse=True)
def mock_latency_checks(monkeypatch):
    """
    Automatically mock all latency checks to prevent real network calls
    and ensure predictable results in integration tests.
    """

    async def mock_measure_latency(*args, **kwargs):
        return 123.45

    # Mock the main latency measurement method in the tester
    monkeypatch.setattr(
        "configstream.testers.SingBoxTester._measure_latency_robust",
        mock_measure_latency,
    )

    # Also mock the direct test method to prevent any network calls
    async def mock_test_direct(self, proxy):
        proxy.is_working = True
        proxy.latency = 123.45
        return proxy

    # Mock the singbox test method too for unit tests that don't want to spawn processes
    # CAUTION: This might bypass logic we want to test in testers.py.
    # Ideally we only mock the network/subprocess part.
    # Since we mocked singbox_factory above, _test_via_singbox should work logic-wise
    # but fail to connect to the fake proxy URL unless we also mock aiohttp.

    # So we mock ClientSession.get to avoid real connection attempts to the fake proxy

    return True


@pytest.fixture(autouse=True)
def mock_aiohttp_session(monkeypatch):
    """Mock aiohttp client session for network isolation."""

    # Create a mock response context manager
    class MockResponse:
        def __init__(self, status=200, json_data=None, text_data=""):
            self.status = status
            self._json = json_data or {}
            self._text = text_data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def json(self):
            return self._json

        async def text(self):
            return self._text

    # Mock ClientSession
    class MockSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def get(self, url, *args, **kwargs):
            # Return success for google/connectivity checks
            if "google" in str(url) or "generate_204" in str(url):
                return MockResponse(status=204)
            if "example.com" in str(url):
                return MockResponse(
                    status=200,
                    text_data="<html><head><title>Example Domain</title></head><body></body></html>",
                )
            return MockResponse(status=200)

    monkeypatch.setattr("aiohttp.ClientSession", MockSession)
