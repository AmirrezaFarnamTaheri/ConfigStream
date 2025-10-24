from datetime import timedelta
import pytest

from configstream.models import Proxy
from configstream.monitor import HealthMonitor


class DummyTester:
    def __init__(self, successes: list[bool]):
        self._successes = successes

    async def test(self, proxy: Proxy) -> Proxy:
        proxy.is_working = self._successes.pop(0)
        proxy.latency = 50
        return proxy


@pytest.mark.asyncio
async def test_health_monitor_records_and_computes_uptime(monkeypatch):
    proxy = Proxy(config="vmess://test", protocol="vmess", address="example.com", port=443)
    monitor = HealthMonitor()
    monitor.tester = DummyTester([True, False, True])

    await monitor.check(proxy)
    await monitor.check(proxy)
    await monitor.check(proxy)

    uptime = monitor.uptime(proxy)
    assert round(uptime, 2) == pytest.approx(2 / 3, abs=0.01)

    recent_uptime = monitor.uptime(proxy, window=timedelta(hours=1))
    assert recent_uptime > 0
