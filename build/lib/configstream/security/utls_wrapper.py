# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Wrapper for the Go-based uTLS sidecar.
"""

import asyncio
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the built binary
BINARY_PATH = Path(__file__).parent.parent.parent.parent / "bin" / "utls-client"

# Track if we've already warned about missing binary
_warned_missing = False


def _compute_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of the file at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_checksum(path: Path) -> Optional[str]:
    """
    Resolve the expected SHA-256 pin for the binary, if one is configured.

    Resolution order:
      1. ``UTLS_CLIENT_SHA256`` environment variable (operator-supplied pin).
      2. A sibling ``<binary>.sha256`` file (first whitespace-delimited token).

    Returns ``None`` when no pin is configured, in which case verification is
    skipped (the binary is trusted as built locally).
    """
    env_pin = os.environ.get("UTLS_CLIENT_SHA256", "").strip()
    if env_pin:
        return env_pin.lower()

    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.is_file():
        try:
            token = sidecar.read_text(encoding="utf-8").strip().split()
            if token:
                return token[0].lower()
        except OSError as exc:
            logger.warning("Could not read checksum sidecar %s: %s", sidecar, exc)
    return None


def _verify_binary_checksum(path: Path) -> bool:
    """
    Verify the SHA-256 checksum of the binary against a configured pin.

    Fails closed (returns ``False``) only when a pin is configured and the
    computed digest does not match. When no pin is configured, the binary is
    trusted (returns ``True``) so locally-built binaries keep working.
    """
    if not path.is_file():
        logger.error("uTLS binary not found for checksum verification: %s", path)
        return False

    expected = _expected_checksum(path)
    if expected is None:
        return True

    try:
        actual = _compute_sha256(path)
    except OSError as exc:
        logger.error("Failed to compute checksum for %s: %s", path, exc)
        return False

    if actual.lower() != expected:
        logger.error(
            "uTLS binary checksum mismatch: expected %s, got %s", expected, actual
        )
        return False
    return True


async def _run_cmd(cmd: list[str], cwd: Path) -> bool:
    """Helper to run async subprocess commands."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.debug(f"Command failed: {cmd} -> {stderr.decode().strip()}")
            return False
        return True
    except Exception as e:
        logger.debug(f"Command execution error: {cmd} -> {e}")
        return False


async def ensure_binary_async() -> bool:
    """Ensure the Go binary exists, building it if necessary (Async)."""
    if BINARY_PATH.exists():
        return True

    # Check for Go
    if not shutil.which("go"):
        logger.warning("Go not found. Cannot build uTLS client.")
        return False

    src_dir = Path(__file__).parent.parent.parent.parent / "src" / "go" / "utls_client"
    if not src_dir.exists():
        # Source directory missing (e.g., in packaged distribution).
        return False

    output_dir = BINARY_PATH.parent
    # mkdir is sync but fast for FS ops; acceptable here or could run in executor
    output_dir.mkdir(exist_ok=True)

    logger.info("Building uTLS client...")

    # We need to initialize a module first if not present
    # These steps are sequential
    await _run_cmd(["go", "mod", "init", "utls-client"], cwd=src_dir)
    await _run_cmd(["go", "get", "github.com/refraction-networking/utls"], cwd=src_dir)

    success = await _run_cmd(
        ["go", "build", "-o", str(BINARY_PATH), "main.go"],
        cwd=src_dir,
    )

    if not success:
        logger.error("Failed to build uTLS client binary.")
        return False

    return True


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
    if not await ensure_binary_async():
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
