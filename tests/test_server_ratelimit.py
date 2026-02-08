import pytest
import nest_asyncio
from fastapi.testclient import TestClient
from configstream.server import app

# Apply nest_asyncio to allow re-entrant loops which TestClient might trigger
nest_asyncio.apply()

# Use 'asyncio' mark to ensure pytest-asyncio handles loop management
@pytest.mark.asyncio
async def test_rate_limit_proxies_endpoint():
    # Use TestClient as context manager to properly handle startup/shutdown events
    with TestClient(app) as client:
        responses = []
        for _ in range(12):
            responses.append(client.get("/api/proxies"))

        rate_limited = [r for r in responses if r.status_code == 429]
        # In test environment, SlowAPI might use MemoryStorage which works.
        # But if get_remote_address fails (e.g. no request.client), it might fail open or error.
        # However, TestClient sets client host to "testclient".
        # We expect rate limiting to kick in.
        assert len(rate_limited) > 0

@pytest.mark.asyncio
async def test_rate_limit_subscribe_endpoint():
    with TestClient(app) as client:
        responses = []
        for _ in range(7):
            responses.append(client.get("/subscribe/base64"))

        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

@pytest.mark.asyncio
async def test_health_endpoint_no_limit():
    with TestClient(app) as client:
        responses = []
        for _ in range(20):
            responses.append(client.get("/health"))

        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) == 0
