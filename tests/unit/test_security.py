from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.security.blocklist import BlocklistManager
from configstream.security.virus_total import check_ip_reputation, scan_url

# --- Blocklist Tests ---


@pytest.fixture
def mock_blocklist_file(tmp_path):
    # Use a path object that can be patched into CACHE_FILE
    return tmp_path / "firehol_level1.netset"


@pytest.fixture(autouse=True)
def reset_blocklist_singleton():
    # Reset singleton before each test
    BlocklistManager._instance = None
    yield
    BlocklistManager._instance = None


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

    with (
        patch("configstream.security.blocklist.CACHE_FILE", mock_blocklist_file),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"9.9.9.9/32\n10.10.10.0/24"

        mock_get.return_value = mock_resp

        await manager.update()

        if not mock_blocklist_file.exists():
            print("File not found after update()")
        else:
            print("File content:", mock_blocklist_file.read_text())

        await manager.load()

        assert manager.is_blocked("9.9.9.9") is True
        assert manager.is_blocked("10.10.10.5") is True


def test_is_suspicious_port():
    manager = BlocklistManager()
    assert manager.is_suspicious_port(23) is True  # Telnet
    assert manager.is_suspicious_port(443) is False


# --- VirusTotal Tests ---


@pytest.mark.asyncio
async def test_scan_url_clean():
    with (
        patch("configstream.security.virus_total.VT_API_KEY", "fake_key"),
        patch("aiohttp.ClientSession.get") as mock_get,
    ):
        mock_resp = MagicMock()
        mock_resp.status = 200

        async def async_json():
            return {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}}

        mock_resp.json = async_json
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await scan_url("http://example.com")
        assert result["malicious"] == 0


@pytest.mark.asyncio
async def test_check_ip_reputation_malicious():
    with (
        patch("configstream.security.virus_total.VT_API_KEY", "fake_key"),
        patch("aiohttp.ClientSession.get") as mock_get,
    ):
        mock_resp = MagicMock()
        mock_resp.status = 200

        async def async_json():
            return {"data": {"attributes": {"last_analysis_stats": {"malicious": 5}}}}

        mock_resp.json = async_json
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await check_ip_reputation("1.2.3.4")
        assert result["malicious"] == 5
