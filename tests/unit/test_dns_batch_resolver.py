# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from configstream.dns_batch_resolver import BatchDNSResolver


@pytest.fixture
def resolver():
    # We patch aiodns to prevent actual initialization issues
    with patch("aiodns.DNSResolver"):
        return BatchDNSResolver()


@pytest.mark.asyncio
async def test_resolve_batch_success(resolver):
    domains = ["example.com", "google.com"]

    # Mock aiodns.DNSResolver
    mock_dns = MagicMock()
    # Mock query response
    # result is a list of objects with .host attribute
    res_example = MagicMock()
    res_example.host = "1.2.3.4"

    res_google = MagicMock()
    res_google.host = "8.8.8.8"

    future_example = asyncio.Future()
    future_example.set_result([res_example])

    future_google = asyncio.Future()
    future_google.set_result([res_google])

    # query returns a Future
    mock_dns.query.side_effect = [future_example, future_google]

    resolver.resolver = mock_dns  # Set the instance attribute directly

    results = await resolver.resolve(domains)

    assert results["example.com"] == "1.2.3.4"
    assert results["google.com"] == "8.8.8.8"


@pytest.mark.asyncio
async def test_resolve_batch_empty(resolver):
    resolver.resolver = MagicMock()
    results = await resolver.resolve([])
    assert results == {}


@pytest.mark.asyncio
async def test_resolve_batch_failures(resolver):
    domains = ["fail.com"]

    mock_dns = MagicMock()
    future_fail = asyncio.Future()
    future_fail.set_exception(Exception("DNS Error"))
    mock_dns.query.return_value = future_fail

    resolver.resolver = mock_dns
    results = await resolver.resolve(domains)

    assert "fail.com" not in results
