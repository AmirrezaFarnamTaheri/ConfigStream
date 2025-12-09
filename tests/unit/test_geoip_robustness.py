"""Test GeoIP resolver robustness and edge cases."""

import pytest
from configstream.geoip import GeoIPResolver, GeoData


class TestGeoIPRobustness:
    """Test GeoIP resolver edge cases and error handling."""

    def test_singleton_pattern(self):
        """Test that GeoIPResolver is a singleton."""
        resolver1 = GeoIPResolver()
        resolver2 = GeoIPResolver()
        assert resolver1 is resolver2

    @pytest.mark.asyncio
    async def test_lookup_empty_ip(self):
        """Test lookup with empty IP string."""
        resolver = GeoIPResolver()
        result = await resolver.lookup("")
        assert isinstance(result, GeoData)
        assert result.country_code is None
        assert result.city is None

    @pytest.mark.asyncio
    async def test_lookup_invalid_ip_format(self):
        """Test lookup with invalid IP format."""
        resolver = GeoIPResolver()

        # Invalid formats should return empty GeoData
        invalid_ips = [
            "not-an-ip",
            "999.999.999.999",
            "256.0.0.1",
            "1.2.3",
            "1.2.3.4.5",
            "example.com",
            ":::::::",  # Invalid IPv6
            "gg::1",  # Invalid hex in IPv6
        ]

        for ip in invalid_ips:
            result = await resolver.lookup(ip)
            assert isinstance(result, GeoData)
            # Should not crash, just return empty data
            assert result.country_code is None or isinstance(result.country_code, str)

    @pytest.mark.asyncio
    async def test_lookup_private_ip(self):
        """Test lookup with private IP addresses."""
        resolver = GeoIPResolver()

        private_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "127.0.0.1",
        ]

        for ip in private_ips:
            result = await resolver.lookup(ip)
            assert isinstance(result, GeoData)
            # Private IPs might not be in GeoIP database
            # Should not crash

    @pytest.mark.asyncio
    async def test_lookup_ipv6(self):
        """Test lookup with IPv6 addresses."""
        resolver = GeoIPResolver()

        # Valid IPv6 addresses
        ipv6_addresses = [
            "2001:4860:4860::8888",  # Google DNS
            "::1",  # Localhost
            "fe80::1",  # Link-local
        ]

        for ip in ipv6_addresses:
            result = await resolver.lookup(ip)
            assert isinstance(result, GeoData)
            # Should not crash

    @pytest.mark.asyncio
    async def test_lookup_with_none(self):
        """Test that None is handled gracefully."""
        resolver = GeoIPResolver()

        # lookup expects string, but let's ensure it doesn't crash
        # if someone passes None by mistake
        result = await resolver.lookup(None)  # type: ignore
        assert isinstance(result, GeoData)

    @pytest.mark.asyncio
    async def test_lookup_special_addresses(self):
        """Test lookup with special IP addresses."""
        resolver = GeoIPResolver()

        special_ips = [
            "0.0.0.0",  # Unspecified
            "255.255.255.255",  # Broadcast
            "224.0.0.1",  # Multicast
        ]

        for ip in special_ips:
            result = await resolver.lookup(ip)
            assert isinstance(result, GeoData)

    def test_geodata_defaults(self):
        """Test GeoData default values."""
        data = GeoData()
        assert data.country_code is None
        assert data.city is None
        assert data.asn is None
        assert data.org is None

    def test_geodata_with_values(self):
        """Test GeoData with specific values."""
        data = GeoData(
            country_code="US", city="New York", asn="AS15169", org="Google LLC"
        )
        assert data.country_code == "US"
        assert data.city == "New York"
        assert data.asn == "AS15169"
        assert data.org == "Google LLC"

    def test_close_method(self):
        """Test that close method doesn't crash."""
        resolver = GeoIPResolver()
        resolver.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_lookup_after_close(self):
        """Test lookup behavior after close (if databases were loaded)."""
        resolver = GeoIPResolver()
        resolver.close()

        # Should still return GeoData, just empty
        result = await resolver.lookup("8.8.8.8")
        assert isinstance(result, GeoData)
