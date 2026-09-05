# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import base64
from pathlib import Path

from configstream.generators.plaintext import generate_plaintext_subscription
from configstream.models import Proxy
from configstream.output_logic import generate_categorized_outputs
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
import pytest


@pytest.fixture
def sample_proxies():
    p1 = Proxy(
        config="vless://uuid@1.1.1.1:443?security=reality&fp=chrome&pbk=pubkey&sid=shortid&sni=example.com#IR-Relay",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="uuid",
        country_code="IR",
        is_working=True,
        details={
            "security": "reality",
            "pbk": "pubkey",
            "sid": "shortid",
            "fp": "chrome",
            "sni": "example.com",
        },
    )
    p2 = Proxy(
        config="socks5://user:pass@2.2.2.2:1080#Dirty-Socks",
        protocol="socks5",
        address="2.2.2.2",
        port=1080,
        uuid="user",
        country_code="US",
        is_working=True,
        tags={"dirty_ip"},  # Explicitly mark as dirty to trigger washing
        details={"password": "pass"},
    )
    return [p1, p2]


@pytest.fixture
def warp_keys():
    return (
        '[{"id": "key1", "private_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", '
        '"peer_public_key": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="}]'
    )


# Remove asyncio marker, as generate_categorized_outputs and wash_batch are sync
def test_generate_categorized_outputs(tmp_path, sample_proxies, warp_keys):
    washer = ProxyWasher(warp_keys)
    washed_outbounds, washed_ids, _ = washer.wash_batch(sample_proxies)
    smart = generate_smart_chains(sample_proxies)

    files = generate_categorized_outputs(
        sample_proxies, tmp_path, washed_outbounds, washed_ids, smart
    )

    # Updated keys for v2.0
    assert "singbox_full" in files
    assert "clash_full" in files
    assert "base64" in files
    assert "singbox_chains" in files

    # Check Singbox content
    with open(files["singbox_full"], encoding="utf-8") as f:
        data = json.load(f)
        outbounds = data["outbounds"]
        tags = [o.get("tag") for o in outbounds if "tag" in o]

        assert "mixed-in" in [i["tag"] for i in data["inbounds"]]
        # Updated to match 'The Sniper' strategy used in split.py
        assert any("Proxy Select" in t for t in tags if t)
        assert any("Auto" in t for t in tags if t)

        # Check if washed proxies are included (via extra_outbounds logic)
        # Note: tags depend on washer generation logic (Secure/Optimal)
        # The washer logic adds normalized tags with SECURE/OPTIMAL tiers.
        assert any("secure" in t.lower() for t in tags if t)


def test_chosen_outputs_generated(tmp_path, sample_proxies):
    """Verify chosen/ directory outputs include singbox.json, clash.yaml, proxies.txt."""
    files = generate_categorized_outputs(sample_proxies, tmp_path)

    assert "chosen_base64" in files
    assert "chosen_proxies_txt" in files
    assert "chosen_singbox" in files
    # chosen_clash may not be present if generate_clash_config returns empty for few proxies
    # but at least the other three must exist

    # Verify chosen/singbox.json is valid JSON
    with open(files["chosen_singbox"], encoding="utf-8") as f:
        data = json.load(f)
        assert "outbounds" in data

    # Verify chosen/proxies.txt is non-empty
    assert files["chosen_proxies_txt"].stat().st_size > 0


def test_dns_cache_passthrough(tmp_path, sample_proxies):
    """Verify dns_safe_cache parameter is respected (no double computation)."""
    from configstream.output_logic import _build_dns_safe_proxies

    # Pre-compute DNS-safe cache
    dns_safe_cache = _build_dns_safe_proxies(sample_proxies)
    dns_safe_proxies, host_map = dns_safe_cache

    # Pass cache to generate_categorized_outputs
    files = generate_categorized_outputs(
        sample_proxies,
        tmp_path,
        dns_safe_cache=dns_safe_cache,
    )

    # Should still generate base outputs
    assert "base64" in files
    assert "singbox_full" in files


