import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from configstream.testers.manager import SingBoxTester
from configstream.models import Proxy


@pytest.fixture
def mock_settings():
    with patch("configstream.testers.manager.AppSettings") as MockSettings:
        settings = MockSettings.return_value
        settings.TEST_URLS = {"google": "http://google.com"}
        yield settings


@pytest.mark.asyncio
async def test_singbox_tester_dry_run(mock_settings):
    tester = SingBoxTester(dry_run=True)
    proxy = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="uuid"
    )

    result = await tester.test(proxy)
    assert result.is_working
    assert result.latency == 123.45
    assert result.tested_at is not None


@pytest.mark.asyncio
async def test_singbox_tester_batch_dry_run(mock_settings):
    tester = SingBoxTester(dry_run=True)
    proxies = [
        Proxy(
            config="test1", protocol="vmess", address="1.1.1.1", port=443, uuid="uuid1"
        ),
        Proxy(
            config="test2", protocol="vless", address="2.2.2.2", port=443, uuid="uuid2"
        ),
    ]

    results = await tester.test_batch(proxies)
    for p in results:
        assert p.is_working
        assert p.latency == 123.45


@pytest.mark.asyncio
async def test_singbox_tester_cache_hit(mock_settings):
    cache = MagicMock()
    cached_proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        uuid="uuid",
        is_working=True,
        latency=50,
    )
    cache.get.return_value = cached_proxy

    tester = SingBoxTester(cache=cache)
    proxy = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="uuid"
    )

    result = await tester.test(proxy)
    assert result.is_working
    assert result.latency == 50
    cache.get.assert_called_with(proxy)


@pytest.mark.asyncio
async def test_singbox_tester_python_direct(mock_settings):
    tester = SingBoxTester()
    tester.python_tester.test_direct = AsyncMock(
        return_value=MagicMock(is_working=True)
    )

    proxy = Proxy(
        config="http://user:pass@1.1.1.1:8080",
        protocol="http",
        address="1.1.1.1",
        port=8080,
    )

    await tester.test(proxy)
    tester.python_tester.test_direct.assert_called_once()


@pytest.mark.asyncio
async def test_singbox_tester_go_fallback(mock_settings):
    tester = SingBoxTester()
    # Mock Go tester as unavailable
    tester.go_tester.available = False
    tester.python_tester.test_via_singbox = AsyncMock(
        return_value=MagicMock(is_working=True)
    )

    proxies = [
        Proxy(config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="uuid")
    ]

    await tester.test_batch(proxies)
    # Should call python tester via semaphore wrapper (internal details hard to mock perfectly, but we check if result populated)
    # Actually we mocked the method, so let's verify call.
    # The batch method calls self.test() wrapped in semaphore.
    # self.test() calls python_tester.test_via_singbox for vmess.
    tester.python_tester.test_via_singbox.assert_called()


@pytest.mark.asyncio
async def test_singbox_tester_close(mock_settings):
    tester = SingBoxTester()
    tester.go_tester.close = AsyncMock()
    await tester.close()
    tester.go_tester.close.assert_called_once()
