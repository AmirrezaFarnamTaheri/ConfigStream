# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import asyncio
from configstream.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerManager,
)


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_initial_state(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state == CircuitBreakerState.CLOSED
        assert not await cb.is_open()

    @pytest.mark.asyncio
    async def test_state_transition(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        await cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert not await cb.is_open()

        await cb.record_failure()
        # Should now be OPEN (threshold reached)
        assert cb.state == CircuitBreakerState.OPEN
        assert await cb.is_open()

    @pytest.mark.asyncio
    async def test_recovery(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        await cb.record_failure()
        assert await cb.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should transition to HALF_OPEN on check
        assert not await cb.is_open()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Success should reset to CLOSED
        await cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        await cb.record_failure()
        await asyncio.sleep(0.15)

        assert not await cb.is_open()  # Transitions to HALF_OPEN

        # Failure in HALF_OPEN should immediately trip back to OPEN
        await cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert await cb.is_open()

    @pytest.mark.asyncio
    async def test_cancelled_probe_does_not_wedge_breaker(self):
        """A HALF_OPEN probe that is cancelled must release the probe token.

        Without reset_probe(), _probe_in_flight would stay True forever and
        is_open() would block every future request to the host.
        """
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        await cb.record_failure()
        await asyncio.sleep(0.15)

        # First caller is elected as the probe (allowed through).
        assert not await cb.is_open()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb._probe_in_flight is True
        # A concurrent caller is blocked while the probe is in flight.
        assert await cb.is_open()

        # The probe request is cancelled before recording an outcome.
        await cb.reset_probe()
        assert cb._probe_in_flight is False
        assert cb.state == CircuitBreakerState.OPEN

        # After the recovery window a fresh probe can be elected again.
        await asyncio.sleep(0.15)
        assert not await cb.is_open()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_reset_probe_noop_when_no_probe(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        # No probe in flight; reset must be a harmless no-op.
        await cb.reset_probe()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._probe_in_flight is False


class TestCircuitBreakerManager:
    @pytest.mark.asyncio
    async def test_get_breaker(self):
        manager = CircuitBreakerManager()
        cb1 = await manager.get_breaker("host1")
        cb2 = await manager.get_breaker("host1")
        cb3 = await manager.get_breaker("host2")

        assert cb1 is cb2
        assert cb1 is not cb3
