
import pytest
import ipaddress
from src.configstream.security.blocklist import BlocklistManager, CACHE_FILE, HONEYPOT_PORTS, HONEYPOT_ASNS
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_blocklist_singleton():
    b1 = BlocklistManager()
    b2 = BlocklistManager()
    assert b1 is b2

    # Reset for tests
    b1.blocked_networks = set()

@pytest.mark.asyncio
async def test_update_success(tmp_path):
    # Mock aiofiles.open for writing is tricky with async context managers.
    # But the error says "a bytes-like object is required, not 'AsyncMock'".
    # This is because `await f.write(content)` expects bytes.
    # `resp.content` is `b"..."`.
    # But when we mock `aiofiles.open`, the `f` object's write method is a mock.
    # Wait, I am NOT mocking aiofiles in `test_update_success`. I am using real file.
    # BUT I am patching `httpx.AsyncClient.get`.
    # And patching `CACHE_FILE`.
    # So `await f.write(content)` writes to the real file at `tmp_path / "firehol.netset"`.
    # The error `Failed to update blocklist: a bytes-like object is required, not 'AsyncMock'` came from `update` catching exception.
    # Why did it raise TypeError?
    # `resp.content = b"..."`
    # `content = resp.content` -> content is bytes.
    # `await f.write(content)` -> write bytes to file.
    # Wait, `resp` is `mock_resp`. `mock_resp.content` is set to bytes.

    # Ah! `mock_get.return_value.__aenter__.return_value = mock_resp`.
    # This mocks `async with client.get(...) as resp`??
    # No, usage is `resp = await client.get(...)`. Not context manager for response.
    # `async with httpx.AsyncClient() as client:`
    # So `client` is the result of `__aenter__`.
    # `client.get` is a method.
    # So `mock_get` patches `httpx.AsyncClient.get`.
    # But `AsyncClient` is instantiated in `async with`.
    # `patch("httpx.AsyncClient")` would mock the class.
    # `patch("httpx.AsyncClient.get")` mocks the method on the class?
    # Yes.
    # But `client` is an instance.

    # Correct way to mock `httpx.AsyncClient`:
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"1.2.3.0/24\n# Comment"
        mock_client.get.return_value = mock_resp

        with patch("src.configstream.security.blocklist.CACHE_FILE", tmp_path / "firehol.netset"):
            bm = BlocklistManager()
            await bm.update()

            assert len(bm.blocked_networks) == 1
            assert ipaddress.ip_network("1.2.3.0/24") in bm.blocked_networks

@pytest.mark.asyncio
async def test_update_failure_loads_cache(tmp_path):
    cache_path = tmp_path / "firehol.netset"
    cache_path.write_text("5.5.5.0/24")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Net error")

        with patch("src.configstream.security.blocklist.CACHE_FILE", cache_path):
            bm = BlocklistManager()
            bm.blocked_networks = set()
            await bm.update()

            assert len(bm.blocked_networks) == 1
            assert ipaddress.ip_network("5.5.5.0/24") in bm.blocked_networks

@pytest.mark.asyncio
async def test_load_no_file():
    with patch("src.configstream.security.blocklist.CACHE_FILE", MagicMock(exists=lambda: False)):
        bm = BlocklistManager()
        bm.blocked_networks = set()
        await bm.load()
        assert len(bm.blocked_networks) == 0

@pytest.mark.asyncio
async def test_load_with_bad_lines(tmp_path):
    cache_path = tmp_path / "firehol.netset"
    cache_path.write_text("1.1.1.1/32\nBADLINE\n# Comment\n2.2.2.2/32")

    with patch("src.configstream.security.blocklist.CACHE_FILE", cache_path):
        bm = BlocklistManager()
        bm.blocked_networks = set()
        await bm.load()
        assert len(bm.blocked_networks) == 2

def test_is_blocked():
    bm = BlocklistManager()
    bm.blocked_networks = {ipaddress.ip_network("10.0.0.0/8")}

    assert bm.is_blocked("10.1.1.1") is True
    assert bm.is_blocked("11.1.1.1") is False
    assert bm.is_blocked("not-an-ip") is False

    bm.blocked_networks = set()
    assert bm.is_blocked("10.1.1.1") is False

def test_is_suspicious_port():
    bm = BlocklistManager()
    for port in HONEYPOT_PORTS:
        assert bm.is_suspicious_port(port) is True
    assert bm.is_suspicious_port(80) is False

def test_is_honeypot():
    bm = BlocklistManager()
    for port in HONEYPOT_PORTS:
        assert bm.is_honeypot("1.1.1.1", port) is True

    for asn in HONEYPOT_ASNS:
        assert bm.is_honeypot("1.1.1.1", 80, asn) is True

    assert bm.is_honeypot("1.1.1.1", 80, "AS_GOOD") is False
