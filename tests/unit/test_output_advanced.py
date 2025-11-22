import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from configstream.models import Proxy
from configstream.output import (
    generate_exotic_chains,
    wash_dirty_proxies,
    generate_split_outputs,
    to_singbox_outbound
)

@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://...",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="uuid1",
            country_code="US",
            is_working=True,
            details={"net": "ws"}
        ),
        Proxy(
            config="hysteria2://...",
            protocol="hysteria2",
            address="2.2.2.2",
            port=443,
            country_code="CN",
            is_working=True,
            details={}
        ),
        Proxy(
            config="socks5://...",
            protocol="socks5",
            address="3.3.3.3",
            port=1080,
            country_code="RU",
            is_working=True,
            tags=["insecure"], # Marked insecure
            details={"tls": "none"}
        ),
        Proxy(
            config="http://...",
            protocol="http",
            address="4.4.4.4",
            port=8080,
            country_code="IR",
            is_working=True,
            tags=["dirty_ip"], # Marked dirty
            details={"tls": "none"}
        ),
        Proxy(
            config="vless://...",
            protocol="vless",
            address="5.5.5.5",
            port=443,
            uuid="uuid2",
            country_code="DE",
            is_working=True,
            is_secure=True,
            details={"tls": "tls"}
        )
    ]

def test_generate_exotic_chains(sample_proxies):
    chains = generate_exotic_chains(sample_proxies)
    # Should find Hysteria2 (Relay) and VMess (Exit)
    # Returns flat list of outbounds (2 per chain)
    # We have 1 relay (hysteria2) and 1 exit (vmess) -> 1 chain -> 2 outbounds

    # Note: VLESS is also an exit candidate depending on definition, but let's check logic
    # relays: hysteria2
    # exits: vmess
    # 1 chain

    assert len(chains) >= 2
    relay = chains[0]
    exit_node = chains[1]

    assert relay["type"] == "hysteria2" or relay["type"] == "tuic" # based on protocol mapping
    assert exit_node["type"] == "vmess"

    assert "tag" in relay
    assert "detour" in exit_node
    assert exit_node["detour"] == relay["tag"]

@patch("os.getenv")
def test_wash_dirty_proxies(mock_getenv, sample_proxies):
    # Mock WARP keys
    warp_keys = '[{"private_key": "pk1", "peer_public_key": "pub1"}]'
    mock_getenv.return_value = warp_keys

    washed = wash_dirty_proxies(sample_proxies)

    # Should wash:
    # 1. socks5 (insecure) -> WARP
    # 2. http (dirty_ip) -> TLS (VLESS)

    # Expecting:
    # SOCKS pair: [socks_outbound, warp_outbound]
    # HTTP pair: [http_outbound, vless_outbound]
    # Total 4 items

    assert len(washed) == 4

    # Verify SOCKS washing
    socks_relay = washed[0]
    warp_exit = washed[1]
    assert socks_relay["type"] == "socks"
    assert warp_exit["type"] == "wireguard"
    assert warp_exit["detour"] == socks_relay["tag"]

    # Verify HTTP washing
    http_relay = washed[2]
    tls_exit = washed[3]
    assert http_relay["type"] == "http"
    assert tls_exit["type"] in ["vless", "trojan", "vmess"]
    assert tls_exit["detour"] == http_relay["tag"]

def test_generate_split_outputs(tmp_path, sample_proxies):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create some dummy washed outbounds
    washed = [
        {"type": "socks", "tag": "RELAY-1"},
        {"type": "wireguard", "tag": "CLEAN-WARP-1", "detour": "RELAY-1"}
    ]

    files = generate_split_outputs(sample_proxies, output_dir, washed)

    assert "singbox_vpn" in files
    assert "singbox" in files
    assert "clash" in files

    # Check Tank (VPN)
    with open(files["singbox_vpn"]) as f:
        vpn_conf = json.load(f)
        # Should have tun inbound
        assert vpn_conf["inbounds"][0]["type"] == "tun"
        # Should include cleaned exits in selector? No, manual says include in config but maybe selector
        # Code says: washed_exits added to selector

        tags = [o["tag"] for o in vpn_conf["outbounds"]]
        assert "CLEAN-WARP-1" in tags
        assert "RELAY-1" in tags # Should be present as outbound, not necessarily in selector

    # Check Sniper
    with open(files["singbox"]) as f:
        sniper_conf = json.load(f)
        # Should have mixed inbound
        assert sniper_conf["inbounds"][0]["type"] == "mixed"
        # Check fragmentation
        for o in sniper_conf["outbounds"]:
            if "tls" in o:
                assert "tls_fragment" in o["tls"]
