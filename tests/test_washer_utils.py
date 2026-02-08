import pytest
from configstream.intelligence.washer.utils import make_entry

def test_make_entry_valid():
    key = "a" * 44  # Mock key
    proxy = make_entry("test", key, "1.1.1.1", None, [0,0,0])
    assert proxy is not None
    assert proxy.protocol == "wireguard"
    assert proxy.details["private_key"] == key
    assert proxy.details["local_address"].startswith("172.16.")

def test_make_entry_short_key():
    assert make_entry("test", "short", "1.1.1.1", None, [0,0,0]) is None

def test_make_entry_empty_key():
    assert make_entry("test", "", "1.1.1.1", None, [0,0,0]) is None

def test_make_entry_unique_ip():
    key1 = "a" * 44
    key2 = "b" * 44
    p1 = make_entry("t1", key1, "1.1.1.1", None, [0,0,0])
    p2 = make_entry("t2", key2, "1.1.1.1", None, [0,0,0])
    assert p1.details["local_address"] != p2.details["local_address"]
