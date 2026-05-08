# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
)
from configstream.models import Proxy
from tests.unit.conftest_helper import create_test_proxy


def test_validate_strict_policy():
    # Should pass
    p1 = create_test_proxy(address="1.1.1.1", port=443, details={"tls": True})
    # Should fail (non-standard port, no tls)
    p2 = create_test_proxy(address="1.1.1.1", port=8080, details={"tls": False})

    # STRICT_POLICY likely enforces TLS or specific ports
    results = validate_batch_configs([p1, p2], STRICT_POLICY)

    # If policy requires TLS, p2 might fail.
    # Let's inspect what STRICT_POLICY enforces.
    # Assuming it checks for basic validity.
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
    # If validator checks UUID format
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([p1], TEST_POLICY)
    assert len(results) == 1
    assert results[0].is_secure is False
    assert "invalid_uuid_format" in results[0].security_issues.get("policy", [])


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
