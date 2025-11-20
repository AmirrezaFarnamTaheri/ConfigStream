import pytest
from configstream.filtering import ProxyFilter
from configstream.models import Proxy


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://...",
            protocol="vmess",
            address="1.1.1.1",
            port=80,
            country_code="US",
            latency=100,
            is_working=True,
            details={"sni": "google.com"},
        ),
        Proxy(
            config="vless://...",
            protocol="vless",
            address="2.2.2.2",
            port=443,
            country_code="CN",
            latency=200,
            is_working=True,
            details={"sni": "baidu.com"},
        ),
        Proxy(
            config="ss://...",
            protocol="ss",
            address="3.3.3.3",
            port=8080,
            country_code="RU",
            latency=50,
            is_working=False,
            details={"sni": "yandex.ru"},
        ),
        Proxy(
            config="trojan://...",
            protocol="trojan",
            address="4.4.4.4",
            port=443,
            country_code="IR",
            latency=300,
            is_working=True,
            details={"sni": "ir-server.com"},
        ),
    ]


def test_regex_filter_address(sample_proxies):
    pf = ProxyFilter(sample_proxies)

    # Exclude 1.1.1.1
    filtered = pf.exclude_by_regex(r"1\.1\.1\.1").to_list()
    assert len(filtered) == 3
    assert all(p.address != "1.1.1.1" for p in filtered)


def test_regex_filter_sni(sample_proxies):
    pf = ProxyFilter(sample_proxies)

    # Exclude baidu
    filtered = pf.exclude_by_regex(r"baidu", fields=["sni"]).to_list()
    assert len(filtered) == 3
    assert all(p.sni != "baidu.com" for p in filtered)


def test_regex_filter_country(sample_proxies):
    pf = ProxyFilter(sample_proxies)

    # Exclude CN and RU
    filtered = pf.exclude_by_regex(r"CN|RU", fields=["country_code"]).to_list()
    assert len(filtered) == 2
    codes = [p.country_code for p in filtered]
    assert "CN" not in codes
    assert "RU" not in codes


def test_regex_filter_invalid(sample_proxies):
    pf = ProxyFilter(sample_proxies)

    # Invalid regex should not crash and return original list
    filtered = pf.exclude_by_regex(r"[invalid").to_list()
    assert len(filtered) == 4
