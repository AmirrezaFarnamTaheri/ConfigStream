import time

from configstream.security.rate_limiter import RateLimiter


def test_rate_limiter_allows_initial_requests():
    limiter = RateLimiter(requests_per_second=10)
    # The bucket is initialized with a full set of tokens
    limiter.buckets["test"] = {"tokens": 10, "last_update": time.time()}
    for _ in range(10):
        assert limiter.is_allowed("test")


def test_rate_limiter_denies_exceeded_requests():
    limiter = RateLimiter(requests_per_second=10)
    limiter.buckets["test"] = {"tokens": 10, "last_update": time.time()}
    for _ in range(10):
        limiter.is_allowed("test")
    assert not limiter.is_allowed("test")


def test_rate_limiter_refills_tokens():
    limiter = RateLimiter(requests_per_second=1)
    limiter.buckets["test"] = {"tokens": 1, "last_update": time.time()}
    assert limiter.is_allowed("test")
    assert not limiter.is_allowed("test")
    time.sleep(1.1)
    assert limiter.is_allowed("test")


def test_get_wait_time_full_bucket():
    limiter = RateLimiter(requests_per_second=10)
    limiter.buckets["test"] = {"tokens": 10, "last_update": time.time()}
    assert limiter.get_wait_time("test") <= 0


def test_get_wait_time_partial_bucket():
    limiter = RateLimiter(requests_per_second=10)
    limiter.buckets["test"] = {"tokens": 5, "last_update": time.time()}
    # Consume some tokens
    for _ in range(5):
        limiter.is_allowed("test")

    wait_time = limiter.get_wait_time("test")
    assert wait_time > 0
    # Expected wait time for 1 token at a rate of 10/sec is 0.1s
    # After consuming 5 tokens, we have 0 left. The next one should be available in ~0.1s
    assert 0.09 < wait_time < 0.11
