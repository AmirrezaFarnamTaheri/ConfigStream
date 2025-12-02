import logging
import pytest
from unittest.mock import MagicMock
from configstream.converters import to_singbox_outbound
from configstream.models import Proxy
from configstream.fetcher import fetch_from_source
from configstream.fetcher_core.models import FetchResult

@pytest.mark.asyncio
async def test_converter_logging_invalid_port(caplog):
    caplog.set_level(logging.WARNING)

    # Use model_construct to bypass Pydantic validation on init
    proxy = Proxy.model_construct(
        source="test",
        address="example.com",
        port=99999, # Invalid
        protocol="vless",
        uuid="uuid",
        config="vless://...",
        is_working=True,
        tags=[]
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
        tags=[]
    )

    result = to_singbox_outbound(proxy)
    assert result is not None
    assert "Generated unique local IP" in caplog.text
