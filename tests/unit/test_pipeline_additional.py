"""Additional pipeline tests to improve coverage."""

from configstream.pipeline import _normalise_source_url, _prepare_sources, SourceValidationError
import pytest


def test_normalise_source_url_valid():
    """Test URL normalization with valid inputs."""
    # HTTP URL
    result = _normalise_source_url("http://example.com/proxies.txt")
    assert result == "http://example.com/proxies.txt"

    # HTTPS URL
    result = _normalise_source_url("https://example.com/proxies.txt")
    assert result == "https://example.com/proxies.txt"

    # File path
    result = _normalise_source_url("/path/to/file.txt")
    assert result == "/path/to/file.txt"


def test_normalise_source_url_with_whitespace():
    """Test URL normalization strips whitespace."""
    result = _normalise_source_url("  https://example.com/test  ")
    assert result == "https://example.com/test"


def test_normalise_source_url_empty():
    """Test empty URL raises error."""
    with pytest.raises(SourceValidationError):
        _normalise_source_url("")

    with pytest.raises(SourceValidationError):
        _normalise_source_url("   ")


def test_normalise_source_url_too_long():
    """Test very long URL raises error."""
    long_url = "http://" + "a" * 10000
    with pytest.raises(SourceValidationError):
        _normalise_source_url(long_url)


def test_normalise_source_url_invalid_scheme():
    """Test invalid scheme raises error."""
    with pytest.raises(SourceValidationError):
        _normalise_source_url("ftp://example.com/file.txt")


def test_prepare_sources_removes_duplicates():
    """Test source preparation removes duplicates."""
    sources = [
        "http://example.com/1",
        "http://example.com/1",  # duplicate
        "http://example.com/2",
    ]

    result = _prepare_sources(sources)

    assert len(result) == 2
    assert "http://example.com/1" in result
    assert "http://example.com/2" in result


def test_prepare_sources_filters_invalid():
    """Test source preparation filters invalid URLs."""
    sources = [
        "http://example.com/valid",
        "",  # empty
        "ftp://invalid.com",  # invalid scheme
    ]

    result = _prepare_sources(sources)

    # Should only include valid URL
    assert len(result) == 1
    assert "http://example.com/valid" in result


from configstream.models import Proxy
from configstream.pipeline import dedupe_and_shuffle


class TestDeduplication:
    def create_proxy(
        self,
        is_working: bool,
        latency: float | None,
        config: str,
        protocol="vless",
        address="test.com",
        port=443,
        uuid="uuid",
        sni="",
        path="",
    ) -> Proxy:
        """Helper to create a proxy for testing."""
        return Proxy(
            is_working=is_working,
            latency=latency,
            config=config,
            protocol=protocol,
            address=address,
            port=port,
            uuid=uuid,
            details={"sni": sni, "path": path},
        )

    def test_prefers_working_over_not_working(self):
        # The not working proxy comes first in the list
        p1 = self.create_proxy(False, 200, "config1")  # Not working
        p2 = self.create_proxy(True, 100, "config2")  # Working

        result = dedupe_and_shuffle([p1, p2])
        assert len(result) == 1
        assert result[0].is_working is True
        assert result[0].config == "config2"

    def test_prefers_lower_latency_when_both_working(self):
        p1 = self.create_proxy(True, 200, "config1")  # Higher latency
        p2 = self.create_proxy(True, 100, "config2")  # Lower latency

        result = dedupe_and_shuffle([p1, p2])
        assert len(result) == 1
        assert result[0].latency == 100
        assert result[0].config == "config2"

    def test_prefers_proxy_with_latency_if_one_is_none(self):
        p1 = self.create_proxy(True, None, "config1")  # No latency
        p2 = self.create_proxy(True, 100, "config2")  # Has latency

        result = dedupe_and_shuffle([p1, p2])
        assert len(result) == 1
        assert result[0].latency == 100
        assert result[0].config == "config2"

    def test_prefers_lower_latency_if_both_not_working(self):
        p1 = self.create_proxy(False, 200, "config1")
        p2 = self.create_proxy(False, 100, "config2")

        # Even if both are not working, the one with the better (lower)
        # last-known latency should be preferred.
        result = dedupe_and_shuffle([p1, p2])
        assert len(result) == 1
        assert result[0].config == "config2"

    def test_identifies_duplicates_with_normalized_fields(self):
        # These two proxies are functionally identical, just with different remarks
        # in their config strings, leading to different configs.
        p1 = self.create_proxy(
            True, 100, "vless://uuid@test.com?sni=cdn.com#remark1", sni="cdn.com"
        )
        p2 = self.create_proxy(
            True, 200, "vless://uuid@test.com?sni=cdn.com#remark2", sni="cdn.com"
        )

        result = dedupe_and_shuffle([p2, p1])  # Put higher latency one first
        assert len(result) == 1
        assert result[0].latency == 100  # Should keep the one with lower latency
        assert result[0].config.endswith("#remark1")
