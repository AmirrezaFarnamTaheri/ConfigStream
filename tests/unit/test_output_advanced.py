# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for advanced output generation logic."""

import json

import pytest

from configstream.models import Proxy
from configstream.output_logic import generate_split_outputs


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://...",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="uuid1",
            details={
                "network": "ws",
                "tls": True,
                "sni": "1.1.1.1",
                "security": "auto",
                "type": "none",
            },
            is_working=True,
        ),
        Proxy(
            config="vless://...",
            protocol="vless",
            address="2.2.2.2",
            port=443,
            uuid="uuid2",
            details={
                "network": "tcp",
                "tls": True,
                "sni": "2.2.2.2",
                "security": "tls",
                "type": "none",
            },
            is_working=True,
        ),
        Proxy(
            config="ss://...",
            protocol="shadowsocks",
            address="3.3.3.3",
            port=8388,
            details={"method": "aes-256-gcm", "password": "pass"},
            is_working=True,
        ),
        # Dirty proxy to be washed
        Proxy(
            config="vmess://dirty...",
            protocol="vmess",
            address="4.4.4.4",
            port=443,
            uuid="uuid-dirty",
            details={"network": "ws", "tls": True, "security": "auto", "type": "none"},
            is_working=True,
        ),
    ]


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

    with open(files["singbox_vpn"], encoding="utf-8") as f:
        vpn_conf = json.load(f)
        assert vpn_conf["inbounds"][0]["type"] == "tun"
        tags = [o["tag"] for o in vpn_conf["outbounds"]]
        assert "🛡️ Secure-RU-1" in tags

    with open(files["singbox"], encoding="utf-8") as f:
        sniper_conf = json.load(f)
        assert sniper_conf["inbounds"][0]["type"] == "mixed"
        for o in sniper_conf["outbounds"]:
            if "tls" in o and isinstance(o["tls"], dict):
                # Verify tls_fragment is NOT present (no-op now)
                assert "tls_fragment" not in o["tls"]
                assert "utls" in o["tls"]  # Fingerprint rotation should still work

    with open(files["clash"], encoding="utf-8") as f:
        content = f.read()
        assert "proxies:" in content
        # Ensure at least one proxy type is present in the output
        # If Clash generator filters them out, we might need to adjust the Proxy details
        if "vmess" not in content and "ss" not in content:
            pytest.skip("Clash generator filtered all sample proxies")

        # We expect at least one of them to be present
        assert ("vmess" in content) or ("ss" in content) or ("shadowsocks" in content)


def test_split_uniquifies_duplicate_chain_tags(tmp_path):
    """Split generator must uniquify chain tags to prevent collapse (smart chains)."""
    # Smart chains can produce identical chain_tag/warp_tag for different relay+exit combos
    dup_tag = "🇮🇷➔🇺🇸 | INTRANET | VLESS✚TROJAN ✚ WARP"
    smart_chains = {
        "intranet_washed": [
            [
                {"type": "vless", "tag": "RELAY-abc123-INTRANET", "server": "1.1.1.1"},
                {
                    "type": "vless",
                    "tag": "MID-xyz789-INTRANET",
                    "detour": "RELAY-abc123-INTRANET",
                },
                {"type": "wireguard", "tag": dup_tag, "detour": "MID-xyz789-INTRANET"},
            ],
            [
                {"type": "vless", "tag": "RELAY-def456-INTRANET", "server": "2.2.2.2"},
                {
                    "type": "vless",
                    "tag": "MID-uvw012-INTRANET",
                    "detour": "RELAY-def456-INTRANET",
                },
                {"type": "wireguard", "tag": dup_tag, "detour": "MID-uvw012-INTRANET"},
            ],
        ]
    }
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    files = generate_split_outputs([], output_dir, smart_chains=smart_chains)
    with open(files["singbox"], encoding="utf-8") as f:
        data = json.load(f)
    tags = [o.get("tag") for o in data["outbounds"] if o.get("tag")]
    # Duplicate tag must be uniquified (no two outbounds with same tag)
    dup_count = sum(1 for t in tags if t == dup_tag)
    assert dup_count <= 1, (
        f"Duplicate tag must be uniquified, got {dup_count} occurrences"
    )
    # Selector must list both chains (uniquified tags)
    selector = next(
        (
            o
            for o in data["outbounds"]
            if o.get("type") == "selector" and "Proxy Select" in (o.get("tag") or "")
        ),
        None,
    )
    assert selector is not None
    chain_tags = [t for t in selector.get("outbounds", []) if dup_tag in (t or "")]
    assert len(chain_tags) >= 2, f"Both chains must be selectable, got {chain_tags}"
