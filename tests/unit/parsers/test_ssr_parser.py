"""Tests for SSR parser."""

import pytest
from configstream.parsers.ssr import parse_ssr
from configstream.models import Proxy
import base64


def test_parse_ssr_valid():
    # ssr://host:port:protocol:method:obfs:base64pass/?obfsparam=base64&protoparam=base64&remarks=base64&group=base64
    # host=1.1.1.1, port=1234, protocol=origin, method=aes-128-ctr, obfs=plain, pass=test

    # Construct config
    # 1.1.1.1:1234:origin:aes-128-ctr:plain:dGVzdA==
    base = "1.1.1.1:1234:origin:aes-128-ctr:plain:dGVzdA=="
    # /?remarks=cmVtYXJr
    suffix = "/?remarks=cmVtYXJr&group=Z3JvdXA="

    ssr_link = "ssr://" + base64.urlsafe_b64encode((base + suffix).encode()).decode()

    proxy = parse_ssr(ssr_link)
    assert proxy is not None
    assert proxy.address == "1.1.1.1"
    assert proxy.port == 1234
    assert proxy.protocol == "ssr"
    assert "ssr" in proxy.config
    assert "remarks" in proxy.config.lower() or "remarks" in str(proxy.details)


def test_parse_ssr_invalid_base64():
    proxy = parse_ssr("ssr://invalid_base64!!!")
    assert proxy is None


def test_parse_ssr_invalid_format():
    # Decodes to something without enough colons
    # "test"
    ssr_link = "ssr://" + base64.urlsafe_b64encode(b"test").decode()
    proxy = parse_ssr(ssr_link)
    assert proxy is None


def test_parse_ssr_invalid_port():
    # Port is not int
    base = "1.1.1.1:abc:origin:aes-128-ctr:plain:dGVzdA=="
    ssr_link = "ssr://" + base64.urlsafe_b64encode(base.encode()).decode()
    proxy = parse_ssr(ssr_link)
    assert proxy is None


def test_parse_ssr_padding_fix():
    # Base64 with missing padding
    base = "1.1.1.1:1234:origin:aes-128-ctr:plain:dGVzdA"  # missing ==
    # encode it
    encoded = base64.urlsafe_b64encode(base.encode()).decode().rstrip("=")
    ssr_link = "ssr://" + encoded

    proxy = parse_ssr(ssr_link)
    assert proxy is not None
    assert proxy.address == "1.1.1.1"


def test_parse_ssr_params():
    # Test params parsing
    base = "1.1.1.1:1234:origin:aes-128-ctr:plain:dGVzdA=="
    # obfsparam=test
    suffix = "/?obfsparam=" + base64.urlsafe_b64encode(b"test").decode()
    ssr_link = "ssr://" + base64.urlsafe_b64encode((base + suffix).encode()).decode()

    proxy = parse_ssr(ssr_link)
    assert proxy is not None
    assert "obfsparam" in proxy.details.get("params", {})
    assert proxy.details["params"]["obfsparam"] == "test"


def test_parse_ssr_not_ssr_protocol():
    # Just to be safe, though usage implies it is called with ssr://
    proxy = parse_ssr("http://test.com")
    assert proxy is None
