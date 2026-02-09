import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from configstream.security.censorship import CensorshipLab


@pytest.fixture
def lab():
    return CensorshipLab()


def test_initialization(lab):
    assert lab.results == {}
    assert len(lab.SENSITIVE_SITES) > 0


@pytest.mark.asyncio
async def test_check_connectivity_success(lab):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        results = await lab.check_connectivity(["https://example.com"])

    assert "https://example.com" in results
    assert results["https://example.com"]["status"] == "reachable"
    assert results["https://example.com"]["code"] == 200


@pytest.mark.asyncio
async def test_check_connectivity_failure(lab):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        results = await lab.check_connectivity(["https://example.com"])

    assert "https://example.com" in results
    assert results["https://example.com"]["status"] == "blocked"


def test_report_generation(lab):
    lab.results = {"site1": {"status": "reachable"}, "site2": {"status": "blocked"}}

    report = lab.get_censorship_report()

    assert report["total_sites"] == 2
    assert report["blocked_count"] == 1
    assert report["censorship_score"] == 50.0
