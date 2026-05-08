# SPDX-License-Identifier: AGPL-3.0-or-later
"""Golden protocol-output fixtures for public protocol claims."""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from configstream.converters.clash import to_clash_proxy
from configstream.converters.singbox import to_singbox_outbound
from configstream.generators import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
)
from configstream.models import Proxy
from configstream.parsers import (
    parse_brook,
    parse_generic_url_scheme,
    parse_hysteria,
    parse_hysteria2,
    parse_juicity,
    parse_naive,
    parse_openvpn,
    parse_snell,
    parse_ss,
    parse_ss2022,
    parse_ssh,
    parse_ssr,
    parse_trojan,
    parse_tuic,
    parse_v2ray_json,
    parse_vless,
    parse_vmess,
    parse_wireguard,
    parse_xray,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_MATRIX = ROOT / "docs" / "protocol_matrix.json"
UUID = "123e4567-e89b-42d3-a456-426614174000"


def _proxy(protocol: str, **overrides: Any) -> Proxy:
    values: dict[str, Any] = {
        "config": f"{protocol}://fixture.example:443#fixture-{protocol}",
        "protocol": protocol,
        "address": "fixture.example",
        "port": 443,
        "uuid": UUID,
        "remarks": f"fixture-{protocol}",
        "country_code": "US",
        "is_working": True,
        "details": {},
    }
    values.update(overrides)
    return Proxy(**values)


GOLDEN_PROXIES: dict[str, Proxy] = {
    "vmess": _proxy("vmess", details={"tls": "tls", "sni": "fixture.example"}),
    "vless": _proxy("vless", details={"tls": "tls", "sni": "fixture.example"}),
    "shadowsocks": _proxy(
        "shadowsocks",
        config="ss://YWVzLTEyOC1nY206cGFzcw==@fixture.example:8388#fixture-ss",
        port=8388,
        uuid="",
        details={"method": "aes-128-gcm", "password": "pass"},
    ),
    "ss2022": _proxy(
        "ss2022",
        port=8389,
        uuid="",
        details={"method": "2022-blake3-aes-128-gcm", "password": "pass"},
    ),
    "ssr": _proxy(
        "ssr", uuid="pass", details={"method": "aes-128-gcm", "password": "pass"}
    ),
    "trojan": _proxy("trojan", uuid="pass", details={"tls": "tls"}),
    "hysteria": _proxy(
        "hysteria",
        uuid="pass",
        details={
            "auth_str": "pass",
            "up_mbps": 100,
            "down_mbps": 100,
            "sni": "fixture.example",
        },
    ),
    "hysteria2": _proxy(
        "hysteria2", uuid="pass", details={"password": "pass", "sni": "fixture.example"}
    ),
    "tuic": _proxy("tuic", details={"password": "pass", "sni": "fixture.example"}),
    "wireguard": _proxy(
        "wireguard",
        port=2408,
        uuid="",
        details={
            "private_key": "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E=",
            "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            "local_address": ["10.0.0.2/32"],
            "mtu": 1280,
        },
    ),
    "naive": _proxy(
        "naive",
        uuid="user",
        details={"username": "user", "password": "pass", "tls": True},
    ),
    "snell": _proxy("snell", uuid="pass", details={"password": "pass"}),
    "brook": _proxy("brook", uuid="pass", details={"password": "pass"}),
    "juicity": _proxy("juicity", details={"password": "pass"}),
    "xray": _proxy("xray"),
    "v2ray": _proxy("v2ray"),
    "ssh": _proxy("ssh", uuid="user", details={"password": "pass"}),
    "http": _proxy("http", uuid="user", details={"password": "pass"}),
    "socks4": _proxy("socks4"),
    "socks5": _proxy(
        "socks5", uuid="user", details={"username": "user", "password": "pass"}
    ),
    "openvpn": _proxy(
        "openvpn",
        config="client\nremote fixture.example 1194 udp\n<ca>\nfixture\n</ca>\n",
        port=1194,
        uuid="",
    ),
}

EXPECTED_SINGBOX_TYPES = {
    "vmess": "vmess",
    "vless": "vless",
    "shadowsocks": "shadowsocks",
    "ss2022": "shadowsocks",
    "trojan": "trojan",
    "hysteria": "hysteria",
    "hysteria2": "hysteria2",
    "tuic": "tuic",
    "wireguard": "wireguard",
    "naive": "naive",
    "ssh": "ssh",
    "http": "http",
    "socks4": "socks",
    "socks5": "socks",
}

EXPECTED_CLASH_TYPES = {
    "vmess": "vmess",
    "vless": "vless",
    "shadowsocks": "ss",
    "ss2022": "ss",
    "trojan": "trojan",
    "hysteria2": "hysteria2",
    "tuic": "tuic",
    "wireguard": "wireguard",
    "socks5": "socks5",
}


def _urlsafe_b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


PARSER_TO_FRONTEND_FIXTURES: dict[str, tuple[Any, str, str]] = {
    "vmess": (
        parse_vmess,
        "vmess://"
        + base64.b64encode(
            json.dumps(
                {
                    "v": "2",
                    "ps": "fixture-vmess",
                    "add": "fixture.example",
                    "port": "443",
                    "id": UUID,
                    "aid": "0",
                    "net": "tcp",
                    "type": "none",
                    "host": "",
                    "path": "",
                    "tls": "tls",
                }
            ).encode("utf-8")
        ).decode("ascii"),
        "vmess",
    ),
    "vless": (
        parse_vless,
        f"vless://{UUID}@fixture.example:443?security=tls&sni=fixture.example#fixture-vless",
        "vless",
    ),
    "shadowsocks": (
        parse_ss,
        "ss://YWVzLTEyOC1nY206cGFzcw==@fixture.example:8388#fixture-ss",
        "shadowsocks",
    ),
    "ss2022": (
        parse_ss2022,
        "ss2022://MjAyMi1ibGFrZTMtYWVzLTEyOC1nY206cGFzcw==@fixture.example:8389#fixture-ss2022",
        "ss2022",
    ),
    "ssr": (
        parse_ssr,
        "ssr://"
        + _urlsafe_b64(
            "fixture.example:8388:origin:aes-128-gcm:plain:"
            + _urlsafe_b64("pass")
            + "/?remarks="
            + _urlsafe_b64("fixture-ssr")
        ),
        "ssr",
    ),
    "trojan": (
        parse_trojan,
        "trojan://pass@fixture.example:443?sni=fixture.example#fixture-trojan",
        "trojan",
    ),
    "hysteria": (
        parse_hysteria,
        "hysteria://pass@fixture.example:443?up_mbps=100&down_mbps=100&sni=fixture.example#fixture-hysteria",
        "hysteria",
    ),
    "hysteria2": (
        parse_hysteria2,
        "hysteria2://pass@fixture.example:443?sni=fixture.example#fixture-hy2",
        "hysteria2",
    ),
    "tuic": (
        parse_tuic,
        f"tuic://{UUID}:pass@fixture.example:443?sni=fixture.example#fixture-tuic",
        "tuic",
    ),
    "wireguard": (
        parse_wireguard,
        "wireguard://fixture@fixture.example:2408?private_key=YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=&public_key=pub&address=10.0.0.2/32#fixture-wg",
        "wireguard",
    ),
    "naive": (
        parse_naive,
        "naive+https://user:pass@fixture.example:443#fixture-naive",
        "naive",
    ),
    "snell": (parse_snell, "snell://pass@fixture.example:443#fixture-snell", "snell"),
    "brook": (parse_brook, "brook://pass@fixture.example:9999#fixture-brook", "brook"),
    "juicity": (
        parse_juicity,
        "juicity://user:pass@fixture.example:443#fixture-juicity",
        "juicity",
    ),
    "xray": (parse_xray, f"xray://{UUID}@fixture.example:443#fixture-xray", "xray"),
    "v2ray": (
        parse_v2ray_json,
        json.dumps(
            {
                "outbounds": [
                    {
                        "protocol": "vmess",
                        "tag": "fixture-v2ray",
                        "settings": {
                            "vnext": [
                                {
                                    "address": "fixture.example",
                                    "port": 443,
                                    "users": [{"id": UUID, "alterId": 0}],
                                }
                            ]
                        },
                    }
                ]
            }
        ),
        "vmess",
    ),
    "ssh": (parse_ssh, "ssh://user:pass@fixture.example:22#fixture-ssh", "ssh"),
    "http": (
        parse_generic_url_scheme,
        "http://user:pass@fixture.example:8080#fixture-http",
        "http",
    ),
    "socks4": (
        parse_generic_url_scheme,
        "socks4://fixture.example:1080#fixture-socks4",
        "socks4",
    ),
    "socks5": (
        parse_generic_url_scheme,
        "socks5://user:pass@fixture.example:1080#fixture-socks5",
        "socks5",
    ),
    "openvpn": (
        parse_openvpn,
        "client\nremote fixture.example 1194 udp\n<ca>\nfixture\n</ca>\n",
        "openvpn",
    ),
}

MALFORMED_PARSER_FIXTURES: dict[str, tuple[str, ...]] = {
    "vmess": (
        "vmess://not-base64",
        "vmess://e2JhZA==",
        "vmess://" + base64.b64encode(
            json.dumps({"add": "fixture.example", "port": "443"}).encode("utf-8")
        ).decode("ascii"),
        "vmess://" + base64.b64encode(
            json.dumps(
                {"add": "fixture.example", "port": "443", "id": ""}
            ).encode("utf-8")
        ).decode("ascii"),
    ),
    "vless": ("vless://@fixture.example:443",),
    "shadowsocks": (
        "ss://c3M6cGFzcw==@fixture.example:8388",
        "ss://@fixture.example:8388",
    ),
    "ss2022": (
        "ss2022://@fixture.example:8389",
        "ss2022://invalid@fixture.example:8389",
    ),
    "ssr": ("ssr://not-base64",),
    "trojan": ("trojan://@fixture.example:443",),
    "hysteria": ("hysteria://",),
    "hysteria2": ("hysteria2://",),
    "tuic": ("tuic://", "tuic://@fixture.example:443"),
    "wireguard": (
        "wireguard://fixture@example.com:2408",
        "wireguard://fixture@fixture.example:2408?private_key=&public_key=",
    ),
    "naive": ("naive+https://fixture.example:443",),
    "snell": ("snell://", "snell://@fixture.example:443"),
    "brook": ("brook://", "brook://@fixture.example:9999"),
    "juicity": ("juicity://@fixture.example:443",),
    "xray": ("xray://@fixture.example:443",),
    "v2ray": ("{bad json", '{"outbounds":[]}'),
    "ssh": ("ssh://", "ssh://@fixture.example:22"),
    "http": ("http://",),
    "socks4": ("socks4://:bad",),
    "socks5": ("socks5://:bad",),
    "openvpn": ("client\nremote\n",),
}


def _public_canonical_matrix_entries() -> list[dict[str, Any]]:
    data = json.loads(PROTOCOL_MATRIX.read_text(encoding="utf-8"))
    entries = data["protocols"]
    return [
        entry
        for entry in entries
        if entry["public"] is True and entry["kind"] == "canonical"
    ]


def test_public_canonical_protocol_fixtures_cover_matrix():
    matrix_protocols = {entry["id"] for entry in _public_canonical_matrix_entries()}
    assert set(GOLDEN_PROXIES) == matrix_protocols


def test_protocol_matrix_export_flags_match_golden_converters():
    for entry in _public_canonical_matrix_entries():
        protocol = entry["id"]
        proxy = GOLDEN_PROXIES[protocol]

        singbox_outbound = to_singbox_outbound(proxy)
        expected_singbox_type = EXPECTED_SINGBOX_TYPES.get(protocol)
        assert (singbox_outbound is not None) is entry["singbox_export"], protocol
        if expected_singbox_type:
            assert singbox_outbound is not None
            assert singbox_outbound["type"] == expected_singbox_type

        clash_proxy = to_clash_proxy(proxy, ignore_status=True)
        expected_clash_type = EXPECTED_CLASH_TYPES.get(protocol)
        assert (clash_proxy is not None) is entry["clash_export"], protocol
        if expected_clash_type:
            assert clash_proxy is not None
            assert clash_proxy["type"] == expected_clash_type


def test_golden_protocols_render_in_subscription_outputs():
    proxies = list(GOLDEN_PROXIES.values())

    singbox = json.loads(generate_singbox_config(proxies))
    singbox_types = {
        outbound["type"]
        for outbound in singbox["outbounds"]
        if outbound.get("tag", "").startswith("fixture-")
    }
    assert set(EXPECTED_SINGBOX_TYPES.values()).issubset(singbox_types)

    clash = yaml.safe_load(generate_clash_config(proxies, ignore_status=True))
    clash_types = {proxy["type"] for proxy in clash["proxies"]}
    assert set(EXPECTED_CLASH_TYPES.values()).issubset(clash_types)

    subscription = base64.b64decode(generate_base64_subscription(proxies)).decode(
        "utf-8"
    )
    assert "vmess://" in subscription
    assert "vless://" in subscription
    assert "trojan://" in subscription
    assert "ss://" in subscription


def test_public_protocol_parsers_feed_frontend_protocol_labels(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for the frontend protocol fixture")

    matrix_protocols = {entry["id"] for entry in _public_canonical_matrix_entries()}
    assert set(PARSER_TO_FRONTEND_FIXTURES) == matrix_protocols

    parsed_records = []
    expected_protocols = []
    for protocol, (
        parser,
        config,
        expected_frontend_protocol,
    ) in PARSER_TO_FRONTEND_FIXTURES.items():
        proxy = parser(config)
        assert proxy is not None, protocol
        parsed_records.append(proxy.model_dump(mode="json"))
        expected_protocols.append(expected_frontend_protocol)

    payload_path = tmp_path / "parsed-proxies.json"
    payload_path.write_text(json.dumps(parsed_records), encoding="utf-8")
    script_path = tmp_path / "process-proxies.mjs"
    proxies_js = ROOT / "frontend" / "assets" / "js" / "proxies.js"
    script_path.write_text(
        f"""
import {{ pathToFileURL }} from 'node:url';
import fs from 'node:fs';

globalThis.document = {{
  addEventListener: () => {{}},
  documentElement: {{ style: {{ setProperty: () => {{}} }} }},
  body: {{ classList: {{ add: () => {{}}, remove: () => {{}} }} }},
  createElement: () => ({{ textContent: '', innerHTML: '' }}),
  getElementById: () => null,
  querySelectorAll: () => [],
}};
globalThis.window = {{
  location: {{ hostname: 'localhost', protocol: 'http:' }},
  localStorage: {{ getItem: () => null, setItem: () => {{}} }},
}};
globalThis.localStorage = globalThis.window.localStorage;

const mod = await import(pathToFileURL({json.dumps(str(proxies_js))}).href);
const input = JSON.parse(fs.readFileSync({json.dumps(str(payload_path))}, 'utf8'));
const processed = input.map(mod.processProxyData);
console.log(JSON.stringify(processed.map((proxy) => proxy.protocol)));
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [node, str(script_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(completed.stdout) == expected_protocols


def test_vless_parser_recovers_missing_authority_uuid_from_query():
    proxy = parse_vless(
        f"vless://@fixture.example:443?uuid={UUID}&security=tls#fixture-vless"
    )

    assert proxy is not None
    assert proxy.uuid == UUID
    assert proxy.details["uuid"] == UUID


def test_public_protocol_parsers_fail_closed_on_malformed_inputs():
    matrix_protocols = {entry["id"] for entry in _public_canonical_matrix_entries()}
    assert set(MALFORMED_PARSER_FIXTURES) == matrix_protocols

    generic_junk = ("", "not a proxy", "://")
    for protocol, (
        parser,
        _valid_config,
        _expected_protocol,
    ) in PARSER_TO_FRONTEND_FIXTURES.items():
        for config in (*generic_junk, *MALFORMED_PARSER_FIXTURES[protocol]):
            assert parser(config) is None, f"{protocol} accepted malformed input"
