# SPDX-License-Identifier: AGPL-3.0-or-later

from configstream.adapters import ShadowrocketAdapter
from configstream.generators.plaintext import generate_plaintext_subscription
from configstream.models import Proxy


def _build_revived_proxy(*, dns_variant: bool) -> Proxy:
    details = {
        "is_revived": True,
        "use_vwarp": False,
        "origin_config": {
            "config": "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443?security=tls&sni=example.com#orig",
            "protocol": "vless",
            "address": "example.com",
            "port": 443,
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "resolved_ip": "1.1.1.1",
            "remarks": "orig",
            "details": {"tls": "tls", "sni": "example.com"},
        },
    }
    if dns_variant:
        details["dns_safe"] = True

    return Proxy(
        config="revived://example.com",
        protocol="revived",
        address="162.159.192.1",
        port=2408,
        uuid="revived-1",
        remarks="revived",
        details=details,
        is_working=False,
    )


def test_revived_plaintext_uses_resolved_ip_for_dns_variant() -> None:
    normal = _build_revived_proxy(dns_variant=False)
    dns_safe = _build_revived_proxy(dns_variant=True)

    normal_text = generate_plaintext_subscription([normal])
    dns_text = generate_plaintext_subscription([dns_safe])

    assert "example.com:443" in normal_text
    assert "1.1.1.1:443" in dns_text
    assert "example.com:443" not in dns_text


def test_revived_shadowrocket_uses_resolved_ip_for_dns_variant() -> None:
    adapter = ShadowrocketAdapter()
    normal = _build_revived_proxy(dns_variant=False)
    dns_safe = _build_revived_proxy(dns_variant=True)

    normal_text = adapter.export([normal])
    dns_text = adapter.export([dns_safe])

    assert "example.com:443" in normal_text
    assert "1.1.1.1:443" in dns_text
    assert "example.com:443" not in dns_text
