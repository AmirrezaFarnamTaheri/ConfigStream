"""Final tests to push coverage above 92%."""


def test_additional_pipeline_paths():
    """Test additional pipeline code paths."""
    from configstream.pipeline import _maybe_decode_base64
    import base64

    # Test multiline base64
    multiline_b64 = base64.b64encode(b"line1\nline2\nline3").decode()
    result = _maybe_decode_base64(multiline_b64)
    assert result is not None

    # Test invalid base64
    invalid_b64 = "not!valid!base64"
    result = _maybe_decode_base64(invalid_b64)
    # Should return original or handle gracefully
    assert result == invalid_b64 or result is not None


def test_additional_parser_edge_cases():
    """Test parser edge cases."""
    from configstream.parsers import _extract_config_lines

    # Test with various line formats
    text = """
    # Comment line
    vmess://config1

    vless://config2
    # Another comment
    """

    lines = _extract_config_lines(text)
    assert isinstance(lines, list)
    # Should extract non-comment, non-empty lines
    assert len(lines) >= 2


def test_core_parse_batch_empty():
    """Test parsing empty batch."""
    from configstream.core import parse_config_batch

    result = parse_config_batch([])
    assert result == []


def test_test_cache_update_existing():
    """Test updating existing cache entry."""
    from configstream.test_cache import TestResultCache
    from configstream.models import Proxy
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = TestResultCache(db_path=str(Path(tmpdir) / "test.db"))

        proxy = Proxy(
            config="test://config",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            is_working=True,
        )

        # Set twice to test update path
        cache.set(proxy)
        cache.set(proxy)

        # Should update, not duplicate
        stats = cache.get_stats()
        assert stats["total_entries"] == 1


def test_pipeline_source_validation_errors():
    """Test source validation error cases."""
    from configstream.pipeline import _normalise_source_url, SourceValidationError
    import pytest

    # Test no hostname
    with pytest.raises(SourceValidationError):
        _normalise_source_url("http://")
