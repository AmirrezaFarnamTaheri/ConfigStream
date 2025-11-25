import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.geoip import GeoIPResolver


@pytest.fixture
def resolver():
    # Reset singleton for test
    GeoIPResolver._instance = None
    with (
        patch("configstream.geoip.Path.exists", return_value=True),
        patch("geoip2.database.Reader"),
    ):
        return GeoIPResolver()


def test_lookup_valid_ip(resolver):
    resolver.reader_city = MagicMock()
    resolver.reader_city.city.return_value.country.iso_code = "US"
    resolver.reader_city.city.return_value.city.name = "New York"

    resolver.reader_asn = MagicMock()
    resolver.reader_asn.asn.return_value.autonomous_system_number = 12345
    resolver.reader_asn.asn.return_value.autonomous_system_organization = "ISP Inc."

    data = resolver.lookup("1.1.1.1")

    assert data.country_code == "US"
    assert data.city == "New York"
    assert data.asn == "12345"
    assert data.org == "ISP Inc."


def test_lookup_invalid_ip(resolver):
    data = resolver.lookup("invalid_ip")
    assert data.country_code is None


def test_lookup_db_error(resolver):
    resolver.reader_city.city.side_effect = Exception("DB Error")
    data = resolver.lookup("1.1.1.1")
    # Should handle gracefully
    assert data.country_code is None


@pytest.mark.asyncio
async def test_download_db_trigger():
    # Test if download is triggered when files missing
    GeoIPResolver._instance = None

    with (
        patch(
            "configstream.geoip.Path.exists", side_effect=[False, False, False, False]
        ),
        patch("configstream.geoip.GeoIPResolver._download_db_async") as mock_download,
        patch("asyncio.create_task") as mock_create_task,
    ):
        # Mock the download to be a coroutine
        mock_download.return_value = AsyncMock()

        GeoIPResolver()

        # Check that create_task was called with the coroutine
        mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_download_db_execution(tmp_path):
    GeoIPResolver._instance = None

    # Mock to prevent __init__ from triggering download
    with (
        patch("configstream.geoip.Path.exists", return_value=True),
        patch("geoip2.database.Reader"),
    ):
        resolver = GeoIPResolver()  # __init__ won't trigger download

    # Now test the download method directly
    with patch("asyncio.create_subprocess_exec") as mock_proc:
        # Mock the process object
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=None)
        mock_proc.return_value = mock_process

        # Manually call download
        await resolver._download_db_async(tmp_path)
        # Should download 2 files (City and ASN)
        assert mock_proc.call_count == 2
