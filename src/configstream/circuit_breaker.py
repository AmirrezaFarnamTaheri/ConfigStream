import time
from enum import Enum
from typing import Dict


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = 0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.monotonic()

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return False
            return True
        return False


class CircuitBreakerManager:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def get_breaker(self, key: str) -> CircuitBreaker:
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker(self._failure_threshold, self._recovery_timeout)
        return self._breakers[key]
