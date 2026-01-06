# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import orjson as json
import shutil
import uuid
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, cast, Set

from ..config import AppSettings
from ..models import Proxy
from ..converters import to_singbox_outbound
from ..constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS

logger = logging.getLogger(__name__)


class GoBatchTester:
    def __init__(
        self,
        binary_path: str = "configstream-tester",
        workers: int = 20,
        timeout: int = 10,
    ):
        # Clamp workers to a safe range
        try:
            w = int(workers)
        except Exception:
            w = 20
        # Clamp between 1 and 100 (reduced from 1000 for stability)
        self.workers = max(1, min(w, 100))
        self.timeout = timeout
        env_path = AppSettings().CONFIGSTREAM_TESTER_BIN

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
        self._proc: Optional[asyncio.subprocess.Process] = None  # type: ignore
        self._lock = asyncio.Lock()
        self._pending_futures: Dict[str, asyncio.Future[Any]] = {}
        self._read_task: Optional[asyncio.Task[None]] = None
        self._stderr_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._stopping = False

        # Log deduplication state
        self._recent_errors: Dict[str, int] = {}
        self._last_log_flush = time.time()
        self._log_lock = asyncio.Lock() # Protect log state

        if not self.available:
            logger.error(
                f"CRITICAL: Go batch tester binary not found (searched: {binary_path}, env: {env_path}, PATH). "
                "No proxies will be tested via the high-performance path!"
            )

    async def start(self) -> None:
        """Start the long-lived tester process."""
        if self.available:
            await self._ensure_process()
            # Start heartbeat loop
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _restart_daemon(self) -> None:
        """Force restart of the daemon process."""
        logger.info("Restarting Go Tester Daemon...")
        await self.close()
        # Ensure 'stopping' flag is cleared so we can start again
        self._stopping = False
        await self._ensure_process()

    async def _heartbeat_loop(self) -> None:
        """Periodically check if process is alive and healthy."""
        while not self._stopping:
            try:
                await asyncio.sleep(10)
                needs_restart = False
                async with self._lock:
                    if self._proc and self._proc.returncode is not None:
                        logger.warning(
                            f"Go Tester exited unexpectedly with code {self._proc.returncode}. Restarting..."
                        )
                        self._proc = None
                        needs_restart = True

                if needs_restart:
                    await self._ensure_process()

                # Periodically flush error summary if any pending
                await self._flush_error_logs()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

    async def close(self) -> None:
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

            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None

            # Cancel pending futures
            for f in self._pending_futures.values():
                if not f.done():
                    f.cancel()
            self._pending_futures.clear()
            logger.info("Go Batch Tester shutdown complete.")

    async def _ensure_process(self) -> None:
        """Ensure the Go process is running."""
        if self._proc and self._proc.returncode is None:
            return

        async with self._lock:
            if self._proc and self._proc.returncode is None:
                return

            if self._stopping:
                return

            cmd = [self.binary_path, "-workers", str(self.workers)]
            # Increase timeout to ensure python reaches to feed all proxies
            cmd.extend(["-timeout", "30s"])

            # NOTE: Avoid module-level AppSettings() instances; settings should be created
            # lazily to respect runtime env changes (important for tests).
            settings = AppSettings()
            if settings.TEST_URLS:
                urls = ",".join(str(u) for u in settings.TEST_URLS.values())
                cmd.extend(["-urls", urls])

            logger.info(f"Starting Go Tester Daemon: {' '.join(cmd)}")

            try:
                # Prepare environment
                env = os.environ.copy()
                env["GOLOG_LOG_LEVEL"] = "error"
                # Ensure temp dir is accessible
                env["TMPDIR"] = os.environ.get("TMPDIR", "/tmp")
                env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")

                # 🚀 FORCE TRAFFIC THROUGH VWARP TUNNEL IF AVAILABLE
                # Check environment directly as it might be set dynamically by pipeline.py
                # or fallback to AppSettings if set globally
                use_vwarp = (
                    os.environ.get("USE_VWARP_TUNNEL") == "true"
                    or settings.USE_VWARP_TUNNEL
                )

                if use_vwarp:
                    # Using Vwarp tunnel configuration from constants
                    env["ALL_PROXY"] = (
                        f"socks5://{VWARP_BIND_ADDRESS}:{VWARP_SOCKS5_PORT}"
                    )
                    logger.info(
                        f"Go Tester using Vwarp tunnel at socks5://{VWARP_BIND_ADDRESS}:{VWARP_SOCKS5_PORT}"
                    )

                    self._proc = await asyncio.create_subprocess_exec(  # type: ignore
                        *cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                    )
                else:
                    self._proc = await asyncio.create_subprocess_exec(  # type: ignore
                        *cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                    )

                # Start background readers
                loop = asyncio.get_running_loop()
                self._read_task = loop.create_task(self._read_loop())
                self._stderr_task = loop.create_task(self._read_stderr_loop())
            except Exception as e:
                logger.error(f"Failed to start Go Tester Daemon: {e}")
                self._proc = None

    async def _read_loop(self) -> None:
        """Background task to read results from stdout."""
        try:
            while self._proc and self._proc.stdout and not self._proc.stdout.at_eof():
                line = await self._proc.stdout.readline()
                if not line:
                    break
                try:
                    # Line is bytes, orjson can handle bytes directly but strict typing might complain
                    # if we pass it to json.loads. json.loads accepts str | bytes | bytearray
                    # depending on type hints.
                    data = json.loads(line)
                    req_id = data.get("id")
                    if req_id:
                        # Thread-safe access to _pending_futures using lock
                        async with self._lock:
                            future = self._pending_futures.pop(req_id, None)
                        if future and not future.done():
                            future.set_result(data)
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

    async def _flush_error_logs(self) -> None:
        """Flush accumulated error logs."""
        async with self._log_lock:
            for error_msg, count in self._recent_errors.items():
                if count > 0:
                    logger.warning(f"Go Tester Error (repeated {count} times): {error_msg}")
            self._recent_errors.clear()
            self._last_log_flush = time.time()

    async def _read_stderr_loop(self) -> None:
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
                        # [FIX] Deduplicate repeating errors (specifically peer key errors)
                        if "failed to get peer by public key" in text or "wireguard" in text:
                            async with self._log_lock:
                                # Simplify error message for aggregation key
                                # E.g. "failed to get peer by public key: hex string does not fit the slice"
                                if "failed to get peer by public key" in text:
                                    key = "WireGuard: failed to get peer by public key"
                                else:
                                    key = text[:50] + "..." # Truncate for key

                                self._recent_errors[key] = self._recent_errors.get(key, 0) + 1

                                # Flush periodically
                                if time.time() - self._last_log_flush > 5:
                                    # Release lock briefly to flush (actually _flush acquires lock, so careful reentrancy)
                                    # We are inside lock, cannot call _flush directly if it acquires lock
                                    pass

                            # Check flush outside lock to avoid deadlock if we refactor logging
                            if time.time() - self._last_log_flush > 5:
                                await self._flush_error_logs()
                        else:
                            # Standard logging for other errors
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
        futures: List[asyncio.Future[Any]] = []
        loop = asyncio.get_running_loop()

        for p in proxies:
            outbound = to_singbox_outbound(p)
            if outbound:
                # Use unique request ID (Full UUID) to handle duplicate proxies collision-free
                req_id = f"{p.id}-{uuid.uuid4().hex}"

                # Handle json.dumps returning bytes or str
                raw_json = json.dumps(outbound)
                if isinstance(raw_json, bytes):
                    config_str = raw_json.decode()
                else:
                    config_str = raw_json

                # FIX: Go Tester template expects "outbounds": [%s, direct]
                inputs.append(
                    {
                        "config": config_str,
                        "id": req_id,
                        "check_honeypot": check_honeypot,
                    }
                )
                req_id_map[req_id] = p

                fut = loop.create_future()
                # [AUDIT FIX] Use lock for thread-safety consistency
                async with self._lock:
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
            # Ensure json.dumps(i) is decoded if it is bytes
            lines = []
            for i in inputs:
                dumped = json.dumps(i)
                if isinstance(dumped, bytes):
                    lines.append(dumped.decode())
                else:
                    lines.append(dumped)

            payload = "\n".join(lines) + "\n"
            self._proc.stdin.write(payload.encode())
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            if not self._stopping:
                logger.error(f"Go Tester Daemon connection lost: {e}")
            # Fail futures to unblock
            for f in futures:
                if not f.done():
                    f.set_exception(e)

            # Mark all proxies in this batch as failed due to daemon crash
            for p in req_id_map.values():
                if p.is_working is None:  # Only if not already processed
                    p.is_working = False
                    p.details["error"] = "DAEMON_CRASHED"
                    p.details["failure_category"] = "CRASH"

            # Process might be dead, ensure restart next time
            await self.close()
            return proxies
        except Exception as e:
            logger.error(f"Failed to write to Go Tester Daemon: {e}")
            # Fail futures to unblock
            for f in futures:
                if not f.done():
                    f.set_exception(e)

            # Mark queued proxies as failed (write/IPC failure)
            for p in req_id_map.values():
                if p.is_working is None:
                    p.is_working = False
                    if not isinstance(p.details, dict):
                        p.details = {}
                    p.details.setdefault("error", "DAEMON_WRITE_FAILED")
                    p.details.setdefault("failure_category", "CRASH")

            # Process might be dead, ensure restart next time
            await self.close()
            return proxies

        # Wait for results
        # Set a total timeout relative to batch size
        # FIX: Increase base buffer to 40s to ensure it exceeds Go worker's timeout and gives Python breathing room
        total_timeout = min(300, len(inputs) * 2 + 40)

        try:
            completed_results = await asyncio.wait_for(
                asyncio.gather(*futures, return_exceptions=True), timeout=total_timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Timed out waiting for {len(inputs)} results from Go Tester Daemon. Restarting daemon..."
            )
            # Cleanup and mark incomplete proxies as unknown/failed
            # Collect keys to remove under lock, then mark proxies outside lock
            async with self._lock:
                keys_to_remove = [
                    req_id
                    for f, req_id in zip(futures, req_id_map.keys())
                    if not f.done()
                ]
                for req_id in keys_to_remove:
                    self._pending_futures.pop(req_id, None)
            for req_id in keys_to_remove:
                if proxy_obj := req_id_map.get(req_id):
                    proxy_obj.is_working = False
                    proxy_obj.details["error"] = "BATCH_TIMEOUT"
                    proxy_obj.details["failure_category"] = "TIMEOUT"
            # Cancel futures after cleanup
            for f in futures:
                if not f.done():
                    f.cancel()

            # Restart daemon asynchronously to recover for next batch
            asyncio.create_task(self._restart_daemon())
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
            # Rename to avoid shadowing the variable 'proxy_obj' from the cleanup loop (if it leaked)
            # although python loop variables leak, but 'proxy_obj' in cleanup was inside the loop scope
            # and this is outside. But to be safe and satisfy linter:
            target_proxy: Optional[Proxy] = req_id_map.get(req_id)
            if not target_proxy:
                continue

            if res_data.get("is_working"):
                target_proxy.is_working = True
                target_proxy.latency = res_data.get("latency")
                working_count += 1
                if res_data.get("issues"):
                    for issue in res_data["issues"]:
                        target_proxy.security_issues.setdefault("go_check", []).append(
                            issue
                        )
                        if issue == "DIRTY_IP":
                            target_proxy.tags.append("dirty_ip")
            else:
                target_proxy.is_working = False
                error_msg = str(res_data.get("error", "unknown"))
                target_proxy.details["error"] = error_msg

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
                    target_proxy.details["failure_category"] = error_cat

        # Log summary
        failure_summary = ", ".join([f"{k}: {v}" for k, v in failure_reasons.items()])
        logger.info(
            f"Go Tester results (Batch): {working_count}/{len(inputs)} working. "
            f"Failures: {failure_summary if failure_summary else 'None'}"
        )

        # Flush logs after batch
        await self._flush_error_logs()

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
        futures: List[asyncio.Future[Any]] = []
        loop = asyncio.get_running_loop()

        for item in configs:
            chain_id = item.get("id")
            outbounds = item.get("outbounds")
            if not chain_id or not outbounds:
                continue

            # FIX: Send as proper JSON array string
            raw_json = json.dumps(outbounds)
            if isinstance(raw_json, bytes):
                config_str = raw_json.decode()
            else:
                config_str = raw_json

            # FIX: Strip brackets only when the JSON is actually an array; keep safe for empty lists.
            if isinstance(outbounds, list):
                s = config_str.strip()
                if not outbounds:
                    continue
                if s.startswith("[") and s.endswith("]") and len(s) >= 2:
                    config_str = s[1:-1]

            # Unique request ID (Full UUID)
            req_id = f"{chain_id}-{uuid.uuid4().hex}"

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
            async with self._lock:
                self._pending_futures[req_id] = fut
            futures.append(fut)

        if not inputs:
            return {}

        # Send
        try:
            lines = []
            for i in inputs:
                dumped = json.dumps(i)
                if isinstance(dumped, bytes):
                    lines.append(dumped.decode())
                else:
                    lines.append(dumped)

            payload = "\n".join(lines) + "\n"
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
            # Cleanup under lock to prevent race with _read_loop
            async with self._lock:
                for req_id in reverse_map.keys():
                    self._pending_futures.pop(req_id, None)
            for f in futures:
                if not f.done():
                    f.cancel()
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
