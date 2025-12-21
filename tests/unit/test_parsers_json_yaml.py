from configstream.parsers.extraction import extract_config_lines
from configstream.parsers import _parse_v2ray_json
import json


class TestParsersExtended:
    def test_extract_json_blob(self):
        payload = '{"outbounds": [{"protocol": "vless", "settings": {"vnext": [{"address": "1.2.3.4", "port": 443, "users": [{"id": "uuid"}]}]}}]}'
        lines, stats = extract_config_lines(payload)
        assert len(lines) == 1
        assert lines[0] == payload

        # Verify it can be parsed by auto_detect logic (simulated)
        assert _parse_v2ray_json(lines[0]) is not None

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
