import pytest
from unittest.mock import MagicMock
from src.configstream.statistics import StatisticsEngine, UptimeStats
from src.configstream.models import Proxy


class TestStatisticsEngine:
    @pytest.fixture
    def sample_proxies(self):
        proxies = []

        # Proxy 1: Working, low latency, US
        p1 = MagicMock(spec=Proxy)
        p1.protocol = "vmess"
        p1.country = "US"
        p1.latency = 50
        p1.is_working = True
        proxies.append(p1)

        # Proxy 2: Working, high latency, DE
        p2 = MagicMock(spec=Proxy)
        p2.protocol = "vless"
        p2.country = "DE"
        p2.latency = 200
        p2.is_working = True
        proxies.append(p2)

        # Proxy 3: Not working, no latency, US
        p3 = MagicMock(spec=Proxy)
        p3.protocol = "vmess"
        p3.country = "US"
        p3.latency = None
        p3.is_working = False
        proxies.append(p3)

        return proxies

    def test_init(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        assert len(engine.proxies) == 3

    def test_protocol_distribution(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        dist = engine.protocol_distribution()
        assert dist["vmess"] == 2
        assert dist["vless"] == 1

    def test_country_distribution(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        dist = engine.country_distribution()
        assert dist["US"] == 2
        assert dist["DE"] == 1

    def test_latency_stats(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        stats = engine.latency_stats()
        assert stats["min"] == 50
        assert stats["max"] == 200
        assert stats["mean"] == 125
        assert stats["median"] == 125
        assert "stdev" in stats

    def test_latency_stats_empty(self):
        engine = StatisticsEngine([])
        assert engine.latency_stats() == {}

    def test_uptime_stats(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        stats = engine.uptime_stats()
        assert isinstance(stats, UptimeStats)
        assert stats.total_tested == 3
        assert stats.working == 2
        assert 0.66 < stats.success_rate < 0.67

    def test_generate_report(self, sample_proxies):
        engine = StatisticsEngine(sample_proxies)
        report = engine.generate_report()
        assert "generated_at" in report
        assert report["total_proxies"] == 3
        assert report["working_proxies"] == 2
        assert report["success_rate"] == 66.67
        assert "protocol_distribution" in report
        assert "country_distribution" in report
        assert "latency" in report
