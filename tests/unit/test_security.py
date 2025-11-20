
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from configstream.security.blocklist import BlocklistManager, DEFAULT_BLOCKLIST
from configstream.security.virus_total import scan_url, check_ip_reputation

# --- Blocklist Tests ---

@pytest.fixture
def mock_blocklist_file(tmp_path):
    # Use a path object that can be patched into CACHE_FILE
    return tmp_path / "firehol_level1.netset"

@pytest.mark.asyncio
async def test_is_blocked_logic(mock_blocklist_file):
    manager = BlocklistManager()

    # Mock the CACHE_FILE path and content loading
    mock_blocklist_file.write_text("1.2.3.4/32\n5.6.7.0/24")

    with patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file):
        await manager.load()

        assert manager.is_blocked("1.2.3.4") is True
        assert manager.is_blocked("5.6.7.8") is True  # Inside /24
        assert manager.is_blocked("8.8.8.8") is False

@pytest.mark.asyncio
async def test_update_blocklist(mock_blocklist_file):
    manager = BlocklistManager()

    with patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file), \
         patch("httpx.AsyncClient.get") as mock_get:

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        # httpx.AsyncClient.get returns a Response object. content is a property.
        # If we mock return_value, mock_resp.content is accessed.
        # We explicitly set it as a non-async attribute.
        # httpx.AsyncClient.get returns a Response object.
        # content attribute is accessed.
        # In tests, if we mock the response object, we must ensure attributes are set correctly.
        # Because httpx.Response.content is a property, MagicMock might mock it as another mock.

        # Create a real-ish mock or configure property
        type(mock_resp).content = PropertyMock(return_value=b"9.9.9.9/32\n10.10.10.0/24")

        # When AsyncClient.get() is awaited (entered via context manager), it returns mock_resp
        mock_get.return_value.__aenter__.return_value = mock_resp

        await manager.update()

        # Verify file was written
        assert mock_blocklist_file.exists()
        content = mock_blocklist_file.read_text()
        assert "9.9.9.9/32" in content

        # Verify in-memory update
        assert manager.is_blocked("9.9.9.9") is True
        assert manager.is_blocked("10.10.10.5") is True

def test_is_honeypot():
    manager = BlocklistManager()
    assert manager.is_honeypot("1.1.1.1", 23) is True  # Telnet
    assert manager.is_honeypot("1.1.1.1", 443) is False


# --- VirusTotal Tests ---

@pytest.mark.asyncio
async def test_scan_url_clean():
    with patch("configstream.security.virus_total.VT_API_KEY", "fake_key"), \
         patch("aiohttp.ClientSession.get") as mock_get:

        mock_resp = MagicMock()
        mock_resp.status = 200

        # Correctly mock the async json() method
        async def async_json():
            return {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}}
        mock_resp.json = async_json

        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await scan_url("http://example.com")
        assert result["malicious"] == 0

@pytest.mark.asyncio
async def test_check_ip_reputation_malicious():
    with patch("configstream.security.virus_total.VT_API_KEY", "fake_key"), \
         patch("aiohttp.ClientSession.get") as mock_get:

        mock_resp = MagicMock()
        mock_resp.status = 200

        # Correctly mock the async json() method
        async def async_json():
            return {"data": {"attributes": {"last_analysis_stats": {"malicious": 5}}}}
        mock_resp.json = async_json

        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await check_ip_reputation("1.2.3.4")
        assert result["malicious"] == 5
