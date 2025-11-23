
import pytest
from src.configstream.parsers.openvpn import parse_openvpn
from src.configstream.models import Proxy
from unittest.mock import patch

def test_parse_openvpn_not_client():
    assert parse_openvpn("server\nremote 1.1.1.1 1194") is None

def test_parse_openvpn_no_remote():
    assert parse_openvpn("client\ndev tun") is None

def test_parse_openvpn_valid_remote_simple():
    config = """
client
dev tun
remote 1.2.3.4 1194
    """
    p = parse_openvpn(config)
    assert p.protocol == "openvpn"
    assert p.address == "1.2.3.4"
    assert p.port == 1194
    assert p.details["transport"] == "udp" # default

def test_parse_openvpn_valid_remote_connection_block():
    config = """
client
<connection>
remote 5.6.7.8 443 tcp
</connection>
    """
    p = parse_openvpn(config)
    assert p.address == "5.6.7.8"
    assert p.port == 443

def test_parse_openvpn_invalid_port():
    config = """
client
remote 1.2.3.4 abc
    """
    # re.findall uses (\d+) so it only matches digits.
    # If "abc", regex won't match "remote 1.2.3.4 abc" with `remote\s+(\S+)\s+(\d+)`.
    # So remotes will be empty -> returns None.
    # To trigger ValueError in int(), regex must match digits but int() fail? Impossible?
    # Unless integer matches regex but is invalid for int()? No.
    # (\d+) matches digits. int() handles any digits string.
    # Overflow? int() handles arbitrarily large integers in Python.
    # So lines 29-31 might be unreachable logic if regex enforces digits?
    # Let's verify.
    assert parse_openvpn(config) is None

def test_parse_openvpn_explicit_proto():
    config = """
client
remote 1.1.1.1 1194
proto tcp
    """
    p = parse_openvpn(config)
    assert p.details["transport"] == "tcp"

def test_parse_openvpn_exception():
    with patch("re.findall") as mock_findall:
        mock_findall.side_effect = Exception("Boom")
        assert parse_openvpn("client") is None
