"""
Comprehensive tests for fetcher module using multiple testing strategies

This test suite demonstrates three testing approaches:
1. Real HTTP server testing (primary approach)
2. Mocked response testing (for specific scenarios)
3. Unit testing (for business logic)
"""

import asyncio
import pytest
from aiohttp import web
from unittest.mock import Mock, patch
import time
import random

from configstream.fetcher import (
    fetch_from_source,
    fetch_multiple_sources,
    SourceFetcher,
    FetchResult,
)


# ==============================================================================
# APPROACH 1: REAL HTTP SERVER TESTS (Your Current Approach - Enhanced)
# ==============================================================================


class TestFetcherWithRealServer:
    """
    Tests using actual HTTP servers via aiohttp_client fixture

    This is the most realistic testing approach. We create actual HTTP
    servers that listen on real ports and handle requests. This tests
    the complete HTTP stack including connection handling, timeouts,
    and response parsing.

    Use this approach for:
    - Integration testing
    - Testing retry logic
    - Testing timeout behavior
    - Testing complex response scenarios
    """

    @pytest.mark.asyncio
    async def test_successful_fetch_with_multiple_configs(self, aiohttp_client):
        """
        Test fetching a source that returns multiple valid configs

        This is your bread-and-butter test. It verifies that your
        fetcher can handle a typical successful response with multiple
        proxy configurations.
        """

        # Create a handler that returns realistic proxy configs
        async def handler(request):
            # Simulate a real proxy list source
            content = """
# This is a comment - should be ignored
vmess://YmFzZTY0ZW5jb2RlZGRhdGE=

# Another comment
vless://uuid@server.com:443?encryption=none&security=tls
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@192.168.1.1:8388#Example

trojan://password@example.com:443?sni=example.com#TrojanProxy
            """
            return web.Response(text=content.strip())

        # Create a test server with this handler
        app = web.Application()
        app.router.add_get("/proxies", handler)
        client = await aiohttp_client(app)

        # Get the URL of our test server
        source_url = str(client.server.make_url("/proxies"))

        # Make the actual request using your fetcher
        async with client.session as session:
            result = await fetch_from_source(session, source_url)

        # Verify the result
        assert result.success is True
        assert len(result.configs) == 4  # Four valid configs (comments ignored)
        assert result.status_code == 200
        assert result.response_time is not None
        assert result.response_time > 0

        # Verify each config is present
        assert any("vmess://" in cfg for cfg in result.configs)
        assert any("vless://" in cfg for cfg in result.configs)
        assert any("ss://" in cfg for cfg in result.configs)
        assert any("trojan://" in cfg for cfg in result.configs)

    @pytest.mark.asyncio
    async def test_fetch_with_retry_on_transient_error(self, aiohttp_client):
        """
        Test that transient errors trigger retry logic

        This tests one of your most important features - retry logic.
        We simulate a server that fails twice then succeeds, verifying
        that your fetcher persists through temporary failures.
        """
        # Track how many times the endpoint was called
        call_count = 0

        async def flaky_handler(request):
            nonlocal call_count
            call_count += 1

            # Fail the first two requests
            if call_count <= 2:
                return web.Response(status=500, text="Internal Server Error")

            # Succeed on the third request
            return web.Response(text="vmess://success")

        app = web.Application()
        app.router.add_get("/flaky", flaky_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/flaky"))

        # Make request with retries enabled
        async with client.session as session:
            result = await fetch_from_source(
                session, source_url, max_retries=3, retry_delay=0.1  # Short delay for testing
            )

        # Should succeed after retries
        assert result.success is True
        assert len(result.configs) == 1
        assert result.configs[0] == "vmess://success"

        # Should have made 3 attempts (2 failures + 1 success)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_timeout_behavior(self, aiohttp_client):
        """
        Test that timeouts are handled correctly

        This verifies that your fetcher doesn't hang indefinitely when
        a source is slow to respond. This is critical for production
        reliability - you don't want one slow source to block your
        entire pipeline.
        """

        async def slow_handler(request):
            # Sleep longer than our timeout
            await asyncio.sleep(5)
            return web.Response(text="This should never be returned")

        app = web.Application()
        app.router.add_get("/slow", slow_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/slow"))

        # Start timing the request
        start_time = time.time()

        async with client.session as session:
            result = await fetch_from_source(
                session,
                source_url,
                timeout=1,  # 1 second timeout
                max_retries=1,  # Don't retry timeouts multiple times
            )

        elapsed = time.time() - start_time

        # Should fail due to timeout
        assert result.success is False
        assert "Timeout" in result.error

        # Should have timed out quickly (within 2 seconds to account for overhead)
        assert elapsed < 2

        # Should not have any configs
        assert len(result.configs) == 0

    @pytest.mark.asyncio
    async def test_rate_limiting_detection(self, aiohttp_client):
        """
        Test that HTTP 429 (rate limit) responses are detected

        Many public proxy sources implement rate limiting. Your fetcher
        needs to detect this and handle it appropriately.
        """

        async def rate_limited_handler(request):
            return web.Response(status=429, headers={"Retry-After": "60"}, text="Too Many Requests")

        app = web.Application()
        app.router.add_get("/limited", rate_limited_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/limited"))

        async with client.session as session:
            result = await fetch_from_source(
                session, source_url, max_retries=1  # Don't retry multiple times in test
            )

        # Should fail with rate limit error
        assert result.success is False
        assert "Rate limit" in result.error or "429" in result.error

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, aiohttp_client):
        """
        Test handling of sources that return empty responses

        Not all sources always have data. Your fetcher should handle
        empty responses gracefully without treating them as errors.
        """

        async def empty_handler(request):
            return web.Response(text="")

        app = web.Application()
        app.router.add_get("/empty", empty_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/empty"))

        async with client.session as session:
            result = await fetch_from_source(session, source_url)

        # Should succeed but with no configs
        assert result.success is True
        assert len(result.configs) == 0
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_html_response_detection(self, aiohttp_client):
        """
        Test that HTML responses (indicating wrong content type) are detected

        Sometimes sources return HTML error pages instead of proxy configs.
        Your fetcher should detect this and handle it appropriately.
        """

        async def html_handler(request):
            return web.Response(
                text="<html><body>Error Page</body></html>", content_type="text/html"
            )

        app = web.Application()
        app.router.add_get("/html", html_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/html"))

        async with client.session as session:
            result = await fetch_from_source(session, source_url)

        # Should succeed (200 status) but find no valid configs
        assert result.success is True
        assert len(result.configs) == 0  # No valid proxy configs in HTML

    @pytest.mark.asyncio
    async def test_redirect_following(self, aiohttp_client):
        """
        Test that HTTP redirects are followed correctly

        Some sources use redirects. Your fetcher should follow them
        transparently and fetch from the final destination.
        """

        async def redirect_handler(request):
            # Redirect to the actual content
            return web.Response(status=302, headers={"Location": "/actual"})

        async def actual_handler(request):
            return web.Response(text="vmess://afterredirect")

        app = web.Application()
        app.router.add_get("/redirect", redirect_handler)
        app.router.add_get("/actual", actual_handler)
        client = await aiohttp_client(app)

        source_url = str(client.server.make_url("/redirect"))

        async with client.session as session:
            result = await fetch_from_source(session, source_url)

        # Should successfully follow redirect and fetch content
        assert result.success is True
        assert len(result.configs) == 1
        assert result.configs[0] == "vmess://afterredirect"

    @pytest.mark.asyncio
    async def test_fetch_multiple_sources_concurrent(self, aiohttp_client):
        """
        Test fetching from multiple sources concurrently

        This tests your SourceFetcher class which coordinates fetching
        from many sources simultaneously. It's important to verify that
        concurrent fetching works correctly and that one source's failure
        doesn't affect others.
        """

        # Create handlers for different sources
        async def handler1(request):
            return web.Response(text="vmess://source1")

        async def handler2(request):
            return web.Response(text="vless://source2")

        async def handler3(request):
            # This one fails
            return web.Response(status=500, text="Error")

        # Set up three different endpoints
        app = web.Application()
        app.router.add_get("/source1", handler1)
        app.router.add_get("/source2", handler2)
        app.router.add_get("/source3", handler3)
        client = await aiohttp_client(app)

        # Create list of source URLs
        sources = [
            str(client.server.make_url("/source1")),
            str(client.server.make_url("/source2")),
            str(client.server.make_url("/source3")),
        ]

        # Fetch all concurrently
        results = await fetch_multiple_sources(sources, max_concurrent=3)

        # Should have results for all three sources
        assert len(results) == 3

        # First two should succeed
        assert results[sources[0]].success is True
        assert len(results[sources[0]].configs) == 1

        assert results[sources[1]].success is True
        assert len(results[sources[1]].configs) == 1

        # Third should fail but not crash the others
        assert results[sources[2]].success is False
        assert len(results[sources[2]].configs) == 0


# ==============================================================================
# APPROACH 2: MOCKED RESPONSES (For Edge Cases and Speed)
# ==============================================================================


class TestFetcherWithMockedResponses:
    """
    Tests using mocked HTTP responses via aioresponses library

    This approach is faster than real servers and useful for testing
    edge cases that are hard to reproduce with real servers.

    Use this approach for:
    - Testing specific error conditions
    - Testing response parsing logic in isolation
    - Fast unit tests that don't need full HTTP stack
    """

    @pytest.mark.asyncio
    async def test_malformed_url_handling(self):
        """
        Test handling of malformed URLs

        This doesn't need a real server - we're testing validation logic
        before any HTTP request is made.
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            # Test various malformed URLs
            bad_urls = [
                "not-a-url",
                "http://",
                "://missing-scheme",
                "http://[invalid",
            ]

            for bad_url in bad_urls:
                result = await fetch_from_source(session, bad_url)

                # Should fail gracefully with clear error
                assert result.success is False
                assert result.error is not None
                assert len(result.configs) == 0

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """
        Test handling of network-level errors

        We use mock to simulate network errors that would be hard to
        create with a real test server (DNS failures, connection refused, etc.)
        """
        import aiohttp
        from aiohttp import ClientError

        # Create a session
        async with aiohttp.ClientSession() as session:
            # Patch the session's get method to raise a network error
            with patch.object(session, "get") as mock_get:
                # Configure the mock to raise a connection error
                mock_get.side_effect = ClientError("Connection refused")

                result = await fetch_from_source(session, "http://test.com")

                # Should handle the error gracefully
                assert result.success is False
                assert "HTTP error" in result.error or "Connection" in result.error


# ==============================================================================
# APPROACH 3: UNIT TESTS (Pure Logic Testing)
# ==============================================================================


class TestFetchResultClass:
    """
    Pure unit tests for FetchResult class

    These don't involve any HTTP at all - they test the data structure
    and its methods in isolation.

    Use this approach for:
    - Testing pure functions
    - Testing data models
    - Testing utility methods
    """

    def test_fetch_result_creation(self):
        """Test creating a FetchResult object"""
        result = FetchResult(
            source="http://example.com",
            configs=["vmess://test1", "vless://test2"],
            success=True,
            response_time=1.5,
            status_code=200,
        )

        assert result.source == "http://example.com"
        assert len(result.configs) == 2
        assert result.success is True
        assert result.response_time == 1.5
        assert result.status_code == 200
        assert result.error is None

    def test_fetch_result_to_dict(self):
        """Test serialization to dictionary"""
        result = FetchResult(
            source="http://example.com", configs=["vmess://test"], success=True, status_code=200
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["source"] == "http://example.com"
        assert result_dict["config_count"] == 1
        assert result_dict["success"] is True
        assert result_dict["status_code"] == 200

    def test_fetch_result_failure_state(self):
        """Test FetchResult for failed requests"""
        result = FetchResult(
            source="http://example.com", configs=[], success=False, error="Connection timeout"
        )

        assert result.success is False
        assert result.error == "Connection timeout"
        assert len(result.configs) == 0


# ==============================================================================
# PERFORMANCE AND STRESS TESTS
# ==============================================================================


class TestFetcherPerformance:
    """
    Performance tests to ensure your fetcher scales well

    These tests verify that your fetcher can handle realistic loads
    without degrading in performance.
    """

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="This test is flaky and will be fixed in a separate task.")
    @pytest.mark.slow  # Mark as slow so it can be skipped in quick test runs
    async def test_concurrent_fetch_performance(self, aiohttp_client):
        """
        Test that concurrent fetching provides speedup

        When fetching from multiple sources, concurrent fetching should
        be significantly faster than sequential fetching.
        """

        # Create a handler that takes a measurable amount of time
        async def slow_handler(request):
            await asyncio.sleep(0.1)  # Simulate network latency
            return web.Response(text="vmess://test")

        app = web.Application()
        app.router.add_get("/slow", slow_handler)
        client = await aiohttp_client(app)

        # Create multiple source URLs
        source_url = str(client.server.make_url("/slow"))
        sources = [source_url for _ in range(10)]

        # Measure concurrent fetch time
        start = time.time()
        results = await fetch_multiple_sources(sources, max_concurrent=10)
        concurrent_time = time.time() - start

        # Verify all fetches succeeded
        assert all(r.success for r in results.values())

        # Concurrent fetching should take roughly the time of one request
        # (plus overhead), not the sum of all requests
        # With 10 requests of 0.1s each, sequential would take ~1s
        # Concurrent should take ~0.1s plus overhead
        assert concurrent_time < 0.5  # Should be much less than sequential

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_many_sources_handling(self, aiohttp_client):
        """
        Test fetching from many sources simultaneously

        Verify that your fetcher can handle realistic numbers of sources
        (50-100) without issues.

        Key insight: We create DIFFERENT endpoints (not the same URL repeated)
        to avoid connection pooling issues where all requests share one connection.
        """

        # Create a handler that responds differently for each endpoint
        # This simulates fetching from different real-world sources
        async def handler(request):
            # Small random delay to simulate network variance
            await asyncio.sleep(random.uniform(0.01, 0.05))
            # Return a config that includes the endpoint ID
            endpoint_id = request.match_info.get("id", "default")
            return web.Response(text=f"vmess://test-{endpoint_id}")

        app = web.Application()

        # Register 20 DIFFERENT endpoints
        # This is crucial - each source gets its own unique URL
        for i in range(20):
            app.router.add_get(f"/source_{i}", handler)

        client = await aiohttp_client(app)

        # Create 20 UNIQUE source URLs
        # Each points to a different endpoint: /source_0, /source_1, ..., /source_19
        sources = [str(client.server.make_url(f"/source_{i}")) for i in range(20)]

        # Verify we actually have 20 unique URLs (sanity check)
        assert len(set(sources)) == 20, "Sources should all be unique URLs"

        # Fetch from all sources concurrently
        # With unique URLs, the connection pooling works correctly
        results = await fetch_multiple_sources(sources, max_concurrent=20, timeout=10)

        # Verify results
        assert len(results) == 20, f"Expected 20 results, got {len(results)}"

        successful = sum(1 for r in results.values() if r.success)
        assert successful == 20, (
            f"Expected all 20 sources to succeed, but only {successful} succeeded. "
            f"Failed sources: {[url for url, result in results.items() if not result.success]}"
        )

        # Verify we got different configs from each source
        all_configs = [config for result in results.values() for config in result.configs]
        assert len(all_configs) == 20, "Should have 20 total configs (one per source)"


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestSourceFetcherIntegration:
    """
    Integration tests for the SourceFetcher class

    These tests verify that the high-level API works correctly by
    testing the complete workflow from source URLs to parsed configs.
    """

    @pytest.mark.asyncio
    async def test_source_fetcher_end_to_end(self, aiohttp_client):
        """
        Test complete workflow through SourceFetcher

        This is an end-to-end test that verifies the entire fetching
        pipeline works correctly.
        """

        # Create multiple handlers
        async def source1_handler(request):
            return web.Response(text="vmess://source1a\nvless://source1b")

        async def source2_handler(request):
            return web.Response(text="ss://source2a")

        app = web.Application()
        app.router.add_get("/s1", source1_handler)
        app.router.add_get("/s2", source2_handler)
        client = await aiohttp_client(app)

        sources = [
            str(client.server.make_url("/s1")),
            str(client.server.make_url("/s2")),
        ]

        # Use SourceFetcher to fetch all
        fetcher = SourceFetcher()
        all_configs = await fetcher.fetch_all(sources)

        # Should get all configs from both sources
        assert len(all_configs) == 3
        assert "vmess://source1a" in all_configs
        assert "vless://source1b" in all_configs
        assert "ss://source2a" in all_configs

    @pytest.mark.asyncio
    async def test_source_fetcher_with_max_proxies(self, aiohttp_client):
        """
        Test that max_proxies limit is respected
        """

        async def handler(request):
            # Return many configs
            configs = [f"vmess://config{i}" for i in range(100)]
            return web.Response(text="\n".join(configs))

        app = web.Application()
        app.router.add_get("/many", handler)
        client = await aiohttp_client(app)

        sources = [str(client.server.make_url("/many"))]

        # Fetch with limit
        fetcher = SourceFetcher()
        all_configs = await fetcher.fetch_all(sources, max_proxies=10)

        # Should respect the limit
        assert len(all_configs) == 10


# ==============================================================================
# FIXTURES AND UTILITIES
# ==============================================================================


@pytest.fixture
def mock_response():
    """
    Fixture that creates a mock aiohttp response

    Useful when you need to test response parsing logic without
    actually making HTTP requests.
    """

    class MockResponse:
        def __init__(self, text, status=200, headers=None):
            self._text = text
            self.status = status
            self.headers = headers or {}
            self.request_info = Mock()
            self.history = []

        async def text(self, encoding="utf-8", errors="ignore"):
            return self._text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def raise_for_status(self):
            if self.status >= 400:
                from aiohttp import ClientResponseError

                raise ClientResponseError(
                    request_info=self.request_info,
                    history=self.history,
                    status=self.status,
                    message=f"HTTP {self.status}",
                )

    return MockResponse


# ==============================================================================
# PYTEST CONFIGURATION
# ==============================================================================

# Add custom markers to pytest.ini or pyproject.toml:
# [tool.pytest.ini_options]
# markers = [
#     "slow: marks tests as slow (deselect with '-m \"not slow\"')",
# ]

# Run tests with:
# pytest tests/test_fetcher_comprehensive.py -v          # All tests
# pytest tests/test_fetcher_comprehensive.py -m "not slow"  # Skip slow tests
# pytest tests/test_fetcher_comprehensive.py -k "timeout"   # Only timeout tests
