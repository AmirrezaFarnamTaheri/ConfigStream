import pytest
from pathlib import Path
from scripts.healthcheck import (
    check_success_rate,
    check_minimum_proxies,
    HealthCheckError,
)


def test_check_success_rate():
    """Test success rate logic"""
    # 50% success
    metadata = {"stats": {"parsed": 100}, "total_working": 50}
    check_success_rate(metadata, 0.2)  # Should pass

    # 10% success
    metadata = {"stats": {"parsed": 100}, "total_working": 10}
    with pytest.raises(HealthCheckError):
        check_success_rate(metadata, 0.2)

    # Edge case: 0 proxies
    metadata = {"stats": {"parsed": 0}, "total_working": 0}
    with pytest.raises(HealthCheckError):
        check_success_rate(metadata, 0.2)


def test_check_minimum_proxies():
    """Test minimum proxy count"""
    proxies = [{"id": 1}] * 10
    check_minimum_proxies(proxies, 5)  # Should pass

    with pytest.raises(HealthCheckError):
        check_minimum_proxies(proxies, 20)
