import asyncio
import logging
import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

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
        if not self.available:
            logger.error(
                f"CRITICAL: Go batch tester binary not found (searched: {binary_path}, env: {env_path}, PATH). "
                "No proxies will be tested via the high-performance path!"
            )

    async def test_batch(
        self, proxies: List[Proxy], check_honeypot: bool = False
    ) -> List[Proxy]:
        if not self.available or not proxies:
            return proxies

        inputs = []
        proxy_map = {}
        for p in proxies:
            outbound = to_singbox_outbound(p)
            if outbound:
                inputs.append(
                    {
                        "config": json.dumps(outbound),
                        "id": p.id,
                        "check_honeypot": check_honeypot,
                    }
                )
                proxy_map[p.id] = p
            else:
                # Log when converter fails - this is likely a major issue
                logger.warning(
                    f"Cannot convert proxy to singbox format: {p.protocol}://{p.address}:{p.port} - skipping test"
                )
                p.is_working = False

        if not inputs:
            logger.warning(
                f"No valid inputs for Go tester from {len(proxies)} proxies - all conversions failed. "
                "Check protocol support and configuration validity."
            )
            return proxies

        return await self._run_tester(inputs, proxy_map)

    async def test_custom_configs(
        self, configs: List[Dict[str, Any]], check_honeypot: bool = False
    ) -> Dict[str, bool]:
        """
        Test raw Sing-box outbounds (or chains) directly.
        Input: List of {'id': str, 'outbounds': List[Dict]}
        Returns: Dict mapping ID to is_working boolean.
        """
        if not self.available or not configs:
            return {}

        inputs = []
        for item in configs:
            chain_id = item.get("id")
            outbounds = item.get("outbounds")
            if not chain_id or not outbounds:
                continue

            # Serialize chain components as comma-separated JSON objects
            # This format is compatible with the Go tester's string formatting template
            config_str = ", ".join(json.dumps(o) for o in outbounds)
            inputs.append(
                {
                    "config": config_str,
                    "id": chain_id,
                    "check_honeypot": check_honeypot,
                }
            )

        if not inputs:
            return {}

        results = await self._execute_go_binary(inputs)

        status_map = {}
        for res in results:
            status_map[res["id"]] = res.get("is_working", False)

        return status_map

    async def _execute_go_binary(self, inputs: List[Dict]) -> List[Dict]:
        """Core execution logic for the Go binary."""
        try:
            cmd = [self.binary_path, "-workers", str(self.workers)]
            cmd.extend(["-timeout", f"{int(AppSettings.TEST_TIMEOUT)}s"])
            if AppSettings.TEST_URLS:
                urls = ",".join(str(u) for u in AppSettings.TEST_URLS.values())
                cmd.extend(["-urls", urls])

            # [FIX] Use NDJSON (Newline Delimited JSON) for streaming compatibility with Go tester
            payload_json = "\n".join(json.dumps(i) for i in inputs)
            payload_kb = len(payload_json) / 1024.0

            logger.info(
                f"Invoking Go tester with {len(inputs)} items. Payload size: {payload_kb:.2f} KB."
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Go tester command: {' '.join(cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                # [FIX] Increased timeout to 600s to accommodate heavy batches/retries
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=payload_json.encode("utf-8")), timeout=600
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    # CRITICAL FIX: Await process termination to prevent
                    # "Event loop is closed" error during garbage collection.
                    # Without this, the subprocess transport is orphaned and
                    # its __del__ method tries to use the closed event loop.
                    await proc.wait()
                except Exception:
                    pass
                logger.error("Go Tester froze! Killing process to save pipeline.")
                return []
            except Exception:
                # Ensure cleanup on any other exception
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                raise

            if stderr:
                stderr_text = stderr.decode().strip()
                if stderr_text:
                    lower_text = stderr_text.lower()

                    if "panic" in lower_text or "fatal" in lower_text:
                        logger.error(f"Go Tester CRASHED: {stderr_text[:4096]}")
                    elif "info:" in lower_text:
                        logger.info(f"Go Tester: {stderr_text[:2048]}")
                    else:
                        logger.warning(f"Go Tester stderr: {stderr_text[:2048]}")

            if not stdout or not stdout.strip():
                logger.error(
                    f"Go Tester produced NO OUTPUT! (Exit Code: {proc.returncode})"
                )
                return []

            results = []
            for line in stdout.decode().splitlines():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return results

        except Exception as e:
            logger.error(f"Go execution failed: {e}")
            return []

    async def _run_tester(
        self, inputs: List[Dict], proxy_map: Dict[str, Proxy]
    ) -> List[Proxy]:
        results = await self._execute_go_binary(inputs)

        result_count = 0
        working_count = 0
        failure_reasons: Dict[str, int] = {}

        for res in results:
            result_count += 1
            p_id = res.get("id")
            if p_id and p_id in proxy_map:
                p = proxy_map[p_id]
                if res.get("is_working"):
                    p.is_working = True
                    p.latency = res.get("latency")
                    working_count += 1
                    if res.get("issues"):
                        for issue in res["issues"]:
                            p.security_issues.setdefault("go_check", []).append(issue)
                            if issue == "DIRTY_IP":
                                p.tags.append("dirty_ip")
                else:
                    p.is_working = False
                    error_msg = res.get("error", "unknown")
                    p.details["error"] = error_msg

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

                    meta_str = f"[ASN:{p.asn or 'N/A'} Country:{p.country or 'N/A'}]"
                    if error_cat not in ["TIMEOUT"]:
                        logger.debug(
                            f"Test failed {meta_str} for {p.protocol}://{p.address}:{p.port} -> {error_msg} (Category: {error_cat})"
                        )
                    else:
                        logger.debug(f"Test timeout {meta_str}: {p.address}")

        failure_summary = ", ".join([f"{k}: {v}" for k, v in failure_reasons.items()])
        logger.info(
            f"Go Tester results: {working_count}/{result_count} working "
            f"(sent {len(inputs)}, parsed {result_count}). "
            f"Failures breakdown: {failure_summary if failure_summary else 'None'}"
        )

        if result_count > 0 and working_count == 0:
            logger.warning(
                "Go Tester returned results but ALL tests failed (Check network or batch quality)."
            )

        return list(proxy_map.values())
