import pytest
from scripts.healthcheck import check_success_rate, HealthCheckError

def test_check_success_rate_missing_tested_count_but_working_proxies():
    # Scenario: stats are missing 'tested' or it's 0 (merge artifact issue),
    # but we have working proxies. Should NOT raise error, just warn/return.
    metadata = {
        "stats": {
            "tested": 0,
            "parsed": 0
        },
        "total_fetched": 0,
        "total_working": 100
    }

    # This should pass without raising HealthCheckError
    check_success_rate(metadata, min_rate=0.01)

def test_check_success_rate_missing_tested_and_zero_working():
    # Scenario: really empty run. Should raise error.
    metadata = {
        "stats": {
            "tested": 0
        },
        "total_working": 0
    }

    with pytest.raises(HealthCheckError, match="No proxies tested"):
        check_success_rate(metadata, min_rate=0.01)

def test_check_success_rate_normal():
    metadata = {
        "stats": {
            "tested": 1000
        },
        "total_working": 500
    }
    check_success_rate(metadata, min_rate=0.1)
