# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verified process launcher for the long-lived Go tester."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from ...config import AppSettings
from ...constants import VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT
from ...async_utils import safe_wait_for
from .manager import (
    GO_TESTER_STREAM_LIMIT,
    GoBatchTester as _StreamingGoBatchTester,
)

from .binary_security import (
    BinaryIdentity,
    initialize_binary_identity,
    minimal_subprocess_environment,
    verify_binary_identity as _check_binary_identity,
)

logger = logging.getLogger(__name__)


class GoBatchTester(_StreamingGoBatchTester):
    """Go tester with executable identity and environment hardening.

    A configured ``CONFIGSTREAM_TESTER_SHA256`` or adjacent ``.sha256`` file
    pins the supply-chain digest. When neither is supplied, a secure-file
    baseline digest is captured during construction and checked again before
    every spawn, preventing path replacement between discovery and execution.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_lock = asyncio.Lock()
        self._identity: Optional[BinaryIdentity] = None
        if self.available:
            self._initialize_binary_identity()

    async def test_batch(self, proxies, check_honeypot: bool = False):
        """Serialize the shared daemon and bound each write to one worker wave.

        The streaming base treats a blocked ``drain()`` as daemon failure. Keep
        each write at or below worker capacity so normal pipe backpressure cannot
        trigger cross-consumer restarts, while preserving Go-side concurrency.
        """
        if not proxies:
            return proxies
        async with self._request_lock:
            results = []
            wave_size = max(1, int(self.workers))
            for start in range(0, len(proxies), wave_size):
                wave = proxies[start : start + wave_size]
                results.extend(await super().test_batch(wave, check_honeypot))
            return results

    async def test_custom_configs(self, configs, check_honeypot: bool = False):
        """Serialize custom-config IPC using the same bounded worker waves."""
        if not configs:
            return {}
        async with self._request_lock:
            results = {}
            wave_size = max(1, int(self.workers))
            for start in range(0, len(configs), wave_size):
                wave = configs[start : start + wave_size]
                results.update(await super().test_custom_configs(wave, check_honeypot))
            return results

    def _initialize_binary_identity(self) -> None:
        try:
            self._identity = initialize_binary_identity(self.binary_path)
            self.binary_path = str(self._identity.path)
            if self._identity.expected_sha256:
                logger.info("Go tester binary verified against a pinned SHA-256 digest")
            else:
                logger.warning(
                    "Go tester has no pinned digest; enforcing secure ownership and a pre-spawn SHA-256 identity check"
                )
        except (OSError, ValueError) as exc:
            logger.error("Go tester binary rejected: %s", str(exc))
            self.available = False
            self._identity = None

    def _verify_binary_integrity(self) -> bool:
        if self._identity is None:
            return False
        res = _check_binary_identity(self._identity)
        if not res:
            logger.error("Go tester integrity verification failed")
            self.available = False
        return res

    @staticmethod
    def _minimal_environment(settings: AppSettings) -> dict[str, str]:
        environment = minimal_subprocess_environment(settings)
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
            except asyncio.TimeoutError as exc:
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
                    limit=GO_TESTER_STREAM_LIMIT,
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
