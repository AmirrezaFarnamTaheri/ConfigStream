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
