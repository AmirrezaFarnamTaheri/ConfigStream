import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from configstream.testers import SingBoxTester
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_singbox_tester_success():
    """Test a successful proxy test."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_instance = mock_sb_proxy.return_value
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.http_proxy_url = "http://127.0.0.1:1080"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_get.return_value.__aenter__.return_value = mock_response

            tester = SingBoxTester()
            result = await tester.test(proxy)

            assert result.is_working is True
            assert result.latency is not None
            assert result.tested_at


@pytest.mark.asyncio
async def test_singbox_tester_failure_masked():
    """Test a failed proxy test with masked errors."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_sb_proxy.side_effect = Exception("Connection error")

        tester = SingBoxTester()
        result = await tester.test(proxy)

        assert result.is_working is False
        assert "Connection failed: [MASKED]" in result.security_issues.get("connectivity", [])
        assert result.tested_at


@pytest.mark.asyncio
async def test_singbox_tester_failure_unmasked():
    """Test a failed proxy test with unmasked errors."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_sb_proxy.side_effect = Exception("Connection error")

        tester = SingBoxTester()
        tester.config.MASK_SENSITIVE_DATA = False
        result = await tester.test(proxy)

        assert result.is_working is False
        assert "Connection failed: Connection error" in result.security_issues.get(
            "connectivity", []
        )


@pytest.mark.asyncio
async def test_singbox_tester_timeout_fallback():
    """Test that the tester correctly handles a timeout and falls back."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_instance = mock_sb_proxy.return_value
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.http_proxy_url = "http://127.0.0.1:1080"

        with patch("aiohttp.ClientSession.get") as mock_get:
            # First URL times out, second one succeeds
            mock_response_fail = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_response_success = AsyncMock()
            mock_response_success.status = 204
            mock_get.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_success,
            ]

            tester = SingBoxTester()
            result = await tester.test(proxy)

            assert result.is_working is True
            assert result.latency is not None
            assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_singbox_tester_all_urls_fail():
    """Test when all test URLs fail."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_instance = mock_sb_proxy.return_value
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.http_proxy_url = "http://127.0.0.1:1080"

        with patch("aiohttp.ClientSession.get") as mock_get:
            # All URLs fail with different exceptions
            mock_get.return_value.__aenter__.side_effect = [
                asyncio.TimeoutError(),
                Exception("Network error"),
                Exception("Connection refused"),
            ]

            tester = SingBoxTester()
            result = await tester.test(proxy)

            assert result.is_working is False
            assert "All test URLs failed" in result.security_issues.get("connectivity", [])


@pytest.mark.asyncio
async def test_singbox_tester_stop_exception():
    """Test that exceptions during sb_proxy.stop() are handled gracefully."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_instance = mock_sb_proxy.return_value
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock(side_effect=Exception("Stop failed"))
        mock_instance.http_proxy_url = "http://127.0.0.1:1080"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_get.return_value.__aenter__.return_value = mock_response

            tester = SingBoxTester()
            result = await tester.test(proxy)

            # Should still complete successfully even if stop() fails
            assert result.is_working is True
            assert result.latency is not None


@pytest.mark.asyncio
async def test_singbox_tester_url_exception_continues():
    """Test that exceptions during URL testing continue to next URL."""
    proxy = Proxy(config="vmess://config", protocol="vmess", address="test.com", port=443)

    with patch("configstream.testers.SingBoxProxy") as mock_sb_proxy:
        mock_instance = mock_sb_proxy.return_value
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.http_proxy_url = "http://127.0.0.1:1080"

        with patch("aiohttp.ClientSession.get") as mock_get:
            # First URL raises exception, second succeeds
            mock_response_success = AsyncMock()
            mock_response_success.status = 204
            mock_get.return_value.__aenter__.side_effect = [
                Exception("Connection error"),
                mock_response_success,
            ]

            tester = SingBoxTester()
            result = await tester.test(proxy)

            assert result.is_working is True
            assert result.latency is not None


def test_singbox_tester_cache_integration():
    """Test tester with cache integration."""
    from configstream.testers import SingBoxTester
    from configstream.test_cache import TestResultCache
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = TestResultCache(db_path=str(Path(tmpdir) / "test.db"))
        tester = SingBoxTester(timeout=6.0, cache=cache)

        # Verify cache is set
        assert tester.cache is not None

        # Test cache stats
        stats = tester.get_cache_stats()
        assert stats["total_tests"] == 0
        assert stats["cache_hits"] == 0


def test_proxy_tester_base_class():
    """Test base proxy tester class."""
    from configstream.testers import ProxyTester
    from configstream.models import Proxy
    import pytest

    tester = ProxyTester()

    proxy = Proxy(config="test", protocol="vmess", address="1.2.3.4", port=443)

    # Base class should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        import asyncio

        asyncio.run(tester.test(proxy))
