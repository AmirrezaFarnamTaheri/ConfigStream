import json
from pathlib import Path
from configstream.models import Proxy
from configstream.output_logic import generate_split_outputs
from configstream.intelligence.washer import ProxyWasher, generate_smart_chains
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
    return '[{"id": "key1", "private_key": "priv1", "peer_public_key": "pub1"}]'


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

        # We don't necessarily need IPv6 Portal in the current logic unless added.
        # But we expect at least the basic groups
        assert "🛡️ Auto-Fallback" in tags
        assert "⚡ Auto-Fast" in tags