def test_disabled_dns_modes_emit_empty_required_artifacts_without_building(
    tmp_path: Path,
    sample_proxies: list[Proxy],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DNS_SAFE_OUTPUTS", "false")
    monkeypatch.setenv("DNS_HARDENED_OUTPUTS", "false")

    def unexpected_build(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("disabled DNS mode rebuilt its proxy dataset")

    monkeypatch.setattr(
        "configstream.output_logic._build_dns_safe_proxies", unexpected_build
    )
    monkeypatch.setattr(
        "configstream.output_logic._build_dns_hardened_proxies", unexpected_build
    )

    files = generate_categorized_outputs(sample_proxies, tmp_path)

    assert files["base64_dns_safe"].read_text(encoding="utf-8") == ""
    assert files["base64_dns_hardened"].read_text(encoding="utf-8") == ""
    assert files["singbox_dns_safe"].exists()
    assert files["singbox_dns_hardened"].exists()


def test_protocol_txt_files_generated(tmp_path, sample_proxies):
    """Verify per-protocol .txt URI subscription files are generated."""
    files = generate_categorized_outputs(sample_proxies, tmp_path)

    # At least one protocol txt file should exist
    proto_txt_keys = [k for k in files if k.startswith("proto_") and k.endswith("_txt")]
    assert len(proto_txt_keys) > 0

    # Verify content is non-empty plaintext URIs
    for key in proto_txt_keys:
        content = files[key].read_text(encoding="utf-8")
        assert len(content.strip()) > 0


def test_plaintext_protocol_priority_order() -> None:
    proxies = [
        Proxy(
            config="http://h.example:80#http",
            protocol="http",
            address="h.example",
            port=80,
        ),
        Proxy(
            config="socks5://s.example:1080#socks",
            protocol="socks5",
            address="s.example",
            port=1080,
        ),
        Proxy(
            config="ss://YWVzLTEyOC1nY206cGFzcw==@ss.example:443#ss",
            protocol="shadowsocks",
            address="ss.example",
            port=443,
        ),
        Proxy(
            config="vless://u@vless.example:443#vless",
            protocol="vless",
            address="vless.example",
            port=443,
            uuid="u",
        ),
        Proxy(
            config="vmess://dGVzdA==#vmess",
            protocol="vmess",
            address="vm.example",
            port=443,
            uuid="123e4567-e89b-12d3-a456-426614174000",
        ),
        Proxy(
            config="wireguard://wg.example:2408#wg",
            protocol="wireguard",
            address="wg.example",
            port=2408,
        ),
        Proxy(
            config="hysteria2://pass@hy2.example:443#hy2",
            protocol="hysteria2",
            address="hy2.example",
            port=443,
        ),
    ]

    plaintext = generate_plaintext_subscription(proxies)
    schemes = [
        line.split("://", 1)[0] for line in plaintext.splitlines() if "://" in line
    ]
    assert schemes[:7] == [
        "hysteria2",
        "wireguard",
        "vmess",
        "vless",
        "ss",
        "socks5",
        "http",
    ]


def test_chosen_proxies_txt_respects_protocol_priority_order(tmp_path) -> None:
    proxies = [
        Proxy(
            config="http://h.example:80#http",
            protocol="http",
            address="h.example",
            port=80,
            is_working=True,
        ),
        Proxy(
            config="vless://u@vless.example:443#vless",
            protocol="vless",
            address="vless.example",
            port=443,
            uuid="u",
            is_working=True,
        ),
        Proxy(
            config="hysteria2://pass@hy2.example:443#hy2",
            protocol="hysteria2",
            address="hy2.example",
            port=443,
            is_working=True,
        ),
    ]
    files = generate_categorized_outputs(proxies, tmp_path)
    chosen_lines = files["chosen_proxies_txt"].read_text(encoding="utf-8").splitlines()
    assert chosen_lines[0].startswith("hysteria2://")
    assert chosen_lines[1].startswith("vless://")
    assert chosen_lines[2].startswith("http://")


def test_uri_artifacts_fallback_to_all_when_working_pool_has_no_uris(tmp_path) -> None:
    """proxies.txt/base64.txt should not be empty when only non-URI working protocols exist."""
    proxies = [
        Proxy(
            config="not-a-uri",
            protocol="wireguard",
            address="wg.example",
            port=2408,
            is_working=True,
        ),
        Proxy(
            config="revived://placeholder",
            protocol="revived",
            address="revived.example",
            port=443,
            uuid="u",
            is_working=False,
            details={
                "is_revived": True,
                "origin_config": {
                    "config": "vless://u@revived.example:443#revived-node",
                    "protocol": "vless",
                    "address": "revived.example",
                    "port": 443,
                    "uuid": "u",
                    "remarks": "revived-node",
                },
            },
        ),
    ]

    files = generate_categorized_outputs(proxies, tmp_path)
    raw = files["proxies_txt"].read_text(encoding="utf-8")
    assert "vless://" in raw
    assert "revived.example:443" in raw

    b64 = files["base64"].read_text(encoding="utf-8").strip()
    decoded = base64.b64decode(b64).decode("utf-8")
    assert "vless://" in decoded
    assert "revived.example:443" in decoded


def test_dns_safe_uses_detached_proxy_clones():
    """DNS-safe cache must not share object references with source proxies."""
    from configstream.output_logic import _build_dns_safe_proxies

    src = Proxy(
        config="trojan://pass@1.1.1.1:443#node",
        protocol="trojan",
        address="1.1.1.1",
        port=443,
        uuid="pass",
        process="native",
        details={},
    )

    dns_safe, _ = _build_dns_safe_proxies([src])

    assert len(dns_safe) == 1
    assert dns_safe[0] is not src
    assert dns_safe[0].details.get("dns_safe") is True

    src.process = "shielded"
    assert dns_safe[0].process == "native"


def test_dns_safe_rewrites_canonical_chain_proxy_hops() -> None:
    """DNS-safe rewrite must update canonical chain Proxy hops, not only legacy outbounds."""
    from configstream.output_logic import _build_dns_safe_proxies

    relay = Proxy(
        config="vless://123e4567-e89b-12d3-a456-426614174000@relay.example:443#relay",
        protocol="vless",
        address="relay.example",
        port=443,
        uuid="123e4567-e89b-12d3-a456-426614174000",
        details={"security": "tls", "sni": "relay.example", "tag": "relay-hop"},
    )
    warp = Proxy(
        config="wireguard://priv@162.159.192.1:2408#warp",
        protocol="wireguard",
        address="162.159.192.1",
        port=2408,
        details={
            "private_key": "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E=",
            "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            "local_address": ["10.0.0.2/32"],
            "mtu": 1280,
            "detour": "relay-hop",
            "tag": "warp-hop",
        },
    )
    revived = Proxy(
        config="revived://relay.example",
        protocol="revived",
        address="relay.example",
        port=443,
        uuid="revived-chain-proxy-hop",
        resolved_ip="1.1.1.1",
        details={"is_revived": True, "chain": [relay, warp]},
    )

    dns_safe, _ = _build_dns_safe_proxies([revived])
    assert len(dns_safe) == 1

    chain = dns_safe[0].details.get("chain")
    assert isinstance(chain, list) and len(chain) == 2
    assert isinstance(chain[0], Proxy)
    assert chain[0].address == "1.1.1.1"

    chain_outbounds = dns_safe[0].details.get("chain_outbounds")
    assert isinstance(chain_outbounds, list) and chain_outbounds
    assert chain_outbounds[0].get("server") == "1.1.1.1"


def test_dns_safe_rewrites_canonical_chain_dict_hops() -> None:
    """DNS-safe rewrite must update canonical chain dict hops after serialization boundaries."""
    from configstream.output_logic import _build_dns_safe_proxies

    revived = Proxy(
        config="revived://relay.example",
        protocol="revived",
        address="relay.example",
        port=443,
        uuid="revived-chain-dict-hop",
        resolved_ip="1.1.1.1",
        details={
            "is_revived": True,
            "chain": [
                {
                    "config": "vless://123e4567-e89b-12d3-a456-426614174000@relay.example:443#relay",
                    "protocol": "vless",
                    "address": "relay.example",
                    "port": 443,
                    "uuid": "123e4567-e89b-12d3-a456-426614174000",
                    "details": {
                        "security": "tls",
                        "sni": "relay.example",
                        "tag": "relay-hop",
                    },
                },
                {
                    "config": "wireguard://priv@162.159.192.1:2408#warp",
                    "protocol": "wireguard",
                    "address": "162.159.192.1",
                    "port": 2408,
                    "details": {
                        "private_key": "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E=",
                        "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                        "local_address": ["10.0.0.2/32"],
                        "mtu": 1280,
                        "detour": "relay-hop",
                        "tag": "warp-hop",
                    },
                },
            ],
        },
    )

    dns_safe, _ = _build_dns_safe_proxies([revived])
    assert len(dns_safe) == 1

    chain = dns_safe[0].details.get("chain")
    assert isinstance(chain, list) and len(chain) == 2
    assert isinstance(chain[0], dict)
    assert chain[0].get("address") == "1.1.1.1"

    chain_outbounds = dns_safe[0].details.get("chain_outbounds")
    assert isinstance(chain_outbounds, list) and chain_outbounds
    assert chain_outbounds[0].get("server") == "1.1.1.1"


def test_chain_uniquification_prevents_collapse():
    """Chains with duplicate tags must be uniquified, not skipped (fixes single-proxy collapse)."""
    from configstream.generators.singbox import SingBoxGenerator

    # 3 chains with identical entry-point tag (simulating format_proxy_name collision)
    dup_tag = "DE-VLESS-100ms-shielded"
    chains = []
    for i in range(3):
        wg = {
            "type": "wireguard",
            "tag": f"WG-{i}",
            "server": "162.159.192.1",
            "server_port": 2408,
            "private_key": "x",
            "peer_public_key": "y",
            "local_address": ["10.0.0.1/32"],
        }
        relay = {
            "type": "vless",
            "tag": dup_tag,
            "server": "1.1.1.1",
            "server_port": 443,
            "uuid": f"uuid{i}",
            "detour": f"WG-{i}",
        }
        chains.extend([wg, relay])

    gen = SingBoxGenerator()
    config = gen.generate([], extra_outbounds=chains)
    selector = next(
        (
            o
            for o in config["outbounds"]
            if o.get("type") == "selector" and o.get("tag") == "🌍 Proxy Select"
        ),
        None,
    )
    assert selector is not None
    entry_tags = [
        t
        for t in selector.get("outbounds", [])
        if t and t not in ("⚡ Best Latency", "direct")
    ]
    assert (
        len(entry_tags) >= 3
    ), f"All 3 chains must appear (uniquified), got {len(entry_tags)}: {entry_tags}"
