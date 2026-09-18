# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

from configstream.converters.singbox import wireguard_outbound_to_endpoint
from configstream.testers.python import _runtime_singbox_document


def test_wireguard_outbound_migrates_complete_singbox_113_endpoint() -> None:
    endpoint = wireguard_outbound_to_endpoint(
        {
            "type": "wireguard",
            "tag": "proxy-test",
            "server": "162.159.192.1",
            "server_port": 2408,
            "local_address": "172.16.0.2/32",
            "local_address_v6": "fd01::2/128",
            "private_key": "private",
            "peer_public_key": "public",
            "pre_shared_key": "psk",
            "reserved": [1, 2, 3],
            "persistent_keepalive_interval": 25,
            "system_interface": "false",
            "interface_name": "wg-test",
            "detour": "relay",
            "mtu": 1280,
        }
    )

    assert endpoint["type"] == "wireguard"
    assert endpoint["tag"] == "proxy-test"
    assert endpoint["address"] == ["172.16.0.2/32", "fd01::2/128"]
    assert endpoint["private_key"] == "private"
    assert endpoint["mtu"] == 1280
    assert endpoint["system"] is False
    assert endpoint["name"] == "wg-test"
    assert endpoint["detour"] == "relay"
    assert "server" not in endpoint
    assert "server_port" not in endpoint
    assert "peer_public_key" not in endpoint

    assert endpoint["peers"] == [
        {
            "address": "162.159.192.1",
            "port": 2408,
            "public_key": "public",
            "allowed_ips": ["0.0.0.0/0", "::/0"],
            "pre_shared_key": "psk",
            "reserved": [1, 2, 3],
            "persistent_keepalive_interval": 25,
        }
    ]


def test_wireguard_endpoint_preserves_multiple_explicit_peers() -> None:
    endpoint = wireguard_outbound_to_endpoint(
        {
            "type": "wireguard",
            "tag": "wg",
            "address": ["10.0.0.2/32"],
            "private_key": "private",
            "peers": [
                {
                    "address": "198.51.100.10",
                    "port": 51820,
                    "public_key": "peer-a",
                    "allowed_ips": ["10.10.0.0/16"],
                },
                {
                    "server": "203.0.113.11",
                    "server_port": "51821",
                    "peer_public_key": "peer-b",
                    "allowed_ips": ["10.20.0.0/16"],
                },
            ],
        }
    )

    assert endpoint["peers"][0] == {
        "address": "198.51.100.10",
        "port": 51820,
        "public_key": "peer-a",
        "allowed_ips": ["10.10.0.0/16"],
    }
    assert endpoint["peers"][1] == {
        "address": "203.0.113.11",
        "port": 51821,
        "public_key": "peer-b",
        "allowed_ips": ["10.20.0.0/16"],
    }


def test_runtime_document_moves_all_wireguard_hops_to_endpoints() -> None:
    primary = {
        "type": "wireguard",
        "tag": "proxy-test",
        "server": "162.159.192.1",
        "server_port": 2408,
        "local_address": "172.16.0.2/32",
        "private_key": "private-a",
        "peer_public_key": "public-a",
        "detour": "relay",
    }
    extras = [
        {
            "type": "socks",
            "tag": "relay",
            "server": "127.0.0.1",
            "server_port": 1080,
        },
        {
            "type": "wireguard",
            "tag": "inner-wg",
            "server": "188.114.96.1",
            "server_port": 2408,
            "local_address": "10.0.0.2/32",
            "private_key": "private-b",
            "peer_public_key": "public-b",
        },
    ]

    document = _runtime_singbox_document(primary, extras, 18080)

    assert document["route"]["final"] == "proxy-test"
    assert document["inbounds"][0]["listen_port"] == 18080
    assert [item["tag"] for item in document["outbounds"]] == ["relay"]
    assert [item["tag"] for item in document["endpoints"]] == [
        "proxy-test",
        "inner-wg",
    ]
    assert all(item["type"] == "wireguard" for item in document["endpoints"])
    assert all(item.get("type") != "wireguard" for item in document["outbounds"])
    assert all("server" not in item for item in document["endpoints"])


