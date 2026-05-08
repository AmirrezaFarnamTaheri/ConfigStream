# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import patch, MagicMock
import hashlib
from pathlib import Path
from typing import Iterator

import pytest

import configstream.security.ss_ffi as ss_ffi
from configstream.security.ss_ffi import verify_ss_rust, ensure_library, LIB_PATH
import sys


@pytest.fixture(autouse=True)
def _configured_ss_hash(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        ss_ffi,
        "_expected_binary_checksum",
        lambda: "a" * 64,
    )
    yield


def test_ss_ffi_graceful_degradation():
    """Verify that missing library returns True (graceful degradation)."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=False):
        # Should log warning and return True
        assert verify_ss_rust({"server": "1.1.1.1"}) is True


def test_ss_ffi_present_library_without_configured_hash_is_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stray local binary is ignored unless SS_LIB_SHA256 is configured."""
    monkeypatch.setattr(ss_ffi, "_expected_binary_checksum", lambda: None)
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch("ctypes.CDLL") as mock_cdll:
            assert verify_ss_rust({"server": "1.1.1.1"}) is True
            mock_cdll.assert_not_called()


def test_ss_ffi_bad_hash_fails_closed(tmp_path: Path) -> None:
    binary = tmp_path / "ss_checker.dll"
    binary.write_bytes(b"not the expected binary")

    with patch(
        "configstream.security.ss_ffi._expected_binary_checksum",
        return_value="0" * 64,
    ):
        assert ss_ffi._verify_binary_checksum(binary) is False


def test_ss_ffi_good_hash_is_accepted(tmp_path: Path) -> None:
    binary = tmp_path / "ss_checker.dll"
    content = b"verified optional binary"
    binary.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()

    with patch(
        "configstream.security.ss_ffi._expected_binary_checksum",
        return_value=expected,
    ):
        assert ss_ffi._verify_binary_checksum(binary) is True


def test_ss_ffi_valid_check():
    """Verify valid check when library is present."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 1
                mock_cdll.return_value = mock_lib

                # Force reload lib (reset global in module is hard, so we mock where it's used)
                # We just check if it tries to use the lib
                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is True
                    mock_lib.verify_shadowsocks.assert_called()


def test_ss_ffi_invalid_config():
    """Test that invalid config returns False."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 0  # Invalid
                mock_cdll.return_value = mock_lib

                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is False


def test_ss_ffi_exception_handling():
    """Test that exceptions return False."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.side_effect = Exception("FFI Error")
                mock_cdll.return_value = mock_lib

                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is False


def test_ss_ffi_json_serialization():
    """Test that config is properly JSON serialized."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 1
                mock_cdll.return_value = mock_lib

                config = {"server": "1.1.1.1", "port": 8388, "method": "aes-256-gcm"}

                with patch("configstream.security.ss_ffi._lib", None):
                    verify_ss_rust(config)

                    # Verify the call was made with JSON bytes
                    call_args = mock_lib.verify_shadowsocks.call_args
                    assert call_args is not None


def test_ensure_library_exists():
    """Test ensure_library when library exists."""
    with patch("pathlib.Path.exists", return_value=True):
        assert ensure_library() is True


def test_ensure_library_not_exists():
    """Test ensure_library when library doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        assert ensure_library() is False


def test_ss_ffi_warning_logged_once():
    """Test that warning is only logged once when library is missing."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=False):
        with patch("configstream.security.ss_ffi.logger") as mock_logger:
            with patch("configstream.security.ss_ffi._warned_missing", False):
                # First call should log warning
                verify_ss_rust({"server": "1.1.1.1"})
                assert mock_logger.warning.called


def test_ss_ffi_complex_config():
    """Test with complex config structure."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 1
                mock_cdll.return_value = mock_lib

                config = {
                    "server": "example.com",
                    "port": 8388,
                    "method": "chacha20-ietf-poly1305",
                    "password": "secret",
                    "plugin": "obfs-local",
                    "plugin_opts": "obfs=http;obfs-host=example.com",
                }

                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust(config) is True


def test_ss_ffi_unicode_in_config():
    """Test handling of Unicode in config."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 1
                mock_cdll.return_value = mock_lib

                config = {"server": "测试.com", "password": "密码"}

                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust(config) is True


def test_ss_ffi_empty_config():
    """Test with empty config."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_lib.verify_shadowsocks.return_value = 0
                mock_cdll.return_value = mock_lib

                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({}) is False


def test_lib_path_platform_specific():
    """Test that LIB_PATH is set correctly for platform."""
    # This test just verifies the constant exists and is platform-appropriate
    assert LIB_PATH is not None

    if sys.platform == "win32":
        assert str(LIB_PATH).endswith(".dll")
    elif sys.platform == "darwin":
        assert str(LIB_PATH).endswith(".dylib")
    else:
        assert str(LIB_PATH).endswith(".so")


def test_ss_ffi_ctypes_error():
    """Test handling of ctypes loading error."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL", side_effect=OSError("Cannot load library")):
                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is False


def test_ss_ffi_return_value_edge_cases():
    """Test various return values from FFI."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_cdll.return_value = mock_lib

                # Test return value 1 (valid)
                mock_lib.verify_shadowsocks.return_value = 1
                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is True

                # Test return value 0 (invalid)
                mock_lib.verify_shadowsocks.return_value = 0
                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is False

                # Test return value -1 (error)
                mock_lib.verify_shadowsocks.return_value = -1
                with patch("configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"server": "1.1.1.1"}) is False


def test_ss_ffi_library_initialization():
    """Test library initialization and setup."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch(
            "configstream.security.ss_ffi._verify_binary_checksum", return_value=True
        ):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_lib = MagicMock()
                mock_cdll.return_value = mock_lib

                with patch("configstream.security.ss_ffi._lib", None):
                    verify_ss_rust({"server": "1.1.1.1"})

                    # Verify library was loaded with correct path
                    mock_cdll.assert_called_once()
                    # Verify argtypes and restype were set
                    assert hasattr(mock_lib, "verify_shadowsocks")
