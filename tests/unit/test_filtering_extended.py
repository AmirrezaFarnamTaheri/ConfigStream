from unittest.mock import MagicMock, patch
from configstream.filtering import (
    proxy_unique_key,
    dedupe_and_shuffle,
    filter_unique_endpoints,
    ProxyFilter,
)
from configstream.models import Proxy


def create_proxy(
    protocol="vless",
    address="1.2.3.4",
    port=443,
    uuid="uuid",
    working=True,
    latency=100,
    sni="example.com",
    path="/path",
    country_code="US",
    details=None,
):
    p = MagicMock(spec=Proxy)
    p.protocol = protocol
    p.address = address
    p.resolved_ip = address  # For simplicity
    p.port = port
    p.uuid = uuid
    p.is_working = working
    p.latency = latency
    p.sni = sni
    p.path = path
    p.country_code = country_code
    p.city = "City"
    p.asn = "AS123"
    p.details = details or {}
    return p


def test_proxy_unique_key():
    p = create_proxy(details={"serviceName": "svc", "mode": "gun", "type": "grpc"})
    key = proxy_unique_key(p)
    assert key[0] == "vless"
    assert key[1] == "1.2.3.4"
    assert key[6] == "svc"  # service_name
    assert key[7] == "gun"  # mode
    assert key[9] == "grpc"  # transport


def test_dedupe_and_shuffle():
    p1 = create_proxy(latency=100)
    p2 = create_proxy(latency=50)  # duplicate of p1 but faster
    p3 = create_proxy(address="5.6.7.8")  # distinct

    result = dedupe_and_shuffle([p1, p2, p3])

    assert len(result) == 2
    # result should contain p2 and p3.
    # Since we used MagicMock, identity might be tricky if dedupe makes copies,
    # but code just stores reference.

    # Check properties
    latencies = sorted([p.latency for p in result])
    assert latencies == [50, 100]
    # p2 (50) and p3 (default 100). p1 (100) should be gone.

    addresses = sorted([p.address for p in result])
    assert addresses == ["1.2.3.4", "5.6.7.8"]


def test_dedupe_prefer_working():
    p1 = create_proxy(working=False, latency=10)
    p2 = create_proxy(working=True, latency=100)

    result = dedupe_and_shuffle([p1, p2])
    assert len(result) == 1
    assert result[0].is_working is True


def test_filter_unique_endpoints():
    p1 = create_proxy(address="1.1.1.1", latency=200)
    p2 = create_proxy(address="example.com", latency=100)
    p2.resolved_ip = "1.1.1.1"  # Resolves to same IP

    result = filter_unique_endpoints([p1, p2])
    assert len(result) == 1
    assert result[0].latency == 100


def test_proxy_filter_chaining():
    proxies = [
        create_proxy(address="1", country_code="US", protocol="vmess", latency=50),
        create_proxy(address="2", country_code="DE", protocol="vless", latency=150),
        create_proxy(address="3", country_code="US", protocol="vless", latency=200),
        create_proxy(
            address="4",
            country_code="GB",
            protocol="trojan",
            latency=300,
            working=False,
        ),
    ]

    pf = ProxyFilter(proxies)

    res = pf.by_country(["US"]).sort_by_latency().to_list()
    assert len(res) == 2
    assert res[0].address == "1"
    assert res[1].address == "3"

    res = pf.by_protocol(["vless"]).to_list()
    assert len(res) == 2  # 2 and 3

    res = pf.working_only().to_list()
    assert len(res) == 3  # 1, 2, 3

    res = pf.limit(1).to_list()
    assert len(res) == 1

    res = pf.by_latency(min_ms=100, max_ms=250).to_list()
    assert len(res) == 2

    p_city = create_proxy(address="5")
    p_city.city = "London"
    res = ProxyFilter([p_city]).by_city(["London"]).to_list()
    assert len(res) == 1

    p_asn = create_proxy(address="6")
    p_asn.asn = "AS12345"
    res = ProxyFilter([p_asn]).by_asn(["AS12345"]).to_list()
    assert len(res) == 1

    res = pf.sort_by_country().to_list()
    assert res[0].country_code == "DE"


def test_dedupe_shuffle_seed():
    p1 = create_proxy(address="1")
    p2 = create_proxy(address="2")

    # Mock os.getenv to return seed
    with patch("os.getenv", return_value="42"):
        res1 = dedupe_and_shuffle([p1, p2])

    with patch("os.getenv", return_value="42"):
        res2 = dedupe_and_shuffle([p1, p2])

    assert [p.address for p in res1] == [p.address for p in res2]
