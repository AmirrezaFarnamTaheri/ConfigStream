# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the new parsers package.
"""

import base64
import json
from configstream.parsers import (
    parse_vmess,
    parse_ss,
    parse_trojan,
    parse_vless,
    parse_generic_url_scheme,
    parse_openvpn,
    parse_wireguard,
)


def test_parse_vmess():
    # Standard VMess
    data = {
        "v": "2",
        "ps": "Test Node",
        "add": "1.1.1.1",
        "port": 443,
        "id": "uuid-1234",
        "aid": 0,
        "net": "ws",
        "type": "none",
        "host": "example.com",
        "path": "/ws",
        "tls": "tls",
    }
    b64_data = base64.b64encode(json.dumps(data).encode()).decode()
    config = f"vmess://{b64_data}"

    proxy = parse_vmess(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.address == "1.1.1.1"
    assert proxy.port == 443
    assert proxy.uuid == "uuid-1234"
    assert proxy.remarks == "Test Node"
    assert proxy.details["net"] == "ws"


def test_parse_ss():
    # SIP002
    # ss://base64(method:password)@hostname:port#remarks
    userpass = base64.b64encode(b"chacha20-ietf-poly1305:password").decode()
    config = f"ss://{userpass}@1.2.3.4:8388#Test%20SS"

    proxy = parse_ss(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8388
    assert proxy.details["method"] == "chacha20-ietf-poly1305"
    assert proxy.details["password"] == "password"
    assert proxy.remarks == "Test SS"


def test_parse_trojan():
    config = "trojan://password@example.com:443?sni=example.com#Trojan-Node"
    proxy = parse_trojan(config)
    assert proxy is not None
    assert proxy.protocol == "trojan"
    assert proxy.address == "example.com"
    assert proxy.port == 443
    assert proxy.uuid == "password"
    assert proxy.details["sni"] == "example.com"
    assert proxy.remarks == "Trojan-Node"


def test_parse_vless():
    config = "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443?security=reality&sni=example.com&fp=chrome&pbk=publickey&sid=1234abcd#VLESS-Reality"
    proxy = parse_vless(config)
    assert proxy is not None
    assert proxy.protocol == "vless"
    assert proxy.address == "example.com"
    assert proxy.uuid == "123e4567-e89b-12d3-a456-426614174000"
    assert proxy.details["security"] == "reality"
    assert proxy.details["pbk"] == "publickey"


def test_parse_generic_http():
    config = "http://user:pass@proxy.example.com:8080#HTTP-Proxy"
    proxy = parse_generic_url_scheme(config)
    assert proxy is not None
    assert proxy.protocol == "http"
    assert proxy.address == "proxy.example.com"
    assert proxy.port == 8080
    assert proxy.uuid == "user"
    assert proxy.details["password"] == "pass"


def test_parse_openvpn_content():
    config = """
client
dev tun
proto udp
remote 1.2.3.4 1194
resolv-retry infinite
nobind
persist-key
persist-tun
-----BEGIN CERTIFICATE-----
MII...
-----END CERTIFICATE-----
    """
    proxy = parse_openvpn(config)
    assert proxy is not None
    assert proxy.protocol == "openvpn"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 1194
    assert proxy.details["transport"] == "udp"


def test_parse_wireguard_valid():
    # Use valid Base64 32-byte key
    valid_key = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
    config = f"wireguard://{valid_key}@1.1.1.1:51820?publickey=pub&reserved=1,2,3#WG"
    # With the new fix in parsers/others.py, if uuid is present and private_key not in details,
    # it maps uuid -> private_key.
    proxy = parse_wireguard(config)
    assert proxy is not None  # Now it should pass!
    assert proxy.details["private_key"] == valid_key

    config_correct = f"wireguard://1.1.1.1:51820?private_key={valid_key}&peer_public_key=pub#WG"
    proxy = parse_wireguard(config_correct)
    assert proxy is not None
    assert proxy.details["private_key"] == valid_key
