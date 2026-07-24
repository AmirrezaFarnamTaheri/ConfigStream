# SPDX-License-Identifier: AGPL-3.0-or-later
"""Executable identity and environment controls for the Go tester process."""

from __future__ import annotations

import hashlib
import hmac
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_DIGEST_ENV = "CONFIGSTREAM_TESTER_SHA256"
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


@dataclass(frozen=True)
class BinaryIdentity:
    path: Path
    baseline_sha256: str
    expected_sha256: Optional[str]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalize_digest(value: str) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.split()[0].lower()
    if len(candidate) != 64 or any(
        char not in "0123456789abcdef" for char in candidate
    ):
        return None
    return candidate


def _sidecar_digest(path: Path) -> Optional[str]:
    candidates = (
        path.with_name(path.name + ".sha256"),
        path.with_suffix(path.suffix + ".sha256"),
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        value = _normalize_digest(candidate.read_text(encoding="ascii"))
        if value is None:
            raise ValueError(f"Invalid tester checksum sidecar: {candidate}")
        return value
    return None


def _validate_file_metadata(path: Path) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        raise ValueError("tester binary must not be a symbolic link")
    resolved = candidate.resolve(strict=True)
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("tester binary is not a regular file")
    if os.name != "nt":
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("tester binary is group/world writable")
        euid = getattr(os, "geteuid", lambda: 0)()
        if metadata.st_uid not in {0, euid}:
            raise ValueError("tester binary has an unexpected owner")
    if not os.access(resolved, os.X_OK):
        raise ValueError("tester binary is not executable")
    return resolved


def initialize_binary_identity(path: Path | str) -> BinaryIdentity:
    resolved = _validate_file_metadata(Path(path))
    configured = os.environ.get(_DIGEST_ENV, "")
    expected = _normalize_digest(configured) if configured else None
    if configured and expected is None:
        raise ValueError(f"{_DIGEST_ENV} is not a valid SHA-256 digest")
    expected = expected or _sidecar_digest(resolved)

    strict_mode = (
        os.environ.get("CS_STRICT_BINARY_TRUST", "").strip() in ("1", "true", "yes")
        or os.environ.get("ENVIRONMENT", "").strip().lower() == "production"
    )
    if strict_mode and expected is None:
        raise ValueError(
            "Strict binary trust requires a pinned SHA-256 digest "
            "(via CONFIGSTREAM_TESTER_SHA256 environment variable or .sha256 sidecar file)"
        )

    baseline = _sha256_file(resolved)
    if expected and not hmac.compare_digest(baseline, expected):
        raise ValueError("tester binary checksum does not match the pinned digest")
    return BinaryIdentity(
        path=resolved,
        baseline_sha256=baseline,
        expected_sha256=expected,
    )


def verify_binary_identity(identity: BinaryIdentity) -> bool:
    if not identity or not identity.path:
        return False
    try:
        path = identity.path
        if path.is_symlink():
            raise ValueError("tester binary became a symbolic link")
        file_stat = path.stat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("tester binary is no longer a regular file")
        if os.name != "nt" and (file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            raise ValueError("tester binary became group/world writable")
        current = _sha256_file(path)
        if not hmac.compare_digest(current, identity.baseline_sha256):
            raise ValueError("tester binary changed after discovery")
        if identity.expected_sha256 and not hmac.compare_digest(
            current, identity.expected_sha256
        ):
            raise ValueError("tester binary no longer matches the pinned digest")
        return True
    except (OSError, ValueError):
        return False


def minimal_subprocess_environment(settings: Any) -> dict[str, str]:
    """Build an explicit environment without propagating unrelated secrets."""
    environment = {
        key: value for key in _ENV_ALLOWLIST if (value := os.environ.get(key))
    }
    environment.setdefault("PATH", os.defpath)
    environment["TMPDIR"] = os.environ.get("TMPDIR") or tempfile.gettempdir()
    environment["GOLOG_LOG_LEVEL"] = "error"
    return environment
