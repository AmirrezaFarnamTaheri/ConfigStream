# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
import hmac
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
_BINARY_DIGEST_ENV = "VWARP_BINARY_SHA256"
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "WINDIR",
    "TMPDIR",
    "TMP",
    "TEMP",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "LANG",
    "LC_ALL",
    "TZ",
)


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


def minimal_vwarp_environment() -> dict[str, str]:
    """Return the environment explicitly allowed into Vwarp subprocesses."""
    environment = {
        key: value for key in _ENV_ALLOWLIST if (value := os.environ.get(key))
    }
    environment.setdefault("PATH", os.defpath)
    environment["TMPDIR"] = os.environ.get("TMPDIR") or tempfile.gettempdir()
    return environment


def _normalize_binary_digest(value: str) -> Optional[str]:
    candidate = (
        str(value or "").strip().split()[0].lower() if str(value or "").strip() else ""
    )
    if not candidate or not _SHA256_RE.fullmatch(candidate):
        return None
    return candidate


def _validate_trusted_file(path: Path, *, executable: bool) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        raise ValueError("Vwarp trusted file must not be a symbolic link")
    resolved = candidate.resolve(strict=True)
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("Vwarp trusted file must be a regular file")
    if os.name != "nt":
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("Vwarp trusted file must not be group/world writable")
        euid = getattr(os, "geteuid", lambda: 0)()
        if metadata.st_uid not in {0, euid}:
            raise ValueError("Vwarp trusted file has an unexpected owner")
    if executable and not os.access(resolved, os.X_OK):
        raise ValueError("Vwarp binary is not executable")
    return resolved


def _binary_sidecar_digest(path: Path) -> Optional[str]:
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.exists():
        return None
    trusted = _validate_trusted_file(sidecar, executable=False)
    digest = _normalize_binary_digest(trusted.read_text(encoding="ascii"))
    if digest is None:
        raise ValueError("Vwarp executable checksum sidecar is invalid")
    return digest


def _expected_binary_digest(
    path: Path, explicit: Optional[str] = None
) -> Optional[str]:
    raw = explicit if explicit is not None else os.environ.get(_BINARY_DIGEST_ENV, "")
    if raw:
        digest = _normalize_binary_digest(raw)
        if digest is None:
            raise ValueError(f"{_BINARY_DIGEST_ENV} is not a valid SHA-256 digest")
        return digest
    return _binary_sidecar_digest(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_binary_digest_sidecar(path: Path, digest: str) -> None:
    sidecar = path.with_name(path.name + ".sha256")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{sidecar.name}.", dir=sidecar.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            handle.write(digest + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, sidecar)
    finally:
        temporary.unlink(missing_ok=True)


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


async def verify_binary(
    binary_path: str, expected_sha256: Optional[str] = None
) -> bool:
    """Verify file provenance and digest before executing the Vwarp binary."""
    try:
        resolved = _validate_trusted_file(Path(binary_path), executable=True)
        expected = _expected_binary_digest(resolved, expected_sha256)
        if expected is None:
            logger.error(
                "Vwarp executable has no trusted SHA-256 pin; set %s or provide %s.sha256",
                _BINARY_DIGEST_ENV,
                resolved,
            )
            return False
        observed = _sha256_file(resolved)
        if not hmac.compare_digest(observed, expected):
            logger.error("Vwarp executable checksum does not match the trusted digest")
            return False

        proc = await asyncio.create_subprocess_exec(
            str(resolved),
            "version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=minimal_vwarp_environment(),
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
    except (OSError, ValueError, UnicodeError) as exc:
        logger.error(
            "Vwarp version check rejected the executable: %s",
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
                executable_digest = _sha256_file(temporary_path)
                if not await verify_binary(
                    str(temporary_path), expected_sha256=executable_digest
                ):
                    logger.error("Downloaded Vwarp binary failed execution check")
                    return None
                os.replace(temporary_path, target_path)
                temporary_path = None
                _write_binary_digest_sidecar(target_path, executable_digest)
                if not await verify_binary(str(target_path)):
                    logger.error("Installed Vwarp binary failed pinned verification")
                    return None
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
