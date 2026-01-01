# SPDX-License-Identifier: AGPL-3.0-or-later
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
    Currently trusts the local filesystem until binary signing infrastructure is established.
    """
    # [SECURITY] Implement real checksum verification if hash is provided via ENV
    expected_hash = "773b0631f4e3c83758364860d50711626084807494f6c12140a321943806a642"  # Example hash, replace with real one or env var
    import hashlib
    import os

    env_hash = os.environ.get("SS_LIB_SHA256")
    if env_hash:
        expected_hash = env_hash.strip().lower()

    if not path.exists():
        return False

    try:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        calculated = sha256_hash.hexdigest()

        # If no env hash provided, we log warning but allow (fail-open for now to avoid breaking CI)
        # But if env hash IS provided, we strictly enforce it.
        if not env_hash:
            logger.debug(f"SS Library Hash: {calculated} (No verification hash provided)")
            return True

        if calculated != expected_hash:
            logger.critical(f"SS Library Hash Mismatch! Expected {expected_hash}, got {calculated}")
            return False

        return True
    except Exception as e:
        logger.error(f"Failed to verify checksum: {e}")
        return False


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
