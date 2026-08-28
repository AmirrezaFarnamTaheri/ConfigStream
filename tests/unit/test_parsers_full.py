# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.parsers.generic import (
    parse_generic_url_scheme,
)
from configstream.parsers.ssr import parse_ssr
from configstream.parsers.trojan import parse_trojan
from configstream.parsers.vless import parse_vless
from configstream.parsers.vmess import parse_vmess
import base64
import json


def test_parse_generic_fallback():
    # Invalid line
    try:
        p = parse_generic_url_scheme("invalid line")
        assert p is None
    except ValueError:
        pass


def test_parse_ssr_invalid():
    p = parse_ssr("ssr://invalid")
    assert p is None


def test_parse_trojan_valid():
    p = parse_trojan("trojan://password@1.1.1.1:443?sni=example.com#Test")
    assert p is not None
    assert p.protocol == "trojan"
    assert p.address == "1.1.1.1"


def test_parse_vless_valid():
    p = parse_vless(
        "vless://123e4567-e89b-12d3-a456-426614174000@1.1.1.1:443?encryption=none&security=tls&sni=example.com#Test"
    )
    assert p is not None
    assert p.protocol == "vless"


def test_parse_vmess_valid():
    # vmess is typically base64 encoded json
    v_obj = {
        "v": "2",
        "ps": "Test",
        "add": "1.1.1.1",
        "port": 443,
        "id": "uuid",
        "aid": 0,
        "net": "ws",
        "type": "none",
        "host": "example.com",
        "path": "/path",
        "tls": "tls",
    }
    b64 = base64.b64encode(json.dumps(v_obj).encode()).decode()
    uri = f"vmess://{b64}"

    p = parse_vmess(uri)
    assert p is not None
    assert p.protocol == "vmess"
    assert p.address == "1.1.1.1"
    assert p.uuid == "uuid"
    assert p.details["net"] == "ws"


def test_parse_vmess_details_is_schema_compliant():
    """Regression for run 33020481885: vmess_details must satisfy
    schema/proxy.schema.json #$defs/vmess_details (additionalProperties: false,
    requires uuid). The legacy URI keys (add, id, port, ps, v, scy, encrypt)
    must not leak into details; ``id`` is remapped to ``uuid`` and ``scy`` to
    ``security``.
    """
    import uuid as _uuid

    v4 = str(_uuid.uuid4())
    v_obj = {
        "v": "2",
        "ps": "Schema VMess",
        "add": "93.184.216.34",
        "port": 443,
        "id": v4,
        "aid": 0,
        "net": "ws",
        "type": "none",
        "host": "example.com",
        "path": "/v2",
        "tls": "tls",
        "scy": "auto",
        "fp": "chrome",
        "alpn": ["h2", "http/1.1"],
        "servicename": "grpc svc",
        "allowInsecure": False,
        "skip_cert_verify": False,
    }
    b64 = base64.b64encode(json.dumps(v_obj).encode()).decode()
    uri = f"vmess://{b64}"

    p = parse_vmess(uri)
    assert p is not None
    # Legacy keys must NOT appear in details
    for forbidden in ("add", "port", "id", "ps", "v", "scy", "encrypt"):
        assert forbidden not in p.details, (
            f"legacy key {forbidden!r} leaked into details: {p.details}"
        )
    # id must be remapped to uuid (required by vmess_details schema)
    assert p.details["uuid"] == v4
    # scy must be remapped to security
    assert p.details["security"] == "auto"
    # Other valid vmess_details keys still present
    assert p.details["aid"] == 0
    assert p.details["net"] == "ws"
    assert p.details["type"] == "none"
    assert p.details["host"] == "example.com"
    assert p.details["path"] == "/v2"
    assert p.details["fp"] == "chrome"
    assert p.details["alpn"] == ["h2", "http/1.1"]
    assert p.details["grpc_service_name"] == "grpc svc"

    # End-to-end: feed it through the published-artifact schema validator
    from scripts.validate_pages_artifact import _validate_proxies

    proxy = {
        "config": uri,
        "protocol": p.protocol,
        "address": p.address,
        "port": p.port,
        "uuid": p.uuid,
        "details": p.details,
        "process": "native",
    }
    errors = _validate_proxies([proxy], "proxies.json")
    assert errors == [], f"schema violations: {errors}"
