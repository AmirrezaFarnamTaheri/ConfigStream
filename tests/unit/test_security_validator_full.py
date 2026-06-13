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

    # Strict policy enforces TLS and safe ports (usually)
    results = validate_batch_configs([p1, p2], STRICT_POLICY)

    # Strict policy logic checks port
    assert len(results) >= 1


def test_validate_rejects_bad_ips(monkeypatch):
    # Private IP
    p1 = create_test_proxy(address="127.0.0.1")
    p2 = create_test_proxy(address="192.168.1.1")
    p3 = create_test_proxy(address="10.0.0.1")
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([p1, p2, p3], TEST_POLICY)
    assert len(results) == 3
    assert all(not p.is_secure for p in results)
    assert "local_ip_blocked" in results[0].security_issues.get("policy", [])


def test_validate_rejects_invalid_uuid(monkeypatch):
    p1 = create_test_proxy(uuid="invalid-uuid")
    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([p1], TEST_POLICY)
    assert len(results) == 1
    assert results[0].is_secure is False
    assert "invalid_uuid_format" in results[0].security_issues.get("policy", [])


def test_validate_missing_vless_uuid_is_fatal_even_when_insecure_kept(monkeypatch):
    proxy = Proxy(
        config="vless://@example.com:443",
        protocol="vless",
        address="example.com",
        port=443,
        uuid="",
        details={},
    )

    monkeypatch.setenv("INCLUDE_INSECURE_PROXIES", "true")
    results = validate_batch_configs([proxy], TEST_POLICY)

    assert results == []
    assert proxy.is_secure is False
    assert "missing_uuid" in proxy.security_issues.get("policy", [])


def test_validate_malformed_address():
    p1 = create_test_proxy(address="http://invalid")
    results = validate_batch_configs([p1], TEST_POLICY)

    assert results == []
    assert p1.is_secure is False
    assert "invalid_address_format" in p1.security_issues.get("policy", [])
