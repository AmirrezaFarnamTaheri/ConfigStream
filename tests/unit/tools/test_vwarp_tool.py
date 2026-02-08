import pytest
from src.configstream.tools.vwarp import VwarpTool


def test_key_validation():
    tool = VwarpTool()

    # Valid-looking key (alphanumeric + length check)
    valid_key = "a" * 45
    assert tool.validate_warp_key(valid_key) is True

    # Invalid key
    invalid_key = "short"
    assert tool.validate_warp_key(invalid_key) is False
