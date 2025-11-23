import pytest
from unittest.mock import patch, AsyncMock
from configstream.security.honeypot import is_honeypot


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
