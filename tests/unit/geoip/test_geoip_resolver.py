from unittest.mock import MagicMock, patch

import pytest

from configstream.geoip import GeoData, GeoIPResolver


@pytest.mark.asyncio
async def test_geoip_lookup_invalid_ip():
    """Test lookup with invalid IP format"""
    resolver = GeoIPResolver()
    # Mock readers to ensure we don't hit FS
    resolver.reader_city = MagicMock()
    resolver.reader_asn = MagicMock()

    res = await resolver.lookup("invalid-ip")
    assert res.country_code is None
    assert res.asn is None


@pytest.mark.asyncio
async def test_geoip_lookup_valid_mock():
    """Test lookup logic with mocked DB response"""
    resolver = GeoIPResolver()

    mock_city = MagicMock()
    mock_city.country.iso_code = "US"
    mock_city.country.name = "United States"
    mock_city.city.name = "New York"
    resolver.reader_city = MagicMock()
    resolver.reader_city.city.return_value = mock_city

    mock_asn = MagicMock()
    mock_asn.autonomous_system_number = 12345
    mock_asn.autonomous_system_organization = "Test Org"
    resolver.reader_asn = MagicMock()
    resolver.reader_asn.asn.return_value = mock_asn

    res = await resolver.lookup("8.8.8.8")
    assert res.country_code == "US"
    assert res.city == "New York"
    assert res.asn == "12345"
    assert res.org == "Test Org"
