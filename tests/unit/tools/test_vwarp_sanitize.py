import json
import os
from pathlib import Path

from configstream.tools.vwarp import VwarpTool


def test_vwarp_write_sanitized_config():
    """Test that _write_temp_config removes unsupported fields."""
    tool = VwarpTool()

    # Create a dummy config with fields that should be stripped
    config = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "endpoint": "1.2.3.4:2408",
        "masque": {"enabled": True, "preferred": True, "config": {"i1": "val"}},
        "psiphon": {"enabled": True, "country": "US"},
    }

    path, flags = tool._write_temp_config(config)
    assert path is not None
    assert path.exists()

    content = json.loads(path.read_text())

    # Verify strict keys are removed
    assert "version" not in content
    assert "metadata" not in content

    # Verify masque structure is preserved (Unified format)
    assert "masque" in content
    assert content["masque"]["config"] == {"i1": "val"}
    assert content["masque"]["enabled"] is True

    # Verify psiphon enabled is preserved
    assert "psiphon" in content
    assert content["psiphon"]["enabled"] is True
    assert content["psiphon"]["country"] == "US"

    # Verify extra_flags logic still worked (using original config)
    # masque.enabled was True, so --masque should be in flags
    assert "--masque" in flags

    # Cleanup
    path.unlink()


def test_vwarp_write_sanitized_config_no_masque_config():
    """Test that _write_temp_config handles masque without config subkey."""
    tool = VwarpTool()

    config = {"masque": {"enabled": False, "preferred": False, "some_param": "val"}}

    path, flags = tool._write_temp_config(config)
    content = json.loads(path.read_text())

    # Should keep enabled/preferred
    assert content["masque"]["enabled"] is False
    assert content["masque"]["preferred"] is False
    assert content["masque"]["some_param"] == "val"

    path.unlink()
