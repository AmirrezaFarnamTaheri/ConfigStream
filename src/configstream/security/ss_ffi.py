"""
Shadowsocks-Rust FFI Wrapper.
"""

import ctypes
import logging
import json
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

# Path to the built library
if sys.platform == "win32":
    LIB_NAME = "ss_checker.dll"
elif sys.platform == "darwin":
    LIB_NAME = "libss_checker.dylib"
else:
    LIB_NAME = "libss_checker.so"

LIB_PATH = Path(__file__).parent.parent.parent.parent / "bin" / LIB_NAME


def ensure_library():
    """Ensure the Rust library exists. DO NOT BUILD at runtime."""
    if LIB_PATH.exists():
        return True

    # In a Zero-Budget / CI environment, we avoid compiling Rust at runtime
    # to save minutes. We rely on the binary being pre-built or just fall back.
    logger.debug(
        "Shadowsocks-Rust library not found. Skipping compilation for efficiency."
    )
    return False


_lib = None
_warned_missing = False


def _verify_binary_checksum(path: Path) -> bool:
    """
    Verify the SHA-256 checksum of the binary.
    TODO: Implement strict checking against signed manifest.
    For now, we trust the local filesystem but this is a placeholder for supply chain security.
    """
    # Placeholder: Always return True until infrastructure for signing is in place
    return True


def verify_ss_rust(config: dict) -> bool:
    """
    Verify a Shadowsocks config using the Rust core.

    Returns:
        True if config is valid or if Rust library unavailable (graceful degradation).
        False if config validation explicitly failed.
    """
    global _lib, _warned_missing
    if not ensure_library():
        # Graceful degradation: Skip this enhanced validation if library unavailable
        if not _warned_missing:
            logger.warning(
                "Shadowsocks-Rust library unavailable - enhanced SS validation disabled. "
                "Pre-build binary required for this feature."
            )
            _warned_missing = True
        return True

    if not _verify_binary_checksum(LIB_PATH):
        logger.error("Shadowsocks-Rust library failed checksum verification.")
        return False

    try:
        if _lib is None:
            _lib = ctypes.CDLL(str(LIB_PATH))
            _lib.verify_shadowsocks.argtypes = [ctypes.c_char_p]
            _lib.verify_shadowsocks.restype = ctypes.c_int

        config_json = json.dumps(config).encode("utf-8")
        result = _lib.verify_shadowsocks(config_json)
        return bool(result == 1)
    except Exception as e:
        logger.error(f"FFI Error: {e}")
        return False
