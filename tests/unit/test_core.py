import pytest
from configstream.core import parse_config
from configstream.models import Proxy


def test_parse_vmess():
    config = "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIlRlc3QgVk1lc3MiLA0KICAiYWRkIjogIjEuMS4xLjEiLA0KICAicG9ydCI6ICI0NDMiLA0KICAiaWQiOiAiYWRtaW4iLA0KICAiYWlkIjogIjAiLA0KICAic2N5IjogImF1dG8iLA0KICAibmV0IjogIndzIiwNCiAgInR5cGUiOiAibm9uZSIsDQogICJob3N0IjogIiIsDQogICJwYXRoIjogIi8iLA0KICAidGxzIjogInRscyIsDQogICJzbmkiOiAiIiwNCiAgImFscG4iOiAiIg0KfQ=="
    proxy = parse_config(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.address == "1.1.1.1"
    assert proxy.port == 443


def test_parse_ss():
    config = "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNzd29yZA==@1.1.1.1:8388#Example"
    proxy = parse_config(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.address == "1.1.1.1"
    assert proxy.port == 8388
    assert proxy.remarks == "Example"


def test_parse_invalid():
    assert parse_config("invalid://garbage") is None
