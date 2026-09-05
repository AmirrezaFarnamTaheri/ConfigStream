# SPDX-License-Identifier: AGPL-3.0-or-later
import json

from configstream.adapters import ShadowrocketAdapter
from configstream.converters.chain_outbounds import chain_outbounds_from_details
from configstream.generators.split import generate_split_outputs
from configstream.models import Proxy

_WG_PRIVATE = "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E="
_WG_PUBLIC = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="


def _build_relay_and_warp_chain() -> list[Proxy]:
    relay = Proxy(
        config="vless://6f1f4f6a-4f1f-4f6a-8f1f-4f6a4f1f4f6a@relay.example:443",
        protocol="vless",
        address="relay.example",
        port=443,
        uuid="6f1f4f6a-4f1f-4f6a-8f1f-4f6a4f1f4f6a",
        details={
            "type": "tcp",
            "security": "tls",
            "sni": "relay.example",
            "tag": "relay-hop",
        },
    )
    warp = Proxy(
        config=f"wireguard://{_WG_PRIVATE}@162.159.192.1:2408",
        protocol="wireguard",
        address="162.159.192.1",
        port=2408,
        details={
            "private_key": _WG_PRIVATE,
            "peer_public_key": _WG_PUBLIC,
            "local_address": ["10.0.0.2/32"],
            "reserved": [1, 2, 3],
            "mtu": 1280,
            "tag": "warp-hop",
            "detour": "relay-hop",
        },
    )
    return [relay, warp]


def test_chain_outbounds_prefers_canonical_chain_over_legacy() -> None:
    chain = _build_relay_and_warp_chain()
    details = {
        "chain": chain,
        "chain_outbounds": [
            {
                "type": "socks",
                "tag": "legacy-hop",
                "server": "127.0.0.1",
                "server_port": 1080,
            }
        ],
    }

    resolved = chain_outbounds_from_details(details)
    tags = [str(ob.get("tag", "")) for ob in resolved]

    assert len(resolved) == 2
    assert "relay-hop" in tags
    assert "warp-hop" in tags
    assert "legacy-hop" not in tags


def test_shadowrocket_export_supports_canonical_chain_details() -> None:
    chain = _build_relay_and_warp_chain()
    revived = Proxy(
        config="revived://relay.example",
        protocol="revived",
        address="162.159.192.1",
        port=2408,
        uuid="revived-chain-1",
        details={"is_revived": True, "chain": chain},
    )

    exported = ShadowrocketAdapter().export([revived])

    assert exported.startswith("vless://")
    assert "@relay.example:443" in exported


def test_split_generator_uses_canonical_chain_details(tmp_path) -> None:
    chain = _build_relay_and_warp_chain()
    revived = Proxy(
        config="revived://relay.example",
        protocol="revived",
        address="162.159.192.1",
        port=2408,
        uuid="revived-chain-2",
        details={"is_revived": True, "chain": chain},
    )

    files = generate_split_outputs([revived], tmp_path)
    singbox_path = files["singbox"]
    payload = json.loads(singbox_path.read_text(encoding="utf-8"))
    outbounds = payload.get("outbounds", [])
    tags = [str(ob.get("tag", "")) for ob in outbounds if isinstance(ob, dict)]

    assert "relay-hop" in tags
    assert "warp-hop" in tags


def test_invalid_canonical_chain_does_not_restore_stale_legacy_path() -> None:
    assert (
        chain_outbounds_from_details(
            {
                "chain": [{"protocol": "vless"}],
                "chain_outbounds": [{"type": "direct", "tag": "stale"}],
            }
        )
        == []
    )


def test_empty_canonical_chain_does_not_restore_stale_legacy_path() -> None:
    assert (
        chain_outbounds_from_details(
            {
                "chain": [],
                "chain_outbounds": [{"type": "direct", "tag": "stale"}],
            }
        )
        == []
    )
    assert (
        chain_outbounds_from_details(
            {
                "chain": "",
                "chain_outbounds": [{"type": "direct", "tag": "stale"}],
            }
        )
        == []
    )


def test_washer_raw_outbounds_are_valid_canonical_chain_details() -> None:
    chain = [
        {"type": "wireguard", "tag": "shield", "server": "1.1.1.1"},
        {"type": "vless", "tag": "relay", "server": "relay.example"},
    ]

    resolved = chain_outbounds_from_details({"chain": chain})

    assert resolved == chain
    assert resolved is not chain
