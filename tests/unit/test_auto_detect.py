# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest
from configstream.auto_detect import auto_detect_and_parse


class TestAutoDetect(unittest.TestCase):
    def test_detect_vmess(self):
        # Valid VMess (simplified b64)
        # {"add":"1.1.1.1","port":443,"id":"uuid","ps":"remark"} -> eyJhZGQiOiIxLjEuMS4xIiwicG9ydCI6NDQzLCJpZCI6InV1aWQiLCJwcyI6InJlbWFyayJ9
        config = "vmess://eyJhZGQiOiIxLjEuMS4xIiwicG9ydCI6NDQzLCJpZCI6InV1aWQiLCJwcyI6InJlbWFyayJ9"
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "vmess")
        self.assertEqual(proxy.address, "1.1.1.1")

    def test_detect_vless(self):
        config = "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443?security=tls&type=ws#remark"
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "vless")
        self.assertEqual(proxy.address, "example.com")

    def test_detect_ss(self):
        # ss://method:pass@host:port
        # Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNzd29yZA== -> chacha20-ietf-poly1305:password
        config = (
            "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNzd29yZA==@192.168.1.1:8388#Example"
        )
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "shadowsocks")
        self.assertEqual(proxy.port, 8388)

    def test_detect_hysteria2(self):
        config = "hysteria2://password@example.com:443?insecure=1&sni=test.com#remark"
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "hysteria2")
        self.assertEqual(proxy.details["sni"], "test.com")

    def test_detect_xray_snell_brook_juicity(self):
        """Xray, Snell, Brook, Juicity parsers wired in auto_detect."""
        xray = auto_detect_and_parse(
            "xray://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=tls"
        )
        self.assertIsNotNone(xray)
        self.assertEqual(xray.protocol, "xray")

        snell = auto_detect_and_parse("snell://user:pass@host:443?version=3")
        self.assertIsNotNone(snell)
        self.assertEqual(snell.protocol, "snell")

        brook = auto_detect_and_parse("brook://user:pass@host:9999")
        self.assertIsNotNone(brook)
        self.assertEqual(brook.protocol, "brook")

        juicity = auto_detect_and_parse(
            "juicity://a1b2c3d4-e5f6-7890-abcd-ef1234567890@host:443"
        )
        self.assertIsNotNone(juicity)
        self.assertEqual(juicity.protocol, "juicity")

    def test_fallback_detection(self):
        # Just a string that looks like a URL but might fail specific parsers first
        # Actually, the fallback logic iterates.
        # Let's try a tricky one.
        config = "trojan://password@example.com:443"
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "trojan")

    def test_invalid_config(self):
        self.assertIsNone(auto_detect_and_parse("invalid-garbage"))
        self.assertIsNone(auto_detect_and_parse(""))
        self.assertIsNone(auto_detect_and_parse("http://"))  # Incomplete

    def test_detect_openvpn_content_based(self):
        """OpenVPN configs are detected by content, not a URL scheme."""
        config = "client\ndev tun\nremote 1.2.3.4 1194\nproto udp\n"
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "openvpn")
        self.assertEqual(proxy.address, "1.2.3.4")

    def test_openvpn_lookalike_without_remote_falls_through(self):
        """Content that only partially resembles OpenVPN yields no match."""
        self.assertIsNone(auto_detect_and_parse("client\ndev tun\nno remote here"))

    def test_detect_naked_ip_port(self):
        """A bare ``host:port`` with no scheme is treated as a SOCKS/HTTP proxy."""
        proxy = auto_detect_and_parse("203.0.113.5:1080")
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "socks5")
        self.assertEqual(proxy.port, 1080)

    def test_port_heuristic_prefers_tls_candidates_on_443(self):
        """Unscheme'd content on port 443 is still resolved through the direct
        scheme map before the port-based TLS heuristic ever runs, so a
        recognized ``trojan://`` URL is parsed as trojan, not misclassified."""
        proxy = auto_detect_and_parse("trojan://secret@example.com:443")
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "trojan")

    def test_detect_clash_json_entry(self):
        config = '{"type": "trojan", "server": "1.2.3.4", "port": 443, "password": "x", "name": "r"}'
        proxy = auto_detect_and_parse(config)
        self.assertIsNotNone(proxy)
        self.assertEqual(proxy.protocol, "trojan")
        self.assertEqual(proxy.address, "1.2.3.4")

    def test_generic_http_scheme_is_not_misclassified_as_a_proxy_protocol(self):
        """A plain ``http://`` URL must not be reinterpreted as trojan, vless,
        hysteria, or wireguard just because it shares a port those protocols
        commonly use (443/typical WireGuard ports)."""
        for config in ("http://example.com:443", "http://1.2.3.4:51820"):
            proxy = auto_detect_and_parse(config)
            self.assertIsNotNone(proxy)
            self.assertEqual(proxy.protocol, "http")

    def test_fallback_loop_rejects_scheme_protocol_mismatch(self):
        """``parse_naive`` is a thin urlparse wrapper: given any
        ``user:pass@host:port`` it happily returns a "naive" proxy regardless
        of scheme. The fallback loop's scheme allowlist must still reject
        that result when the URL's own scheme isn't one of naive's schemes,
        otherwise an arbitrary ``scheme://user:pass@host:port`` string would
        be laundered into a bogus proxy entry."""
        from configstream.parsers import parse_naive

        # Confirm the premise: parse_naive alone is scheme-agnostic.
        self.assertEqual(
            parse_naive("totallyunknown://user:pass@1.2.3.4:51820").protocol, "naive"
        )
        # auto_detect_and_parse must still reject it via the scheme allowlist.
        self.assertIsNone(
            auto_detect_and_parse("totallyunknown://user:pass@1.2.3.4:51820")
        )

    def test_unrecognized_scheme_is_dropped_not_crashed(self):
        self.assertIsNone(auto_detect_and_parse("totallyunknown://x@1.2.3.4:1080"))


if __name__ == "__main__":
    unittest.main()
