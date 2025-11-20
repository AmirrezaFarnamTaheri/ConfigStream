from unittest.mock import MagicMock
from configstream.filtering import ProxyFilter
from configstream.models import Proxy


def test_exclude_by_regex():
    p1 = MagicMock(spec=Proxy)
    p1.address = "1.2.3.4"
    p1.country_code = "US"
    p1.org = "Bad ISP"

    p2 = MagicMock(spec=Proxy)
    p2.address = "5.6.7.8"
    p2.country_code = "DE"
    p2.org = "Good ISP"

    proxies = [p1, p2]

    # Test simple regex
    f = ProxyFilter(proxies)
    res = f.exclude_by_regex("Bad ISP").to_list()
    assert len(res) == 1
    assert res[0] == p2

    # Test field specific
    res = f.exclude_by_regex("US", fields=["country_code"]).to_list()
    assert len(res) == 1
    assert res[0] == p2

    # Test no match
    res = f.exclude_by_regex("NonExistent").to_list()
    assert len(res) == 2

    # Test invalid regex
    res = f.exclude_by_regex("[(").to_list()
    assert len(res) == 2
