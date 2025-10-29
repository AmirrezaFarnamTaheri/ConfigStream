import time
from unittest.mock import patch

import pytest

from configstream.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerState,
)


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.is_open is False

    def test_failure_increments_count(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_trips_to_open_state_on_threshold(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.is_open is True

    def test_success_resets_failure_count(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_moves_to_half_open_after_timeout(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.is_open is True

        # Mock time to be in the future
        with patch("time.monotonic", return_value=time.monotonic() + 2):
            assert breaker.is_open is False  # Should now be half-open
            assert breaker.state == CircuitBreakerState.HALF_OPEN

            # A subsequent success should close it
            breaker.record_success()
            assert breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerManager:
    def test_creates_new_breaker_for_new_key(self):
        manager = CircuitBreakerManager()
        breaker1 = manager.get_breaker("host1")
        assert isinstance(breaker1, CircuitBreaker)

        breaker2 = manager.get_breaker("host2")
        assert breaker1 is not breaker2

    def test_returns_same_breaker_for_same_key(self):
        manager = CircuitBreakerManager()
        breaker1 = manager.get_breaker("host1")
        breaker2 = manager.get_breaker("host1")
        assert breaker1 is breaker2
