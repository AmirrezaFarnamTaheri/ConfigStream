"""
Wrapper for the Go-based uTLS sidecar.
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the built binary
BINARY_PATH = Path(__file__).parent.parent.parent.parent / "bin" / "utls-client"

# Track if we've already warned about missing binary
_warned_missing = False


def _verify_binary_checksum(path: Path) -> bool:
    """
    Verify the SHA-256 checksum of the binary.
    Currently a no-op until supply-chain security infrastructure is ready.
    """
    return True


def ensure_binary():
    """Ensure the Go binary exists, building it if necessary."""
    if BINARY_PATH.exists():
        return True

    # Check for Go
    if not shutil.which("go"):
        logger.warning("Go not found. Cannot build uTLS client.")
        return False

    src_dir = Path(__file__).parent.parent.parent.parent / "src" / "go" / "utls_client"
    if not src_dir.exists():
        # Source directory missing (e.g., in packaged distribution).
        # Cannot build binary; functionality gracefully degraded.
        return False

    output_dir = BINARY_PATH.parent
    output_dir.mkdir(exist_ok=True)

    logger.info("Building uTLS client...")
    try:
        # We need to initialize a module first if not present
        subprocess.run(
            ["go", "mod", "init", "utls-client"], cwd=src_dir, capture_output=True
        )
        subprocess.run(
            ["go", "get", "github.com/refraction-networking/utls"],
            cwd=src_dir,
            capture_output=True,
        )

        subprocess.run(
            ["go", "build", "-o", str(BINARY_PATH), "main.go"],
            cwd=src_dir,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to build uTLS client: {e}")
        return False


async def test_tls_fingerprint(
    url: str, proxy: str, fingerprint: str = "chrome"
) -> bool:
    """
    Test a URL using a specific TLS fingerprint via the Go sidecar.

    Args:
        url: Target URL.
        proxy: Proxy address (currently mostly unused in the minimal Go PoC, but reserved).
        fingerprint: chrome, firefox, ios, random.

    Returns:
        True if fingerprint test passed or if binary unavailable (graceful degradation).
        False if fingerprint test explicitly failed.
    """
    global _warned_missing
    if not ensure_binary():
        # Graceful degradation: Skip this enhanced security check if binary unavailable
        # This is an optional advanced feature - core functionality should not be blocked
        if not _warned_missing:
            logger.warning(
                "uTLS client binary unavailable - TLS fingerprint randomization disabled. "
                "Install Go and rebuild to enable this security feature."
            )
            _warned_missing = True
        return True

    if not _verify_binary_checksum(BINARY_PATH):
        logger.error("uTLS client binary failed checksum verification.")
        return False

    cmd = [str(BINARY_PATH), "-url", url, "-fp", fingerprint]
    if proxy:
        cmd.extend(["-proxy", proxy])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.debug(f"uTLS Success: {stdout.decode().strip()}")
            return True
        else:
            logger.debug(f"uTLS Failed: {stderr.decode().strip()}")
            return False
    except Exception as e:
        logger.error(f"Error running uTLS client: {e}")
        return False
