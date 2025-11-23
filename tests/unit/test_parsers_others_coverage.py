
import pytest
from src.configstream.parsers.others import (
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
from src.configstream.models import Proxy
from unittest.mock import patch

# --- _parse_url_scheme ---

def test_parse_url_scheme_invalid_host():
    assert _parse_url_scheme("proto://", "proto", 80) is None
    # hostname too long
    long_host = "a" * 256
    assert _parse_url_scheme(f"proto://{long_host}", "proto", 80) is None

def test_parse_url_scheme_invalid_port():
    # If port is 0, parsed.port is 0 (Falsey).
    # Line 26: port = parsed.port or default_port
    # So if parsed.port is 0, it takes default_port!
    # So "proto://host:0" with default 80 becomes port 80.
    # To trigger "invalid port", we need `1 <= port <= 65535` to be false.
    # If we pass default_port=0?
    assert _parse_url_scheme("proto://host:0", "proto", 0) is None

    # Or explicitly use valid default, but port 0?
    # No, because `or` logic.
    # What if port is 65536?
    assert _parse_url_scheme("proto://host:65536", "proto", 80) is None

def test_parse_url_scheme_mismatched_scheme():
    # Covers line 18: elif parsed.scheme.lower() != protocol.lower():
    # If mismatch, it passes (does nothing) and continues?
    # Line 18: pass.
    # So "http://host" parsed with protocol "ssh" -> scheme mismatch, but proceeds.
    # Then returns Proxy with protocol "ssh".
    # This seems like loose behavior but we just need to cover it.
    p = _parse_url_scheme("http://host", "ssh", 22)
    assert p.protocol == "ssh"

def test_parse_url_scheme_exception():
    with patch("src.configstream.parsers.others.urlparse") as mock_urlparse:
        mock_urlparse.side_effect = ValueError("Boom")
        assert _parse_url_scheme("proto://host", "proto", 80) is None

# --- parse_hysteria ---

def test_parse_hysteria_basic():
    p = parse_hysteria("hysteria://1.1.1.1:443")
    assert p.protocol == "hysteria"

# --- parse_hysteria2 ---

def test_parse_hysteria2_basic():
    p = parse_hysteria2("hysteria2://user@1.1.1.1:443")
    assert p.protocol == "hysteria2"
    assert p.uuid == "user"

def test_parse_hysteria2_ports_valid():
    config = "hysteria2://1.1.1.1?ports=80,443,8000-9000"
    p = parse_hysteria2(config)
    assert p.details["ports"] == "80,443,8000-9000"

def test_parse_hysteria2_ports_invalid():
    config = "hysteria2://1.1.1.1?ports=invalid"
    p = parse_hysteria2(config)
    assert "ports" not in p.details

def test_parse_hysteria2_obfs():
    config = "hysteria2://1.1.1.1?obfs=salamander"
    p = parse_hysteria2(config)
    assert p.details["obfs"] == "salamander"

# --- parse_tuic ---

def test_parse_tuic_basic():
    p = parse_tuic("tuic://uuid:pass@1.1.1.1:1080")
    assert p.protocol == "tuic"
    assert p.uuid == "uuid"

# --- parse_wireguard ---

def test_parse_wireguard_missing_private_key():
    # This returns a proxy from _parse_url_scheme, but then checks details.
    assert parse_wireguard("wireguard://1.1.1.1") is None

def test_parse_wireguard_invalid_scheme_url():
    # Force _parse_url_scheme to return None (e.g. no host)
    # This hits line 71: if not proxy: return None
    assert parse_wireguard("wireguard://") is None

def test_parse_wireguard_valid():
    config = "wireguard://1.1.1.1?private_key=key123"
    p = parse_wireguard(config)
    assert p.protocol == "wireguard"

def test_parse_wireguard_reserved_valid_bracketed():
    config = "wireguard://1.1.1.1?private_key=key&reserved=[1,2,3]"
    p = parse_wireguard(config)
    assert p.details["reserved"] == "[1,2,3]"

def test_parse_wireguard_reserved_valid_csv():
    config = "wireguard://1.1.1.1?private_key=key&reserved=1,2,3"
    p = parse_wireguard(config)
    assert p.details["reserved"] == "1,2,3"

def test_parse_wireguard_reserved_valid_b64():
    config = "wireguard://1.1.1.1?private_key=key&reserved=YWJj"
    p = parse_wireguard(config)
    assert p.details["reserved"] == "YWJj"

def test_parse_wireguard_reserved_invalid_str():
    config = "wireguard://1.1.1.1?private_key=key&reserved=bad$reserved"
    p = parse_wireguard(config)
    assert "reserved" not in p.details

def test_parse_wireguard_reserved_invalid_type_and_list_check():
    # Mocking _parse_url_scheme to return a proxy with list in details
    with patch("src.configstream.parsers.others._parse_url_scheme") as mock_parse:
        p = Proxy(config="c", protocol="wireguard", address="1.1.1.1", port=51820,
                  details={"private_key": "k", "reserved": [1, 2, 3]})
        mock_parse.return_value = p
        res = parse_wireguard("c")
        assert res.details["reserved"] == [1, 2, 3]

        # Invalid list
        p.details["reserved"] = ["a", 1]
        mock_parse.return_value = p
        res = parse_wireguard("c")
        assert "reserved" not in res.details

# --- parse_xray ---

def test_parse_xray_missing_uuid():
    assert parse_xray("xray://1.1.1.1") is None

def test_parse_xray_valid():
    assert parse_xray("xray://uuid@1.1.1.1") is not None

# --- parse_snell ---
def test_parse_snell():
    assert parse_snell("snell://1.1.1.1").protocol == "snell"

# --- parse_brook ---
def test_parse_brook():
    assert parse_brook("brook://1.1.1.1").protocol == "brook"

# --- parse_juicity ---
def test_parse_juicity_missing_uuid():
    assert parse_juicity("juicity://1.1.1.1") is None

def test_parse_juicity_valid():
    assert parse_juicity("juicity://uuid@1.1.1.1").protocol == "juicity"

# --- parse_ssh ---
def test_parse_ssh_password():
    p = parse_ssh("ssh://user:pass@1.1.1.1")
    assert p.protocol == "ssh"
    assert p.details["password"] == "pass"

def test_parse_ssh_no_password():
    p = parse_ssh("ssh://user@1.1.1.1")
    assert p.protocol == "ssh"
    assert "password" not in p.details
