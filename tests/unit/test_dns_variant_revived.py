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


def test_dns_chain_rewrite_does_not_depend_on_record_order():
    from configstream.output.native_configs import build_dns_hardened_proxies

    chain = Proxy(
        config="revived://test",
        protocol="revived",
        address="1.1.1.1",
        port=443,
        details={
            "chain_outbounds": [
                {
                    "type": "trojan",
                    "tag": "hop",
                    "server": "relay.example",
                    "server_port": 443,
                    "password": "test",
                    "tls": {"enabled": True},
                }
            ]
        },
    )
    relay = Proxy(
        config="socks5://relay.example:1080",
        protocol="socks5",
        address="relay.example",
        port=1080,
        resolved_ip="8.8.8.8",
    )
    forward, _ = build_dns_hardened_proxies([chain, relay])
    reverse, _ = build_dns_hardened_proxies([relay, chain])
    assert forward[0].details == reverse[1].details
    assert forward[0].details["chain_outbounds"][0]["server"] == "8.8.8.8"


def test_chosen_subscription_ranks_zero_latency_first():
    from configstream.output.subscriptions import select_chosen_proxies

    proxies = [
        Proxy(
            config=f"socks5://1.1.1.1:{port}",
            protocol="socks5",
            address="1.1.1.1",
            port=port,
            latency=latency,
            is_working=True,
        )
        for port, latency in [(1080, 0), (1081, 10)]
    ]
    assert select_chosen_proxies(proxies, 1, 1)[0].latency == 0


def test_dns_safe_excludes_unresolved_chain_hop():
    from configstream.output.native_configs import build_dns_safe_proxies

    proxy = Proxy(
        config="revived://test",
        protocol="revived",
        address="1.1.1.1",
        port=443,
        details={
            "chain_outbounds": [
                {
                    "type": "trojan",
                    "tag": "hop",
                    "server": "unresolved.example",
                    "server_port": 443,
                    "password": "test",
                }
            ]
        },
    )
    safe, _ = build_dns_safe_proxies([proxy])
    assert safe == []


def test_chain_conversion_never_returns_partial_path():
    from configstream.converters.chain_outbounds import chain_obs_from_details

    hop = Proxy(
        config="socks5://1.1.1.1:1080", protocol="socks5", address="1.1.1.1", port=1080
    )
    assert chain_obs_from_details({"chain": [hop, {"invalid": True}]}) == []
    assert chain_obs_from_details({"chain_outbounds": [{"type": "socks"}, None]}) == []


def test_side_product_archive_preserves_colliding_names(tmp_path):
    import zipfile
    from configstream.output.subscriptions import generate_side_products_pack
    from configstream.models import Proxy

    proxies = [
        Proxy(
            config=f"client\nremote 1.1.1.{n} 1194\n",
            protocol="openvpn",
            address=f"1.1.1.{n}",
            port=1194,
            remarks="same",
        )
        for n in (1, 2)
    ]
    archive = tmp_path / "side.zip"
    assert generate_side_products_pack(proxies, archive, "", tmp_path) == archive
    with zipfile.ZipFile(archive) as handle:
        names = [name for name in handle.namelist() if name.endswith(".ovpn")]
        assert len(names) == len(set(names)) == 2
        assert handle.read(names[0]) != handle.read(names[1])


def test_public_source_host_drops_userinfo():
    from configstream.serialize import _sanitize_source
    assert _sanitize_source('https://user:private-password@example.com:443/sub?token=secret') == 'example.com'
