import time

from configstream.security.rate_limiter import RateLimiter


from unittest.mock import patch
import time

def test_rate_limiter_allows_initial_requests():
    limiter = RateLimiter(requests_per_second=10)
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = time.monotonic()
        for i in range(10):
            assert limiter.is_allowed("test")
            mock_monotonic.return_value += 0.01


def test_rate_limiter_denies_exceeded_requests():
    limiter = RateLimiter(requests_per_second=10)
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = time.monotonic()
        for i in range(10):
            assert limiter.is_allowed("test")
            mock_monotonic.return_value += 0.01
        assert not limiter.is_allowed("test")


def test_rate_limiter_refills_tokens():
    limiter = RateLimiter(requests_per_second=1)
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = time.monotonic()
        assert limiter.is_allowed("test")
        assert not limiter.is_allowed("test")
        mock_monotonic.return_value += 1.1
        assert limiter.is_allowed("test")


def test_get_wait_time_full_bucket():
    limiter = RateLimiter(requests_per_second=10)
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = time.monotonic()
        for _ in range(10):
            assert limiter.is_allowed("test")
            mock_monotonic.return_value += 0.01
        assert limiter.get_wait_time("test") > 0


def test_get_wait_time_partial_bucket():
    limiter = RateLimiter(requests_per_second=10)
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = time.monotonic()
        for i in range(5):
            assert limiter.is_allowed("test")
            mock_monotonic.return_value += 0.01
        wait_time = limiter.get_wait_time("test")
        assert 0.04 < wait_time < 0.06
