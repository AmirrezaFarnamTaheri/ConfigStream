from __future__ import annotations
import base64
import pytest
from configstream.models import Proxy
from configstream.parsers import (
    _parse_ss,
    _parse_ssr,
    _parse_vmess,
    _parse_vless,
    _parse_trojan,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_tuic,
    _parse_wireguard,
    _parse_xray,
    _parse_snell,
    _parse_brook,
    _parse_juicity,
    _safe_b64_decode,
    _validate_b64_input,
    _extract_config_lines,
    _is_plausible_proxy_config,
    _parse_v2ray_json,
    _parse_naive,
    _parse_generic_url_scheme,
)


def _safe_b64_encode(s: str) -> str:
    """Safely base64 encode a string, handling potential errors."""
    try:
        return base64.urlsafe_b64encode(s.encode()).rstrip(b"=").decode()
    except (AttributeError, TypeError):
        return s  # Return original if not a string


def test_is_plausible_proxy_config():
    assert _is_plausible_proxy_config("vmess://asdf")
    assert not _is_plausible_proxy_config("just a string")
    assert not _is_plausible_proxy_config("protocol_too_longgggggggggggggggggggg://rest")
    assert not _is_plausible_proxy_config("p://s")


def test_extract_config_lines():
    payload = """
    vmess://config1
    # comment
    vless://config2

    trojan://config3
    """
    configs = _extract_config_lines(payload)
    assert len(configs) == 3
    assert configs[0] == "vmess://config1"
    assert configs[1] == "vless://config2"
    assert configs[2] == "trojan://config3"


def test_extract_config_lines_max_lines():
    payload = "\n".join([f"vmess://config{i}" for i in range(20)])
    configs = _extract_config_lines(payload, max_lines=10)
    assert len(configs) == 10


def test_safe_b64_decode():
    assert _safe_b64_decode("aGVsbG8=") == "hello"
    assert _safe_b64_decode("not base64") == "not base64"
    assert _safe_b64_decode("") == ""


def test_validate_b64_input():
    assert _validate_b64_input("aGVsbG8=") == "aGVsbG8="
    assert _validate_b64_input("not base64$") is None


