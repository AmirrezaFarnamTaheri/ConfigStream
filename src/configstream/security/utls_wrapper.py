# SPDX-License-Identifier: AGPL-3.0-or-later
"""Wrapper for the Go-based uTLS sidecar."""

import asyncio
import hashlib
import hmac
import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BINARY_PATH = REPOSITORY_ROOT / "bin" / "utls-client"
SOURCE_DIR = REPOSITORY_ROOT / "src" / "go" / "utls_client"

_warned_missing = False
BUILD_TIMEOUT_SECONDS = 300
PROBE_TIMEOUT_SECONDS = 30
_SHA256_HEX = frozenset("0123456789abcdef")
_BASE_ENV_ALLOWLIST = (
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
_GO_ENV_ALLOWLIST = (
    "GOCACHE",
    "GOMODCACHE",
    "GOPATH",
    "GOPROXY",
    "GONOPROXY",
    "GOSUMDB",
    "GONOSUMDB",
)


def _compute_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of the file at ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_checksum(value: str) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.split()[0].lower()
    if len(candidate) != 64 or any(char not in _SHA256_HEX for char in candidate):
        return None
    return candidate


def _validate_trusted_file(path: Path, *, executable: bool) -> Path:
    if path.is_symlink():
        raise ValueError("uTLS trusted file must not be a symbolic link")
    resolved = path.resolve(strict=True)
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("uTLS trusted file must be a regular file")
    if os.name != "nt":
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("uTLS trusted file must not be group/world writable")
        euid = getattr(os, "geteuid", lambda: 0)()
        if metadata.st_uid not in {0, euid}:
            raise ValueError("uTLS trusted file has an unexpected owner")
    if executable and not os.access(resolved, os.X_OK):
        raise ValueError("uTLS client is not executable")
    return resolved


def _expected_checksum(path: Path) -> Optional[str]:
    """Resolve a trusted executable checksum from env or protected sidecar."""
    env_pin = os.environ.get("UTLS_CLIENT_SHA256", "").strip()
    if env_pin:
        normalized = _normalize_checksum(env_pin)
        if normalized is None:
            raise ValueError("UTLS_CLIENT_SHA256 is not a valid SHA-256 digest")
        return normalized

    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.exists():
        return None
    trusted_sidecar = _validate_trusted_file(sidecar, executable=False)
    normalized = _normalize_checksum(trusted_sidecar.read_text(encoding="ascii"))
    if normalized is None:
        raise ValueError("uTLS checksum sidecar is invalid")
    return normalized


def _verify_binary_checksum(path: Path) -> bool:
    """Require a trusted executable pin and exact digest match before execution."""
    try:
        resolved = _validate_trusted_file(path, executable=True)
        expected = _expected_checksum(resolved)
        if expected is None:
            logger.error(
                "uTLS executable has no trusted SHA-256 pin; configure "
                "UTLS_CLIENT_SHA256 or provide %s.sha256",
                resolved,
            )
            return False
        actual = _compute_sha256(resolved)
    except (OSError, UnicodeError, ValueError) as exc:
        logger.error("uTLS executable verification failed: %s", type(exc).__name__)
        return False

    if not hmac.compare_digest(actual, expected):
        logger.error("uTLS binary checksum does not match the trusted digest")
        return False
    return True


def _minimal_subprocess_environment(*, include_go: bool = False) -> dict[str, str]:
    """Build an explicit child environment without unrelated pipeline secrets.

    Go builds additionally disable the per-user GOENV file, workspace discovery,
    automatic toolchain downloads, and cgo. This keeps the locally built sidecar
    tied to the committed module and the already-selected Go executable instead
    of silently inheriting hidden user build flags or executing a C toolchain.
    """
    allowed = list(_BASE_ENV_ALLOWLIST)
    if include_go:
        allowed.extend(_GO_ENV_ALLOWLIST)
    environment = {
        key: value for key in allowed if (value := os.environ.get(key))
    }
    environment.setdefault("PATH", os.defpath)
    environment["TMPDIR"] = os.environ.get("TMPDIR") or tempfile.gettempdir()
    if include_go:
        environment["GOENV"] = "off"
        environment["GOTOOLCHAIN"] = "local"
        environment["GOWORK"] = "off"
        environment["CGO_ENABLED"] = "0"
    return environment


def _write_checksum_sidecar(path: Path, digest: str) -> None:
    sidecar = path.with_name(path.name + ".sha256")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{sidecar.name}.", dir=sidecar.parent)
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


async def _communicate_bounded(
    proc: asyncio.subprocess.Process,
    *,
    timeout_seconds: float,
) -> tuple[bytes, bytes] | None:
    """Collect a child process result and kill it if the deadline expires."""
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return None


async def _run_cmd(
    cmd: list[str],
    cwd: Path,
    *,
    timeout_seconds: float = BUILD_TIMEOUT_SECONDS,
) -> bool:
    """Run one fixed argv build command without exposing unrelated secrets."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_minimal_subprocess_environment(include_go=True),
        )
        result = await _communicate_bounded(proc, timeout_seconds=timeout_seconds)
        if result is None:
            logger.warning("Command timed out after %ss: %s", timeout_seconds, cmd[0])
            return False
        _, stderr = result
        if proc.returncode != 0:
            logger.debug(
                "Command failed: %s -> %s", cmd, stderr.decode(errors="replace").strip()
            )
            return False
        return True
    except (OSError, ValueError) as exc:
        logger.debug("Command execution error: %s -> %s", cmd, type(exc).__name__)
        return False


async def ensure_binary_async() -> bool:
    """Ensure a pinned locally-built uTLS executable is available."""
    if BINARY_PATH.exists() and _verify_binary_checksum(BINARY_PATH):
        return True

    go_binary = shutil.which("go")
    if not go_binary:
        logger.warning("Go not found. Cannot build uTLS client.")
        return False

    src_dir = SOURCE_DIR
    if not src_dir.exists():
        return False
    if not (src_dir / "go.mod").is_file() or not (src_dir / "go.sum").is_file():
        logger.error(
            "uTLS source module is incomplete; go.mod and go.sum are required."
        )
        return False

    output_dir = BINARY_PATH.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".utls-client-", dir=output_dir)
    os.close(fd)
    temporary = Path(temporary_name)
    temporary.unlink(missing_ok=True)

    logger.info("Building uTLS client from the committed Go module...")
    try:
        success = await _run_cmd(
            [
                go_binary,
                "build",
                "-trimpath",
                "-mod=readonly",
                "-o",
                str(temporary),
                ".",
            ],
            cwd=src_dir,
        )
        if not success or not temporary.is_file():
            logger.error("Failed to build uTLS client binary.")
            return False
        if os.name != "nt":
            temporary.chmod(0o700)
        digest = _compute_sha256(temporary)
        os.replace(temporary, BINARY_PATH)
        _write_checksum_sidecar(BINARY_PATH, digest)
        if not _verify_binary_checksum(BINARY_PATH):
            logger.error("Locally built uTLS client failed pinned verification.")
            return False
        return True
    except (OSError, ValueError) as exc:
        logger.error("Failed to install uTLS client: %s", type(exc).__name__)
        return False
    finally:
        temporary.unlink(missing_ok=True)


async def test_tls_fingerprint(
    url: str, proxy: str, fingerprint: str = "chrome"
) -> bool:
    """Test a URL using the pinned Go uTLS sidecar."""
    global _warned_missing
    if not await ensure_binary_async():
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
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_minimal_subprocess_environment(),
        )
        result = await _communicate_bounded(
            proc,
            timeout_seconds=PROBE_TIMEOUT_SECONDS,
        )
        if result is None:
            logger.error("uTLS client timed out after %ss", PROBE_TIMEOUT_SECONDS)
            return False
        stdout, stderr = result

        if proc.returncode == 0:
            logger.debug("uTLS Success: %s", stdout.decode(errors="replace").strip())
            return True
        logger.debug("uTLS Failed: %s", stderr.decode(errors="replace").strip())
        return False
    except (OSError, ValueError) as exc:
        logger.error("Error running uTLS client: %s", type(exc).__name__)
        return False