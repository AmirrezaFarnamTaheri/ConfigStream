import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.security.utls_wrapper import ensure_binary_async, test_tls_fingerprint as verify_tls_fingerprint

@pytest.mark.asyncio
async def test_ensure_binary_async_success():
    with patch("shutil.which", return_value="/usr/bin/go"),          patch("pathlib.Path.exists", side_effect=[False, True]),          patch("configstream.security.utls_wrapper._run_cmd", new_callable=AsyncMock, return_value=True):
        result = await ensure_binary_async()
        assert result is True

@pytest.mark.asyncio
async def test_ensure_binary_async_fail_no_go():
    with patch("pathlib.Path.exists", return_value=False),          patch("shutil.which", return_value=None):
        result = await ensure_binary_async()
        assert result is False

@pytest.mark.asyncio
async def test_verify_tls_fingerprint_success():
    with patch("configstream.security.utls_wrapper.ensure_binary_async", new_callable=AsyncMock, return_value=True),          patch("configstream.security.utls_wrapper._verify_binary_checksum", return_value=True),          patch("asyncio.create_subprocess_exec") as mock_exec:

        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        result = await verify_tls_fingerprint("https://example.com", "1.2.3.4:443")
        assert result is True

@pytest.mark.asyncio
async def test_verify_tls_fingerprint_fail():
    with patch("configstream.security.utls_wrapper.ensure_binary_async", new_callable=AsyncMock, return_value=True),          patch("configstream.security.utls_wrapper._verify_binary_checksum", return_value=True),          patch("asyncio.create_subprocess_exec") as mock_exec:

        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        result = await verify_tls_fingerprint("https://example.com", "1.2.3.4:443")
        assert result is False
