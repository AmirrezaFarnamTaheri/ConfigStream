# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
import logging
import os
import platform
import re
import shutil
import stat
import sys
import tempfile
import urllib.parse
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

MAX_VWARP_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_VWARP_BINARY_BYTES = 64 * 1024 * 1024
VERIFY_TIMEOUT_SECONDS = 10.0
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _is_supported_platform() -> bool:
    """Vwarp binary is currently only available for Linux."""
    return sys.platform.startswith("linux")


def _platform_asset() -> Tuple[Optional[str], Optional[str]]:
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
    return None, None


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
    elif asset_name:
        url = f"{VWARP_RELEASE_BASE}/{version}/{asset_name}"
    else:
        raise ValueError(
            f"unsupported Vwarp architecture: {platform.machine() or 'unknown'}"
        )

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Vwarp download URL must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Vwarp download URL must not contain credentials")

    checksum = env_sha or default_sha
    return url, checksum or None, version


def _validate_download_digest(content: bytes, expected: Optional[str]) -> bool:
    """Require a well-formed SHA-256 pin and an exact archive digest match."""
    if not expected or not _SHA256_RE.fullmatch(expected):
        return False
    return hashlib.sha256(content).hexdigest() == expected.lower()


async def _download_archive(client: httpx.AsyncClient, url: str) -> bytes:
    """Download the release archive without buffering beyond the safety limit."""

    async with client.stream("GET", url) as response:
        response.raise_for_status()
        declared = response.headers.get("content-length")
        if declared:
            try:
                declared_size = int(declared)
            except ValueError as exc:
                raise ValueError("Vwarp archive Content-Length is invalid") from exc
            if declared_size < 0 or declared_size > MAX_VWARP_ARCHIVE_BYTES:
                raise ValueError("Vwarp archive exceeds the download safety limit")

        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > MAX_VWARP_ARCHIVE_BYTES:
                raise ValueError("Vwarp archive exceeds the download safety limit")
        return bytes(content)


def _prepare_install_dir() -> Path:
    """Return a writable install directory without trusting shared temp paths."""

    preferred = Path.home() / ".local" / "bin"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        if os.access(preferred, os.W_OK):
            return preferred
    except OSError:
        pass

    fallback = Path(tempfile.mkdtemp(prefix="configstream-bin-"))
    logger.warning(
        "Cannot use ~/.local/bin; installing Vwarp in temporary directory %s",
        fallback,
    )
    return fallback


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
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=VERIFY_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("Vwarp version check timed out")
            return False
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
    except OSError as exc:
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
        if await verify_binary(binary):
            return binary
        logger.warning("Existing Vwarp binary failed verification; reinstalling")

    try:
        url, checksum, version = _get_download_spec()
    except ValueError as exc:
        logger.error(
            "Vwarp download configuration is invalid: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return None
    if not checksum or not _SHA256_RE.fullmatch(checksum):
        logger.error(
            "No valid SHA-256 checksum is configured for Vwarp %s. "
            "Set VWARP_SHA256 to the exact 64-hex release digest.",
            version,
        )
        return None
    logger.info(f"Vwarp binary not found. Attempting to download {version}...")

    try:
        install_dir = _prepare_install_dir()
        target_path = install_dir / "vwarp"

        logger.info(
            "Downloading Vwarp from %s",
            SecurityValidator.sanitize_log_message(url),
        )

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=60.0, trust_env=False
        ) as client:
            content = await _download_archive(client, url)
        if not _validate_download_digest(content, checksum):
            logger.error(
                "Vwarp checksum mismatch; refusing to install downloaded binary."
            )
            return None

        temporary_path: Path | None = None
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

            if (
                vwarp_member_info.file_size <= 0
                or vwarp_member_info.file_size > MAX_VWARP_BINARY_BYTES
            ):
                logger.error("Vwarp binary size is outside the allowed bounds.")
                return None

            handle, temporary_name = tempfile.mkstemp(prefix=".vwarp-", dir=install_dir)
            os.close(handle)
            temporary_path = Path(temporary_name)
            try:
                copied = 0
                with (
                    zf.open(vwarp_member_info) as source,
                    temporary_path.open("wb") as target,
                ):
                    while chunk := source.read(1024 * 1024):
                        copied += len(chunk)
                        if copied > MAX_VWARP_BINARY_BYTES:
                            raise ValueError(
                                "Vwarp binary exceeds the extraction safety limit"
                            )
                        target.write(chunk)

                st = temporary_path.stat()
                temporary_path.chmod(st.st_mode | stat.S_IEXEC)
                if not await verify_binary(str(temporary_path)):
                    logger.error("Downloaded Vwarp binary failed execution check")
                    return None
                os.replace(temporary_path, target_path)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

        logger.info(f"✅ Vwarp successfully installed to {target_path}")
        return str(target_path)

    except (httpx.HTTPError, OSError, zipfile.BadZipFile, ValueError) as exc:
        logger.error(
            "Failed to install Vwarp: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return None


def _parse_version(version: str) -> Tuple[int, ...]:
    """Parse a version string like ``v2.2.1`` into a numeric tuple ``(2, 2, 1)``.

    Compares versions numerically rather than lexicographically (string
    comparison wrongly orders e.g. ``v2.10.0`` before ``v2.9.0``). Non-numeric
    or malformed components are treated as ``0`` so parsing never raises.
    """
    import re

    if not version:
        return (0,)
    cleaned = version.strip().lstrip("vV")
    parts = re.split(r"[.\-+]", cleaned)
    numbers: list[int] = []
    for part in parts:
        match = re.match(r"\d+", part)
        numbers.append(int(match.group()) if match else 0)
    return tuple(numbers)
