# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from unittest.mock import patch
from configstream.models import Proxy
from configstream.generators.singbox import (
    generate_singbox_config,
    _strip_internal_metadata,
)


def test_strip_internal_metadata():
    obs = [{"type": "a", "_process": "washed"}, {"type": "b"}]
    cleaned = _strip_internal_metadata(obs)
    assert "_process" not in cleaned[0]
    assert "type" in cleaned[0]
    assert len(cleaned) == 2


def test_generate_singbox_config_basics():
    proxies = [
        Proxy(
            config="vless://1",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="u1",
            remarks="P1",
        )
    ]

    with patch(
        "configstream.generators.singbox.to_singbox_outbound",
        return_value={"type": "vless"},
    ):
        config_str = generate_singbox_config(proxies)
        config = json.loads(config_str)

        assert "outbounds" in config
        tags = [o.get("tag") for o in config["outbounds"]]
        assert "P1" in tags
        assert "🌍 Proxy Select" in tags
        assert "⚡ Best Latency" in tags
        assert "direct" in tags
        assert "dns-out" in tags


def test_generate_singbox_config_extra_outbounds():
    proxies = []
    # Proper chain topology: WARP is the entry point, RELAY-123 is the inner hop
    # WARP routes traffic through RELAY-123 via the detour field
    extras = [
        {"type": "wireguard", "tag": "WARP", "detour": "RELAY-123"},
        {"type": "vless", "tag": "RELAY-123"},
    ]

    config_str = generate_singbox_config(proxies, extra_outbounds=extras)
    config = json.loads(config_str)

    outbounds = config["outbounds"]
    tags = [o.get("tag") for o in outbounds]

    assert "WARP" in tags
    assert "RELAY-123" in tags

    # Inner hop (detour target) should NOT be in selector; entry point should
    selector = next(o for o in outbounds if o["type"] == "selector")
    assert "WARP" in selector["outbounds"]
    assert "RELAY-123" not in selector["outbounds"]

    # Entry point should also be in urltest for auto-select
    urltest = next(o for o in outbounds if o["type"] == "urltest")
    assert "WARP" in urltest["outbounds"]
    assert "RELAY-123" not in urltest["outbounds"]


def test_generate_singbox_config_has_no_dead_legacy_selector_outbounds():
    """Only the returned final outbound list is authoritative."""
    config = json.loads(generate_singbox_config([]))
    tags = [outbound.get("tag") for outbound in config["outbounds"]]

    assert "🌍 Proxy Select" in tags
    assert "⚡ Best Latency" in tags
    assert "🚀 Mode Selector" not in tags
    assert "🛡️ Auto-Fallback" not in tags


def test_generate_singbox_config_empty_urltest_falls_back_to_direct():
    """Country/protocol subsets with no convertible proxies must stay valid."""
    config = json.loads(generate_singbox_config([]))
    urltest = next(
        item for item in config["outbounds"] if item.get("type") == "urltest"
    )
    assert urltest["outbounds"] == ["direct"]
