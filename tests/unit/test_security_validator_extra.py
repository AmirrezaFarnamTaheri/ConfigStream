from unittest.mock import patch


def test_validate_url():
    from configstream.security_validator import SecurityValidator

    # Valid
    assert SecurityValidator.validate_url("https://google.com")[0] is True
    assert SecurityValidator.validate_url("http://example.com")[0] is True

    # Invalid
    assert SecurityValidator.validate_url("")[0] is False
    assert SecurityValidator.validate_url("ftp://example.com")[0] is False
    assert SecurityValidator.validate_url("https://")[0] is False

    # Suspicious domain (using default SAFE check)
    # Mocking _is_address_safe to simulate failure
    with patch.object(SecurityValidator, "_is_address_safe", return_value=False):
        assert SecurityValidator.validate_url("https://suspicious.com")[0] is False

    # Exception handling
    with patch(
        "configstream.security_validator.urlparse", side_effect=Exception("Boom")
    ):
        assert SecurityValidator.validate_url("https://google.com")[0] is False


def test_sanitize_log_message():
    from configstream.security_validator import SecurityValidator

    msg = "User 12345678-1234-1234-1234-1234567890ab logged in with pass:secret@host"
    sanitized = SecurityValidator.sanitize_log_message(msg)
    assert "[UUID]" in sanitized
    assert "12345678-" not in sanitized
    assert ":[MASKED]@" in sanitized
    assert "secret" not in sanitized

    # No mask
    assert SecurityValidator.sanitize_log_message(msg, mask_patterns=False) == msg

    # Base64
    b64 = "a" * 30
    msg = f"Data: {b64}"
    sanitized = SecurityValidator.sanitize_log_message(msg)
    assert "[BASE64]" in sanitized


def test_validate_batch_configs():
    from configstream.security_validator import validate_batch_configs
    from configstream.models import Proxy

    proxies = [
        Proxy(protocol="ss", address="1.1.1.1", port=443, config="safe"),
        Proxy(protocol="ss", address="suspicious.com", port=443, config="unsafe"),
    ]

    # Mock validator to fail the second one
    with patch(
        "configstream.security_validator.SecurityValidator.validate_proxy_config"
    ) as mock_val:
        mock_val.side_effect = [(True, {}), (False, {"category": ["issue"]})]

        secure = validate_batch_configs(proxies)
        assert len(secure) == 1
        assert secure[0].address == "1.1.1.1"
        assert proxies[1].is_secure is False
