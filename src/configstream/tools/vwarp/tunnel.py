# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import os
import shlex
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional

from configstream.async_utils import safe_wait_for
from configstream.constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from configstream.security_validator import SecurityValidator
from .binary import verify_binary
from .config import write_temp_config

logger = logging.getLogger(__name__)


class VwarpTunnel:
    def __init__(self, binary_path: Optional[str]):
        self.binary_path = binary_path
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._config_path: Optional[Path] = None
        self._config_owned: bool = False
        self._stream_tasks: "set[asyncio.Task[Any]]" = set()

    async def start(
        self,
        bind_addr: str = VWARP_BIND_ADDRESS,
        port: int = VWARP_SOCKS5_PORT,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Starts the Vwarp SOCKS5 tunnel in the background."""
        if not self.binary_path or not await verify_binary(self.binary_path):
            return False

        if self._proc:
            return True

        success = await self._start_attempt(bind_addr, port, config_override)
        if success:
            return True

        # Fallback logic would go here, currently simplified to keep this module focused.
        return False

    async def _start_attempt(
        self,
        bind_addr: str,
        port: int,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        self._cleanup_config_file()

        cmd = await self._build_tunnel_command(bind_addr, port, config_override)
        if not cmd:
            logger.error("Vwarp tunnel command could not be constructed.")
            self._cleanup_config_file()
            return False

        try:
            logger.info("🚀 Starting Vwarp SOCKS5 Tunnel on %s:%d...", bind_addr, port)
            self._proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.sleep(0.5)
            if self._proc.returncode is not None:
                stdout, stderr = await self._proc.communicate()
                logger.error(
                    "Vwarp failed: %s",
                    SecurityValidator.sanitize_log_message(
                        (stdout or b"").decode() + (stderr or b"").decode()
                    ),
                )
                self._cleanup_config_file()
                return False

            if not await self._wait_for_port(bind_addr, port):
                logger.error("Vwarp Tunnel started but port check timed out.")
                await self.stop()
                return False

            async def consume_stream(stream, level):
                while stream and not stream.at_eof():
                    line = await stream.readline()
                    if line:
                        safe_line = SecurityValidator.sanitize_log_message(
                            line.decode(errors="ignore")
                        ).strip()
                        logger.log(level, "Vwarp: %s", safe_line)

            for stream, level in (
                (self._proc.stdout, logging.DEBUG),
                (self._proc.stderr, logging.WARNING),
            ):
                task = asyncio.create_task(consume_stream(stream, level))
                self._stream_tasks.add(task)
                task.add_done_callback(self._stream_tasks.discard)

            return True
        except Exception as e:
            logger.error(
                "Failed to start Vwarp tunnel: %s",
                SecurityValidator.sanitize_log_message(str(e)),
            )
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stops the background tunnel process."""
        if self._proc:
            try:
                self._proc.terminate()
                with suppress(asyncio.TimeoutError):
                    await safe_wait_for(self._proc.wait(), timeout=2.0)
            except ProcessLookupError:
                pass
            finally:
                self._proc = None

        for task in list(self._stream_tasks):
            task.cancel()
        self._stream_tasks.clear()
        self._cleanup_config_file()

    async def _wait_for_port(self, host: str, port: int, timeout: int = 45) -> bool:
        """Polls the given host:port until it accepts connections."""
        # Wildcard binds are probed via loopback; this is a client-side probe,
        # not a listener bind (B104 false positive).
        probe_host = (
            host if host not in ("0.0.0.0", "::", "") else "127.0.0.1"  # nosec B104
        )
        start = time.time()
        while time.time() - start < timeout:
            if self._proc and self._proc.returncode is not None:
                return False
            try:
                reader, writer = await safe_wait_for(
                    asyncio.open_connection(probe_host, port), timeout=1
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (OSError, asyncio.TimeoutError, ConnectionRefusedError):
                await asyncio.sleep(1.0)
        return False

    async def _build_tunnel_command(
        self,
        bind_addr: str,
        port: int,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build the best available tunnel command."""
        if not self.binary_path:
            return []

        bind_value = f"{bind_addr}:{port}"
        env_args = os.environ.get("VWARP_TUNNEL_ARGS", "").strip()
        if env_args:
            return [self.binary_path] + shlex.split(
                env_args.replace("{bind}", bind_value)
            )

        # write_temp_config performs blocking file I/O; offload to a thread
        # to keep the event loop responsive.
        config_path, extra_flags = await asyncio.to_thread(
            write_temp_config,
            self._build_initial_config(bind_addr, port, config_override),
        )

        self._config_path = config_path
        self._config_owned = config_path is not None

        if config_path:
            return [self.binary_path, "--config", str(config_path)] + extra_flags

        return [self.binary_path, "--bind", bind_value]

    def _build_initial_config(
        self, bind_addr: str, port: int, override: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        from .config import build_vwarp_config

        cfg = build_vwarp_config(bind=f"{bind_addr}:{port}")
        if override:
            cfg.update(override)
        return cfg

    def _cleanup_config_file(self) -> None:
        if self._config_owned and self._config_path:
            with suppress(Exception):
                self._config_path.unlink(missing_ok=True)
            self._config_path = None
            self._config_owned = False
