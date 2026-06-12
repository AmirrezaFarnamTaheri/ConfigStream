# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import orjson as json
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GoTesterIPC:
    def __init__(self, proc: asyncio.subprocess.Process):
        self._proc = proc
        self._pending_futures: Dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()

    def _json_str(self, obj: Any) -> str:
        raw = json.dumps(obj)
        return raw.decode() if isinstance(raw, bytes) else raw

    async def send_command(self, cmd: str, payload: Dict[str, Any]) -> Any:
        future = asyncio.get_running_loop().create_future()
        request_id = str(time.time_ns())
        
        async with self._lock:
            self._pending_futures[request_id] = future
            
        stdin = self._proc.stdin
        if stdin is None:
            async with self._lock:
                self._pending_futures.pop(request_id, None)
            raise RuntimeError("Go tester process has no stdin pipe")

        message = {"id": request_id, "cmd": cmd, **payload}
        stdin.write(self._json_str(message).encode() + b"\n")
        await stdin.drain()
        
        return await asyncio.wait_for(future, timeout=30.0)
    
    async def read_loop(self):
        try:
            while self._proc and self._proc.stdout and not self._proc.stdout.at_eof():
                line = await self._proc.stdout.readline()
                if not line:
                    break
                try:
                    data = json.loads(line)
                    req_id = str(data.get("id"))
                    async with self._lock:
                        future = self._pending_futures.pop(req_id, None)
                    if future and not future.done():
                        future.set_result(data)
                except Exception as e:
                    logger.error(f"IPC Parse Error: {e}")
        except Exception as e:
            logger.error(f"IPC Read Loop Error: {e}")
