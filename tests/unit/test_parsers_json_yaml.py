# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.parsers.extraction import extract_config_lines
from configstream.parsers import parse_v2ray_json
from configstream.parsers.clash_json import parse_clash_json
import json


class TestParsersExtended:
    def test_extract_json_blob(self):
        payload = '{"outbounds": [{"protocol": "vless", "settings": {"vnext": [{"address": "1.2.3.4", "port": 443, "users": [{"id": "uuid"}]}]}}]}'
        lines, stats = extract_config_lines(payload)
        assert len(lines) == 1
        assert lines[0] == payload

        # Verify it can be parsed by auto_detect logic (simulated)
        assert parse_v2ray_json(lines[0]) is not None

    def test_extract_yaml_blob(self):
        payload = """
proxies:
  - name: "vless"
    type: vless
    server: 1.2.3.4
    port: 443
    uuid: uuid
"""
        lines, stats = extract_config_lines(payload)
        assert len(lines) == 1
        # It should be converted to a JSON string representation of the proxy
        assert json.loads(lines[0])["name"] == "vless"


class TestClashJsonParser:
    def test_parse_clash_json_vless_requires_uuid(self):
        payload = {
            "name": "missing-uuid",
            "type": "vless",
            "server": "example.com",
            "port": 443,
        }
        assert parse_clash_json(json.dumps(payload)) is None

    def test_parse_clash_json_trojan_requires_password(self):
        payload = {
            "name": "missing-password",
            "type": "trojan",
            "server": "example.com",
            "port": 443,
        }
        assert parse_clash_json(json.dumps(payload)) is None

    def test_parse_clash_json_shadowsocks_rejects_invalid_method(self):
        payload = {
            "name": "bad-method",
            "type": "ss",
            "server": "example.com",
            "port": 8388,
            "cipher": "ss",
            "password": "secret",
        }
        assert parse_clash_json(json.dumps(payload)) is None

    def test_parse_clash_json_rejects_invalid_port(self):
        payload = {
            "name": "bad-port",
            "type": "vmess",
            "server": "example.com",
            "port": 70000,
            "uuid": "123e4567-e89b-42d3-a456-426614174000",
        }
        assert parse_clash_json(json.dumps(payload)) is None

    def test_parse_clash_json_rejects_unknown_type(self):
        payload = {
            "name": "unknown",
            "type": "unknown-protocol",
            "server": "example.com",
            "port": 443,
        }
        assert parse_clash_json(json.dumps(payload)) is None

    def test_parse_clash_json_accepts_valid_shadowsocks(self):
        payload = {
            "name": "valid-ss",
            "type": "ss",
            "server": "example.com",
            "port": 8388,
            "cipher": "aes-128-gcm",
            "password": "secret",
        }
        proxy = parse_clash_json(json.dumps(payload))
        assert proxy is not None
        assert proxy.protocol == "shadowsocks"
        assert proxy.details["password"] == "secret"
