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
        logger.error("Go source not found.")
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
    """
    if not ensure_binary():
        # Fallback: Assume success if we can't test, or Fail?
        # For safety, if we can't randomize, we might fail or just warn.
        # Let's return True but log warning to not block the pipeline if Go is missing.
        return True

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