def test_parse_ss_sip002():
    config = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:8888#test-remark"
    proxy = _parse_ss(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8888
    assert proxy.remarks == "test-remark"
    assert proxy.details["method"] == "aes-256-gcm"
    assert proxy.details["password"] == "password"


def test_parse_ss_plain():
    config = "ss://aes-256-gcm:password@1.2.3.4:8888#test-remark"
    proxy = _parse_ss(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8888
    assert proxy.remarks == "test-remark"
    assert proxy.details["method"] == "aes-256-gcm"
    assert proxy.details["password"] == "password"


def test_parse_ssr_known_good():
    # This is a real-world example of a valid SSR config.
    config = "ssr://MjA3LjI0Ni4xMDYuMjI3OjgwOTk6YXV0aF9hZXMxMjhfbWQ1OmFlcy0yNTYtY2ZiOnRsczEuMl90aWNrZXRfYXV0aDpNakV4TXpZNU5qVTAvP29iZnNwYXJhbT1kWE5sY201aGJpNWpiMjAmcHJvdG9wYXJhbT1NVGd6T0RrNU9URTUmcmVtYXJrcz1kM2QzJmdyb3VwPWQzZDM"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.protocol == "ssr"
    assert proxy.address == "207.246.106.227"
    assert proxy.port == 8099
    assert proxy.remarks == "www"  # remarks are base64 decoded from params
    assert proxy.details["protocol"] == "auth_aes128_md5"
    assert proxy.details["cipher"] == "aes-256-cfb"
    assert proxy.details["obfs"] == "tls1.2_ticket_auth"
    assert proxy.details["password"] == "211369654"  # password is base64 decoded
    assert proxy.details["params"]["obfsparam"] == "usernan.com"  # base64 decoded
    assert proxy.details["params"]["protoparam"] == "183899919"  # base64 decoded
    assert proxy.details["params"]["group"] == "www"  # base64 decoded


def test_parse_ssr_urlsafe_base64():
    # Construct a payload with urlsafe chars (-) and (_)
    # "remarks=hello-world" -> cmVtYXJrcz1oZWxsby13b3JsZA
    # server:port:proto:cipher:obfs:passwd_b64/?remarks_b64
    payload = "1.1.1.1:80:p:c:o:cGFzc3dvcmQ/?remarks=aGVsbG8td29ybGQ"
    encoded_payload = _safe_b64_encode(payload)
    config = f"ssr://{encoded_payload}"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.address == "1.1.1.1"
    assert proxy.details["password"] == "password"
    assert proxy.remarks == "hello-world"


def test_parse_ssr_plain_text_params():
    # The new parser should not fail if a parameter is not valid base64.
    # It should be passed through as-is. This is the opposite of the old test.
    config = "ssr://MS4yLjMuNDo4ODg4OmF1dGhfYWVzMTI4X3NoYTE6YWVzLTI1Ni1jZmI6dGxzMS4yX3RpY2tldF9hdXRoOlBhc3N3b3JkLz9yZW1hcmtzPVJlbWFyayZvYmZzcGFyYW09aW52YWxpZCE"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.remarks == "E隮"
    assert proxy.details["params"]["obfsparam"] == "invalid!"  # This is plain text


def test_parse_ssr_empty_and_no_value_params():
    # main_part = "1.2.3.4:8888:p:c:o:pwd_b64" -> MS4yLjMuNDo4ODg4OnA6YzpvOnB3ZF9iNjQ=
    # qs = /?remarks=&group=d3d3&noval
    payload = "1.2.3.4:8888:p:c:o:cGFzcw/?remarks=&group=d3d3&noval"
    config = f"ssr://{_safe_b64_encode(payload)}"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.address == "1.2.3.4"
    assert proxy.details["password"] == "pass"
    assert "remarks" in proxy.details["params"]
    assert proxy.details["params"]["remarks"] == ""  # empty value
    assert "noval" in proxy.details["params"]
    assert proxy.details["params"]["noval"] == ""  # no value becomes empty string
    assert proxy.details["params"]["group"] == "www"
    assert proxy.remarks == ""  # remarks param is empty


def test_parse_ssr_no_params():
    payload = "1.2.3.4:8888:auth_aes128_sha1:aes-256-cfb:tls1.2_ticket_auth:UGFzc3dvcmQ"
    config = f"ssr://{_safe_b64_encode(payload)}"
    proxy = _parse_ssr(config)
    assert proxy is not None
    assert proxy.address == "1.2.3.4"
    assert proxy.details["password"] == "Password"
    assert proxy.remarks == ""  # No remarks param, so it's empty
    assert proxy.details["params"] == {}


@pytest.mark.parametrize(
    "config",
    [
        # Invalid prefix
        "ss://whatever",
        # Payload is not valid base64
        "ssr://!!!!!!!!",
        # Decoded payload doesn't have 6 parts
        f"ssr://{_safe_b64_encode('1:2:3:4:5')}",
        # Port is not a number
        f"ssr://{_safe_b64_encode('1.1.1.1:notaport:p:c:o:pwd')}",
        # Port is out of range
        f"ssr://{_safe_b64_encode('1.1.1.1:99999:p:c:o:pwd')}",
    ],
)
def test_parse_ssr_invalid_configs(config):
    assert _parse_ssr(config) is None


def test_parse_vmess_invalid():
    assert _parse_vmess("vmess://") is None
    assert _parse_vmess("vmess://aW52YWxpZCBqc29u") is None


def test_parse_vless_invalid():
    assert _parse_vless("vless://@") is None


def test_parse_trojan_invalid():
    assert _parse_trojan("trojan://@") is None


def test_parse_hysteria():
    config = "hysteria://1.2.3.4:443?protocol=udp&auth=someauth#Test"
    proxy = _parse_hysteria(config)
    assert proxy is not None
    assert proxy.protocol == "hysteria"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 443
    assert proxy.remarks == "Test"
    assert proxy.details["protocol"] == ["udp"]
    assert proxy.details["auth"] == ["someauth"]


def test_parse_hysteria2_missing_password():
    config = "hysteria2://1.2.3.4:443"
    assert _parse_hysteria2(config) is None


def test_parse_hysteria2_valid():
    config = "hysteria2://password@1.2.3.4:443#Test"
    proxy = _parse_hysteria2(config)
    assert proxy is not None
    assert proxy.protocol == "hysteria2"
    assert proxy.uuid == "password"


def test_parse_tuic():
    config = "tuic://uuid@1.2.3.4:443?congestion_control=bbr#Test"
    proxy = _parse_tuic(config)
    assert proxy is not None
    assert proxy.protocol == "tuic"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 443
    assert proxy.uuid == "uuid"
    assert proxy.details["congestion_control"] == ["bbr"]


def test_parse_wireguard_missing_private_key():
    config = "wireguard://1.2.3.4:51820#Test"
    assert _parse_wireguard(config) is None


def test_parse_wireguard_valid():
    config = "wireguard://1.2.3.4:51820?private_key=key#Test"
    proxy = _parse_wireguard(config)
    assert proxy is not None
    assert proxy.protocol == "wireguard"
    assert proxy.details["private_key"] == ["key"]


def test_parse_xray_missing_uuid():
    config = "xray://1.2.3.4:443#Test"
    assert _parse_xray(config) is None


def test_parse_xray_valid():
    config = "xray://uuid@1.2.3.4:443?flow=xtls-rprx-vision#Test"
    proxy = _parse_xray(config)
    assert proxy is not None
    assert proxy.protocol == "xray"
    assert proxy.uuid == "uuid"


def test_parse_snell():
    config = "snell://psk@1.2.3.4:443#Test"
    proxy = _parse_snell(config)
    assert proxy is not None
    assert proxy.protocol == "snell"


def test_parse_brook():
    config = "brook://password@1.2.3.4:9999#Test"
    proxy = _parse_brook(config)
    assert proxy is not None
    assert proxy.protocol == "brook"


def test_parse_juicity_missing_uuid():
    config = "juicity://1.2.3.4:443#Test"
    assert _parse_juicity(config) is None


def test_parse_juicity_valid():
    config = "juicity://uuid@1.2.3.4:443#Test"
    proxy = _parse_juicity(config)
    assert proxy is not None
    assert proxy.protocol == "juicity"
    assert proxy.uuid == "uuid"


def test_parse_v2ray_json_valid():
    config = """
    {
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": "1.2.3.4",
                            "port": 1234,
                            "users": [
                                {
                                    "id": "uuid"
                                }
                            ]
                        }
                    ]
                },
                "tag": "proxy"
            }
        ]
    }
    """
    proxy = _parse_v2ray_json(config)
    assert proxy is not None
    assert proxy.protocol == "v2ray"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 1234
    assert proxy.uuid == "uuid"


def test_parse_v2ray_json_invalid():
    assert _parse_v2ray_json("{not_json") is None
    assert _parse_v2ray_json('{"outbounds": []}') is None


def test_parse_naive_valid():
    config = "naive+https://user:pass@example.com#test"
    proxy = _parse_naive(config)
    assert proxy is not None
    assert proxy.protocol == "naive"
    assert proxy.address == "example.com"
    assert proxy.uuid == "user"
    assert proxy.details["password"] == "pass"


def test_parse_naive_invalid():
    assert _parse_naive("naive+https://example.com") is None


def test_parse_generic_url_scheme_http():
    config = "http://user:pass@example.com:8080#test"
    proxy = _parse_generic_url_scheme(config)
    assert proxy is not None
    assert proxy.protocol == "http"
    assert proxy.port == 8080


def test_parse_generic_url_scheme_socks5():
    config = "socks5://user:pass@example.com:1080#test"
    proxy = _parse_generic_url_scheme(config)
    assert proxy is not None
    assert proxy.protocol == "socks5"
    assert proxy.port == 1080


def test_parse_ss_invalid_port():
    config = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:99999#test"
    assert _parse_ss(config) is None
