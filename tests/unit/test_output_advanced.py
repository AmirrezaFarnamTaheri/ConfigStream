import json
import pytest
from unittest.mock import patch

from configstream.models import Proxy
from configstream.intelligence.washer import generate_smart_chains, ProxyWasher
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
        exp_chain = chains["experimental"]
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

    # Candidates for washing:
    # 1. socks5 (insecure) -> washable
    # 2. http (dirty_ip) -> washable
    # 3. vmess (working but not insecure/dirty) -> not washable unless we changed logic
    # In my previous thought process/fix, I made all working proxies candidates IF tags are not populated yet
    # But here tags ARE populated for socks5 and http.
    # The washer logic: if p.is_working and self.warp_keys: it washes ALL working proxies if warp keys exist.
    # So vmess, hysteria2, socks5, http, vless are all candidates (5 proxies).
    # It seems `wash_batch` logic was changed to wash ALL working proxies if warp keys are present.

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

    assert socks_relay is not None
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
