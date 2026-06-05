# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import os
import shutil
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
        
        self._proc = await asyncio.create_subprocess_exec(
            self.binary_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return self._proc

    async def stop(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except:
                self._proc.kill()
