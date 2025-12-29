import pytest
from configstream.utils.bool_parser import parse_bool
from configstream.models import Proxy
from configstream.converters.singbox import to_singbox_outbound

def test_parse_bool():
    assert parse_bool("true") is True
    assert parse_bool("True") is True
    assert parse_bool("1") is True
    assert parse_bool(1) is True
    assert parse_bool(True) is True

    assert parse_bool("false") is False
    assert parse_bool("False") is False
    assert parse_bool("0") is False
    assert parse_bool(0) is False
    assert parse_bool(False) is False
    assert parse_bool(None) is False
    assert parse_bool("") is False
    assert parse_bool("random") is False

def test_singbox_converter_bool_fix():
    # Test Hysteria2
    p = Proxy(
        config="",
        id="test_id",
        protocol="hysteria2",
        address="1.2.3.4",
        port=443,
        details={
            "password": "pass",
            "skip_cert_verify": "false"  # String "false"
        }
    )
    out = to_singbox_outbound(p)
    assert out["tls"]["insecure"] is False, "Should be False for string 'false'"

    p.details["skip_cert_verify"] = "true"
    out = to_singbox_outbound(p)
    assert out["tls"]["insecure"] is True, "Should be True for string 'true'"

    # Test TUIC
    p2 = Proxy(
        config="",
        id="test_id_2",
        protocol="tuic",
        address="1.2.3.4",
        port=443,
        uuid="123e4567-e89b-12d3-a456-426614174000",
        details={
            "password": "pass",
            "allowInsecure": "0"
        }
    )
    out2 = to_singbox_outbound(p2)
    assert out2["tls"]["insecure"] is False, "Should be False for string '0'"
