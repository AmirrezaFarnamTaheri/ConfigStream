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


if __name__ == "__main__":
    unittest.main()
