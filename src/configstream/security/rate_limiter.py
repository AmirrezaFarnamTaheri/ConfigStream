import asyncio
from collections import defaultdict
from time import time
from typing import DefaultDict, Dict


class RateLimiter:
    """Token bucket rate limiter for proxy testing (async-safe)"""

    # Maximum number of unique identifiers to track (prevents unbounded memory growth)
    MAX_BUCKETS = 10000
    # Cleanup threshold - when to trigger cleanup
    CLEANUP_THRESHOLD = 8000
    # How old an unused bucket must be before eviction (seconds)
    BUCKET_EXPIRY = 3600  # 1 hour

    def __init__(self, requests_per_second: float = 10) -> None:
        self.rate = requests_per_second
        self.buckets: DefaultDict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": 0.0, "last_update": time()}
        )
        self._lock = asyncio.Lock()
        self._last_cleanup = time()

    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed (async-safe with lock)"""
        async with self._lock:
            current_time = time()

            # Periodic cleanup to prevent unbounded memory growth
            if len(self.buckets) > self.CLEANUP_THRESHOLD:
                await self._cleanup_expired_buckets(current_time)

            bucket = self.buckets[identifier]

            # Add tokens based on time elapsed
            time_passed = current_time - bucket["last_update"]
            bucket["tokens"] += time_passed * self.rate
            bucket["tokens"] = min(bucket["tokens"], self.rate)  # Cap at rate
            bucket["last_update"] = current_time

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True

            return False

    async def _cleanup_expired_buckets(self, current_time: float) -> None:
        """Remove buckets that haven't been accessed recently (called with lock held)."""
        expired_keys = [
            key
            for key, bucket in self.buckets.items()
            if current_time - bucket["last_update"] > self.BUCKET_EXPIRY
        ]
        for key in expired_keys:
            del self.buckets[key]

        # If still too many, remove oldest entries
        if len(self.buckets) > self.MAX_BUCKETS:
            sorted_buckets = sorted(
                self.buckets.items(), key=lambda x: x[1]["last_update"]
            )
            to_remove = (
                len(self.buckets) - self.MAX_BUCKETS + 100
            )  # Remove extra buffer
            for key, _ in sorted_buckets[:to_remove]:
                del self.buckets[key]

    async def get_wait_time(self, identifier: str) -> float:
        """Get seconds to wait before next allowed request (async-safe)"""
        async with self._lock:
            bucket = self.buckets[identifier]
            return (1 - bucket["tokens"]) / self.rate
