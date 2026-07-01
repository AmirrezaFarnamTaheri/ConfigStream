# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shadowsocks-Rust FFI Wrapper.
"""

import ctypes
import hashlib
import logging
import json
from pathlib import Path
import sys
from typing import Optional

from configstream.config import AppSettings

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
_warned_unconfigured_hash = False


def _expected_binary_checksum() -> Optional[str]:
    expected_hash = AppSettings().SS_LIB_SHA256
    if not expected_hash:
        return None
    expected_hash = expected_hash.strip().lower()
    if not expected_hash:
        return None
    return expected_hash


def _verify_binary_checksum(path: Path) -> bool:
    """
    Verify the SHA-256 checksum of the optional Rust binary.

    The Rust FFI path is enabled only when operators provide SS_LIB_SHA256.
    Without that configured hash, callers must treat the binary as unavailable.
    """
    expected_hash = _expected_binary_checksum()
    if not expected_hash:
        return False

    if not path.exists():
        return False

    try:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        calculated = sha256_hash.hexdigest()

        if calculated != expected_hash:
            logger.critical(
                "SS Library Hash Mismatch! Integrity check failed. "
                "Expected configured SHA-256 does not match local binary."
            )
            return False

        return True
    except Exception:
        logger.error("Failed to verify Shadowsocks-Rust library checksum.")
        return False


def verify_ss_rust(config: dict) -> bool:
    """
    Verify a Shadowsocks config using the Rust core.

    Returns:
        True if config is valid or if optional Rust validation is unavailable.
        False if config validation explicitly failed.
    """
    global _lib, _warned_missing, _warned_unconfigured_hash
    if not ensure_library():
        if not _warned_missing:
            logger.warning(
                "Optional Shadowsocks-Rust validation unavailable; "
                "continuing with Python validation only."
            )
            _warned_missing = True
        return True

    if _expected_binary_checksum() is None:
        if not _warned_unconfigured_hash:
            logger.warning(
                "Optional Shadowsocks-Rust validation disabled because "
                "SS_LIB_SHA256 is not configured."
            )
            _warned_unconfigured_hash = True
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
    except Exception:
        logger.error("Shadowsocks-Rust FFI validation failed.")
        return False
