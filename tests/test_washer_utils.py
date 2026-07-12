import base64

from configstream.intelligence.washer.utils import make_entry


def _key(byte: int) -> str:
    return base64.b64encode(bytes([byte]) * 32).decode("ascii")


def test_make_entry_valid():
    key = _key(1)
    proxy = make_entry("test", key, "1.1.1.1", None, [0, 0, 0])
    assert proxy is not None
    assert proxy.protocol == "wireguard"
    assert proxy.details["private_key"] == key
    assert proxy.details["local_address"].startswith("172.16.")


def test_make_entry_short_key():
    assert make_entry("test", "short", "1.1.1.1", None, [0, 0, 0]) is None


def test_make_entry_empty_key():
    assert make_entry("test", "", "1.1.1.1", None, [0, 0, 0]) is None


def test_make_entry_unique_ip():
    p1 = make_entry("t1", _key(1), "1.1.1.1", None, [0, 0, 0])
    p2 = make_entry("t2", _key(2), "1.1.1.1", None, [0, 0, 0])
    assert p1 is not None and p2 is not None
    assert p1.details["local_address"] != p2.details["local_address"]
