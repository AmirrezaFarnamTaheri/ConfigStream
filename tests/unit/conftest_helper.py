# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.models import Proxy


def create_test_proxy(
    config: str = "vmess://test",
    protocol: str = "vmess",
    address: str = "1.1.1.1",
    port: int = 443,
    is_working: bool = True,
    **kwargs,
):
    # Ensure default vmess/vless proxies have a valid UUID if not provided
    if protocol in ("vmess", "vless") and "uuid" not in kwargs:
        kwargs["uuid"] = "12345678-1234-5678-1234-567812345678"

    return Proxy(
        config=config,
        protocol=protocol,
        address=address,
        port=port,
        is_working=is_working,
        **kwargs,
    )


@pytest.fixture
def test_proxy():
    return create_test_proxy()
