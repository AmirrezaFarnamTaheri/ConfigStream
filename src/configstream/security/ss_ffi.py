"""
Shadowsocks-Rust FFI Wrapper.
"""

import ctypes
import logging
import shutil
import subprocess
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
    """Ensure the Rust library exists, building it if necessary."""
    if LIB_PATH.exists():
        return True

    if not shutil.which("cargo"):
        logger.warning("Cargo not found. Cannot build Shadowsocks-Rust FFI.")
        return False

    src_dir = Path(__file__).parent.parent.parent.parent / "src" / "rust" / "ss_checker"

    logger.info("Building Shadowsocks-Rust FFI...")
    try:
        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=src_dir,
            check=True,
            capture_output=True,
        )

        # Move artifact to bin/
        target_dir = src_dir / "target" / "release"
        # Find the dylib
        found = list(target_dir.glob(f"*{Path(LIB_NAME).suffix}"))
        if found:
            output_dir = LIB_PATH.parent
            output_dir.mkdir(exist_ok=True)
            shutil.copy(found[0], LIB_PATH)
            return True
        else:
            logger.error("Build passed but artifact not found.")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to build Rust library: {e}")
        return False


_lib = None


def verify_ss_rust(config: dict) -> bool:
    """
    Verify a Shadowsocks config using the Rust core.
    """
    global _lib
    if not ensure_library():
        return True  # Fallback

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
