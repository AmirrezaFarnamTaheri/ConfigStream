import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from configstream.models import Proxy
from configstream.output import (
    generate_smart_chains,
    ProxyWasher,
    generate_split_outputs,
)
from configstream.converters import to_singbox_outbound


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
    assert "experimental" in chains
    exp_chain = chains["experimental"]

    if exp_chain:
        relay = exp_chain[0]
        exit_node = exp_chain[1]
        assert "tag" in relay
        assert "detour" in exit_node
        assert exit_node["detour"] == relay["tag"]


@patch("os.getenv")
def test_wash_dirty_proxies(mock_getenv, sample_proxies):
    warp_keys = '[{"private_key": "pk1", "peer_public_key": "pub1"}]'
    mock_getenv.return_value = warp_keys

    washer = ProxyWasher(warp_keys)
    washed, washed_ids = washer.wash_batch(sample_proxies)

    assert len(washed) >= 4
    socks_relay = washed[0]
    warp_exit = washed[1]
    assert socks_relay["type"] == "socks"
    assert warp_exit["type"] == "wireguard"
    assert warp_exit["detour"] == socks_relay["tag"]


def test_generate_split_outputs(tmp_path, sample_proxies):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    washed = [
        {"type": "socks", "tag": "RELAY-1"},
        {"type": "wireguard", "tag": "🛡️ Secure-RU-1", "detour": "RELAY-1"},
    ]

    washed_ids = {"uuid-dirty"}

    smart_chains = {"intranet": [], "ipv6": [], "streamer": [], "experimental": []}

    files = generate_split_outputs(sample_proxies, output_dir, washed, washed_ids, smart_chains)

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
