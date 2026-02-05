# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import patch
from configstream.intelligence.chaining import (
    find_optimal_relay,
    generate_smart_chains,
    ProxyStub,
    haversine,
    create_chain,
    is_likely_ipv4,
)
from configstream.models import Proxy


def test_haversine():
    # Test London to Paris ~344km
    london = (51.5074, -0.1278)
    paris = (48.8566, 2.3522)
    dist = haversine(london[0], london[1], paris[0], paris[1])
    # Roughly 344 km
    assert 340 < dist < 350


def test_find_optimal_relay():
    origin = "IR"
    exit_node = ProxyStub("US", 37.09, -95.71, "wireguard")

    # Candidates
    relay_tr = ProxyStub("TR", 38.96, 35.24, "hysteria2")  # Turkey (Good)
    relay_cn = ProxyStub("CN", 35.86, 104.19, "vmess")  # China (Bad protocol penalty)

    candidates = [relay_tr, relay_cn]

    result = find_optimal_relay(origin, exit_node, candidates)

    assert "relay" in result
    assert result["relay"] == relay_tr
    # Distance + penalty logic check (implicit)


def test_find_optimal_relay_no_candidates():
    origin = "IR"
    exit_node = ProxyStub("US", 37.09, -95.71, "wireguard")
    candidates = []

    result = find_optimal_relay(origin, exit_node, candidates)
    assert "error" in result


def test_is_likely_ipv4():
    assert is_likely_ipv4("1.1.1.1") is True
    assert is_likely_ipv4("example.com") is True
    assert is_likely_ipv4("2001:db8::1") is False


def test_create_chain():
    relay = Proxy(
        config="vless://1",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="u1",
        country="TR",
    )
    exit_node = Proxy(
        config="vmess://2",
        protocol="vmess",
        address="2.2.2.2",
        port=443,
        uuid="u2",
        country="US",
    )

    # Mock converters
    with patch(
        "configstream.intelligence.chaining.to_singbox_outbound",
        side_effect=lambda x: {"type": x.protocol},
    ):
        chain = create_chain(relay, exit_node, "TEST")
        assert len(chain) == 2
        assert chain[0]["tag"].startswith("TEST-RELAY")
        assert chain[1]["tag"].startswith("TEST-EXIT")
        assert chain[1]["detour"] == chain[0]["tag"]


def test_generate_smart_chains():
    # Setup proxies
    relays = [
        Proxy(
            config="p1",
            protocol="hysteria2",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            country="IR",
            country_code="IR",
            is_working=True,
        ),
    ]
    exits = [
        Proxy(
            config="p2",
            protocol="vmess",
            address="2.2.2.2",
            port=443,
            uuid="u2",
            country="US",
            country_code="US",
            is_working=True,
        ),
    ]

    proxies = relays + exits

    with patch(
        "configstream.intelligence.chaining.to_singbox_outbound",
        side_effect=lambda x: {"type": x.protocol},
    ):
        chains = generate_smart_chains(proxies)

        assert "intranet" in chains
        assert len(chains["intranet"]) > 0
