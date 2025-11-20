from configstream.parsers import _parse_vless


def test_vless_reality_valid():
    config = "vless://uuid@example.com:443?security=reality&encryption=none&pbk=publickey&sid=shortid&fp=chrome&type=grpc&serviceName=grpc#Reality"
    proxy = _parse_vless(config)
    assert proxy is not None
    assert proxy.protocol == "vless"
    assert proxy.details["security"] == "reality"
    assert proxy.details["pbk"] == "publickey"
    assert proxy.details["sid"] == "shortid"


def test_vless_reality_missing_pbk():
    config = "vless://uuid@example.com:443?security=reality&encryption=none&sid=shortid&fp=chrome#Invalid"
    proxy = _parse_vless(config)
    assert proxy is None


def test_vless_reality_missing_sid():
    config = "vless://uuid@example.com:443?security=reality&encryption=none&pbk=publickey&fp=chrome#Invalid"
    proxy = _parse_vless(config)
    assert proxy is None


def test_vless_normal():
    config = "vless://uuid@example.com:443?security=tls&encryption=none#Normal"
    proxy = _parse_vless(config)
    assert proxy is not None
    assert proxy.details["security"] == "tls"
