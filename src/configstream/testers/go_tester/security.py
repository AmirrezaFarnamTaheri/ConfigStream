# SPDX-License-Identifier: AGPL-3.0-or-later
"""Trust and process-isolation helpers for the bundled Go tester."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Mapping, Optional

from ...config import AppSettings

logger = logging.getLogger(__name__)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SAFE_ENV_KEYS = (
    "PATH",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "LANG",
    "LC_ALL",
    "TZ",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)


def resolve_tester_binary(
    binary_name: str = "configstream-tester",
    *,
    configured_path: Optional[str] = None,
) -> Optional[str]:
    """Resolve the tester from an explicit/configured path, PATH, or known locations."""

    candidates: list[Path] = []
    if configured_path:
        candidates.append(Path(configured_path))
    if os.path.isabs(binary_name):
        candidates.append(Path(binary_name))

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    resolved = shutil.which(binary_name)
    if resolved and Path(resolved).is_file():
        return resolved

    # Windows runners can occasionally miss extensionless tools in shutil.which().
    if not os.path.isabs(binary_name):
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            candidate = Path(entry) / binary_name
            if candidate.is_file():
                return str(candidate)

    for candidate in (
        Path.cwd() / "configstream-tester",
        Path.cwd() / "src/go/tester/configstream-tester",
        Path("/usr/local/bin/configstream-tester"),
        Path("/opt/configstream/bin/configstream-tester"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _normalize_sha256(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    if not _SHA256_RE.fullmatch(normalized):
        return None
    return normalized


def _sidecar_sha256(path: Path) -> Optional[str]:
    """Read a conventional ``<binary>.sha256`` sidecar, if present and valid."""

    candidates = [Path(f"{path}.sha256")]
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        resolved = path
    resolved_sidecar = Path(f"{resolved}.sha256")
    if resolved_sidecar not in candidates:
        candidates.append(resolved_sidecar)

    for sidecar in candidates:
        try:
            token = sidecar.read_text(encoding="utf-8").strip().split()[0]
        except (OSError, IndexError):
            continue
        normalized = _normalize_sha256(token)
        if normalized:
            return normalized
    return None


def expected_tester_sha256(path: str | Path) -> Optional[str]:
    """Return the configured tester digest, falling back to an immutable sidecar."""

    configured = _normalize_sha256(AppSettings().CONFIGSTREAM_TESTER_SHA256)
    if configured:
        return configured
    return _sidecar_sha256(Path(path))


def calculate_tester_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_tester_binary(path: str | Path) -> bool:
    """Fail closed unless the tester exists and matches a configured/sidecar digest."""

    candidate = Path(path)
    if not candidate.is_file():
        return False

    expected = expected_tester_sha256(candidate)
    if not expected:
        logger.error(
            "Go tester disabled: no CONFIGSTREAM_TESTER_SHA256 or valid .sha256 sidecar is available."
        )
        return False

    try:
        calculated = calculate_tester_sha256(candidate)
    except OSError as exc:
        logger.error("Go tester checksum verification failed: %s", type(exc).__name__)
        return False

    if not hmac.compare_digest(calculated, expected):
        logger.critical(
            "Go tester SHA-256 mismatch; refusing to execute the untrusted binary."
        )
        return False
    return True


def build_tester_environment(
    *,
    use_vwarp: bool = False,
    vwarp_bind_address: str = "127.0.0.1",
    vwarp_port: int = 10808,
    parent: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    """Build a small child environment instead of forwarding application secrets."""

    source = os.environ if parent is None else parent
    env = {key: source[key] for key in _SAFE_ENV_KEYS if source.get(key)}
    env.setdefault("PATH", os.defpath)
    env.setdefault("TMPDIR", source.get("TMPDIR") or tempfile.gettempdir())
    env["GOLOG_LOG_LEVEL"] = "error"

    if use_vwarp:
        env["ALL_PROXY"] = f"socks5://{vwarp_bind_address}:{int(vwarp_port)}"

    return env
