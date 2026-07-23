import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from configstream.intelligence.washer.warp_scraper import WarpScraper

TRUSTED_TEST_URL = "https://raw.githubusercontent.com/example/test/main/data.txt"


def _key(byte: int = 1) -> str:
    return base64.b64encode(bytes([byte]) * 32).decode("ascii")


def _mock_httpx_response(text: str):
    """Create a patched httpx.AsyncClient that returns the given text."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = text
    mock_resp.content = text.encode("utf-8")
    mock_resp.headers = {}
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_scrape_endpoint_list():
    scraper = WarpScraper()
    mock_client = _mock_httpx_response("162.159.192.1:2408\ninvalid\n1.1.1.1")

    with (
        patch(
            "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
            [{"name": "test", "url": TRUSTED_TEST_URL, "kind": "endpoint_list"}],
        ),
        patch(
            "configstream.intelligence.washer.warp_scraper.httpx.AsyncClient",
            return_value=mock_client,
        ),
    ):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 0
        endpoints = scraper.get_scraped_endpoints()
        assert "162.159.192.1" in endpoints
        assert "1.1.1.1" in endpoints
        assert "invalid" not in endpoints


@pytest.mark.asyncio
async def test_scrape_text_decode_warp_uri():
    scraper = WarpScraper()
    private_key = _key(1)
    peer_key = _key(2)
    warp_uri = f"warp://{private_key}@1.2.3.4:5678?peer={peer_key}&reserved=1,2,3"
    mock_client = _mock_httpx_response(warp_uri)

    with (
        patch(
            "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
            [{"name": "test", "url": TRUSTED_TEST_URL, "kind": "text_decode"}],
        ),
        patch(
            "configstream.intelligence.washer.warp_scraper.httpx.AsyncClient",
            return_value=mock_client,
        ),
    ):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 1
        proxy = proxies[0]
        assert proxy.details["private_key"] == private_key
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 5678
        assert proxy.details["peer_public_key"] == peer_key
        assert proxy.details["reserved"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_scrape_singbox_json():
    private_key = _key(1)
    json_content = f"""{{
        "outbounds": [
            {{
                "type": "wireguard",
                "private_key": "{private_key}",
                "local_address": ["172.16.0.2/32"]
            }}
        ]
    }}"""
    scraper = WarpScraper()
    mock_client = _mock_httpx_response(json_content)

    with (
        patch(
            "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
            [{"name": "test", "url": TRUSTED_TEST_URL, "kind": "singbox"}],
        ),
        patch(
            "configstream.intelligence.washer.warp_scraper.httpx.AsyncClient",
            return_value=mock_client,
        ),
    ):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 1
        assert proxies[0].details["private_key"] == private_key


@pytest.mark.asyncio
async def test_parse_warp_uri_invalid():
    scraper = WarpScraper()
    assert scraper._parse_warp_uri("invalid") is None
    assert scraper._parse_warp_uri("warp://short@host:port") is None
