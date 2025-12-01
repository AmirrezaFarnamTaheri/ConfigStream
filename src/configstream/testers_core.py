"""
Core Tester Implementation.
Refactored from testers.py to reduce monolith size.
"""

import asyncio
import logging
import os
import json
import time
import shutil
import stat
import tempfile
import atexit
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from contextlib import contextmanager

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import AppSettings
from .models import Proxy
from .test_cache import TestResultCache
from .converters import to_singbox_outbound

logger = logging.getLogger(__name__)

# Optional dependency
try:
    from singbox2proxy import SingBoxProxy as singbox_factory
except ImportError:
    singbox_factory = None
    logger.warning(
        "singbox2proxy not installed - Python fallback testing will be limited. "
        "Install with: pip install singbox2proxy"
    )

_TEMP_FILES: Set[str] = set()
_TEMP_FILES_LOCK = threading.Lock()


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _cleanup_temp_files():
    for path in _TEMP_FILES:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


@contextmanager
def SecureConfigContext(content: str):
    fd, path = tempfile.mkstemp(suffix=".json")
    with _TEMP_FILES_LOCK:
        _TEMP_FILES.add(path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        if not os.path.exists(path):
            raise OSError(f"Failed to create temp config file at {path}")
        logger.debug(f"Created temp config file: {path}")
        yield path
    finally:
        try:
            # os.unlink raises FileNotFoundError if file doesn't exist, which is fine
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("Failed to unlink temp file %s: %s", path, e)
        finally:
            with _TEMP_FILES_LOCK:
                _TEMP_FILES.discard(path)
            logger.debug(f"Cleaned up temp config file: {path}")


class GoBatchTester:
    def __init__(self, binary_path: str = "/usr/local/bin/configstream-tester"):
        env_path = os.environ.get("CONFIGSTREAM_TESTER_BIN")
        if env_path:
            binary_path = env_path

        resolved = None
        if os.path.exists(binary_path):
            resolved = binary_path
        else:
            which_result = shutil.which(Path(binary_path).name)
            if which_result:
                resolved = which_result
            else:
                name_only = Path(binary_path).name
                for base in os.environ.get("PATH", "").split(os.pathsep):
                    candidate = Path(base) / name_only
                    if candidate.exists():
                        resolved = str(candidate)
                        break

        self.binary_path = resolved or binary_path
        self.available = resolved is not None
        if not self.available:
            # Fail loudly here so operators understand that NO proxies will be tested
            # when the Go batch tester is expected but missing.
            logger.error(
                "CRITICAL: Go batch tester binary not found at %s. "
                "No proxies will be tested via the high-performance path!",
                binary_path,
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
            cmd = [self.binary_path, "-workers", "50"]

            # Pass timeout
            cmd.extend(["-timeout", f"{int(AppSettings.TEST_TIMEOUT)}s"])

            # Pass URLs
            if AppSettings.TEST_URLS:
                urls = ",".join(str(u) for u in AppSettings.TEST_URLS.values())
                cmd.extend(["-urls", urls])

            logger.info(
                f"Invoking Go tester with {len(inputs)} proxies: {' '.join(cmd)}"
            )

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdin_data = "\n".join(json.dumps(i) for i in inputs).encode("utf-8")

            try:
                # [FIX] Increased timeout to 600s to accommodate heavy batches/retries
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_data), timeout=600
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
                                logger.info(
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


class SingBoxTester:
    def __init__(
        self,
        timeout: float = 10.0,
        cache: Optional[TestResultCache] = None,
        strict_security: bool = False,
        dry_run: bool = False,
    ):
        self.timeout = timeout
        self.cache = cache
        self.strict_security = strict_security
        self.settings = AppSettings()
        self.dry_run = dry_run
        self.go_tester = GoBatchTester()

    async def test(self, proxy: Proxy) -> Proxy:
        if self.dry_run:
            proxy.is_working = True
            proxy.latency = 123.45
            return proxy

        if self.cache and (cached := self.cache.get(proxy)):
            return cached

        if proxy.protocol.lower() in ("http", "https", "socks", "socks5"):
            return await self._test_direct(proxy)

        return await self._test_via_singbox(proxy)

    async def test_batch(self, proxies: List[Proxy]) -> List[Proxy]:
        if self.go_tester.available:
            to_test = []
            for p in proxies:
                if self.cache and (cached := self.cache.get(p)):
                    p.is_working = cached.is_working
                    p.latency = cached.latency
                else:
                    to_test.append(p)

            if to_test:
                await self.go_tester.test_batch(
                    to_test, check_honeypot=self.strict_security
                )
                if self.cache:
                    for p in to_test:
                        self._finalize_result(p)
            return proxies
        else:
            logger.info(
                f"Fallback: Testing batch of {len(proxies)} proxies using Python tester"
            )
            tasks = [self.test(p) for p in proxies]
            return await asyncio.gather(*tasks)

    async def _test_direct(self, proxy: Proxy) -> Proxy:
        try:
            proto = "socks5" if "socks" in proxy.protocol else proxy.protocol
            url = f"{proto}://{proxy.address}:{proxy.port}"
            logger.debug(f"Testing direct connection: {url}")
            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session, proxy)
                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True
                    if (
                        proxy.protocol in ["http", "socks", "socks5"]
                        and proxy.details.get("tls") != "tls"
                    ):
                        proxy.tags.append("insecure")
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False
        except Exception as e:
            proxy.is_working = False
            proxy.details["error"] = str(e)
        self._finalize_result(proxy)
        return proxy

    async def _test_via_singbox(self, proxy: Proxy) -> Proxy:
        if not proxy.config:
            proxy.is_working = False
            return proxy

        loop = asyncio.get_running_loop()
        outbound_config = to_singbox_outbound(proxy)
        if not outbound_config:
            proxy.is_working = False
            return proxy

        outbound_config["tag"] = "proxy-test"
        full_config = {
            "log": {"level": "info"},
            "inbounds": [
                {
                    "type": "mixed",
                    "tag": "mixed-in",
                    "listen": "127.0.0.1",
                    "listen_port": 0,
                }
            ],
            "outbounds": [outbound_config],
        }
        config_content = json.dumps(full_config)

        with SecureConfigContext(config_content) as config_path:
            sb_instance = None
            try:
                if singbox_factory:
                    try:
                        sb_instance = await asyncio.wait_for(
                            loop.run_in_executor(
                                None, lambda: singbox_factory(config_path)
                            ),
                            timeout=self.timeout,
                        )
                    except asyncio.TimeoutError:
                        proxy.is_working = False
                        return proxy

                    if not sb_instance or not sb_instance.http_proxy_url:
                        proxy.is_working = False
                        return proxy

                    async with aiohttp.ClientSession(
                        connector=ProxyConnector.from_url(sb_instance.http_proxy_url)
                    ) as session:
                        latency = await self._measure_latency_robust(session, proxy)
                        if latency is not None:
                            proxy.latency = latency
                            proxy.is_working = True
                            if self.strict_security:
                                await self._run_security_checks(session, proxy)
                        else:
                            proxy.is_working = False
                else:
                    logger.warning(
                        "Skipping test: 'singbox2proxy' library not found. Install it or use the Go tester."
                    )
                    proxy.is_working = False
            except Exception as e:
                logger.warning(
                    f"Exception during proxy test for {proxy.address}:{proxy.port}: {e}"
                )
                proxy.is_working = False
                proxy.details["error"] = str(e)
            finally:
                if sb_instance:
                    try:
                        await asyncio.wait_for(
                            loop.run_in_executor(None, sb_instance.stop), timeout=5.0
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to stop Sing-box instance gracefully: {e}"
                        )
        self._finalize_result(proxy)
        return proxy

    async def _measure_latency_robust(
        self, session: aiohttp.ClientSession, proxy: Optional[Proxy] = None
    ) -> Optional[float]:
        async def _try_url(url: str) -> Optional[float]:
            latencies = []
            for _ in range(2):
                try:
                    start = time.monotonic()
                    async with session.get(
                        url, timeout=self.timeout, allow_redirects=False
                    ) as resp:
                        if 200 <= resp.status < 300:
                            latencies.append((time.monotonic() - start) * 1000)
                except Exception:
                    pass
            if not latencies:
                return None
            return sum(latencies) / len(latencies)

        google_url = self.settings.TEST_URLS.get(
            "google", "https://www.google.com/generate_204"
        )
        latency = await _try_url(google_url)
        if latency is not None:
            return round(latency, 2)

        fallback_url = "http://cp.cloudflare.com/generate_204"
        latency = await _try_url(fallback_url)
        if latency is not None:
            if proxy is not None:
                proxy.tags.append("dirty_ip")
            return round(latency, 2)
        return None

    async def _run_security_checks(self, session: aiohttp.ClientSession, proxy: Proxy):
        if proxy.resolved_ip:
            from .security.blocklist import DEFAULT_BLOCKLIST

            if DEFAULT_BLOCKLIST.is_blocked(proxy.resolved_ip):
                proxy.is_working = False
                proxy.security_issues.setdefault("blocklist", []).append(
                    "FireHol Blocked (Late Check)"
                )
                return
        proxy.tags.append("secure-checked")

    def _finalize_result(self, proxy: Proxy):
        proxy.tested_at = datetime_now_iso()
        if self.cache:
            # Only cache if we actually got a definitive test result
            # Don't cache if this was never converted/tested properly
            # Check if is_working is False and latency is None - likely a conversion failure
            if not proxy.is_working and proxy.latency is None:
                logger.debug(
                    f"Skipping cache for untested/failed-conversion proxy: {proxy.id}"
                )
                return
            self.cache.set(proxy)
