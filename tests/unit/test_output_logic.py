import json
from configstream.models import Proxy
from configstream.output_logic import generate_categorized_outputs
from configstream.intelligence.washer import ProxyWasher
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
    return '[{"id": "key1", "private_key": "priv1", "peer_public_key": "pub1"}]'


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
    assert "sub_full" in files

    # Check Singbox content
    with open(files["singbox_full"]) as f:
        data = json.load(f)
        outbounds = data["outbounds"]
        tags = [o.get("tag") for o in outbounds if "tag" in o]

        assert "mixed-in" in [i["tag"] for i in data["inbounds"]]
        # Updated to match 'The Sniper' strategy used in split.py
        assert "🌍 Proxy Select" in tags or "🚀 Select Proxy" in tags
        assert "🚀 Auto" in tags or "⚡ Auto-Fast" in tags

        # Check if washed proxies are included (via extra_outbounds logic)
        # Note: tags depend on washer generation logic (Secure/Optimal)
        # The washer logic adds tags like "🛡️ Secure-US-1"
        assert any(t.startswith("🛡️ Secure") for t in tags)
