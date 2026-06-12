import json
import os

from configstream.tools.vwarp import VwarpTool


def test_vwarp_write_sanitized_config():
    """Test that _write_temp_config removes unsupported fields when VWARP_VERSION < v2.2.1."""
    os.environ["VWARP_VERSION"] = "v2.1.0"
    try:
        tool = VwarpTool()

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

        assert "version" not in content
        assert "metadata" not in content

        assert "masque" in content
        assert content["masque"]["config"] == {"i1": "val"}
        assert "enabled" not in content["masque"]
        assert "preferred" not in content["masque"]

        assert "psiphon" in content
        assert content["psiphon"]["enabled"] is True
        assert content["psiphon"]["country"] == "US"

        assert "--masque" in flags

        path.unlink()
    finally:
        os.environ.pop("VWARP_VERSION", None)


def test_vwarp_sanitize_removes_junk_interval():
    """Test that wireguard.atomicnoize.JunkInterval is removed when VWARP_VERSION < v2.2.1."""
    os.environ["VWARP_VERSION"] = "v2.1.0"
    try:
        tool = VwarpTool()

        config = {
            "bind": "127.0.0.1:10808",
            "wireguard": {
                "enabled": True,
                "atomicnoize": {"Jc": 8, "JunkInterval": 15000000, "Jmin": 40},
            },
        }

        path, _ = tool._write_temp_config(config)
        content = json.loads(path.read_text())

        assert "wireguard" in content
        assert "atomicnoize" in content["wireguard"]
        assert "JunkInterval" not in content["wireguard"]["atomicnoize"]
        assert content["wireguard"]["atomicnoize"]["Jc"] == 8
        assert content["wireguard"]["atomicnoize"]["Jmin"] == 40

        path.unlink()
    finally:
        os.environ.pop("VWARP_VERSION", None)


def test_vwarp_write_sanitized_config_no_masque_config():
    """Test that _write_temp_config handles masque without config subkey when VWARP_VERSION < v2.2.1."""
    os.environ["VWARP_VERSION"] = "v2.1.0"
    try:
        tool = VwarpTool()

        config = {"masque": {"enabled": False, "preferred": False, "some_param": "val"}}

        path, flags = tool._write_temp_config(config)
        content = json.loads(path.read_text())

        # enabled/preferred removed for binary; other params preserved
        assert "enabled" not in content["masque"]
        assert "preferred" not in content["masque"]
        assert content["masque"]["some_param"] == "val"

        path.unlink()
    finally:
        os.environ.pop("VWARP_VERSION", None)


def test_vwarp_v222_preserves_full_config():
    """Test that v2.2.2+ preserves JunkInterval, masque.enabled, masque.preferred (no sanitization)."""
    os.environ.pop("VWARP_VERSION", None)  # Use default v2.2.2
    try:
        tool = VwarpTool()

        config = {
            "bind": "127.0.0.1:10808",
            "wireguard": {
                "enabled": True,
                "atomicnoize": {"Jc": 8, "JunkInterval": 15000000, "Jmin": 40},
            },
            "masque": {"enabled": True, "preferred": False, "config": {"i1": " "}},
        }

        path, _ = tool._write_temp_config(config)
        content = json.loads(path.read_text())

        assert "JunkInterval" in content["wireguard"]["atomicnoize"]
        assert content["wireguard"]["atomicnoize"]["JunkInterval"] == 15000000
        assert content["masque"]["enabled"] is True
        assert content["masque"]["preferred"] is False

        path.unlink()
    finally:
        os.environ.pop("VWARP_VERSION", None)
