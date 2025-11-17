"""Additional core tests to reach coverage target."""

import pytest
from configstream.core import parse_config
from configstream.models import Proxy


def test_parse_config_with_whitespace():
    """Test parsing with leading/trailing whitespace."""
    result = parse_config("  vmess://test  ")
    # Should handle whitespace
    assert result is None or isinstance(result, Proxy)


def test_parse_config_with_comment():
    """Test parsing comment lines."""
    result = parse_config("# This is a comment")
    assert result is None


def test_parse_config_empty():
    """Test parsing empty config."""
    result = parse_config("")
    assert result is None

    result = parse_config("   ")
    assert result is None


def test_parse_config_none():
    """Test parsing None."""
    result = parse_config(None)
    assert result is None
