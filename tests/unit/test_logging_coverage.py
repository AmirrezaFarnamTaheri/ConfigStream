import logging

import pytest

from configstream.converters import to_singbox_outbound
from configstream.models import Proxy


@pytest.mark.asyncio
async def test_converter_logging_invalid_port(caplog):
    caplog.set_level(logging.DEBUG)

    # Use model_construct to bypass Pydantic validation on init
    proxy = Proxy.model_construct(
        source="test",
        address="example.com",
        port=99999,  # Invalid
        protocol="vless",
        uuid="uuid",
        config="vless://...",
        is_working=True,
        tags=[],
    )

    result = to_singbox_outbound(proxy)
    assert result is None
    assert "Conversion failed: invalid port 99999" in caplog.text


@pytest.mark.asyncio
async def test_wireguard_ip_generation_logging(caplog):
    caplog.set_level(logging.DEBUG)

    proxy = Proxy(
        source="test",
        address="vpn.example.com",
        port=51820,
        protocol="wireguard",
        details={"private_key": "key", "peer_public_key": "pub"},
        config="wg://...",
        is_working=True,
        tags=[],
    )

    result = to_singbox_outbound(proxy)
    assert result is not None
    # Ensure the log indicates IP generation and references the sanitized address
    assert "Generated unique local IP" in caplog.text
    assert "vpn.example.com" not in caplog.text
