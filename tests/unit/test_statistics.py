from configstream.models import Proxy
from configstream.statistics import StatisticsEngine


def _proxy(protocol: str, latency: float | None, country: str, working: bool) -> Proxy:
    return Proxy(
        config=f"{protocol}://example",
        protocol=protocol,
        address="example.com",
        port=443,
        country=country,
        country_code=country[:2].upper(),
        latency=latency,
        is_working=working,
    )


def test_statistics_engine_report() -> None:
    proxies = [
        _proxy("vmess", 100, "United States", True),
        _proxy("ss", 200, "Germany", True),
        _proxy("ss", None, "Germany", False),
    ]

    engine = StatisticsEngine(proxies)
    report = engine.generate_report()

    assert report["total_proxies"] == 3
    assert report["working_proxies"] == 2
    assert report["protocol_distribution"] == {"vmess": 1, "ss": 2}
    assert report["country_distribution"]["Germany"] == 2
    latency_stats = report["latency"]
    assert latency_stats["min"] == 100
    assert latency_stats["max"] == 200
    assert round(latency_stats["mean"], 1) == 150.0
