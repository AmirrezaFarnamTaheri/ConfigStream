# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for output format correctness and client compatibility across adapters and converters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.adapters import get_adapter
from configstream.adapters.loon import LoonAdapter
from configstream.adapters.quantumult import QuantumultXAdapter
from configstream.adapters.shadowrocket import ShadowrocketAdapter
from configstream.adapters.sip008 import SIP008Adapter
from configstream.adapters.surge import SurgeAdapter
from configstream.converters.clash import to_clash_proxy
from configstream.converters.singbox import to_singbox_outbound
from configstream.models import Proxy

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def sample_proxies() -> list[Proxy]:
    """Provide a diverse set of valid proxies across supported protocols."""
    return [
        Proxy(
            config="vless://11111111-2222-3333-4444-555555555555@104.21.45.10:443?type=tcp&security=tls#US-VLESS-Fast",
            protocol="vless",
            address="104.21.45.10",
            port=443,
            uuid="11111111-2222-3333-4444-555555555555",
            country_code="US",
            remarks="US-VLESS-Fast",
            is_working=True,
            details={
                "type": "tcp",
                "security": "tls",
                "sni": "us.example.com",
                "flow": "xtls-rprx-vision",
            },
        ),
        Proxy(
            config="vmess://eyJhZGQiOiIxMDQuMjEuNDUuMTEiLCJwb3J0Ijo4NDQzLCJpZCI6IjIyMjIyMjIyLTMzMzMtNDQ0NC01NTU1LTY2NjY2NjY2NjY2NiIsIm5ldCI6IndzIiwicHMiOiJERS1WTWVzcy1XUyJ9",
            protocol="vmess",
            address="104.21.45.11",
            port=8443,
            uuid="22222222-3333-4444-5555-666666666666",
            country_code="DE",
            remarks="DE-VMess-WS",
            is_working=True,
            details={
                "net": "ws",
                "path": "/stream",
                "host": "de.example.com",
                "tls": "tls",
                "sni": "de.example.com",
            },
        ),
        Proxy(
            config="trojan://secret-trojan-pw@104.21.45.12:443?security=tls&sni=jp.example.com#JP-Trojan-TLS",
            protocol="trojan",
            address="104.21.45.12",
            port=443,
            uuid="secret-trojan-pw",
            country_code="JP",
            remarks="JP-Trojan-TLS",
            is_working=True,
            details={
                "security": "tls",
                "sni": "jp.example.com",
                "alpn": "h2,http/1.1",
            },
        ),
        Proxy(
            config="ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpjaGFjaGEtcGFzc3dvcmQ=@104.21.45.13:8388#FR-SS-AEAD",
            protocol="shadowsocks",
            address="104.21.45.13",
            port=8388,
            uuid="chacha-password",
            country_code="FR",
            remarks="FR-SS-AEAD",
            is_working=True,
            details={
                "method": "chacha20-ietf-poly1305",
                "password": "chacha-password",
            },
        ),
        Proxy(
            config="hysteria2://hy2-token@104.21.45.14:443/?sni=gb.example.com#GB-Hysteria2",
            protocol="hysteria2",
            address="104.21.45.14",
            port=443,
            uuid="77777777-7777-4777-8777-777777777777",
            country_code="GB",
            remarks="GB-Hysteria2",
            is_working=True,
            details={
                "password": "hy2-token",
                "sni": "gb.example.com",
                "insecure": 0,
            },
        ),
        Proxy(
            config="wireguard://104.21.45.15:51820?publickey=QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI=&reserved=0,0,0#SG-WireGuard",
            protocol="wireguard",
            address="104.21.45.15",
            port=51820,
            uuid="88888888-8888-4888-8888-888888888888",
            country_code="SG",
            remarks="SG-WireGuard",
            is_working=True,
            details={
                "private_key": "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=",
                "peer_public_key": "QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI=",
                "local_address": "172.16.0.2/32",
                "mtu": 1420,
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Sing-box Outbound Output Correctness
# ---------------------------------------------------------------------------


def test_singbox_outbound_format_correctness(sample_proxies: list[Proxy]) -> None:
    """Verify Sing-Box outbound conversion produces valid schema dictionaries."""
    for proxy in sample_proxies:
        outbound = to_singbox_outbound(proxy)
        assert (
            outbound is not None
        ), f"Sing-box outbound generation failed for {proxy.protocol}"
        assert isinstance(outbound, dict)
        assert "type" in outbound
        assert "tag" in outbound
        assert outbound["server"] == proxy.address
        assert outbound["server_port"] == proxy.port

        if proxy.protocol == "vless":
            assert outbound["type"] == "vless"
            assert outbound["uuid"] == proxy.uuid
            assert "tls" in outbound
        elif proxy.protocol == "vmess":
            assert outbound["type"] == "vmess"
            assert outbound["uuid"] == proxy.uuid
            assert "transport" in outbound
            assert outbound["transport"]["type"] == "ws"
        elif proxy.protocol == "trojan":
            assert outbound["type"] == "trojan"
            assert outbound["password"] == proxy.uuid
            assert "tls" in outbound
        elif proxy.protocol == "shadowsocks":
            assert outbound["type"] == "shadowsocks"
            assert outbound["method"] == "chacha20-ietf-poly1305"
            assert outbound["password"] == "chacha-password"
        elif proxy.protocol == "hysteria2":
            assert outbound["type"] == "hysteria2"
            assert outbound["password"] == "hy2-token"
        elif proxy.protocol == "wireguard":
            assert outbound["type"] == "wireguard"
            assert (
                outbound["private_key"]
                == "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE="
            )
            assert (
                outbound["peer_public_key"]
                == "QkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkI="
            )


# ---------------------------------------------------------------------------
# Clash Proxy Output Correctness
# ---------------------------------------------------------------------------


def test_clash_proxy_format_correctness(sample_proxies: list[Proxy]) -> None:
    """Verify Clash proxy conversion produces compatible proxy configurations."""
    for proxy in sample_proxies:
        clash_obj = to_clash_proxy(proxy, ignore_status=True)
        assert clash_obj is not None, f"Clash conversion failed for {proxy.protocol}"
        assert isinstance(clash_obj, dict)
        assert "name" in clash_obj
        assert "type" in clash_obj
        assert clash_obj["server"] == proxy.address
        assert clash_obj["port"] == proxy.port

        if proxy.protocol == "shadowsocks":
            assert clash_obj["type"] == "ss"
            assert clash_obj["cipher"] == "chacha20-ietf-poly1305"
        elif proxy.protocol == "vmess":
            assert clash_obj["type"] == "vmess"
            assert clash_obj["uuid"] == proxy.uuid
            assert clash_obj.get("network") == "ws"
        elif proxy.protocol == "trojan":
            assert clash_obj["type"] == "trojan"
            assert clash_obj["password"] == proxy.uuid
            assert clash_obj.get("tls") is True


# ---------------------------------------------------------------------------
# Client Adapters Export Correctness
# ---------------------------------------------------------------------------


def test_adapter_factory_registry() -> None:
    """Verify adapter factory instantiates all documented client adapters."""
    for name, expected_cls in [
        ("surge", SurgeAdapter),
        ("loon", LoonAdapter),
        ("qx", QuantumultXAdapter),
        ("shadowrocket", ShadowrocketAdapter),
        ("sip008", SIP008Adapter),
    ]:
        adapter = get_adapter(name)
        assert isinstance(adapter, expected_cls)


def test_surge_adapter_export(sample_proxies: list[Proxy]) -> None:
    """Verify Surge adapter produces valid policy lines."""
    adapter = SurgeAdapter()
    exported = adapter.export(sample_proxies)
    assert isinstance(exported, str)
    assert "# Surge Policy Export" in exported
    lines = [
        line.strip()
        for line in exported.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(lines) >= 3


def test_loon_adapter_export(sample_proxies: list[Proxy]) -> None:
    """Verify Loon adapter produces valid configuration lines."""
    adapter = LoonAdapter()
    exported = adapter.export(sample_proxies)
    assert isinstance(exported, str)
    assert len(exported) > 0


def test_quantumult_adapter_export(sample_proxies: list[Proxy]) -> None:
    """Verify Quantumult X adapter produces valid proxy lines."""
    adapter = QuantumultXAdapter()
    exported = adapter.export(sample_proxies)
    assert isinstance(exported, str)
    assert len(exported) > 0


def test_sip008_adapter_export(sample_proxies: list[Proxy]) -> None:
    """Verify SIP008 JSON schema compliance for Shadowsocks delivery."""
    adapter = SIP008Adapter()
    exported = adapter.export(sample_proxies)
    data = json.loads(exported)
    assert isinstance(data, dict)
    assert data.get("version") == 1
    assert "servers" in data
    assert isinstance(data["servers"], list)
    # Only shadowsocks proxies are included in SIP008
    assert len(data["servers"]) >= 1
    ss_server = data["servers"][0]
    assert ss_server["server"] == "104.21.45.13"
    assert ss_server["server_port"] == 8388
    assert ss_server["method"] == "chacha20-ietf-poly1305"
