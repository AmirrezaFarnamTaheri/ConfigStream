import asyncio
import logging
import os
import orjson as json
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, cast

from ..config import AppSettings
from ..models import Proxy
from ..converters import to_singbox_outbound

logger = logging.getLogger(__name__)


class GoBatchTester:
    def __init__(
        self,
        binary_path: str = "configstream-tester",
        workers: int = 50,
    ):
        # Clamp workers to a safe range
        try:
            w = int(workers)
        except Exception:
            w = 50
        self.workers = max(1, min(w, 1000))
        env_path = os.environ.get("CONFIGSTREAM_TESTER_BIN")

        # Priority: Env Var > Absolute Path arg > PATH lookup
        resolved = None

        if env_path and os.path.exists(env_path):
            resolved = env_path
        elif os.path.isabs(binary_path) and os.path.exists(binary_path):
            resolved = binary_path
        else:
            # Try finding in PATH or current directory
            resolved = shutil.which(binary_path)
            if not resolved:
                # Fallback to looking in known locations
                common_locations = [
                    Path.cwd() / "configstream-tester",
                    Path.cwd() / "src/go/tester/configstream-tester",
                    Path("/usr/local/bin/configstream-tester"),
                    Path("/opt/configstream/bin/configstream-tester"),
                ]
                for loc in common_locations:
                    if loc.exists():
                        resolved = str(loc)
                        break

        self.binary_path = resolved or binary_path
        self.available = resolved is not None

        # Long-lived process state
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._pending_futures: Dict[str, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._stopping = False

        if not self.available:
            logger.error(
                f"CRITICAL: Go batch tester binary not found (searched: {binary_path}, env: {env_path}, PATH). "
                "No proxies will be tested via the high-performance path!"
            )

    async def start(self):
        """Start the long-lived tester process."""
        if self.available:
            await self._ensure_process()

    async def close(self):
        """Stop the tester process and cleanup resources."""
        self._stopping = True
        async with self._lock:
            if self._proc:
                try:
                    if self._proc.stdin:
                        self._proc.stdin.close()
                        await asyncio.sleep(0.1)  # Give time to flush/close
                    self._proc.terminate()
                    try:
                        await asyncio.wait_for(self._proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        self._proc.kill()
                except Exception as e:
                    logger.debug(f"Error closing Go tester process: {e}")
                finally:
                    self._proc = None

            # Cancel tasks
            if self._read_task:
                self._read_task.cancel()
                try:
                    await self._read_task
                except asyncio.CancelledError:
                    pass
                self._read_task = None

            if self._stderr_task:
                self._stderr_task.cancel()
                try:
                    await self._stderr_task
                except asyncio.CancelledError:
                    pass
                self._stderr_task = None

            # Cancel pending futures
            for f in self._pending_futures.values():
                if not f.done():
                    f.cancel()
            self._pending_futures.clear()
            logger.info("Go Batch Tester shutdown complete.")

    async def _ensure_process(self):
        """Ensure the Go process is running."""
        if self._proc and self._proc.returncode is None:
            return

        async with self._lock:
            if self._proc and self._proc.returncode is None:
                return

            if self._stopping:
                return

            cmd = [self.binary_path, "-workers", str(self.workers)]
            cmd.extend(["-timeout", f"{int(AppSettings.TEST_TIMEOUT)}s"])
            if AppSettings.TEST_URLS:
                urls = ",".join(str(u) for u in AppSettings.TEST_URLS.values())
                cmd.extend(["-urls", urls])

            logger.info(f"Starting Go Tester Daemon: {' '.join(cmd)}")

            try:
                self._proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Start background readers
                loop = asyncio.get_running_loop()
                self._read_task = loop.create_task(self._read_loop())
                self._stderr_task = loop.create_task(self._read_stderr_loop())
            except Exception as e:
                logger.error(f"Failed to start Go Tester Daemon: {e}")
                self._proc = None

    async def _read_loop(self):
        """Background task to read results from stdout."""
        try:
            while self._proc and self._proc.stdout and not self._proc.stdout.at_eof():
                line = await self._proc.stdout.readline()
                if not line:
                    break
                try:
                    # Line is bytes
                    data = json.loads(line)
                    req_id = data.get("id")
                    if req_id and req_id in self._pending_futures:
                        future = self._pending_futures[req_id]
                        if not future.done():
                            future.set_result(data)
                        del self._pending_futures[req_id]
                except json.JSONDecodeError:
                    logger.debug(f"Go Tester output decode error: {line[:100]!r}")
                except Exception as e:
                    logger.error(f"Error processing Go Tester output: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._stopping:
                logger.error(f"Go Tester read loop fatal error: {e}")
        finally:
            if not self._stopping:
                logger.warning("Go Tester stdout closed (process died?)")

    async def _read_stderr_loop(self):
        """Background task to read logs from stderr."""
        try:
            while self._proc and self._proc.stderr and not self._proc.stderr.at_eof():
                line = await self._proc.stderr.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    lower = text.lower()
                    if "panic" in lower or "fatal" in lower:
                        logger.error(f"Go Tester Daemon: {text}")
                    elif "info" in lower:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Go Tester: {text}")
                    elif "error" in lower:
                        logger.warning(f"Go Tester: {text}")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def test_batch(
        self, proxies: List[Proxy], check_honeypot: bool = False
    ) -> List[Proxy]:
        if not self.available or not proxies:
            return proxies

        await self._ensure_process()
        if not self._proc or not self._proc.stdin:
            logger.error("Go Tester process unavailable, skipping batch")
            return proxies

        inputs = []
        req_id_map: Dict[str, Proxy] = {}  # Map req_id -> Proxy
        futures = []
        loop = asyncio.get_running_loop()

        for p in proxies:
            outbound = to_singbox_outbound(p)
            if outbound:
                # Use unique request ID to handle duplicate proxies in different batches
                req_id = f"{p.id}-{uuid.uuid4().hex[:8]}"
                inputs.append(
                    {
                        "config": json.dumps(outbound).decode(),
                        "id": req_id,
                        "check_honeypot": check_honeypot,
                    }
                )
                req_id_map[req_id] = p

                fut = loop.create_future()
                self._pending_futures[req_id] = fut
                futures.append(fut)
            else:
                p.is_working = False
                p.details["error"] = "CONVERSION_FAILED"

        if not inputs:
            return proxies

        if not self._proc.stdin:
            logger.error("Go Tester stdin closed unexpectedly")
            return proxies

        # Send batch to daemon
        try:
            # Use NDJSON
            payload = "\n".join(json.dumps(i).decode() for i in inputs) + "\n"
            self._proc.stdin.write(payload.encode())
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Go Tester Daemon connection lost: {e}")
            # Fail futures to unblock
            for f in futures:
                if not f.done():
                    f.set_exception(e)
            # Process might be dead, ensure restart next time
            await self.close()
            return proxies
        except Exception as e:
            logger.error(f"Failed to write to Go Tester Daemon: {e}")
            # Fail futures to unblock
            for f in futures:
                if not f.done():
                    f.set_exception(e)
            # Process might be dead, ensure restart next time
            await self.close()
            return proxies

        # Wait for results
        # Set a total timeout relative to batch size
        total_timeout = min(300, len(inputs) * 2 + 10)

        try:
            completed_results = await asyncio.wait_for(
                asyncio.gather(*futures, return_exceptions=True), timeout=total_timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Timed out waiting for {len(inputs)} results from Go Tester Daemon"
            )
            # Cleanup
            for f, req_id in zip(futures, req_id_map.keys()):
                if not f.done():
                    f.cancel()
                    self._pending_futures.pop(req_id, None)
            return proxies

        # Process Results
        working_count = 0
        failure_reasons: Dict[str, int] = {}

        for res in completed_results:
            if isinstance(res, BaseException):
                logger.debug(f"Go Tester result error: {res}")
                continue

            # res is the JSON dict
            res_data = cast(Dict[str, Any], res)
            req_id = str(res_data.get("id"))
            proxy_obj: Optional[Proxy] = req_id_map.get(req_id)
            if not proxy_obj:
                continue

            if res_data.get("is_working"):
                proxy_obj.is_working = True
                proxy_obj.latency = res_data.get("latency")
                working_count += 1
                if res_data.get("issues"):
                    for issue in res_data["issues"]:
                        proxy_obj.security_issues.setdefault("go_check", []).append(
                            issue
                        )
                        if issue == "DIRTY_IP":
                            proxy_obj.tags.append("dirty_ip")
            else:
                proxy_obj.is_working = False
                error_msg = str(res_data.get("error", "unknown"))
                proxy_obj.details["error"] = error_msg

                # Categorize error
                if "HONEYPOT" in error_msg:
                    error_cat = "HONEYPOT"
                elif "DIRTY_IP" in error_msg:
                    error_cat = "DIRTY_IP"
                elif "PANIC" in error_msg:
                    error_cat = "PANIC"
                elif "timeout" in error_msg.lower():
                    error_cat = "TIMEOUT"
                elif "bind" in error_msg.lower() and "in use" in error_msg.lower():
                    error_cat = "BIND_ERROR"
                elif "handshake" in error_msg.lower():
                    error_cat = "HANDSHAKE_FAIL"
                elif "connection refused" in error_msg.lower():
                    error_cat = "CONN_REFUSED"
                else:
                    error_cat = "OTHER"

                failure_reasons[error_cat] = failure_reasons.get(error_cat, 0) + 1
                if error_cat not in ["TIMEOUT", "OTHER"]:
                    p.details["failure_category"] = error_cat

        # Log summary
        failure_summary = ", ".join([f"{k}: {v}" for k, v in failure_reasons.items()])
        logger.info(
            f"Go Tester results (Batch): {working_count}/{len(inputs)} working. "
            f"Failures: {failure_summary if failure_summary else 'None'}"
        )

        return proxies

    async def test_custom_configs(
        self, configs: List[Dict[str, Any]], check_honeypot: bool = False
    ) -> Dict[str, bool]:
        """Test custom configs using the daemon."""
        if not self.available or not configs:
            return {}

        await self._ensure_process()
        if not self._proc or not self._proc.stdin:
            return {}

        inputs = []
        req_id_map: Dict[str, str] = {}  # original_id -> req_id
        reverse_map: Dict[str, str] = {}  # req_id -> original_id
        futures = []
        loop = asyncio.get_running_loop()

        for item in configs:
            chain_id = item.get("id")
            outbounds = item.get("outbounds")
            if not chain_id or not outbounds:
                continue

            config_str = ", ".join(json.dumps(o).decode() for o in outbounds)
            # Unique request ID
            req_id = f"{chain_id}-{uuid.uuid4().hex[:8]}"

            inputs.append(
                {
                    "config": config_str,
                    "id": req_id,
                    "check_honeypot": check_honeypot,
                }
            )
            req_id_map[chain_id] = req_id
            reverse_map[req_id] = chain_id

            fut = loop.create_future()
            self._pending_futures[req_id] = fut
            futures.append(fut)

        if not inputs:
            return {}

        # Send
        try:
            payload = "\n".join(json.dumps(i).decode() for i in inputs) + "\n"
            self._proc.stdin.write(payload.encode())
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.error(
                f"Go Tester Daemon connection lost during custom config test: {e}"
            )
            await self.close()
            return {}
        except Exception as e:
            logger.error(f"Failed to write to Go Tester Daemon (custom): {e}")
            return {}

        # Wait
        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*futures, return_exceptions=True), timeout=120
            )
        except asyncio.TimeoutError:
            # Cleanup
            for f, req_id in zip(futures, reverse_map.keys()):
                if not f.done():
                    f.cancel()
                    self._pending_futures.pop(req_id, None)
            return {}

        results = {}
        for res in completed:
            if isinstance(res, dict):
                req_id_raw = res.get("id")
                # Ensure req_id is string for lookup
                if req_id_raw is not None:
                    orig_id_val = reverse_map.get(str(req_id_raw))
                    if orig_id_val:
                        results[orig_id_val] = bool(res.get("is_working", False))

        return results
