
import pytest
from configstream.security.blocklist import BlocklistManager
import ipaddress
import asyncio
from unittest.mock import patch, MagicMock

@pytest.fixture
def blocklist_manager():
    # Reset singleton state if needed or create new instance (it's singleton so strict reset is hard without access)
    # We can just clear the internal set for the test instance
    bm = BlocklistManager()
    # Reset state
    bm.blocked_networks = set()
    bm._v4_index = {}
    bm._v6_index = {}
    return bm

@pytest.mark.asyncio
async def test_blocklist_manager_initialization(blocklist_manager):
    assert isinstance(blocklist_manager.blocked_networks, set)

@pytest.mark.asyncio
async def test_blocklist_manager_load_logic(blocklist_manager, tmp_path):
    # Mock cache file
    cache_file = tmp_path / "firehol.netset"
    cache_file.write_text("1.1.1.0/24\n# comment\n2.2.2.2")

    # Patch CACHE_FILE path in the module
    with patch("configstream.security.blocklist.CACHE_FILE", cache_file):
        await blocklist_manager.load()

        assert blocklist_manager.is_blocked("1.1.1.5") is True
        assert blocklist_manager.is_blocked("2.2.2.2") is True
        assert blocklist_manager.is_blocked("3.3.3.3") is False

def test_blocklist_manager_is_blocked_manual(blocklist_manager):
    # Manually populate for unit test of checking logic
    net = ipaddress.ip_network("10.0.0.0/8")
    blocklist_manager.blocked_networks.add(net)

    # Rebuild index manually for test
    first_octet = int(net.network_address.packed[0])
    blocklist_manager._v4_index[first_octet] = {net}

    assert blocklist_manager.is_blocked("10.1.1.1") is True
    assert blocklist_manager.is_blocked("11.1.1.1") is False

def test_blocklist_manager_suspicious_port(blocklist_manager):
    assert blocklist_manager.is_suspicious_port(23) is True
    assert blocklist_manager.is_suspicious_port(2222) is False # Removed per comments
    assert blocklist_manager.is_suspicious_port(443) is False

def test_blocklist_manager_is_honeypot_deprecated(blocklist_manager):
    # Wraps is_suspicious_port
    assert blocklist_manager.is_honeypot("1.1.1.1", 23) is True
    assert blocklist_manager.is_honeypot("1.1.1.1", 443) is False
