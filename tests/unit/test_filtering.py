from configstream.filtering import ProxyFilter
from configstream.models import Proxy


def test_filter_by_country():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, country_code="US"),
        Proxy(config="", protocol="", address="", port=0, country_code="CA"),
        Proxy(config="", protocol="", address="", port=0, country_code="US"),
    ]
    filtered = ProxyFilter(proxies).by_country(["US"]).to_list()
    assert len(filtered) == 2
    assert all(p.country_code == "US" for p in filtered)


def test_filter_by_city():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, city="New York"),
        Proxy(config="", protocol="", address="", port=0, city="Toronto"),
        Proxy(config="", protocol="", address="", port=0, city="New York"),
    ]
    filtered = ProxyFilter(proxies).by_city(["New York"]).to_list()
    assert len(filtered) == 2
    assert all(p.city == "New York" for p in filtered)


def test_filter_by_protocol():
    proxies = [
        Proxy(config="", protocol="vmess", address="", port=0),
        Proxy(config="", protocol="ss", address="", port=0),
        Proxy(config="", protocol="vmess", address="", port=0),
    ]
    filtered = ProxyFilter(proxies).by_protocol(["vmess"]).to_list()
    assert len(filtered) == 2
    assert all(p.protocol == "vmess" for p in filtered)


def test_filter_by_latency():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, latency=100),
        Proxy(config="", protocol="", address="", port=0, latency=500),
        Proxy(config="", protocol="", address="", port=0, latency=1000),
        Proxy(config="", protocol="", address="", port=0, latency=None),
    ]
    filtered = ProxyFilter(proxies).by_latency(min_ms=200, max_ms=800).to_list()
    assert len(filtered) == 1
    assert filtered[0].latency == 500


def test_sort_by_latency():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, latency=500),
        Proxy(config="", protocol="", address="", port=0, latency=100),
        Proxy(config="", protocol="", address="", port=0, latency=1000),
    ]
    sorted_proxies = ProxyFilter(proxies).sort_by_latency().to_list()
    assert [p.latency for p in sorted_proxies] == [100, 500, 1000]


def test_sort_by_country():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, country_code="US"),
        Proxy(config="", protocol="", address="", port=0, country_code="CA"),
        Proxy(config="", protocol="", address="", port=0, country_code="AA"),
    ]
    sorted_proxies = ProxyFilter(proxies).sort_by_country().to_list()
    assert [p.country_code for p in sorted_proxies] == ["AA", "CA", "US"]


def test_filter_by_asn():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, asn="AS12345"),
        Proxy(config="", protocol="", address="", port=0, asn="AS67890"),
        Proxy(config="", protocol="", address="", port=0, asn="AS12345"),
        Proxy(config="", protocol="", address="", port=0, asn=None),
    ]
    filtered = ProxyFilter(proxies).by_asn(["AS12345"]).to_list()
    assert len(filtered) == 2
    assert all(p.asn == "AS12345" for p in filtered)


def test_filter_by_asn_case_insensitive():
    proxies = [
        Proxy(config="", protocol="", address="", port=0, asn="AS12345"),
        Proxy(config="", protocol="", address="", port=0, asn="as12345"),
    ]
    filtered = ProxyFilter(proxies).by_asn(["as12345"]).to_list()
    assert len(filtered) == 2


def test_chain_method():
    """Test the chain method with custom filter functions."""
    proxies = [
        Proxy(config="", protocol="vmess", address="", port=0, country_code="US", latency=100),
        Proxy(config="", protocol="ss", address="", port=0, country_code="CA", latency=500),
        Proxy(config="", protocol="vmess", address="", port=0, country_code="US", latency=1000),
    ]

    def filter_fast(proxies):
        return [p for p in proxies if p.latency and p.latency < 600]

    def filter_vmess(proxies):
        return [p for p in proxies if p.protocol == "vmess"]

    filtered = ProxyFilter(proxies).chain(filter_fast, filter_vmess).to_list()
    assert len(filtered) == 1
    assert filtered[0].protocol == "vmess"
    assert filtered[0].latency == 100


def test_chaining_filters():
    proxies = [
        Proxy(config="", protocol="vmess", address="", port=0, country_code="US", latency=100),
        Proxy(config="", protocol="ss", address="", port=0, country_code="CA", latency=500),
        Proxy(config="", protocol="vmess", address="", port=0, country_code="US", latency=1000),
    ]
    filtered = (
        ProxyFilter(proxies)
        .by_protocol(["vmess"])
        .by_country(["US"])
        .by_latency(max_ms=500)
        .to_list()
    )
    assert len(filtered) == 1
    assert filtered[0].latency == 100
