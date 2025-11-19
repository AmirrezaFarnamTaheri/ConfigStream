from collections import defaultdict
from time import monotonic
from typing import DefaultDict, Dict


class RateLimiter:
    """Token bucket rate limiter for proxy testing"""

    def __init__(self, requests_per_second: float = 10) -> None:
        self.rate = requests_per_second
        self.buckets: DefaultDict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": 0.0, "last_update": monotonic()}
        )

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        current_time = monotonic()
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

    def get_wait_time(self, identifier: str) -> float:
        """Get seconds to wait before next allowed request"""
        bucket = self.buckets[identifier]
        return (1 - bucket["tokens"]) / self.rate

    def cleanup(self, max_age: int = 3600) -> None:
        """Remove buckets that haven't been used recently."""
        current_time = monotonic()
        keys_to_delete = [
            key
            for key, bucket in self.buckets.items()
            if current_time - bucket["last_update"] > max_age
        ]
        for key in keys_to_delete:
            del self.buckets[key]
