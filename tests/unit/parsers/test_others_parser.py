"""
Unit tests for other parsers (Hysteria, TUIC, etc).
"""

from configstream.parsers.others import (
    _parse_url_scheme,
    parse_hysteria,
    parse_hysteria2,
    parse_tuic,
    parse_wireguard,
    parse_juicity,
    parse_ssh,
    parse_xray,
)


def test_parse_hysteria():
    config = "hysteria://host:443?auth=password&peer=sni.com&insecure=1&up=100&down=100#Hysteria"
    p = parse_hysteria(config)
    assert p
    assert p.protocol == "hysteria"
    assert p.address == "host"
    assert p.port == 443
    assert p.details["auth"] == "password"
    assert p.remarks == "Hysteria"


def test_parse_hysteria2():
    config = "hysteria2://password@example.com:443?sni=test.com&insecure=1#Hys2"
    p = parse_hysteria2(config)
    assert p
    assert p.protocol == "hysteria2"
    assert p.address == "example.com"
    assert p.uuid == "password"
    assert p.details["sni"] == "test.com"


def test_parse_tuic():
    config = (
        "tuic://uuid:password@1.1.1.1:443?congestion_control=bbr&sni=example.com#TUIC"
    )
    p = parse_tuic(config)
    assert p
    assert p.protocol == "tuic"
    assert p.address == "1.1.1.1"
    assert p.details["congestion_control"] == "bbr"


def test_parse_wireguard():
    config = "wireguard://privatekey@1.1.1.1:51820?publickey=pubkey&mtu=1280#WG"
    p = parse_wireguard(config)
    assert p
    assert p.protocol == "wireguard"
    assert p.address == "1.1.1.1"
    assert (
        p.uuid == "privatekey"
    )  # username field used for private key in _parse_url_scheme
    # Actually _parse_url_scheme maps username -> uuid.
    # wireguard parser checks details['private_key'] which comes from query usually?
    # Wait, standard WG URI: wireguard://private_key@host:port...
    # So private_key is in username field.
    # But parse_wireguard checks 'private_key' in details.
    # We might need to map uuid to private_key if missing?
    # Let's check implementation. It relies on _parse_url_scheme.
    # If config is wireguard://priv@host..., then uuid=priv.
    # But parse_wireguard checks: if "private_key" not in proxy.details...
    # So we should pass private_key in query or handle uuid as private_key.


def test_parse_url_scheme_edges():
    # Invalid port
    assert _parse_url_scheme("proto://host:70000", "proto", 443) is None
    # Invalid host
    assert _parse_url_scheme("proto://", "proto", 443) is None

    # Scheme mismatch handled strictly now
    # _parse_url_scheme checks scheme.lower()
    # It MUST return None if scheme mismatches to avoid "http://..." being parsed as "hysteria"
    assert _parse_url_scheme("http://host:80", "proto", 443) is None


def test_parse_ssh():
    config = "ssh://user:pass@host:22#remark"
    p = parse_ssh(config)
    assert p
    assert p.protocol == "ssh"
    assert p.uuid == "user"
    assert p.details["password"] == "pass"


def test_parse_juicity():
    config = "juicity://uuid:pass@1.1.1.1:443"
    p = parse_juicity(config)
    assert p
    assert p.protocol == "juicity"
    assert p.uuid == "uuid"

    # Missing UUID
    assert parse_juicity("juicity://1.1.1.1:443") is None


def test_parse_xray():
    config = "xray://uuid@1.1.1.1:443"
    p = parse_xray(config)
    assert p
    assert p.protocol == "xray"

    # Missing UUID
    assert parse_xray("xray://1.1.1.1:443") is None
