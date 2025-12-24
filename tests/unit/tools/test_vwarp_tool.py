import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from configstream.tools.vwarp import VwarpTool


@pytest.mark.asyncio
async def test_vwarp_is_available():
    with patch("shutil.which", return_value="/usr/bin/vwarp"):
        tool = VwarpTool()
        assert await tool.is_available()

    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.exists", return_value=False),
    ):
        tool = VwarpTool()
        assert not await tool.is_available()


@pytest.mark.asyncio
async def test_scan_endpoints():
    tool = VwarpTool()
    tool.is_available = AsyncMock(return_value=True)
    tool.binary = "vwarp"

    # Mock subprocess
    process_mock = AsyncMock()
    # Output: "162.159.192.10:2408 - 150ms\n[2001:db8::1]:2408 - 100ms"
    process_mock.communicate.return_value = (
        b"162.159.192.10:2408 - 150ms\n[2001:db8::1]:2408 - 100ms",
        b"",
    )

    with patch("asyncio.create_subprocess_exec", return_value=process_mock):
        eps = await tool.scan_endpoints()
        assert len(eps) == 2
        assert ("162.159.192.10", 2408) in eps
        assert ("2001:db8::1", 2408) in eps


@pytest.mark.asyncio
async def test_generate_masque_config():
    tool = VwarpTool()
    tool.is_available = AsyncMock(return_value=True)

    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b'{"type": "wireguard"}', b"")

    with patch("asyncio.create_subprocess_exec", return_value=process_mock):
        cfg = await tool.generate_masque_config()
        assert cfg["type"] == "wireguard"
