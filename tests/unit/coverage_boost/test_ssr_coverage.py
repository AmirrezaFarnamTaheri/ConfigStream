
import pytest
from configstream.parsers.ssr import parse_ssr
from configstream.models import Proxy

def test_parse_ssr_valid():
    # ssr://server:port:protocol:method:obfs:password_b64/?obfsparam=...
    # base64(server:port:protocol:method:obfs:password_base64/?params)

    # Example: 1.1.1.1:443:origin:aes-256-cfb:plain:cGFzc3dvcmQ
    # cGFzc3dvcmQ = "password"
    raw = "ssr://MS4xLjEuMTo0NDM6b3JpZ2luOmFlcy0yNTYtY2ZiOnBsYWluOmNHRnpjM2R2Y21R"

    proxy = parse_ssr(raw)
    assert proxy is not None
    assert proxy.protocol == "ssr"
    assert proxy.address == "1.1.1.1"
    assert proxy.port == 443
    # Mapped to 'cipher'
    assert proxy.details["cipher"] == "aes-256-cfb"
    assert proxy.details["protocol"] == "origin"
    assert proxy.details["obfs"] == "plain"
    assert proxy.details["password"] == "password"

def test_parse_ssr_invalid_b64():
    proxy = parse_ssr("ssr://Invalid!!!")
    assert proxy is None

def test_parse_ssr_missing_fields():
    # Malformed decoded string
    # "1.1.1.1:443" (missing other parts) -> B64: MS4xLjEuMTo0NDM=
    proxy = parse_ssr("ssr://MS4xLjEuMTo0NDM=")
    assert proxy is None

def test_parse_ssr_legacy_params():
    # Test with parameters /?obfsparam=...
    # 1.1.1.1:443:origin:aes-256-cfb:plain:cGFzc3dvcmQ/?obfsparam=b2JmczEyMw==&protoparam=cHJvdG8xMjM=
    # b2JmczEyMw== -> obfs123
    # cHJvdG8xMjM= -> proto123

    # B64 of whole string
    raw_inner = "1.1.1.1:443:origin:aes-256-cfb:plain:cGFzc3dvcmQ/?obfsparam=b2JmczEyMw==&protoparam=cHJvdG8xMjM="
    import base64
    b64 = base64.urlsafe_b64encode(raw_inner.encode()).decode()

    proxy = parse_ssr(f"ssr://{b64}")
    assert proxy is not None

    params = proxy.details["params"]
    # Check for parameters flexibly
    obfs_found = False
    proto_found = False

    if "obfs_param" in params and params["obfs_param"] == "obfs123":
        obfs_found = True
    elif "obfsparam" in params and params["obfsparam"] == "obfs123":
        obfs_found = True

    if "protocol_param" in params and params["protocol_param"] == "proto123":
        proto_found = True
    elif "protoparam" in params and params["protoparam"] == "proto123":
        proto_found = True

    assert obfs_found
    assert proto_found
