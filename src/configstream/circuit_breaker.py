import asyncio
import time
import json
import logging
from enum import Enum
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)
CIRCUIT_BREAKER_CACHE_PATH = Path("data/circuit_breakers.json")


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

    def to_dict(self) -> dict:
        """Serialize state for persistence."""
        return {
            "failure_count": self.failure_count,
            "state": self.state.value,
            "last_failure_time": self.last_failure_time,
        }

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

        # Load persisted state on initialization
        self._load_state()

    def _load_state(self) -> None:
        """Load circuit breaker state from disk."""
        try:
            if CIRCUIT_BREAKER_CACHE_PATH.exists():
                data = json.loads(CIRCUIT_BREAKER_CACHE_PATH.read_text())
                for key, state in data.items():
                    breaker = CircuitBreaker(self._failure_threshold, self._recovery_timeout)
                    breaker.failure_count = state.get("failure_count", 0)
                    breaker.state = CircuitBreakerState(state.get("state", "CLOSED"))
                    breaker.last_failure_time = state.get("last_failure_time", 0.0)
                    self._breakers[key] = breaker
                logger.info(f"Loaded {len(self._breakers)} circuit breaker states from disk")
        except Exception as e:
            logger.debug(f"Could not load circuit breaker state: {e}")

    def save_state(self) -> None:
        """Save circuit breaker state to disk."""
        try:
            CIRCUIT_BREAKER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {key: breaker.to_dict() for key, breaker in self._breakers.items()}
            CIRCUIT_BREAKER_CACHE_PATH.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved {len(data)} circuit breaker states to disk")
        except Exception as e:
            logger.warning(f"Could not save circuit breaker state: {e}")

    async def save_state_async(self) -> None:
        """Async wrapper for save_state."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.save_state)

    async def get_breaker(self, key: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the given key (async-safe with lock)."""
        async with self._lock:
            if key not in self._breakers:
                self._breakers[key] = CircuitBreaker(
                    self._failure_threshold, self._recovery_timeout
                )
            return self._breakers[key]
