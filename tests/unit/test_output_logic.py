import pytest
import json
from configstream.intelligence.washer import (
    ProxyWasher,
    generate_smart_chains,
    create_chain,
)
from configstream.output import generate_split_outputs
from configstream.models import Proxy


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vless://uuid@1.1.1.1:443?security=reality&fp=chrome&pbk=pubkey&sid=shortid&sni=example.com#IR-Relay",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="uuid",
            country_code="IR",
            details={
                "security": "reality",
                "pbk": "pubkey",
                "sid": "shortid",
                "sni": "example.com",
            },
            is_working=True,
            latency=100.0,
        ),
        Proxy(
            config="hysteria2://pass@2.2.2.2:443?sni=fast.com#Fast-Relay",
            protocol="hysteria2",
            address="2.2.2.2",
            port=443,
            uuid="pass",
            country_code="DE",
            details={"sni": "fast.com"},
            is_working=True,
            latency=50.0,
        ),
        Proxy(
            config="vmess://uuid@3.3.3.3:443?security=auto#US-Exit",
            protocol="vmess",
            address="3.3.3.3",
            port=443,
            uuid="uuid",
            country_code="US",
            is_working=True,
            latency=150.0,
        ),
        Proxy(
            config="socks5://user:pass@4.4.4.4:1080#Dirty-Socks",
            protocol="socks5",
            address="4.4.4.4",
            port=1080,
            uuid="user",
            details={"password": "pass"},
            is_working=True,
            tags=["dirty_ip", "insecure"],
            latency=80.0,
        ),
    ]


@pytest.fixture
def warp_keys():
    return json.dumps(
        [{"id": "key1", "private_key": "priv1", "peer_public_key": "pub1"}]
    )


def test_proxy_washer_washing(sample_proxies, warp_keys):
    washer = ProxyWasher(warp_keys)
    washed_outbounds, washed_ids = washer.wash_batch(sample_proxies)

    # Should only wash the 'Dirty-Socks' proxy
    # Output should contain 2 items: Relay and Exit
    assert len(washed_outbounds) == 2
    assert len(washed_ids) == 1

    relay = washed_outbounds[0]
    exit_node = washed_outbounds[1]

    assert relay["type"] == "socks"
    assert relay["tag"].startswith("RELAY-CHAIN-")

    assert exit_node["type"] == "wireguard"
    assert exit_node["tag"].startswith("🛡️ Secure-")
    assert exit_node["detour"] == relay["tag"]
    assert exit_node["private_key"] == "priv1"


def test_proxy_washer_consistent_hashing(sample_proxies, warp_keys):
    washer1 = ProxyWasher(warp_keys)
    res1, ids1 = washer1.wash_batch(sample_proxies)

    washer2 = ProxyWasher(warp_keys)
    res2, ids2 = washer2.wash_batch(sample_proxies)

    # Results should be identical including tags and selected keys
    assert res1 == res2
    assert res1[0]["tag"] == res2[0]["tag"]
    assert ids1 == ids2


def test_generate_smart_chains(sample_proxies):
    chains = generate_smart_chains(sample_proxies)

    # 1. Intranet Bridge: IR Relay -> Foreign Exits
    # sample_proxies[0] is IR
    # It should pair with sample_proxies[1] (DE) and sample_proxies[2] (US)

    intranet_chains = chains["intranet"]
    assert len(intranet_chains) >= 4  # 2 chains * 2 objects (Relay + Exit)

    # Check that we have both Hysteria2 (DE) and VMess (US) as exits
    exit_types = [o["type"] for o in intranet_chains if "EXIT" in o["tag"]]
    assert "hysteria2" in exit_types
    assert "vmess" in exit_types

    # 2. Experimental: Hysteria -> VMess
    # sample_proxies[1] is Hysteria, sample_proxies[2] is VMess
    assert len(chains["experimental"]) >= 2

    exp_relay = chains["experimental"][0]
    exp_exit = chains["experimental"][1]

    assert exp_relay["type"] == "hysteria2"
    assert exp_exit["type"] == "vmess"
    assert exp_exit["detour"] == exp_relay["tag"]


def test_create_chain(sample_proxies):
    relay = sample_proxies[1]  # Hysteria
    exit_node = sample_proxies[2]  # VMess

    chain = create_chain(relay, exit_node, "TEST")

    assert len(chain) == 2
    assert chain[0]["tag"] == f"TEST-RELAY-{relay.id[:6]}"
    assert chain[1]["tag"] == f"TEST-EXIT-{exit_node.country}-{exit_node.id[:6]}"
    assert chain[1]["detour"] == chain[0]["tag"]


def test_generate_split_outputs(tmp_path, sample_proxies, warp_keys):
    washer = ProxyWasher(warp_keys)
    washed_outbounds, washed_ids = washer.wash_batch(sample_proxies)
    smart = generate_smart_chains(sample_proxies)

    files = generate_split_outputs(
        sample_proxies, tmp_path, washed_outbounds, washed_ids, smart
    )

    assert "singbox_vpn" in files
    assert "singbox" in files
    assert "clash" in files

    # Check Singbox VPN content
    with open(files["singbox_vpn"]) as f:
        data = json.load(f)
        outbounds = data["outbounds"]
        tags = [o["tag"] for o in outbounds]

        assert "tun-in" in [i["tag"] for i in data["inbounds"]]
        assert "🌍 Proxy Select" in tags
        assert "🛡️ Washed" in tags
        assert "🇮🇷 Intranet" in tags

        # Check if washed proxies are included
        assert any(t.startswith("🛡️ Secure") for t in tags)

    # Check Sniper content
    with open(files["singbox"]) as f:
        data = json.load(f)
        tags = [o["tag"] for o in data["outbounds"]]

        assert "mixed-in" in [i["tag"] for i in data["inbounds"]]
        assert "🚀 Mode Selector" in tags
        assert "🌌 IPv6 Portal" in tags
