import pytest
from unittest.mock import MagicMock, patch
from configstream.geoip import GeoIPResolver, GeoData


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


def test_download_db_trigger():
    # Test if download is triggered when files missing
    GeoIPResolver._instance = None

    with (
        patch(
            "configstream.geoip.Path.exists", side_effect=[False, False, False, False]
        ),
        patch("configstream.geoip.GeoIPResolver._download_db") as mock_download,
    ):

        GeoIPResolver()
        mock_download.assert_called_once()


def test_download_db_execution(tmp_path):
    GeoIPResolver._instance = None

    # Mock subprocess to simulate download
    with patch("subprocess.run") as mock_run:
        resolver = GeoIPResolver()  # Mocks above will handle init
        # Manually call download
        resolver._download_db(tmp_path)
        assert mock_run.call_count == 2  # 2 files
