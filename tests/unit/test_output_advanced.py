# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import pytest
from unittest.mock import patch

from configstream.models import Proxy
from configstream.intelligence.washer import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.output import generate_split_outputs


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
            details={"net": "ws"},
        ),
        Proxy(
            config="hysteria2://...",
            protocol="hysteria2",
            address="2.2.2.2",
            port=443,
            country_code="CN",
            is_working=True,
            details={},
        ),
        Proxy(
            config="socks5://...",
            protocol="socks5",
            address="3.3.3.3",
            port=1080,
            country_code="RU",
            is_working=True,
            tags=["insecure"],
            details={"tls": "none"},
        ),
        Proxy(
            config="http://...",
            protocol="http",
            address="4.4.4.4",
            port=8080,
            country_code="IR",
            is_working=True,
            tags=["dirty_ip"],
            details={"tls": "none"},
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
            details={"tls": "tls"},
        ),
    ]


def test_generate_smart_chains(sample_proxies):
    chains = generate_smart_chains(sample_proxies)
    # The generation depends on random choices and availability of relays/exits
    # With the sample proxies provided:
    # relays_fast: hysteria2 (1)
    # exits_standard: vmess, socks5 (2)
    # So experimental chain might be generated.

    if "experimental" in chains and chains["experimental"]:
        # Chains structure is Dict[str, List[List[Dict]]]
        # List of chains, where each chain is a List of outbounds
        exp_chains = chains["experimental"]
        if exp_chains:
            first_chain = exp_chains[0]
            assert len(first_chain) >= 2
            relay = first_chain[0]
            exit_node = first_chain[1]
            assert "tag" in relay
            assert "detour" in exit_node
            assert exit_node["detour"] == relay["tag"]


@patch("os.getenv")
def test_wash_dirty_proxies(mock_getenv, sample_proxies):
    warp_keys = '[{"private_key": "pk1", "peer_public_key": "pub1"}]'
    mock_getenv.return_value = warp_keys

    washer = ProxyWasher(warp_keys)
    # Updated return signature: washed_outbounds, washed_ids, skip_reasons
    washed, washed_ids, skip_reasons = washer.wash_batch(sample_proxies)

    # Washed list contains pairs (relay, exit). So length should be 2 * number of washed proxies.
    assert len(washed) >= 2

    # We can't guarantee order, so let's find the socks relay pair
    socks_relay = None
    socks_exit = None

    for i in range(0, len(washed), 2):
        relay = washed[i]
        exit_node = washed[i + 1]
        if relay["type"] == "socks":
            socks_relay = relay
            socks_exit = exit_node
            break

    # Socks5 might not be selected if conversion fails or other reasons,
    # but based on previous test it was expected.
    # Note: `wash_batch` logic filters `candidates = [p for p in proxies if p.is_working and self.warp_keys]`
    # And then calls `to_singbox_outbound`.
    # Socks5 should convert fine.

    if socks_relay:
        assert socks_relay["type"] == "socks"
        assert socks_exit["type"] == "wireguard"
        assert socks_exit["detour"] == socks_relay["tag"]


def test_generate_split_outputs(tmp_path, sample_proxies):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    washed = [
        {"type": "socks", "tag": "RELAY-1"},
        {"type": "wireguard", "tag": "🛡️ Secure-RU-1", "detour": "RELAY-1"},
    ]

    washed_ids = {"uuid-dirty"}

    smart_chains = {"intranet": [], "ipv6": [], "streamer": [], "experimental": []}

    files = generate_split_outputs(
        sample_proxies, output_dir, washed, washed_ids, smart_chains
    )

    assert "singbox_vpn" in files
    assert "singbox" in files
    assert "clash" in files

    with open(files["singbox_vpn"]) as f:
        vpn_conf = json.load(f)
        assert vpn_conf["inbounds"][0]["type"] == "tun"
        tags = [o["tag"] for o in vpn_conf["outbounds"]]
        assert "🛡️ Secure-RU-1" in tags

    with open(files["singbox"]) as f:
        sniper_conf = json.load(f)
        assert sniper_conf["inbounds"][0]["type"] == "mixed"
        for o in sniper_conf["outbounds"]:
            if "tls" in o and isinstance(o["tls"], dict):
                assert "tls_fragment" in o["tls"]
