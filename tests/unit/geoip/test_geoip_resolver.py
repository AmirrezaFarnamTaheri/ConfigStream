# SPDX-License-Identifier: AGPL-3.0-or-later
import threading
from unittest.mock import MagicMock

import pytest

from configstream.geoip import GeoIPResolver


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


# ---------------------------------------------------------------------------
# close() null-out tests (P0-3 fix coverage)
# ---------------------------------------------------------------------------


def test_close_nulls_out_readers():
    """After close(), reader_city and reader_asn must be None (P0-3 fix)."""
    resolver = GeoIPResolver()
    mock_city = MagicMock()
    mock_asn = MagicMock()
    resolver.reader_city = mock_city
    resolver.reader_asn = mock_asn

    resolver.close()

    # Readers must be nulled so a concurrent _do_lookup call cannot call
    # .city()/.asn() on a closed reader.
    assert resolver.reader_city is None
    assert resolver.reader_asn is None
    # Underlying close() must have been called exactly once each.
    mock_city.close.assert_called_once()
    mock_asn.close.assert_called_once()


def test_close_is_idempotent():
    """Calling close() twice must not raise."""
    resolver = GeoIPResolver()
    resolver.reader_city = MagicMock()
    resolver.reader_asn = MagicMock()
    resolver.close()
    # Second call: readers are already None, should be a no-op.
    resolver.close()


@pytest.mark.asyncio
async def test_lookup_after_close_returns_empty():
    """A lookup after close() must return an empty GeoData, not raise."""
    resolver = GeoIPResolver()
    resolver.reader_city = MagicMock()
    resolver.reader_asn = MagicMock()
    resolver.close()

    result = await resolver.lookup("8.8.8.8")
    # No reader is present; lookup should return empty GeoData gracefully.
    assert result.country_code in (None, "XX", "Unknown (DB Missing)")


# ---------------------------------------------------------------------------
# Double-init race-condition test (P0-3 fix coverage)
# ---------------------------------------------------------------------------


def test_singleton_is_thread_safe():
    """Multiple threads accessing GeoIPResolver() must get the same instance."""
    instances = []
    errors = []

    def get_instance():
        try:
            instances.append(GeoIPResolver())
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=get_instance) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors during concurrent init: {errors}"
    # All threads must have received the same singleton instance.
    first = instances[0]
    assert all(
        inst is first for inst in instances
    ), "GeoIPResolver singleton broken: multiple instances created"
