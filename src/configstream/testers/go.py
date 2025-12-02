import asyncio
import logging
import os
import json
import shutil
from pathlib import Path
from typing import List, Dict

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

        try:
            # Construct command with flags
            cmd = [self.binary_path, "-workers", str(self.workers)]

            # Pass timeout
            cmd.extend(["-timeout", f"{int(AppSettings.TEST_TIMEOUT)}s"])

            # Pass URLs
            if AppSettings.TEST_URLS:
                urls = ",".join(str(u) for u in AppSettings.TEST_URLS.values())
                cmd.extend(["-urls", urls])

            payload_json = json.dumps(inputs)
            payload_kb = len(payload_json) / 1024.0

            logger.info(
                f"Invoking Go tester with {len(inputs)} proxies. Payload size: {payload_kb:.2f} KB."
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
                except Exception:
                    pass
                logger.error("Go Tester froze! Killing process to save pipeline.")
                return proxies

            # CRITICAL: Log stderr at WARNING level to surface Go tester issues
            if stderr:
                stderr_text = stderr.decode().strip()
                if stderr_text:
                    # Check for critical errors vs warnings
                    if "panic" in stderr_text.lower() or "fatal" in stderr_text.lower():
                        # [FIX] Increased limit to 4KB to capture full stack traces
                        logger.error(f"Go Tester CRASHED: {stderr_text[:4096]}")
                    else:
                        # [FIX] Increased limit to 2KB for standard warnings
                        logger.warning(f"Go Tester stderr: {stderr_text[:2048]}")

            # Check if we got any output at all
            if not stdout or not stdout.strip():
                logger.error(
                    f"Go Tester produced NO OUTPUT! (Exit Code: {proc.returncode}) "
                    f"Sent {len(inputs)} proxies, received nothing. "
                    f"Stderr: {stderr.decode()[:500] if stderr else 'None'}. "
                    "Check if sing-box core is working correctly."
                )
                if stderr:
                    logger.debug(f"Full Go Tester Stderr: {stderr.decode()}")
                # Ensure we log context for the first few failures to aid debugging
                if inputs:
                    sample_input = json.dumps(inputs[0])
                    logger.debug(f"Sample input causing failure: {sample_input}")
                # Mark all as failed explicitly
                for p in proxies:
                    p.is_working = False
                return proxies

            # Count results for diagnostics
            result_count = 0
            working_count = 0
            failure_reasons: Dict[str, int] = {}

            for line in stdout.decode().splitlines():
                try:
                    res = json.loads(line)
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
                                    p.security_issues.setdefault("go_check", []).append(
                                        issue
                                    )
                                    if issue == "DIRTY_IP":
                                        p.tags.append("dirty_ip")
                        else:
                            p.is_working = False
                            error_msg = res.get("error", "unknown")
                            p.details["error"] = error_msg

                            # Categorize errors for better visibility
                            if "HONEYPOT" in error_msg:
                                error_cat = "HONEYPOT"
                            elif "DIRTY_IP" in error_msg:
                                error_cat = "DIRTY_IP"
                            elif "PANIC" in error_msg:
                                error_cat = "PANIC"
                            elif "timeout" in error_msg.lower():
                                error_cat = "TIMEOUT"
                            elif (
                                "bind" in error_msg.lower()
                                and "in use" in error_msg.lower()
                            ):
                                error_cat = "BIND_ERROR"
                            elif "handshake" in error_msg.lower():
                                error_cat = "HANDSHAKE_FAIL"
                            elif "connection refused" in error_msg.lower():
                                error_cat = "CONN_REFUSED"
                            else:
                                error_cat = "OTHER"

                            failure_reasons[error_cat] = (
                                failure_reasons.get(error_cat, 0) + 1
                            )

                            # Enhanced Metadata Tracking
                            # Track failure reason in details for analytics
                            if error_cat not in ["TIMEOUT", "OTHER"]:
                                p.details["failure_category"] = error_cat

                            # [LOGGING] Enhanced failure visibility
                            # Log explicit failure reason regardless of success rate if it's not a timeout
                            # This provides granular visibility into protocol mismatches or blockages
                            meta_str = (
                                f"[ASN:{p.asn or 'N/A'} Country:{p.country or 'N/A'}]"
                            )

                            if error_cat not in ["TIMEOUT"]:
                                logger.debug(
                                    f"Test failed {meta_str} for {p.protocol}://{p.address}:{p.port} -> {error_msg} (Category: {error_cat})"
                                )
                            else:
                                logger.debug(f"Test timeout {meta_str}: {p.address}")

                            # Additional per-proxy debug logging for transparency
                            if logger.isEnabledFor(logging.DEBUG) and not p.is_working:
                                logger.debug(
                                    f"Detailed failure for {p.id} ({p.protocol}): {p.details.get('error')}"
                                )

                except json.JSONDecodeError:
                    continue

            # Log summary statistics
            failure_summary = ", ".join(
                [f"{k}: {v}" for k, v in failure_reasons.items()]
            )
            logger.info(
                f"Go Tester results: {working_count}/{result_count} working "
                f"(sent {len(inputs)}, parsed {result_count}). "
                f"Failures breakdown: {failure_summary if failure_summary else 'None'}"
            )

            # Detect if Go tester is returning but all failing
            if result_count > 0 and working_count == 0:
                logger.error(
                    "Go Tester returned results but ALL tests failed. "
                    "Possible causes: network blocked, test URLs unreachable, "
                    "or sing-box outbound config issues. "
                    f"Breakdown: {failure_summary}"
                )

        except Exception as e:
            logger.error(f"Go Batch Tester failed: {e}")

        return proxies
