import pytest
from configstream.parsers import _parse_vless
from configstream.models import Proxy


def test_vless_sid_enforcement():
    # Config with sid - should pass
    valid_config = "vless://uuid@1.2.3.4:443?security=reality&sni=example.com&pbk=publickey&sid=sessionid&type=tcp&flow=xtls-rprx-vision#Valid"
    proxy = _parse_vless(valid_config)
    assert proxy is not None
    assert proxy.details.get("sid") == "sessionid"

    # Config WITHOUT sid - should fail (strict memory requirement)
    invalid_config = "vless://uuid@1.2.3.4:443?security=reality&sni=example.com&pbk=publickey&type=tcp&flow=xtls-rprx-vision#Invalid"
    proxy = _parse_vless(invalid_config)
    assert proxy is None


def test_vless_unquote_remarks():
    # Config with URL-encoded remarks
    config = "vless://uuid@1.2.3.4:443?type=tcp#Test%20Proxy"
    proxy = _parse_vless(config)
    assert proxy is not None
    assert proxy.remarks == "Test Proxy"
