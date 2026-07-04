# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive tests for generic parser (parse_generic_url_scheme, parse_naive, parse_v2ray_json)."""

import json
from configstream.parsers.generic import (
    parse_generic_url_scheme,
    parse_naive,
    parse_v2ray_json,
)


class TestGenericURLScheme:
    """Tests for parse_generic_url_scheme."""

    def test_http_url(self):
        """Standard HTTP URL."""
        proxy = parse_generic_url_scheme("http://1.2.3.4:8080")
        assert proxy is not None
        assert proxy.protocol == "http"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 8080

    def test_https_url(self):
        """HTTPS URL should be mapped to http with tls=True."""
        proxy = parse_generic_url_scheme("https://example.com:443")
        assert proxy is not None
        assert proxy.protocol == "http"
        assert proxy.details.get("tls") is True
        assert proxy.port == 443

    def test_socks5_url(self):
        """SOCKS5 URL."""
        proxy = parse_generic_url_scheme("socks5://1.2.3.4:1080")
        assert proxy is not None
        assert proxy.protocol == "socks5"

    def test_socks4_url(self):
        """SOCKS4 URL."""
        proxy = parse_generic_url_scheme("socks4://1.2.3.4:1080")
        assert proxy is not None
        assert proxy.protocol == "socks4"

    def test_socks_url_normalized(self):
        """socks:// should be normalized to socks5."""
        proxy = parse_generic_url_scheme("socks://1.2.3.4:1080")
        assert proxy is not None
        assert proxy.protocol == "socks5"

    def test_naked_ip_port_http_port(self):
        """Naked IP:PORT with non-standard port defaults to http."""
        proxy = parse_generic_url_scheme("1.2.3.4:9999")
        assert proxy is not None
        assert proxy.protocol == "http"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 9999

    def test_naked_ip_port_socks_port(self):
        """Naked IP:PORT with port 1080 defaults to socks5."""
        proxy = parse_generic_url_scheme("1.2.3.4:1080")
        assert proxy is not None
        assert proxy.protocol == "socks5"

    def test_naked_ip_port_9050(self):
        """Port 9050 (Tor) should default to socks5."""
        proxy = parse_generic_url_scheme("1.2.3.4:9050")
        assert proxy is not None
        assert proxy.protocol == "socks5"

    def test_naked_ipv6_bracketed(self):
        """Naked IPv6 [::1]:Port format."""
        proxy = parse_generic_url_scheme("[::1]:8080")
        assert proxy is not None
        assert proxy.address == "::1"
        assert proxy.port == 8080

    def test_empty_config_returns_none(self):
        """Empty config should return None."""
        assert parse_generic_url_scheme("") is None

    def test_invalid_hostname_rejected(self):
        """Config with invalid hostname should return None."""
        assert parse_generic_url_scheme("not_valid_host_!@#$:8080") is None

    def test_invalid_port_range(self):
        """Port outside 0-65535 raises ValueError in urlparse and parser returns None."""
        assert parse_generic_url_scheme("http://1.2.3.4:65536") is None

    def test_garbage_hostname_rejected(self):
        """'garbage' as hostname should be rejected."""
        assert parse_generic_url_scheme("http://garbage:8080") is None

    def test_hostname_invalid_keyword_rejected(self):
        """'invalid' as hostname should be rejected."""
        assert parse_generic_url_scheme("http://invalid:8080") is None

    def test_http_with_username(self):
        """HTTP URL with username."""
        proxy = parse_generic_url_scheme("http://user:pass@1.2.3.4:8080")
        assert proxy is not None
        assert proxy.details.get("username") == "user"
        assert proxy.details.get("password") == "pass"

    def test_http_default_port(self):
        """HTTP without port should default to 80."""
        proxy = parse_generic_url_scheme("http://example.com")
        assert proxy is not None
        assert proxy.port == 80

    def test_https_default_port(self):
        """HTTPS without port should default to 443."""
        proxy = parse_generic_url_scheme("https://example.com")
        assert proxy is not None
        assert proxy.port == 443
        assert proxy.details.get("tls") is True

    def test_long_config_rejected(self):
        """Config exceeding MAX_CONFIG_LINE_LENGTH should be rejected."""
        long_url = "http://" + "a" * 10000 + ":8080"
        assert parse_generic_url_scheme(long_url) is None


