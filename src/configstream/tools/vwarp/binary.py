# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
import logging
import os
import platform
import shutil
import stat
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import httpx

from configstream.security_validator import SecurityValidator
from .constants import (
    VWARP_VERSION,
    VWARP_SHA256_AMD64,
    VWARP_ASSET_AMD64,
    VWARP_ASSET_ARM64,
    VWARP_RELEASE_BASE,
)

logger = logging.getLogger(__name__)

def _is_supported_platform() -> bool:
    """Vwarp binary is currently only available for Linux."""
    return sys.platform.startswith("linux")

def _platform_asset() -> Tuple[str, Optional[str]]:
    """
    Resolve the appropriate asset and checksum for this platform.
    Returns (asset_name, sha256_or_none).
    """
    machine = (platform.machine() or "").lower()
    if machine in ("x86_64", "amd64"):
        return VWARP_ASSET_AMD64, VWARP_SHA256_AMD64
    if machine in ("aarch64", "arm64"):
        # SHA256 unknown for arm64 unless provided via env override.
        return VWARP_ASSET_ARM64, None
    # Default to amd64 asset for unknown Linux machines.
    return VWARP_ASSET_AMD64, VWARP_SHA256_AMD64

def _get_download_spec() -> Tuple[str, Optional[str], str]:
    """
    Resolve download URL and checksum.
    Environment overrides:
    - VWARP_VERSION
    - VWARP_URL
    - VWARP_SHA256
    """
    version = os.environ.get("VWARP_VERSION", VWARP_VERSION)
    env_url = os.environ.get("VWARP_URL", "").strip()
    env_sha = os.environ.get("VWARP_SHA256", "").strip()
    asset_name, default_sha = _platform_asset()

    if env_url:
        url = env_url
    else:
        url = f"{VWARP_RELEASE_BASE}/{version}/{asset_name}"

    checksum = env_sha or default_sha
    return url, checksum or None, version

def find_binary() -> Optional[str]:
    """Locates the vwarp binary in PATH or common locations."""
    # 1. Check PATH
    binary = shutil.which("vwarp")
    if binary:
        return binary

    # 2. Check user local bin
    home = Path.home()
    local_bin = home / ".local" / "bin" / "vwarp"
    if local_bin.exists() and os.access(local_bin, os.X_OK):
        return str(local_bin)

    # 3. Check fallback paths
    possible_paths = ["/usr/local/bin/vwarp", "/opt/vwarp/vwarp", "./vwarp"]
    for p in possible_paths:
        if Path(p).exists() and os.access(p, os.X_OK):
            return p

    return None

async def verify_binary(binary_path: str) -> bool:
    """Verify the existing binary executes properly."""
    try:
        proc = await asyncio.create_subprocess_exec(
            binary_path,
            "version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True
        if stderr:
            logger.error(
                "Vwarp version check failed: %s",
                SecurityValidator.sanitize_log_message(stderr.decode(errors="ignore")),
            )
        elif stdout:
            logger.error(
                "Vwarp version check failed: %s",
                SecurityValidator.sanitize_log_message(stdout.decode(errors="ignore")),
            )
        return False
    except Exception as exc:
        logger.error(
            "Vwarp version check error: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return False

async def ensure_installed() -> Optional[str]:
    """
    Ensures Vwarp is installed. Downloads if missing.
    Returns path to binary if installed/available, None otherwise.
    """
    if not _is_supported_platform():
        platform_hint = (
            "Use USE_VWARP_TUNNEL=false for non-Linux environments."
            if sys.platform == "win32"
            else "Vwarp binary is Linux-only."
        )
        logger.info(
            "Vwarp install skipped: unsupported platform (%s). %s",
            sys.platform,
            platform_hint,
        )
        return None
    
    binary = find_binary()
    if binary and Path(binary).exists():
        return binary

    url, checksum, version = _get_download_spec()
    logger.info(f"Vwarp binary not found. Attempting to download {version}...")

    try:
        home = Path.home()
        install_dir = home / ".local" / "bin"
        install_dir.mkdir(parents=True, exist_ok=True)
        target_path = install_dir / "vwarp"

        if not os.access(install_dir, os.W_OK):
            install_dir = Path("/tmp/configstream-bin")  # nosec
            install_dir.mkdir(parents=True, exist_ok=True)
            target_path = install_dir / "vwarp"
            logger.warning(
                f"Cannot write to ~/.local/bin, installing to {target_path}"
            )

        logger.info(
            "Downloading Vwarp from %s",
            SecurityValidator.sanitize_log_message(url),
        )

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=60.0
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.content

        if checksum:
            digest = hashlib.sha256(content).hexdigest()
            if digest != checksum:
                if os.environ.get("VWARP_SKIP_CHECKSUM", "").lower() in (
                    "1",
                    "true",
                    "yes",
                ):
                    logger.warning(
                        "Vwarp checksum mismatch but VWARP_SKIP_CHECKSUM=true; continuing install."
                    )
                else:
                    logger.error(
                        "Vwarp checksum mismatch! Expected %s, got %s.",
                        checksum,
                        digest,
                    )
                    return None
        
        with zipfile.ZipFile(BytesIO(content)) as zf:
            vwarp_member_info = None
            for member_info in zf.infolist():
                if (
                    not member_info.is_dir()
                    and Path(member_info.filename).name == "vwarp"
                ):
                    vwarp_member_info = member_info
                    break

            if not vwarp_member_info:
                logger.error("Vwarp binary not found in zip archive.")
                return None

            with (
                zf.open(vwarp_member_info) as source,
                open(target_path, "wb") as target,
            ):
                shutil.copyfileobj(source, target)

        st = os.stat(target_path)
        os.chmod(target_path, st.st_mode | stat.S_IEXEC)

        if await verify_binary(str(target_path)):
            logger.info(f"✅ Vwarp successfully installed to {target_path}")
            return str(target_path)
        else:
            logger.error("Vwarp installed but failed execution check")
            return None

    except Exception as e:
        logger.error("Failed to install Vwarp: %s", SecurityValidator.sanitize_log_message(str(e)))
        return None
