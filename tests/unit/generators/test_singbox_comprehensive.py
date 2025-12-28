import json
from unittest.mock import patch

import pytest

from configstream.generators.singbox import (_strip_internal_metadata,
                                             generate_singbox_config)
from configstream.models import Proxy


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
        assert "🚀 Select Proxy" in tags
        assert "⚡ Best Latency" in tags
        assert "DIRECT" in tags
        assert "dns-out" in tags


def test_generate_singbox_config_extra_outbounds():
    proxies = []
    extras = [
        {"type": "wireguard", "tag": "WARP"},
        {"type": "vless", "tag": "RELAY-123"},
    ]

    config_str = generate_singbox_config(proxies, extra_outbounds=extras)
    config = json.loads(config_str)

    outbounds = config["outbounds"]
    tags = [o.get("tag") for o in outbounds]

    assert "WARP" in tags
    assert "RELAY-123" in tags

    # RELAY should not be in selector
    selector = next(o for o in outbounds if o["type"] == "selector")
    assert "WARP" in selector["outbounds"]
    assert "RELAY-123" not in selector["outbounds"]