class TestNaiveParser:
    """Tests for parse_naive."""

    def test_naive_https(self):
        """Standard Naive HTTPS config."""
        proxy = parse_naive(
            "naive+https://user:pass@example.com:443?padding=true#MyNaive"
        )
        assert proxy is not None
        assert proxy.protocol == "naive"
        assert proxy.address == "example.com"
        assert proxy.port == 443
        assert proxy.details.get("username") == "user"
        assert proxy.details.get("password") == "pass"

    def test_naive_http(self):
        """Naive HTTP config."""
        proxy = parse_naive("naive+http://user:pass@example.com:8080")
        assert proxy is not None
        assert proxy.protocol == "naive"
        assert proxy.port == 8080
        assert proxy.details.get("tls") is not True  # No TLS for http

    def test_naive_missing_credentials(self):
        """Naive without username/password should return None."""
        assert parse_naive("naive+https://example.com") is None

    def test_naive_empty_config(self):
        """Empty config should return None."""
        assert parse_naive("") is None

    def test_naive_html_escaped(self):
        """Naive config with HTML entities should be unescaped."""
        proxy = parse_naive(
            "naive+https://user:pass@example.com?padding=true#My&amp;Server"
        )
        assert proxy is not None
        assert "&" in proxy.remarks  # &amp; should be unescaped to &