def test_runtime_document_keeps_non_wireguard_shape_without_endpoints() -> None:
    document = _runtime_singbox_document(
        {
            "type": "socks",
            "tag": "proxy-test",
            "server": "127.0.0.1",
            "server_port": 1080,
        },
        None,
        18081,
    )

    assert document["outbounds"][0]["tag"] == "proxy-test"
    assert "endpoints" not in document


def test_wireguard_endpoint_rejects_invalid_runtime_fields() -> None:
    base = {
        "type": "wireguard",
        "tag": "wg",
        "address": ["10.0.0.2/32"],
        "private_key": "private",
        "server": "198.51.100.10",
        "server_port": 51820,
        "peer_public_key": "public",
    }

    invalid_cases: list[tuple[dict, str]] = [
        ({"tag": ""}, "tag"),
        ({"address": [], "local_address": "", "local_address_v6": ""}, "local address"),
        ({"private_key": ""}, "private key"),
        ({"server_port": 0}, "peer port"),
        ({"server_port": 65536}, "peer port"),
        ({"server_port": "not-a-port"}, "peer port"),
        ({"peer_public_key": ""}, "peer public key"),
        ({"mtu": 0}, "mtu"),
        ({"mtu": "invalid"}, "mtu"),
        ({"reserved": [1, 2]}, "reserved"),
        ({"reserved": [1, 2, 256]}, "reserved"),
        ({"persistent_keepalive_interval": -1}, "keepalive"),
        ({"listen_port": -1}, "listen_port"),
        ({"workers": -1}, "workers"),
    ]

    for updates, match in invalid_cases:
        candidate = dict(base)
        candidate.update(updates)
        with pytest.raises(ValueError, match=match):
            wireguard_outbound_to_endpoint(candidate)


def test_wireguard_endpoint_rejects_malformed_explicit_peers() -> None:
    base = {
        "type": "wireguard",
        "tag": "wg",
        "address": ["10.0.0.2/32"],
        "private_key": "private",
    }
    with pytest.raises(ValueError, match="peers must be a list"):
        wireguard_outbound_to_endpoint({**base, "peers": "invalid"})
    with pytest.raises(ValueError, match="peers must contain objects"):
        wireguard_outbound_to_endpoint({**base, "peers": [{"address": "a"}, "invalid"]})
    with pytest.raises(ValueError, match="peer address"):
        wireguard_outbound_to_endpoint(
            {
                **base,
                "peers": [{"port": 51820, "public_key": "public"}],
            }
        )
    with pytest.raises(ValueError, match="peer public key"):
        wireguard_outbound_to_endpoint(
            {
                **base,
                "peers": [{"address": "198.51.100.10", "port": 51820}],
            }
        )


def test_wireguard_endpoint_preserves_zero_runtime_defaults() -> None:
    endpoint = wireguard_outbound_to_endpoint(
        {
            "type": "wireguard",
            "tag": "wg",
            "address": ["10.0.0.2/32"],
            "private_key": "private",
            "server": "198.51.100.10",
            "server_port": 51820,
            "peer_public_key": "public",
            "listen_port": 0,
            "workers": 0,
            "persistent_keepalive_interval": 0,
        }
    )
    assert endpoint["listen_port"] == 0
    assert endpoint["workers"] == 0
    assert endpoint["peers"][0]["persistent_keepalive_interval"] == 0


def test_wireguard_endpoint_rejects_explicit_zero_peer_port() -> None:
    with pytest.raises(ValueError, match="peer port"):
        wireguard_outbound_to_endpoint(
            {
                "type": "wireguard",
                "tag": "wg",
                "address": ["10.0.0.2/32"],
                "private_key": "private",
                "server_port": 51820,
                "peers": [
                    {
                        "address": "198.51.100.10",
                        "port": 0,
                        "public_key": "peer",
                    }
                ],
            }
        )
