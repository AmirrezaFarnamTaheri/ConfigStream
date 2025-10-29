import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from configstream.models import Proxy
from configstream.testers import SingBoxTester


@pytest.fixture
def proxy(fs):
    """Provides a default Proxy object for testing."""
    # The config needs to be a real file path for sing-box to start
    config_path = fs.create_file("test_config.json", contents="{}")
    return Proxy(config=str(config_path), protocol="http", address="127.0.0.1", port=8080)


@pytest.fixture
def tester():
    """Provides a SingBoxTester instance."""
    return SingBoxTester()


@pytest.fixture
def successful_response_mock():
    """Provides a MagicMock for a successful aiohttp.ClientResponse."""
    response_mock = MagicMock(spec=aiohttp.ClientResponse)
    response_mock.status = 200
    response_mock.headers = {"X-Canary": "KEEP", "Location": ""}
    # Mock methods that might be called on the response object
    response_mock.json = AsyncMock(
        return_value={
            "headers": {"x-canary": "KEEP"},
            "json": {"status": "ok", "canary": "KEEP"},
        }
    )
    return response_mock


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_success(
    mock_perform_request, proxy, tester, successful_response_mock
):
    """Test a successful proxy test."""
    mock_perform_request.return_value = successful_response_mock

    result = await tester.test(proxy)
    assert result.is_working is True
    assert result.latency is not None


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_failure(mock_perform_request, proxy, tester):
    """Test a failed proxy test."""
    mock_perform_request.return_value = None

    result = await tester.test(proxy)
    assert result.is_working is False


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_timeout_fallback(
    mock_perform_request, proxy, tester, successful_response_mock
):
    """Test that the tester correctly handles a timeout and falls back."""
    mock_perform_request.side_effect = [
        None,  # First URL fails
        successful_response_mock,  # Second URL succeeds
    ]

    result = await tester.test(proxy)
    assert result.is_working is True


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_stop_exception(
    mock_perform_request, proxy, tester, successful_response_mock
):
    """Test that exceptions during sb_proxy.stop() are handled gracefully."""
    mock_sb_proxy_factory = MagicMock()
    mock_sb_instance = MagicMock()
    mock_sb_instance.http_proxy_url = "http://127.0.0.1:1080"
    mock_sb_instance.stop.side_effect = Exception("Stop failed")
    mock_sb_proxy_factory.return_value = mock_sb_instance

    # Make the direct HTTP/SOCKS test fail, then the sing-box test succeed.
    mock_perform_request.side_effect = [
        None,  # This fails the direct test
        successful_response_mock,  # This makes the sing-box proxied test succeed
    ]

    with patch(
        "configstream.testers.SingBoxTester._get_singbox_factory",
        return_value=mock_sb_proxy_factory,
    ):
        result = await tester.test(proxy)

    assert result.is_working is True
    # Verify that the factory was called and stop was called on the instance
    mock_sb_proxy_factory.assert_called_once_with(proxy.config)
    mock_sb_instance.stop.assert_called_once()


@pytest.mark.asyncio
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_url_exception_continues(
    mock_perform_request, proxy, tester, successful_response_mock
):
    """Test that exceptions during URL testing continue to next URL."""
    mock_perform_request.side_effect = [
        None,
        successful_response_mock,
    ]

    result = await tester.test(proxy)
    assert result.is_working is True


def test_singbox_tester_cache_integration():
    """Test tester with cache integration."""
    from configstream.test_cache import TestResultCache
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = TestResultCache(db_path=str(Path(tmpdir) / "test.db"))
        tester = SingBoxTester(timeout=6.0, cache=cache)

        assert tester.cache is not None
        stats = tester.get_cache_stats()
        assert stats["cache_hits"] == 0