class TestV2RayJsonParser:
    """Tests for parse_v2ray_json."""

    def make_vmess_v2ray(
        self, address="1.2.3.4", port=443, uuid="550e8400-e29b-41d4-a716-446655440000"
    ):
        return json.dumps(
            {
                "outbound": {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {"address": address, "port": port, "users": [{"id": uuid}]}
                        ]
                    },
                }
            }
        )

    def test_v2ray_vmess_basic(self):
        """Basic VMess v2ray JSON config."""
        config = self.make_vmess_v2ray()
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "vmess"
        assert proxy.address == "1.2.3.4"
        assert proxy.port == 443
        assert proxy.uuid == "550e8400-e29b-41d4-a716-446655440000"

    def test_v2ray_vless(self):
        """VLESS v2ray JSON config."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": "example.com",
                                "port": 443,
                                "users": [{"id": "uuid1234", "encryption": "none"}],
                            }
                        ]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "vless"
        assert proxy.address == "example.com"
        assert proxy.details.get("encryption") == "none"

    def test_v2ray_trojan(self):
        """Trojan v2ray JSON config."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "trojan",
                    "settings": {
                        "servers": [
                            {
                                "address": "trojan.example.com",
                                "port": 443,
                                "password": "secretpw",
                            }
                        ]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "trojan"
        assert proxy.uuid == "secretpw"

    def test_v2ray_shadowsocks(self):
        """Shadowsocks v2ray JSON config."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [
                            {
                                "address": "ss.example.com",
                                "port": 8388,
                                "password": "mypass",
                                "method": "aes-256-gcm",
                            }
                        ]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "shadowsocks"
        assert proxy.details.get("password") == "mypass"
        assert proxy.details.get("method") == "aes-256-gcm"

    def test_v2ray_ss_alias(self):
        """ss protocol alias should normalize to shadowsocks."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "ss",
                    "settings": {
                        "servers": [
                            {
                                "address": "ss.example.com",
                                "port": 8388,
                                "password": "pw",
                                "method": "chacha20-ietf-poly1305",
                            }
                        ]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "shadowsocks"

    def test_v2ray_socks(self):
        """SOCKS v2ray JSON config."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "socks",
                    "settings": {
                        "servers": [{"address": "socks.example.com", "port": 1080}]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "socks5"
        assert proxy.port == 1080

    def test_v2ray_http(self):
        """HTTP v2ray JSON config."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "http",
                    "settings": {
                        "servers": [{"address": "http.example.com", "port": 3128}]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.protocol == "http"

    def test_v2ray_no_outbound(self):
        """Config missing outbound should return None."""
        assert parse_v2ray_json('{"invalid": true}') is None

    def test_v2ray_empty_config(self):
        """Empty config should return None."""
        assert parse_v2ray_json("") is None

    def test_v2ray_not_json(self):
        """Non-JSON config should return None."""
        assert parse_v2ray_json("not json") is None

    def test_v2ray_no_protocol(self):
        """Config without protocol should return None."""
        assert parse_v2ray_json('{"outbound": {"settings": {}}}') is None

    def test_v2ray_unknown_protocol(self):
        """Unknown protocol should return None."""
        assert (
            parse_v2ray_json('{"outbound": {"protocol": "unknown", "settings": {}}}')
            is None
        )

    def test_v2ray_vmess_missing_uuid(self):
        """VMess without UUID should return None."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [{"address": "1.2.3.4", "port": 443, "users": [{}]}]
                    },
                }
            }
        )
        assert parse_v2ray_json(config) is None

    def test_v2ray_trojan_missing_password(self):
        """Trojan without password should return None."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "trojan",
                    "settings": {"servers": [{"address": "host", "port": 443}]},
                }
            }
        )
        assert parse_v2ray_json(config) is None

    def test_v2ray_stream_settings_ws(self):
        """VMess with WebSocket stream settings."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": "example.com",
                                "port": 443,
                                "users": [{"id": "uuid1234"}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": "tls",
                        "wsSettings": {
                            "path": "/ws",
                            "headers": {"Host": "example.com"},
                        },
                        "tlsSettings": {"serverName": "example.com"},
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.details.get("net") == "ws"
        assert proxy.details.get("path") == "/ws"
        assert proxy.details.get("host") == "example.com"
        assert proxy.details.get("sni") == "example.com"
        assert proxy.details.get("security") == "tls"

    def test_v2ray_stream_settings_grpc(self):
        """VMess with gRPC stream settings."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": "example.com",
                                "port": 443,
                                "users": [{"id": "uuid1234"}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "grpc",
                        "grpcSettings": {"serviceName": "mygrpc"},
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.details.get("serviceName") == "mygrpc"

    def test_v2ray_reality_settings(self):
        """VLESS with Reality settings."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": "example.com",
                                "port": 443,
                                "users": [
                                    {
                                        "id": "uuid1234",
                                        "flow": "xtls-rprx-vision",
                                        "encryption": "none",
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "serverName": "example.com",
                            "publicKey": "abc123publickey",
                            "shortId": "1234",
                            "fingerprint": "chrome",
                        },
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.details.get("security") == "reality"
        assert proxy.details.get("pbk") == "abc123publickey"
        assert proxy.details.get("sid") == "1234"
        assert proxy.details.get("fp") == "chrome"
        assert proxy.details.get("flow") == "xtls-rprx-vision"

    def test_v2ray_invalid_port(self):
        """Config with invalid port should return None."""
        config = self.make_vmess_v2ray(port="notanumber")
        assert parse_v2ray_json(config) is None

    def test_v2ray_outbounds_list(self):
        """Config with outbounds array should use first entry."""
        config = json.dumps(
            {
                "outbounds": [
                    {
                        "protocol": "vmess",
                        "settings": {
                            "vnext": [
                                {
                                    "address": "10.0.0.1",
                                    "port": 8443,
                                    "users": [{"id": "test-uuid"}],
                                }
                            ]
                        },
                    }
                ]
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.address == "10.0.0.1"
        assert proxy.port == 8443

    def test_v2ray_shadowsocks_missing_password(self):
        """Shadowsocks without password should return None."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [
                            {"address": "host", "port": 443, "method": "aes-256-gcm"}
                        ]
                    },
                }
            }
        )
        assert parse_v2ray_json(config) is None

    def test_v2ray_shadowsocks_invalid_method(self):
        """Shadowsocks with invalid method should return None."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [
                            {
                                "address": "host",
                                "port": 443,
                                "password": "pw",
                                "method": "aes",
                            }
                        ]
                    },
                }
            }
        )
        assert parse_v2ray_json(config) is None

    def test_v2ray_vmess_alter_id(self):
        """VMess with alterId."""
        config = json.dumps(
            {
                "outbound": {
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": "1.2.3.4",
                                "port": 443,
                                "users": [{"id": "uuid1234", "alterId": 64}],
                            }
                        ]
                    },
                }
            }
        )
        proxy = parse_v2ray_json(config)
        assert proxy is not None
        assert proxy.details.get("aid") == 64

    def test_v2ray_no_address(self):
        """Config missing address should return None."""
        assert (
            parse_v2ray_json(
                json.dumps(
                    {
                        "outbound": {
                            "protocol": "vmess",
                            "settings": {
                                "vnext": [{"port": 443, "users": [{"id": "uuid"}]}]
                            },
                        }
                    }
                )
            )
            is None
        )
