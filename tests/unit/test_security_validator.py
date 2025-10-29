"""Tests for security validation functionality."""

from configstream.security_validator import (
    SecurityValidator,
    validate_batch_configs,
    DANGEROUS_PORTS,
    VALID_PROTOCOLS,
    ValidationPolicy,
    STRICT_POLICY,
    TEST_POLICY,
)
from configstream.models import Proxy


class TestSecurityValidator:
    """Test suite for SecurityValidator class."""

    def test_safe_proxy_passes_validation(self):
        """Test that a safe proxy configuration passes validation."""
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="valid-proxy-domain.com",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is True
        assert len(issues) == 0

    def test_dangerous_port_detected(self):
        """Test that dangerous ports are detected."""
        for port in DANGEROUS_PORTS[:3]:  # Test first 3
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address="valid-proxy-domain.com",
                port=port,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=TEST_POLICY
            )

            assert is_secure is False
            assert "port_security" in issues
            assert any("port" in issue.lower() for issue in issues["port_security"])

    def test_invalid_port_range(self):
        """Test that ports outside valid range are rejected."""
        invalid_ports = [0, -1, 65536, 99999]

        for port in invalid_ports:
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address="valid-proxy-domain.com",
                port=port,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=TEST_POLICY
            )

            assert is_secure is False
            assert "port_security" in issues
            assert any("port" in issue.lower() for issue in issues["port_security"])

    def test_localhost_address_rejected(self):
        """Test that localhost addresses are rejected."""
        suspicious_addresses = ["localhost", "127.0.0.1", "0.0.0.0"]

        for address in suspicious_addresses:
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address=address,
                port=443,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=STRICT_POLICY
            )

            assert is_secure is False
            assert (
                "address_private_ip" in issues or "address_suspicious" in issues
            ), f"Expected 'address_private_ip' or 'address_suspicious' for {address}"

            category = "address_private_ip" if "address_private_ip" in issues else "address_suspicious"
            assert any("address" in issue.lower() for issue in issues[category])

    def test_private_ip_ranges_rejected(self):
        """Test that private IP ranges are rejected."""
        private_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "172.31.255.255",
            "169.254.1.1",
        ]

        for ip in private_ips:
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address=ip,
                port=443,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=STRICT_POLICY
            )

            assert is_secure is False
            assert "address_private_ip" in issues
            assert any("address" in issue.lower() for issue in issues["address_private_ip"])

    def test_empty_address_rejected(self):
        """Test that empty addresses are rejected."""
        proxy = Proxy(
            config="vmess://test",
            protocol="vmess",
            address="",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is False
        assert "address_suspicious" in issues
        assert any("address" in issue.lower() for issue in issues["address_suspicious"])

    def test_ipv6_special_addresses_rejected(self):
        """Test that special IPv6 addresses are rejected."""
        ipv6_addresses = [
            "::1",  # IPv6 loopback
            "fe80::1",  # IPv6 link-local
            "fc00::1",  # IPv6 unique local
            "fd00::1",  # IPv6 unique local
        ]

        for ip in ipv6_addresses:
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address=ip,
                port=443,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=STRICT_POLICY
            )

            assert is_secure is False, f"IPv6 address {ip} should be rejected"
            assert "address_private_ip" in issues
            assert any("address" in issue.lower() for issue in issues["address_private_ip"])

    def test_non_standard_ip_notation_rejected(self):
        """Test that non-standard IP notations are rejected."""
        non_standard_ips = [
            "0x7f000001",  # Hexadecimal notation for 127.0.0.1
            "0177.0.0.1",  # Octal notation
        ]

        for ip in non_standard_ips:
            proxy = Proxy(
                config="vmess://test",
                protocol="vmess",
                address=ip,
                port=443,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=STRICT_POLICY
            )

            assert is_secure is False, f"Non-standard IP {ip} should be rejected"
            assert "address_suspicious" in issues
            assert any(
                "notation" in issue.lower() for issue in issues["address_suspicious"]
            )

    def test_empty_config_string_rejected(self):
        """Test that empty config strings are rejected."""
        proxy = Proxy(
            config="",
            protocol="vmess",
            address="valid-proxy-domain.com",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is False
        assert "suspicious_config_format" in issues

    def test_unknown_protocol_rejected(self):
        """Test that unknown protocols are rejected."""
        proxy = Proxy(
            config="unknownprotocol://test",
            protocol="unknownprotocol",
            address="valid-proxy-domain.com",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is False
        assert "protocol_invalid" in issues

    def test_known_protocols_accepted(self):
        """Test that all known safe protocols are accepted."""
        for protocol in VALID_PROTOCOLS:
            proxy = Proxy(
                config=f"{protocol}://test",
                protocol=protocol,
                address="valid-proxy-domain.com",
                port=8080,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=TEST_POLICY
            )

            assert is_secure is True, f"Protocol {protocol} should be safe"
            assert len(issues) == 0

    def test_null_byte_in_config_rejected(self):
        """Test that configs with null bytes are rejected."""
        proxy = Proxy(
            config="vmess://test\x00malicious",
            protocol="vmess",
            address="valid-proxy-domain.com",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is False
        assert "suspicious_config_malformed" in issues

    def test_command_injection_patterns_rejected(self):
        """Test that command injection patterns are rejected."""
        malicious_configs = [
            "vmess://test$(rm -rf /)",
            "vmess://test; rm -rf /",
            "vmess://test && rm -rf /",
            "vmess://test | sh",
            "vmess://test`whoami`",
            "vmess://eval(malicious)",
        ]

        for config in malicious_configs:
            proxy = Proxy(
                config=config,
                protocol="vmess",
                address="valid-proxy-domain.com",
                port=443,
                uuid="test-uuid",
            )

            is_secure, issues = SecurityValidator.validate_proxy_config(
                proxy, policy=TEST_POLICY
            )

            assert is_secure is False
            assert "suspicious_injection_attempt" in issues

    def test_excessively_long_config_rejected(self):
        """Test that excessively long configs are rejected."""
        long_config = "vmess://" + "A" * 15000

        proxy = Proxy(
            config=long_config,
            protocol="vmess",
            address="valid-proxy-domain.com",
            port=443,
            uuid="test-uuid",
        )

        is_secure, issues = SecurityValidator.validate_proxy_config(
            proxy, policy=TEST_POLICY
        )

        assert is_secure is False
        assert "suspicious_config_format" in issues


class TestURLValidation:
    """Test suite for URL validation."""

    def test_valid_http_url(self):
        """Test that valid HTTP URL passes."""
        is_valid, error = SecurityValidator.validate_url("http://valid-proxy-domain.com/path")

        assert is_valid is True
        assert error is None

    def test_valid_https_url(self):
        """Test that valid HTTPS URL passes."""
        is_valid, error = SecurityValidator.validate_url("https://valid-proxy-domain.com/path")

        assert is_valid is True
        assert error is None

    def test_empty_url_rejected(self):
        """Test that empty URL is rejected."""
        is_valid, error = SecurityValidator.validate_url("")

        assert is_valid is False
        assert "empty" in error.lower()

    def test_missing_scheme_rejected(self):
        """Test that URL without scheme is rejected."""
        is_valid, error = SecurityValidator.validate_url("valid-proxy-domain.com/path")

        assert is_valid is False
        assert "scheme" in error.lower()

    def test_invalid_scheme_rejected(self):
        """Test that non-HTTP schemes are rejected."""
        invalid_schemes = [
            "ftp://valid-proxy-domain.com",
            "file:///etc/passwd",
            "javascript:alert(1)",
        ]

        for url in invalid_schemes:
            is_valid, error = SecurityValidator.validate_url(url)

            assert is_valid is False
            assert "scheme" in error.lower()

    def test_localhost_url_rejected(self):
        """Test that localhost URLs are rejected."""
        localhost_urls = [
            "http://localhost/",
            "http://127.0.0.1/",
            "http://0.0.0.0/",
        ]

        for url in localhost_urls:
            is_valid, error = SecurityValidator.validate_url(url)

            assert is_valid is False
            assert "suspicious" in error.lower() or "domain" in error.lower()

    def test_private_ip_url_rejected(self):
        """Test that private IP URLs are rejected."""
        private_urls = [
            "http://192.168.1.1/",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
        ]

        for url in private_urls:
            is_valid, error = SecurityValidator.validate_url(url)

            assert is_valid is False

    def test_missing_domain_rejected(self):
        """Test that URLs without domain/netloc are rejected."""
        # URL with scheme but no domain
        is_valid, error = SecurityValidator.validate_url("http://")

        assert is_valid is False
        assert "domain" in error.lower()


class TestLogSanitization:
    """Test suite for log message sanitization."""

    def test_uuid_masked(self):
        """Test that UUIDs are masked in log messages."""
        message = "Proxy 12345678-1234-5678-9abc-123456789abc failed"
        sanitized = SecurityValidator.sanitize_log_message(message, mask_patterns=True)

        assert "12345678-1234-5678-9abc-123456789abc" not in sanitized
        assert "[UUID]" in sanitized

    def test_password_in_url_masked(self):
        """Test that passwords in URLs are masked."""
        message = "Connecting to http://user:password123@valid-proxy-domain.com/"
        sanitized = SecurityValidator.sanitize_log_message(message, mask_patterns=True)

        assert "password123" not in sanitized
        assert "[MASKED]" in sanitized

    def test_base64_data_masked(self):
        """Test that long base64 strings are masked."""
        message = (
            "Decoded: VGhpc0lzQVRlc3RTdHJpbmdXaXRoTG9uZ0Jhc2U2NEVuY29kaW5nVGhhdFNob3VsZEJlTWFza2Vk"
        )
        sanitized = SecurityValidator.sanitize_log_message(message, mask_patterns=True)

        assert "[BASE64]" in sanitized

    def test_no_masking_when_disabled(self):
        """Test that masking can be disabled."""
        message = "Proxy 1234-5678-9abc-def012345678 with password:secret@host"
        sanitized = SecurityValidator.sanitize_log_message(message, mask_patterns=False)

        assert sanitized == message

    def test_multiple_patterns_masked(self):
        """Test that multiple patterns are masked in one message."""
        message = (
            "UUID: 12345678-1234-1234-1234-123456789abc "
            "Password: user:secret@host "
            "Data: VGhpc0lzQVRlc3RTdHJpbmdXaXRoTG9uZ0Jhc2U2NEVuY29kaW5n"
        )
        sanitized = SecurityValidator.sanitize_log_message(message, mask_patterns=True)

        assert "[UUID]" in sanitized
        assert "[MASKED]" in sanitized
        assert "[BASE64]" in sanitized
        assert "secret" not in sanitized


class TestBatchValidation:
    """Test suite for batch proxy validation."""

    def test_batch_filters_insecure_proxies(self):
        """Test that batch validation filters out insecure proxies."""
        proxies = [
            Proxy(
                config="vmess://safe1",
                protocol="vmess",
                address="valid-proxy-domain.com",
                port=443,
                uuid="uuid1",
            ),
            Proxy(
                config="vmess://unsafe",
                protocol="vmess",
                address="localhost",
                port=22,
                uuid="uuid2",
            ),
            Proxy(
                config="vless://safe2",
                protocol="vless",
                address="another-valid-proxy.net",
                port=8080,
                uuid="uuid3",
            ),
        ]

        secure_proxies = validate_batch_configs(proxies, policy=TEST_POLICY)

        assert len(secure_proxies) == 2
        assert all(p.address not in ["localhost"] for p in secure_proxies)

    def test_batch_validation_marks_insecure_proxies(self):
        """Test that insecure proxies are marked with is_secure=False."""
        proxies = [
            Proxy(
                config="vmess://test",
                protocol="vmess",
                address="127.0.0.1",
                port=443,
                uuid="uuid1",
            ),
        ]

        validate_batch_configs(proxies, policy=STRICT_POLICY)

        assert proxies[0].is_secure is False
        assert len(proxies[0].security_issues) > 0

    def test_batch_validation_preserves_secure_proxies(self):
        """Test that secure proxies pass through unchanged."""
        proxies = [
            Proxy(
                config="vmess://test",
                protocol="vmess",
                address="valid-proxy-domain.com",
                port=443,
                uuid="uuid1",
            ),
        ]

        secure_proxies = validate_batch_configs(proxies, policy=TEST_POLICY)

        assert len(secure_proxies) == 1
        assert secure_proxies[0].address == "valid-proxy-domain.com"

    def test_empty_batch_returns_empty_list(self):
        """Test that empty batch returns empty list."""
        secure_proxies = validate_batch_configs([], policy=TEST_POLICY)

        assert secure_proxies == []

    def test_all_insecure_batch_returns_empty_list(self):
        """Test that batch with all insecure proxies returns empty list."""
        proxies = [
            Proxy(
                config="vmess://test",
                protocol="vmess",
                address="localhost",
                port=22,
                uuid="uuid1",
            ),
            Proxy(
                config="vmess://test",
                protocol="vmess",
                address="127.0.0.1",
                port=23,
                uuid="uuid2",
            ),
        ]

        secure_proxies = validate_batch_configs(proxies)

        assert len(secure_proxies) == 0
