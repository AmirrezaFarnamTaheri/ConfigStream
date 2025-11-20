from configstream.parsers import _parse_openvpn


def test_openvpn_valid_config():
    config = """client
dev tun
proto udp
remote 1.2.3.4 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
verb 3
<ca>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</ca>"""

    proxy = _parse_openvpn(config)
    assert proxy is not None
    assert proxy.protocol == "openvpn"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 1194
    assert proxy.details["proto"] == "udp"
    assert "full_config" in proxy.details


def test_openvpn_invalid_config():
    config = "http://example.com"
    assert _parse_openvpn(config) is None


def test_openvpn_no_remote():
    config = """client
dev tun
<ca>
...
</ca>"""
    assert _parse_openvpn(config) is None
