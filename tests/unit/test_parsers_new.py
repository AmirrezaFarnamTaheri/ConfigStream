import pytest
from src.configstream.parsers import (
    _parse_ss,
    _parse_vless,
    _parse_vmess,
    _parse_trojan,
    _parse_hysteria2,
    _parse_wireguard,
    _parse_openvpn,
    _extract_config_lines,
)
from src.configstream.models import Proxy


class TestParsers:
    def test_parse_ss_simple(self):
        config = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@127.0.0.1:8388#Example"
        proxy = _parse_ss(config)
        assert proxy is not None
        assert proxy.protocol == "shadowsocks"
        assert proxy.address == "127.0.0.1"
        assert proxy.port == 8388
        assert proxy.details["method"] == "aes-256-gcm"
        assert proxy.details["password"] == "password"
        assert proxy.remarks == "Example"

    def test_parse_vless_reality(self):
        config = "vless://uuid@example.com:443?security=reality&sni=example.com&fp=chrome&pbk=publickey&sid=shortid&type=tcp&flow=xtls-rprx-vision#Reality"
        proxy = _parse_vless(config)
        assert proxy is not None
        assert proxy.protocol == "vless"
        assert proxy.details["security"] == "reality"
        assert proxy.details["pbk"] == "publickey"
        assert proxy.remarks == "Reality"

    def test_parse_hysteria2_ports(self):
        config = "hysteria2://password@example.com:443?ports=80,443,10000-20000&obfs=salamander&obfs-password=secret#Hys2"
        proxy = _parse_hysteria2(config)
        assert proxy is not None
        assert proxy.protocol == "hysteria2"
        assert proxy.details["ports"] == "80,443,10000-20000"
        assert proxy.details["obfs"] == "salamander"

    def test_parse_wireguard_reserved(self):
        config = "wireguard://user@1.2.3.4:51820?public_key=pub&private_key=priv&reserved=[1,2,3]&address=10.0.0.1/24#WG"
        proxy = _parse_wireguard(config)
        assert proxy is not None
        assert proxy.protocol == "wireguard"
        config_bad = "wireguard://user@1.2.3.4:51820?public_key=pub&private_key=priv&reserved=badformat&address=10.0.0.1/24#WG"
        proxy_bad = _parse_wireguard(config_bad)
        assert proxy_bad is not None

    def test_extract_config_lines(self):
        payload = """
        ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@127.0.0.1:8388#One
        # This is a comment
        vless://uuid@example.com:443#Two
        InvalidLine
        """
        lines = _extract_config_lines(payload)
        assert len(lines) == 2
        assert "ss://" in lines[0]
        assert "vless://" in lines[1]

    def test_parse_openvpn(self):
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
verb 3"""
        proxy = _parse_openvpn(config)
        assert proxy is not None
        assert proxy.protocol == "openvpn"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 1194
        assert proxy.details["transport"] == "udp"
