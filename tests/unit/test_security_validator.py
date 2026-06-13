# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
    SecurityValidator,
)
from configstream.models import Proxy
from tests.unit.conftest_helper import create_test_proxy


def test_validate_strict_policy():
    p1 = create_test_proxy(address="1.1.1.1", port=443, details={"tls": True})
    p2 = create_test_proxy(address="1.1.1.1", port=8080, details={"tls": False})

    results = validate_batch_configs([p1, p2], STRICT_POLICY)

    assert len(results) >= 1


def test_validate_rejects_bad_ips(monkeypatch):
    # Private IP
    p1 = create_test_proxy(address="127.0.0.1")
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([p1], TEST_POLICY)
    assert len(results) == 1
    assert results[0].is_secure is False
    assert "local_ip_blocked" in results[0].security_issues.get("policy", [])


def test_validate_rejects_invalid_uuid(monkeypatch):
    p1 = create_test_proxy(uuid="invalid-uuid")
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([p1], TEST_POLICY)
    assert len(results) == 1
    assert results[0].is_secure is False
    assert "invalid_uuid_format" in results[0].security_issues.get("policy", [])


def test_validate_rejects_protocol_like_address(monkeypatch):
    proxy = create_test_proxy(address="http://invalid")
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")

    results = validate_batch_configs([proxy], TEST_POLICY)

    assert results == []
    assert proxy.is_secure is False
    assert "invalid_address_format" in proxy.security_issues.get("policy", [])


def test_sanitize_masks_url_password_without_masking_plain_prose():
    prose = "Error: Connection failed @ 192.168.1.1:8080"
    assert (
        SecurityValidator.sanitize_log_message(prose)
        == "Error: Connection failed @ [IP]:8080"
    )

    url = "https://user:secret@example.com/path?token=value"
    sanitized = SecurityValidator.sanitize_log_message(url)
    assert "secret" not in sanitized
    assert "value" not in sanitized
    assert "https://user:[MASKED]@example.com/path?token=[MASKED]" == sanitized


def test_validate_missing_vmess_uuid_is_fatal_even_when_insecure_kept(monkeypatch):
    proxy = Proxy(
        config="vmess://missing-uuid",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        uuid="",
        details={},
    )

    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([proxy], TEST_POLICY)

    assert results == []
    assert proxy.is_secure is False
    assert "missing_uuid" in proxy.security_issues.get("policy", [])
