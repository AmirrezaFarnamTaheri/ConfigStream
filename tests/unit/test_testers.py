import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.models import Proxy
from configstream.testers import SingBoxTester

pytestmark = pytest.mark.asyncio


@pytest.fixture
def proxy():
    """Provides a default Proxy object for testing."""
    return Proxy(config="test_config", protocol="http", address="127.0.0.1", port=8080)


@pytest.fixture
def tester():
    """Provides a SingBoxTester instance."""
    return SingBoxTester()


@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_success(mock_perform_request, proxy, tester):
    """Test a successful proxy test."""
    mock_perform_request.return_value = AsyncMock(status=200)

    result = await tester.test(proxy)
    assert result.is_working is True
    assert result.latency is not None


@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_failure(mock_perform_request, proxy, tester):
    """Test a failed proxy test."""
    mock_perform_request.return_value = None

    result = await tester.test(proxy)
    assert result.is_working is False


@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_timeout_fallback(mock_perform_request, proxy, tester):
    """Test that the tester correctly handles a timeout and falls back."""
    mock_perform_request.side_effect = [
        None,  # First URL fails
        AsyncMock(status=200),  # Second URL succeeds
    ]

    result = await tester.test(proxy)
    assert result.is_working is True


@patch("configstream.testers.SingBoxProxy")
@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_stop_exception(mock_perform_request, mock_sb_proxy, proxy, tester):
    """Test that exceptions during sb_proxy.stop() are handled gracefully."""
    mock_instance = mock_sb_proxy.return_value
    mock_instance.start = MagicMock()
    mock_instance.stop = MagicMock(side_effect=Exception("Stop failed"))
    mock_instance.http_proxy_url = "http://127.0.0.1:1080"

    mock_perform_request.return_value = AsyncMock(status=200)

    result = await tester.test(proxy)
    assert result.is_working is True


@patch("configstream.testers.SingBoxTester._perform_request")
async def test_singbox_tester_url_exception_continues(mock_perform_request, proxy, tester):
    """Test that exceptions during URL testing continue to next URL."""
    mock_perform_request.side_effect = [
        None,
        AsyncMock(status=200),
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
