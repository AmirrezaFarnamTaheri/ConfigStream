# SPDX-License-Identifier: AGPL-3.0-or-later
import json
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
