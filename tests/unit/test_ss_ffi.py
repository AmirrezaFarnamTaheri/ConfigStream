from unittest.mock import patch, MagicMock
from configstream.security.ss_ffi import verify_ss_rust


def test_ss_ffi_graceful_degradation():
    """Verify that missing library returns True (graceful degradation)."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=False):
        # Should log warning and return True
        assert verify_ss_rust({"server": "1.1.1.1"}) is True


def test_ss_ffi_valid_check():
    """Verify valid check when library is present."""
    with patch("configstream.security.ss_ffi.ensure_library", return_value=True):
        with patch("ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.verify_shadowsocks.return_value = 1
            mock_cdll.return_value = mock_lib

            # Force reload lib (reset global in module is hard, so we mock where it's used)
            # We just check if it tries to use the lib
            with patch("configstream.security.ss_ffi._lib", None):
                assert verify_ss_rust({"server": "1.1.1.1"}) is True
                mock_lib.verify_shadowsocks.assert_called()
