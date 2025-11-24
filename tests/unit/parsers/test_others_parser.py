"""Tests for Other Parsers (Hysteria, WG, etc)."""

import pytest
from configstream.parsers.others import (
    parse_hysteria,
    parse_hysteria2,
    parse_tuic,
    parse_wireguard,
    parse_xray,
    parse_snell,
    parse_brook,
    parse_juicity,
    parse_ssh,
    _parse_url_scheme,
)
from configstream.models import Proxy


def test_parse_hysteria():
    # Valid
    config = "hysteria://host:443?auth=key&peer=domain#remark"
    p = parse_hysteria(config)
    assert p is not None
    assert p.protocol == "hysteria"
    assert p.port == 443
    assert p.details["auth"] == "key"
    assert p.remarks == "remark"


def test_parse_hysteria2():
    # With ports range
    config = "hysteria2://host:443?ports=80,443,1000-2000&obfs=salamander"
    p = parse_hysteria2(config)
    assert p is not None
    assert p.protocol == "hysteria2"
    assert "ports" in p.details
    assert "obfs" in p.details

    # Invalid ports
    config = "hysteria2://host:443?ports=invalid"
    p = parse_hysteria2(config)
    assert "ports" not in p.details


def test_parse_wireguard():
    # Missing private key -> None
    config = "wireguard://host:51820"
    assert parse_wireguard(config) is None

    # Valid
    config = "wireguard://host:51820?private_key=key&reserved=[0,1,2]"
    p = parse_wireguard(config)
    assert p is not None
    assert p.details["private_key"] == "key"
    assert p.details["reserved"] == "[0,1,2]"

    # Invalid reserved
    config = "wireguard://host:51820?private_key=key&reserved=invalid!"
    p = parse_wireguard(config)
    assert "reserved" not in p.details


def test_parse_others_basic():
    # Snell
    assert parse_snell("snell://host:443").protocol == "snell"
    # Brook
    assert parse_brook("brook://host:9999").protocol == "brook"
    # TUIC
    assert parse_tuic("tuic://host:443").protocol == "tuic"


def test_parse_xray():
    # Missing UUID
    assert parse_xray("xray://host:443") is None
    # Valid
    assert parse_xray("xray://uuid@host:443").protocol == "xray"


def test_parse_juicity():
    assert parse_juicity("juicity://host:443") is None
    assert parse_juicity("juicity://uuid@host:443").protocol == "juicity"


def test_parse_ssh():
    config = "ssh://user:pass@host:22#remark"
    p = parse_ssh(config)
    assert p.protocol == "ssh"
    assert (
        p.uuid == "user"
    )  # username maps to uuid field usually for legacy reasons in _parse_url_scheme
    assert p.details["password"] == "pass"


def test_parse_url_scheme_edges():
    # Invalid port
    assert _parse_url_scheme("proto://host:70000", "proto", 443) is None
    # Invalid host
    assert _parse_url_scheme("proto://", "proto", 443) is None
    # Scheme mismatch handled?
    # _parse_url_scheme checks scheme.lower()
    assert (
        _parse_url_scheme("http://host:80", "proto", 443) is not None
    )  # Actually it returns object if parseable but might log mismatch?
    # Wait, code says: if scheme not in (protocol) -> pass (continue).
    # So it parses "http" scheme as "proto" protocol if structure is URL-like.
    p = _parse_url_scheme("http://host:80", "proto", 443)
    assert p.protocol == "proto"

    # Empty config
    assert _parse_url_scheme("", "proto", 443) is None
