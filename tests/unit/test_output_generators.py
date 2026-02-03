# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.generators import generate_clash_config
from tests.unit.conftest_helper import create_test_proxy


def test_generate_clash():
    sample_proxies = [
        create_test_proxy(
            config="vmess://test",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="a1b2c3d4",
            remarks="Test Proxy",
            network="ws",
            details={
                "ws_path": "/",
                "ws_headers": {"Host": "example.com"},
                "tls": True,
                "sni": "example.com",
            },
            is_working=True,
        )
    ]

    output = generate_clash_config(sample_proxies)
    assert "proxies:" in output
    # The proxy name format is "XX 01 | VMESS" (country code + index + protocol)
    # "Test Proxy" is remarks, which is NOT used as the name in the generator loop.
    # It uses: f"{p.country_code or 'XX'} {i:02d} | {p.protocol.upper()}"
    assert "Test Proxy" in output
