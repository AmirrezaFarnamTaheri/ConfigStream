import pytest
from unittest.mock import MagicMock, patch
from configstream.parsers.shadowsocks import parse_ss
from configstream.security.rate_limiter import RateLimiter
from configstream.security.virus_total import check_ip_reputation

# --- Shadowsocks Parser Tests ---


def test_parse_ss_valid():
    uri = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:8388#Remarks"
    proxy = parse_ss(uri)
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8388
    assert proxy.details["method"] == "aes-256-gcm"
    assert proxy.details["password"] == "password"
    assert proxy.remarks == "Remarks"


def test_parse_ss_legacy():
    # SIP002
    uri = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMS4yLjMuNDo4Mzg4#Remarks"
    proxy = parse_ss(uri)
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8388
    assert proxy.details["method"] == "aes-256-gcm"
    assert proxy.details["password"] == "password"


def test_parse_ss_invalid():
    proxy = parse_ss("invalid://garbage")
    assert proxy is None


# --- Rate Limiter Tests ---


@pytest.mark.asyncio
async def test_rate_limiter_allow():
    limiter = RateLimiter(requests_per_second=10)
    # Manually set state to avoid timing issues
    # Ensure buckets exist
    if "host1" not in limiter.buckets:
        limiter.buckets["host1"] = {"tokens": 1.0, "last_update": 0}

    limiter.buckets["host1"]["last_update"] = 1000
    limiter.buckets["host1"]["tokens"] = 0

    with patch("configstream.security.rate_limiter.time") as mock_time:
        mock_time.return_value = 1001  # 1 second later
        assert await limiter.is_allowed("host1") is True


@pytest.mark.asyncio
async def test_rate_limiter_block():
    limiter = RateLimiter(requests_per_second=1)
    if "host1" not in limiter.buckets:
        limiter.buckets["host1"] = {"tokens": 1.0, "last_update": 0}

    limiter.buckets["host1"]["last_update"] = 1000
    limiter.buckets["host1"]["tokens"] = 0

    with patch("configstream.security.rate_limiter.time") as mock_time:
        mock_time.return_value = 1000.01  # 0.01s later
        assert await limiter.is_allowed("host1") is False


# --- VirusTotal Tests ---


class MockResponse:
    def __init__(self, status, data):
        self.status = status
        self._data = data

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_vt_ip_clean():
    mock_response = MockResponse(
        200, {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}}
    )

    with patch(
        "configstream.security.virus_total.aiohttp.ClientSession"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
            result = await check_ip_reputation("1.1.1.1")
            assert result["malicious"] == 0


@pytest.mark.asyncio
async def test_vt_ip_malicious():
    mock_response = MockResponse(
        200, {"data": {"attributes": {"last_analysis_stats": {"malicious": 5}}}}
    )

    with patch(
        "configstream.security.virus_total.aiohttp.ClientSession"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_response

        with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
            result = await check_ip_reputation("2.2.2.2")  # Unique IP
            assert result["malicious"] == 5


@pytest.mark.asyncio
async def test_vt_ip_error():
    with patch(
        "configstream.security.virus_total.aiohttp.ClientSession"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        # Simulate network error on get()
        mock_session.get.side_effect = Exception("Network Error")

        with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
            result = await check_ip_reputation("3.3.3.3")  # Unique IP
            assert result["malicious"] == 0
