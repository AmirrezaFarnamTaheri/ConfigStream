# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for artifact consistency across client cores:
- Sing-box WireGuard outbound format (mtu default, reserved, detour)
- Clash/Mihomo WireGuard format (ip, private-key, public-key, mtu, udp)
- Surge/Loon chain export (broadened tag matching, mtu, relay protocols)
- WireGuard .conf export (MTU in [Interface])
- adapters_base relay protocol support (vless, trojan, hy2, http, socks5)
"""

import pytest
from configstream.models import Proxy
from configstream.converters.singbox import to_singbox_outbound
from configstream.converters.clash import to_clash_proxy
from configstream.adapters import SurgeAdapter, LoonAdapter
from configstream.adapters_base import (
    convert_singbox_outbound_to_surge_string,
    format_singbox_chain_for_surge,
    format_singbox_chain_for_loon,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _wg_proxy(**overrides):
    """Create a working WireGuard proxy with sensible defaults."""
    defaults = dict(
        config="wireguard://key@1.2.3.4:2408",
        protocol="wireguard",
        address="162.159.192.1",
        port=2408,
        uuid="",
        details={
            "private_key": "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=",
            "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            "local_address": ["172.16.0.2/32"],
            "reserved": [0, 0, 0],
        },
        is_working=True,
    )
    defaults.update(overrides)
    return Proxy(**defaults)


def _chain_outbounds(relay_type="shadowsocks", tag_prefix="🛡️ Secure"):
    """Create a pair of chain outbounds (relay + warp exit)."""
    relay = {
        "type": relay_type,
        "tag": "RELAY-CHAIN-1",
        "server": "5.6.7.8",
        "server_port": 443,
    }
    if relay_type == "shadowsocks":
        relay["method"] = "aes-128-gcm"
        relay["password"] = "testpass"
    elif relay_type == "vmess":
        relay["uuid"] = "test-uuid"
    elif relay_type == "vless":
        relay["uuid"] = "test-uuid"
        relay["tls"] = {"server_name": "example.com"}
    elif relay_type == "trojan":
        relay["password"] = "test-trojan-pass"
        relay["tls"] = {"server_name": "example.com"}
    elif relay_type == "hysteria2":
        relay["password"] = "hy2pass"
    elif relay_type == "http":
        pass
    elif relay_type == "socks5":
        pass

    warp_exit = {
        "type": "wireguard",
        "tag": f"{tag_prefix}-US-1",
        "server": "162.159.192.1",
        "server_port": 2408,
        "local_address": ["10.0.0.1/32"],
        "private_key": "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=",
        "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
        "reserved": [0, 0, 0],
        "mtu": 1280,
        "detour": "RELAY-CHAIN-1",
    }
    return [relay, warp_exit]


# ---------------------------------------------------------------------------
# Sing-box converter: WireGuard mtu default
# ---------------------------------------------------------------------------


class TestSingboxWireGuardMtu:
    def test_mtu_defaults_to_1280(self):
        proxy = _wg_proxy()
        out = to_singbox_outbound(proxy)
        assert out is not None
        assert out["mtu"] == 1280

    def test_mtu_preserved_when_set(self):
        proxy = _wg_proxy(
            details={
                "private_key": "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=",
                "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                "local_address": ["172.16.0.2/32"],
                "mtu": 1400,
            }
        )
        out = to_singbox_outbound(proxy)
        assert out is not None
        assert out["mtu"] == 1400


# ---------------------------------------------------------------------------
# Clash converter: WireGuard mtu default + fields
# ---------------------------------------------------------------------------


class TestClashWireGuard:
    def test_mtu_defaults_to_1280(self):
        proxy = _wg_proxy()
        out = to_clash_proxy(proxy)
        assert out is not None
        assert out["mtu"] == 1280

    def test_udp_enabled(self):
        proxy = _wg_proxy()
        out = to_clash_proxy(proxy)
        assert out is not None
        assert out["udp"] is True

    def test_clash_field_names(self):
        proxy = _wg_proxy()
        out = to_clash_proxy(proxy)
        assert out is not None
        assert "private-key" in out
        assert "public-key" in out
        assert "ip" in out

    def test_reserved_passthrough(self):
        proxy = _wg_proxy()
        out = to_clash_proxy(proxy)
        assert out is not None
        assert out.get("reserved") == [0, 0, 0]


# ---------------------------------------------------------------------------
# Clash converter: Trojan transport
# ---------------------------------------------------------------------------


class TestClashTrojanTransport:
    def test_trojan_ws_transport(self):
        proxy = Proxy(
            config="trojan://pass@1.2.3.4:443",
            protocol="trojan",
            address="1.2.3.4",
            port=443,
            uuid="pass",
            details={
                "sni": "example.com",
                "network": "ws",
                "path": "/ws",
                "host": "example.com",
            },
            is_working=True,
        )
        out = to_clash_proxy(proxy)
        assert out is not None
        assert out.get("network") == "ws"
        assert "ws-opts" in out
        assert out["ws-opts"]["path"] == "/ws"

    def test_trojan_grpc_transport(self):
        proxy = Proxy(
            config="trojan://pass@1.2.3.4:443",
            protocol="trojan",
            address="1.2.3.4",
            port=443,
            uuid="pass",
            details={
                "sni": "example.com",
                "network": "grpc",
                "serviceName": "grpc-svc",
            },
            is_working=True,
        )
        out = to_clash_proxy(proxy)
        assert out is not None
        assert out.get("network") == "grpc"
        assert "grpc-opts" in out


# ---------------------------------------------------------------------------
# adapters_base: relay protocol support in chain formatters
# ---------------------------------------------------------------------------


class TestAdaptersBaseRelayProtocols:
    @pytest.mark.parametrize(
        "relay_type",
        [
            "shadowsocks",
            "vmess",
            "vless",
            "trojan",
            "hysteria2",
            "http",
            "socks5",
        ],
    )
    def test_surge_string_for_relay_type(self, relay_type):
        relay = _chain_outbounds(relay_type=relay_type)[0]
        result = convert_singbox_outbound_to_surge_string(relay)
        assert result is not None, f"Failed for relay type: {relay_type}"
        assert relay["tag"] in result

    @pytest.mark.parametrize("relay_type", ["shadowsocks", "vmess", "vless", "trojan"])
    def test_surge_chain_includes_mtu(self, relay_type):
        outbounds = _chain_outbounds(relay_type=relay_type)
        result = format_singbox_chain_for_surge(outbounds[1], outbounds)
        assert result is not None
        assert "mtu=1280" in result

    @pytest.mark.parametrize("relay_type", ["shadowsocks", "vmess", "vless", "trojan"])
    def test_loon_chain_includes_mtu(self, relay_type):
        outbounds = _chain_outbounds(relay_type=relay_type)
        result = format_singbox_chain_for_loon(outbounds[1], outbounds)
        assert result is not None
        assert "mtu=1280" in result


# ---------------------------------------------------------------------------
# Surge/Loon adapters: broadened chain tag matching
# ---------------------------------------------------------------------------


class TestAdapterChainBroadening:
    """Verify adapters export ALL chain types, not just 🛡️ Secure."""

    @pytest.mark.parametrize(
        "tag_prefix",
        [
            "🛡️ Secure",
            "🛡️⚡ Optimal",
            "VWARP-REVIVE",
            "WARP-REVIVE",
        ],
    )
    def test_surge_exports_all_chain_tags(self, tag_prefix):
        outbounds = _chain_outbounds(tag_prefix=tag_prefix)
        adapter = SurgeAdapter()
        output = adapter.export([], washed_outbounds=outbounds)
        # Should contain the WireGuard chain line
        assert "wireguard" in output.lower()

    @pytest.mark.parametrize(
        "tag_prefix",
        [
            "🛡️ Secure",
            "🛡️⚡ Optimal",
            "VWARP-REVIVE",
            "WARP-REVIVE",
        ],
    )
    def test_loon_exports_all_chain_tags(self, tag_prefix):
        outbounds = _chain_outbounds(tag_prefix=tag_prefix)
        adapter = LoonAdapter()
        output = adapter.export([], washed_outbounds=outbounds)
        assert "wireguard" in output.lower()
