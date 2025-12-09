import pytest
from unittest.mock import MagicMock, patch
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


@pytest.mark.asyncio
async def test_lookup_valid_ip(resolver):
    resolver.reader_city = MagicMock()
    resolver.reader_city.city.return_value.country.iso_code = "US"
    resolver.reader_city.city.return_value.city.name = "New York"

    resolver.reader_asn = MagicMock()
    resolver.reader_asn.asn.return_value.autonomous_system_number = 12345
    resolver.reader_asn.asn.return_value.autonomous_system_organization = "ISP Inc."

    data = await resolver.lookup("1.1.1.1")

    assert data.country_code == "US"
    assert data.city == "New York"
    assert data.asn == "12345"
    assert data.org == "ISP Inc."


@pytest.mark.asyncio
async def test_lookup_invalid_ip(resolver):
    data = await resolver.lookup("invalid_ip")
    assert data.country_code is None


@pytest.mark.asyncio
async def test_lookup_db_error(resolver):
    resolver.reader_city.city.side_effect = Exception("DB Error")
    data = await resolver.lookup("1.1.1.1")
    # Should handle gracefully
    assert data.country_code is None
