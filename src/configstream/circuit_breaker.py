# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
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
        self.last_failure_time: float = 0.0
        self._lock = asyncio.Lock()
        self._logged_open = False  # Track if we've logged the open state

    async def record_failure(self) -> None:
        """Record a failure (async-safe with lock)"""
        async with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.last_failure_time = time.monotonic()

    async def record_success(self) -> None:
        """Record a success (async-safe with lock)"""
        async with self._lock:
            # In HALF_OPEN, a success resets to CLOSED
            # In CLOSED, it just resets failure count (though likely 0 already)
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED
            self._logged_open = False  # Reset logged state on recovery

    async def is_open(self) -> bool:
        """Check if circuit breaker is open (async-safe with lock)"""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    # Allow a probe request
                    return False
                return True
            # In HALF_OPEN, we allow requests. If they fail, it trips back to OPEN (via record_failure).
            # We don't enforce a strict 'single probe' here to keep it simple, but rely on concurrent
            # requests racing. If one succeeds, it closes. If one fails, it opens.
            return False

    async def should_log_open(self) -> bool:
        """Check if we should log the open state (first time only)."""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN and not self._logged_open:
                self._logged_open = True
                return True
            return False


class CircuitBreakerManager:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._lock = asyncio.Lock()

    async def get_breaker(self, key: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the given key (async-safe with lock)."""
        async with self._lock:
            if key not in self._breakers:
                self._breakers[key] = CircuitBreaker(
                    self._failure_threshold, self._recovery_timeout
                )
            return self._breakers[key]
