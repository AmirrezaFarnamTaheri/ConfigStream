# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import uuid
import time
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, cast, Set

from ...config import AppSettings
from ...models import Proxy
from ...converters import to_singbox_outbound
from ...constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from ...async_utils import safe_wait_for
from ...intelligence.evasion import enrich_outbound_with_evasion
from .interfaces import ITester
from .process import ProcessManager
from .rpc import GoTesterIPC

logger = logging.getLogger(__name__)

class GoBatchTester(ITester):
    def __init__(
        self,
        binary_path: str = "configstream-tester",
        workers: int = 20,
        timeout: int = 10,
    ):
        self.workers = max(1, int(workers))
        self.timeout = timeout
        
        self.proc_manager = ProcessManager(binary_name=binary_path)
        self.available = self.proc_manager.binary_path is not None
        self.ipc: Optional[GoTesterIPC] = None

        # Long-lived process state
        self._lock = asyncio.Lock()
        self._stopping = False

    async def _ensure_process(self) -> None:
        proc = await self.proc_manager.ensure_running()
        if not self.ipc or self.ipc._proc != proc:
            self.ipc = GoTesterIPC(proc)
            asyncio.create_task(self.ipc.read_loop())

    async def start(self) -> None:
        """Start the long-lived tester process."""
        if self.available:
            await self._ensure_process()
            # Perform quick self-test logic here if needed...

    async def close(self) -> None:
        """Stop the tester process and cleanup resources."""
        self._stopping = True
        await self.proc_manager.stop()
        logger.info("Go Batch Tester shutdown complete.")

    async def _restart_daemon(self) -> None:
        """Force restart of the daemon process."""
        logger.info("Restarting Go Tester Daemon...")
        await self.close()
        self._stopping = False
        await self._ensure_process()

    async def test_batch(self, proxies: List[Proxy], check_honeypot: bool = False) -> List[Proxy]:
        if not self.available or not proxies:
            return proxies

        await self._ensure_process()
        if not self.ipc:
            raise RuntimeError("Go Tester IPC unavailable")

        # Conversion, enrichment, IPC communication using self.ipc.send_command
        # (Simplified for demonstration of delegating to IPC)
        return proxies

    async def test_custom_configs(self, configs: List[Dict[str, Any]], check_honeypot: bool = False) -> Dict[str, bool]:
        if not self.available or not configs:
            return {}

        await self._ensure_process()
        if not self.ipc:
            raise RuntimeError("Go Tester IPC unavailable")
            
        return {}
