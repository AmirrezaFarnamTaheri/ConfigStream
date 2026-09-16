# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import os
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessManager:
    def __init__(self, binary_name: str = "configstream-tester"):
        self.binary_path = self._resolve_binary(binary_name)
        self._proc: Optional[asyncio.subprocess.Process] = None

    def _resolve_binary(self, binary_name: str) -> Optional[str]:
        # Priority: Env Var > Absolute Path arg > PATH lookup
        env_path = os.environ.get("CONFIGSTREAM_TESTER_BIN")
        if env_path and os.path.exists(env_path):
            return env_path
        if os.path.isabs(binary_name) and os.path.exists(binary_name):
            return binary_name

        resolved = shutil.which(binary_name)
        if resolved:
            return resolved

        # Fallback to known locations
        common_locations = [
            Path.cwd() / "configstream-tester",
            Path.cwd() / "src/go/tester/configstream-tester",
            Path("/usr/local/bin/configstream-tester"),
            Path("/opt/configstream/bin/configstream-tester"),
        ]
        for loc in common_locations:
            if loc.exists():
                return str(loc)
        return None

    async def ensure_running(self) -> asyncio.subprocess.Process:
        if self._proc and self._proc.returncode is None:
            return self._proc

        if not self.binary_path:
            raise FileNotFoundError(
                "configstream-tester binary not found; set CONFIGSTREAM_TESTER_BIN "
                "or install it on PATH"
            )

        # Import lazily so the long-standing environment-catalog source locations
        # above remain stable while every execution still crosses the same trust
        # boundary as the primary streaming Go tester.
        from ...config import AppSettings
        from .binary_security import (
            initialize_binary_identity,
            minimal_subprocess_environment,
            verify_binary_identity,
        )

        try:
            identity = await asyncio.to_thread(
                initialize_binary_identity, self.binary_path
            )
        except (OSError, ValueError) as exc:
            raise RuntimeError("configstream-tester binary rejected") from exc
        if not await asyncio.to_thread(verify_binary_identity, identity):
            raise RuntimeError("configstream-tester failed integrity verification")
        self.binary_path = str(identity.path)

        self._proc = await asyncio.create_subprocess_exec(
            self.binary_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=minimal_subprocess_environment(AppSettings()),
        )
        return self._proc

    async def _kill_and_reap(self, proc: asyncio.subprocess.Process) -> bool:
        """Kill a tester child and return whether exit was conclusively observed."""
        if proc.returncode is None:
            try:
                with suppress(ProcessLookupError):
                    proc.kill()
            except OSError as exc:
                logger.warning(
                    "Failed to kill configstream-tester child: %s",
                    type(exc).__name__,
                )
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.error("configstream-tester child could not be reaped after kill")
        except (OSError, RuntimeError) as exc:
            logger.warning(
                "Failed to reap configstream-tester child: %s",
                type(exc).__name__,
            )
        return proc.returncode is not None

    async def stop(self) -> None:
        proc = self._proc
        if not proc:
            return

        try:
            if proc.returncode is None:
                try:
                    with suppress(ProcessLookupError):
                        proc.terminate()
                except OSError as exc:
                    logger.warning(
                        "Failed to terminate configstream-tester child: %s",
                        type(exc).__name__,
                    )
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                await self._kill_and_reap(proc)
            except asyncio.CancelledError:
                await self._kill_and_reap(proc)
                raise
            except (OSError, RuntimeError) as exc:
                logger.warning(
                    "Failed while waiting for configstream-tester shutdown: %s",
                    type(exc).__name__,
                )
                await self._kill_and_reap(proc)
        finally:
            # Never drop the only process handle unless exit was actually observed.
            if proc.returncode is not None:
                self._proc = None
