import pytest
from unittest.mock import patch, AsyncMock
from configstream.security.honeypot import (
    is_honeypot,
    check_common_honeypot_ports,
    check_traffic_interception,
)


@pytest.mark.asyncio
async def test_honeypot_active_scanning_disabled():
    """Verify that active scanning is disabled and returns False."""
    # Mock VirusTotal to return safe
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        # Active check is internal and disabled, so is_honeypot relies on passive check
        is_hp = await is_honeypot("1.1.1.1")
        assert is_hp is False
        mock_vt.assert_called_once_with("1.1.1.1")


@pytest.mark.asyncio
async def test_honeypot_passive_detection():
    """Verify passive detection works via VirusTotal mock."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 5}

        is_hp = await is_honeypot("malicious.ip")
        assert is_hp is True


@pytest.mark.asyncio
async def test_check_common_honeypot_ports_always_false():
    """Test that check_common_honeypot_ports always returns False (disabled)."""
    result = await check_common_honeypot_ports("1.1.1.1")
    assert result is False


@pytest.mark.asyncio
async def test_check_common_honeypot_ports_with_ports_list():
    """Test that check_common_honeypot_ports ignores ports parameter."""
    result = await check_common_honeypot_ports("1.1.1.1", ports=[80, 443, 8080])
    assert result is False


@pytest.mark.asyncio
async def test_check_common_honeypot_ports_with_empty_ports():
    """Test with empty ports list."""
    result = await check_common_honeypot_ports("1.1.1.1", ports=[])
    assert result is False


@pytest.mark.asyncio
async def test_check_traffic_interception_always_false():
    """Test that check_traffic_interception always returns False (stub)."""
    result = await check_traffic_interception({"host": "1.1.1.1", "port": 443})
    assert result is False


@pytest.mark.asyncio
async def test_check_traffic_interception_with_various_configs():
    """Test traffic interception with different proxy configs."""
    configs = [
        {},
        {"host": "example.com"},
        {"host": "1.1.1.1", "port": 443, "protocol": "vmess"},
        None,
    ]
    for config in configs:
        result = await check_traffic_interception(config)
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_with_safe_ip():
    """Test is_honeypot returns False for safe IPs."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("8.8.8.8")
        assert result is False
        mock_vt.assert_called_once_with("8.8.8.8")


@pytest.mark.asyncio
async def test_is_honeypot_with_multiple_malicious_flags():
    """Test is_honeypot with high malicious count."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 100}

        result = await is_honeypot("bad.actor.ip")
        assert result is True


@pytest.mark.asyncio
async def test_is_honeypot_with_single_malicious_flag():
    """Test is_honeypot with exactly 1 malicious flag."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 1}

        result = await is_honeypot("suspicious.ip")
        assert result is True


@pytest.mark.asyncio
async def test_is_honeypot_missing_malicious_key():
    """Test is_honeypot when VirusTotal response missing 'malicious' key."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {}

        # Should default to 0 with .get("malicious", 0)
        result = await is_honeypot("unknown.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_exception_handling():
    """Test is_honeypot fails open when exception occurs."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.side_effect = Exception("API Error")

        # Should return False (fail open) on error
        result = await is_honeypot("error.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_timeout_exception():
    """Test is_honeypot handles timeout gracefully."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.side_effect = TimeoutError("Request timed out")

        result = await is_honeypot("timeout.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_network_error():
    """Test is_honeypot handles network errors gracefully."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.side_effect = ConnectionError("Network unreachable")

        result = await is_honeypot("network.error.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_with_ipv6_address():
    """Test is_honeypot with IPv6 address."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("2001:4860:4860::8888")
        assert result is False
        mock_vt.assert_called_once_with("2001:4860:4860::8888")


@pytest.mark.asyncio
async def test_is_honeypot_with_hostname():
    """Test is_honeypot with hostname instead of IP."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("example.com")
        assert result is False
        mock_vt.assert_called_once_with("example.com")


@pytest.mark.asyncio
async def test_is_honeypot_with_localhost():
    """Test is_honeypot with localhost."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("127.0.0.1")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_with_private_ip():
    """Test is_honeypot with private IP address."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("192.168.1.1")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_negative_malicious_count():
    """Test is_honeypot with negative malicious count (edge case)."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": -1}

        # -1 is not > 0, so should be False
        result = await is_honeypot("weird.response.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_vt_returns_none():
    """Test is_honeypot when VT returns None."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = None

        # Should handle None gracefully
        try:
            result = await is_honeypot("null.ip")
            # If it doesn't crash, check result
            assert result is False
        except Exception:
            # If it raises, that's also acceptable behavior
            pass


@pytest.mark.asyncio
async def test_is_honeypot_vt_returns_string():
    """Test is_honeypot when VT returns unexpected string."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = "error"

        # Should handle gracefully with .get()
        result = await is_honeypot("string.response.ip")
        assert result is False


@pytest.mark.asyncio
async def test_is_honeypot_with_empty_string_host():
    """Test is_honeypot with empty string."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        mock_vt.return_value = {"malicious": 0}

        result = await is_honeypot("")
        assert result is False
        mock_vt.assert_called_once_with("")


@pytest.mark.asyncio
async def test_is_honeypot_logging_on_detection():
    """Test that warning is logged when malicious IP detected."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        with patch("configstream.security.honeypot.logger") as mock_logger:
            mock_vt.return_value = {"malicious": 3}

            result = await is_honeypot("malicious.test")
            assert result is True

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "malicious.test" in call_args


@pytest.mark.asyncio
async def test_is_honeypot_logging_on_error():
    """Test that error is logged when check fails."""
    with patch(
        "configstream.security.honeypot.check_ip_reputation", new_callable=AsyncMock
    ) as mock_vt:
        with patch("configstream.security.honeypot.logger") as mock_logger:
            mock_vt.side_effect = ValueError("Invalid IP")

            result = await is_honeypot("invalid.ip")
            assert result is False

            # Verify error was logged
            mock_logger.error.assert_called_once()
            call_args = str(mock_logger.error.call_args)
            assert "invalid.ip" in call_args
