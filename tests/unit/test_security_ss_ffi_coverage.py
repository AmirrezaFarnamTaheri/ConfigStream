
import pytest
import sys
import ctypes
from unittest.mock import MagicMock, patch
from src.configstream.security.ss_ffi import ensure_library, verify_ss_rust, LIB_PATH

# --- ensure_library ---

def test_ensure_library_exists():
    with patch("src.configstream.security.ss_ffi.LIB_PATH") as mock_path:
        mock_path.exists.return_value = True
        assert ensure_library() is True

def test_ensure_library_missing():
    with patch("src.configstream.security.ss_ffi.LIB_PATH") as mock_path:
        mock_path.exists.return_value = False
        assert ensure_library() is False

# --- verify_ss_rust ---

def test_verify_ss_rust_no_library():
    with patch("src.configstream.security.ss_ffi.ensure_library", return_value=False):
        # Should log warning and return True (fail open)
        with patch("src.configstream.security.ss_ffi.logger") as mock_logger:
            assert verify_ss_rust({"server": "1.1.1.1"}) is True
            mock_logger.warning.assert_called()

def test_verify_ss_rust_valid():
    with patch("src.configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch("ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            # return 1 for valid
            mock_lib.verify_shadowsocks.return_value = 1

            # Need to mock LIB_PATH because CDLL takes str(LIB_PATH)
            with patch("src.configstream.security.ss_ffi.LIB_PATH", MagicMock()):
                # Reset global _lib? It persists across tests if we are not careful.
                # But we can mock ctypes.CDLL to return our mock.
                # To force reload of global, we might need to mock within the function scope or reset it.
                # `src.configstream.security.ss_ffi._lib` is global.
                # We can patch it directly.
                with patch("src.configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"config": "valid"}) is True

def test_verify_ss_rust_invalid():
    with patch("src.configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch("ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            # return 0 for invalid
            mock_lib.verify_shadowsocks.return_value = 0

            with patch("src.configstream.security.ss_ffi.LIB_PATH", MagicMock()):
                with patch("src.configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({"config": "invalid"}) is False

def test_verify_ss_rust_exception():
    with patch("src.configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch("ctypes.CDLL", side_effect=Exception("FFI Boom")):
             with patch("src.configstream.security.ss_ffi.LIB_PATH", MagicMock()):
                with patch("src.configstream.security.ss_ffi._lib", None):
                    assert verify_ss_rust({}) is False
