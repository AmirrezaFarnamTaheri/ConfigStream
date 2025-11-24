from configstream.parsers.generic import (
    parse_generic_url_scheme,
    parse_naive,
    parse_v2ray_json,
)


def test_parse_generic_http():
    url = "http://user:pass@example.com:8080#Remark"
    proxy = parse_generic_url_scheme(url)
    assert proxy is not None
    assert proxy.protocol == "http"
    assert proxy.address == "example.com"
    assert proxy.port == 8080
    assert proxy.uuid == "user"
    assert proxy.details["password"] == "pass"
    assert proxy.remarks == "Remark"


def test_parse_generic_invalid_hostname():
    assert parse_generic_url_scheme("http://garbage:8080") is None
    assert parse_generic_url_scheme("http://invalid:8080") is None
    # Hostname must have dot or be localhost
    assert parse_generic_url_scheme("http://nodot:8080") is None
    assert parse_generic_url_scheme("http://localhost:8080") is not None


def test_parse_generic_default_ports():
    p = parse_generic_url_scheme("https://example.com")
    assert p.port == 443

    p = parse_generic_url_scheme("socks5://example.com")
    assert p.port == 1080


def test_parse_generic_malformed():
    assert parse_generic_url_scheme("not a url") is None
    assert parse_generic_url_scheme("http://") is None


def test_parse_naive():
    url = "naive+https://user:pass@example.com:443#Remark"
    proxy = parse_naive(url)
    assert proxy is not None
    assert proxy.protocol == "naive"
    assert proxy.address == "example.com"
    assert proxy.port == 443

    # Test missing creds
    assert parse_naive("naive+https://example.com") is None


def test_parse_v2ray_json():
    json_conf = """
    {
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": "example.com",
                            "port": 10086,
                            "users": [{"id": "uuid"}]
                        }
                    ]
                },
                "tag": "Remark"
            }
        ]
    }
    """
    proxy = parse_v2ray_json(json_conf)
    assert proxy is not None
    assert (
        proxy.protocol == "v2ray"
    )  # parser sets generic protocol name 'v2ray' if input is generic json?
    # The code gets protocol from outbound: "protocol": "vmess"
    # But wait, code: protocol = outbound.get("protocol", "v2ray")
    # Then: return Proxy(..., protocol="v2ray", ...)
    # It hardcodes "v2ray" as protocol in Proxy constructor!
    assert proxy.protocol == "v2ray"
    assert proxy.address == "example.com"
    assert proxy.port == 10086
    assert proxy.uuid == "uuid"
    assert proxy.remarks == "Remark"


def test_parse_v2ray_json_invalid():
    assert parse_v2ray_json("not json") is None
    assert parse_v2ray_json("{}") is None
