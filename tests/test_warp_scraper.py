import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.intelligence.washer.warp_scraper import WarpScraper


def _mock_httpx_response(text: str):
    """Create a patched httpx.AsyncClient that returns the given text."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = text
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

    with patch(
        "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
        [{"name": "test", "url": "http://test", "kind": "endpoint_list"}],
    ), patch("configstream.intelligence.washer.warp_scraper.httpx.AsyncClient", return_value=mock_client):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 0  # endpoint_list produces no proxies directly
        endpoints = scraper.get_scraped_endpoints()
        assert "162.159.192.1" in endpoints
        assert "1.1.1.1" in endpoints
        assert "invalid" not in endpoints


@pytest.mark.asyncio
async def test_scrape_text_decode_warp_uri():
    scraper = WarpScraper()
    warp_uri = "warp://someprivatekey1234567890123456789012345678901234567890@1.2.3.4:5678?peer=pubkey&reserved=1,2,3"
    mock_client = _mock_httpx_response(warp_uri)

    with patch(
        "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
        [{"name": "test", "url": "http://test", "kind": "text_decode"}],
    ), patch("configstream.intelligence.washer.warp_scraper.httpx.AsyncClient", return_value=mock_client):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 1
        p = proxies[0]
        assert (
            p.details["private_key"]
            == "someprivatekey1234567890123456789012345678901234567890"
        )
        assert p.address == "1.2.3.4"
        assert p.port == 5678
        assert p.details["peer_public_key"] == "pubkey"
        assert p.details["reserved"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_scrape_singbox_json():
    json_content = """
    {
        "outbounds": [
            {
                "type": "wireguard",
                "private_key": "someprivatekey1234567890123456789012345678901234567890",
                "local_address": ["172.16.0.2/32"]
            }
        ]
    }
    """
    scraper = WarpScraper()
    mock_client = _mock_httpx_response(json_content)

    with patch(
        "configstream.intelligence.washer.warp_scraper.WARP_SOURCES",
        [{"name": "test", "url": "http://test", "kind": "singbox"}],
    ), patch("configstream.intelligence.washer.warp_scraper.httpx.AsyncClient", return_value=mock_client):
        proxies = await scraper.scrape_warp_sources()
        assert len(proxies) == 1
        assert (
            proxies[0].details["private_key"]
            == "someprivatekey1234567890123456789012345678901234567890"
        )


@pytest.mark.asyncio
async def test_parse_warp_uri_invalid():
    scraper = WarpScraper()
    assert scraper._parse_warp_uri("invalid") is None
    assert scraper._parse_warp_uri("warp://short@host:port") is None
