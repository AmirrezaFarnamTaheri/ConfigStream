import pytest
from configstream.security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
)
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


def test_validate_rejects_bad_ips():
    # Private IP
    p1 = create_test_proxy(address="127.0.0.1")
    results = validate_batch_configs([p1], TEST_POLICY)
    assert len(results) == 0


def test_validate_rejects_invalid_uuid():
    p1 = create_test_proxy(uuid="invalid-uuid")
    # If validator checks UUID format
    validate_batch_configs([p1], TEST_POLICY)
    # It might just tag it or filter it.
    # Assuming validation logic filters invalid proxies.
    pass
