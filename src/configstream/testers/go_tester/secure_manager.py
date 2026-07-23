# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verified process launcher for the long-lived Go tester."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import stat
import tempfile
from pathlib import Path
from typing import Optional

from ...config import AppSettings
from ...constants import VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT
from ...async_utils import safe_wait_for
from .manager import GoBatchTester as _StreamingGoBatchTester

logger = logging.getLogger(__name__)

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalize_digest(value: str) -> Optional[str]:
    candidate = (
        str(value or "").strip().lower().split()[0] if str(value or "").strip() else ""
    )
    if len(candidate) != 64 or any(
        char not in "0123456789abcdef" for char in candidate
    ):
        return None
    return candidate


def _sidecar_digest(path: Path) -> Optional[str]:
    for candidate in (
        path.with_name(path.name + ".sha256"),
        path.with_suffix(path.suffix + ".sha256"),
    ):
        try:
            if candidate.is_file():
                digest = _normalize_digest(candidate.read_text(encoding="ascii"))
                if digest:
                    return digest
                logger.error("Invalid tester checksum sidecar: %s", candidate)
        except OSError as exc:
            logger.warning(
                "Unable to read tester checksum sidecar: %s", type(exc).__name__
            )
    return None


class GoBatchTester(_StreamingGoBatchTester):
    """Go tester with executable identity and environment hardening.

    A configured ``CONFIGSTREAM_TESTER_SHA256`` or adjacent ``.sha256`` file
    pins the supply-chain digest. When neither is supplied, a secure-file
    baseline digest is captured during construction and checked again before
    every spawn, preventing path replacement between discovery and execution.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._binary_file: Optional[Path] = None
        self._baseline_digest: Optional[str] = None
        self._expected_digest: Optional[str] = None
        if self.available:
            self._initialize_binary_identity()

    def _initialize_binary_identity(self) -> None:
        try:
            candidate = Path(self.binary_path)
            if candidate.is_symlink():
                raise ValueError(
                    "symbolic links are not accepted for the tester binary"
                )
            resolved = candidate.resolve(strict=True)
            file_stat = resolved.stat()
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError("tester binary is not a regular file")
            if os.name != "nt" and (file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
                raise ValueError("tester binary is group/world writable")
            euid = getattr(os, "geteuid", lambda: 0)()
            if os.name != "nt" and file_stat.st_uid not in {0, euid}:
                raise ValueError("tester binary is owned by an unexpected user")
            if not os.access(resolved, os.X_OK):
                raise ValueError("tester binary is not executable")

            configured = os.environ.get(_DIGEST_ENV, "")
            expected = _normalize_digest(configured) if configured else None
            if configured and expected is None:
                raise ValueError(f"{_DIGEST_ENV} is not a valid SHA-256 digest")
            expected = expected or _sidecar_digest(resolved)
            baseline = _sha256_file(resolved)
            if expected and not hmac.compare_digest(baseline, expected):
                raise ValueError(
                    "tester binary checksum does not match the pinned digest"
                )

            self.binary_path = str(resolved)
            self._binary_file = resolved
            self._baseline_digest = baseline
            self._expected_digest = expected
            if expected:
                logger.info("Go tester binary verified against a pinned SHA-256 digest")
            else:
                logger.warning(
                    "Go tester has no pinned digest; enforcing secure ownership and a pre-spawn SHA-256 identity check"
                )
        except (OSError, ValueError) as exc:
            logger.error("Go tester binary rejected: %s", str(exc))
            self.available = False
            self._binary_file = None
            self._baseline_digest = None

    def _verify_binary_integrity(self) -> bool:
        path = self._binary_file
        baseline = self._baseline_digest
        if path is None or baseline is None:
            return False
        try:
            if path.is_symlink():
                raise ValueError("tester binary became a symbolic link")
            file_stat = path.stat()
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError("tester binary is no longer a regular file")
            if os.name != "nt" and (file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
                raise ValueError("tester binary became group/world writable")
            current = _sha256_file(path)
            if not hmac.compare_digest(current, baseline):
                raise ValueError("tester binary changed after discovery")
            if self._expected_digest and not hmac.compare_digest(
                current, self._expected_digest
            ):
                raise ValueError("tester binary no longer matches the pinned digest")
            return True
        except (OSError, ValueError) as exc:
            logger.error("Go tester integrity verification failed: %s", str(exc))
            self.available = False
            return False

    @staticmethod
    def _minimal_environment(settings: AppSettings) -> dict[str, str]:
        environment = {
            key: value for key in _ENV_ALLOWLIST if (value := os.environ.get(key))
        }
        environment.setdefault("PATH", os.defpath)
        environment["TMPDIR"] = os.environ.get("TMPDIR") or tempfile.gettempdir()
        environment["GOLOG_LOG_LEVEL"] = "error"

        tunnel_override = os.environ.get("USE_VWARP_TUNNEL")
        use_tunnel = (
            False
            if tunnel_override == "false"
            else True if tunnel_override == "true" else settings.USE_VWARP_TUNNEL
        )
        if use_tunnel:
            environment["ALL_PROXY"] = (
                f"socks5://{VWARP_BIND_ADDRESS}:{VWARP_SOCKS5_PORT}"
            )
        return environment

    async def _ensure_process(self) -> None:
        if self._restart_task and not self._restart_task.done():
            try:
                await safe_wait_for(self._restart_task, timeout=15.0)
            except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
                logger.debug("Tester restart wait ended: %s", type(exc).__name__)
            self._restart_task = None

        if self._proc and self._proc.returncode is None:
            return

        async with self._lock:
            if self._proc and self._proc.returncode is None:
                return
            if self._stopping or not self.available:
                return
            if not await asyncio.to_thread(self._verify_binary_integrity):
                return

            settings = AppSettings()
            command = [self.binary_path, "-workers", str(self.workers)]
            command.extend(["-timeout", f"{max(1, int(self.timeout))}s"])
            if settings.TEST_URLS:
                url_map = settings.TEST_URLS
                if os.environ.get("CI") == "true":
                    preferred = {"cloudflare", "gstatic", "google"}
                    filtered = {
                        key: value
                        for key, value in url_map.items()
                        if key in preferred and value
                    }
                    url_map = filtered or url_map
                command.extend(
                    ["-urls", ",".join(str(url) for url in url_map.values())]
                )

            logger.info("Starting verified Go tester daemon")
            try:
                self._proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._minimal_environment(settings),
                )
                loop = asyncio.get_running_loop()
                self._read_task = loop.create_task(self._read_loop())
                self._read_task.add_done_callback(self._silence_task)
                self._stderr_task = loop.create_task(self._read_stderr_loop())
                self._stderr_task.add_done_callback(self._silence_task)
            except (OSError, ValueError) as exc:
                logger.error(
                    "Failed to start verified Go tester daemon: %s", type(exc).__name__
                )
                self._proc = None
