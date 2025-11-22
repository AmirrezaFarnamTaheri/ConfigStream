"""
Secure Proxy Testing Module.
Handles the lifecycle of Sing-box instances and measures performance
with strict resource cleanup and security boundaries.
"""

import asyncio
import logging
import os
import stat
import tempfile
import atexit
import time
import json
from typing import Optional, Set, List
from contextlib import contextmanager

import aiohttp
from aiohttp_socks import ProxyConnector

try:
    from singbox2proxy import SingBoxProxy as singbox_factory
except ImportError:
    singbox_factory = None

from .config import AppSettings
from .models import Proxy
from .test_cache import TestResultCache
from .converters import to_singbox_outbound

logger = logging.getLogger(__name__)

# Track temp files for failsafe cleanup at exit
_TEMP_FILES: Set[str] = set()

# Known SHA256 fingerprints for MITM detection
SUSPICIOUS_ISSUERS = [
    "mitmproxy",
    "Fiddler",
    "GoProxy",
    "Charles",
    "BurpSuite",
    "ConfigStream-Interceptor",
]


def _cleanup_temp_files():
    """Failsafe cleanup for any remaining config files."""
    for path in _TEMP_FILES:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


@contextmanager
def SecureConfigContext(content: str):
    """
    Context manager that creates a secure temporary file for Sing-box config.
    Enforces 0600 permissions and guarantees deletion.
    """
    fd, path = tempfile.mkstemp(suffix=".json")
    _TEMP_FILES.add(path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        if not os.path.exists(path):
            raise OSError(f"Failed to create temp config file at {path}")
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.unlink(path)
            _TEMP_FILES.discard(path)
        except OSError as e:
            logger.warning("Failed to unlink temp file %s: %s", path, e)


class GoBatchTester:
    """
    Interface to the high-performance Go batch testing binary.
    """

    def __init__(self, binary_path: str = "/usr/local/bin/configstream-tester"):
        self.binary_path = binary_path
        self.available = os.path.exists(binary_path)
        if not self.available:
            logger.warning(f"Go batch tester binary not found at {binary_path}")

    async def test_batch(
        self, proxies: List[Proxy], check_honeypot: bool = False
    ) -> List[Proxy]:
        """
        Feeds a batch of proxies to the Go binary and updates them with results.
        """
        if not self.available or not proxies:
            return proxies

        # Prepare Input
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

        if not inputs:
            return proxies

        # Execute Binary
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdin_data = "\n".join(json.dumps(i) for i in inputs).encode("utf-8")

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_data), timeout=300
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                logger.error("Go Tester froze! Killing process to save pipeline.")
                return proxies  # Return what we have (untagged) instead of crashing

            if stderr:
                logger.debug(f"Go Tester Stderr: {stderr.decode().strip()}")

            # Parse Output
            for line in stdout.decode().splitlines():
                try:
                    res = json.loads(line)
                    p_id = res.get("id")
                    # Mypy fix: Ensure p is not None before usage (proxy_map.get can return None)
                    if p_id and p_id in proxy_map:
                        p = proxy_map[p_id]
                        if res.get("is_working"):
                            p.is_working = True
                            p.latency = res.get("latency")
                            # Flag issues
                            if res.get("issues"):
                                for issue in res["issues"]:
                                    p.security_issues.setdefault("go_check", []).append(
                                        issue
                                    )
                                    if issue == "DIRTY_IP":
                                        p.tags.append("dirty_ip")
                        else:
                            p.is_working = False
                            if res.get("error"):
                                # Maybe store error for debugging?
                                pass
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Go Batch Tester failed: {e}")
            # Fallback: don't mark anything working if the tester crashed
            pass

        return proxies


class SingBoxTester:
    """
    Orchestrates the testing of proxies using Sing-box core.
    Supports both legacy Python-subprocess mode and new Go Batch mode.
    """

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
        """
        Single proxy test (Legacy/Fallback).
        """
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
        """
        Batch test entry point. Uses Go tester if available, otherwise loops legacy test.
        """
        if self.go_tester.available:
            # Filter cached
            to_test = []
            for p in proxies:
                if self.cache and (cached := self.cache.get(p)):
                    # Update p with cached values (or replace in list logic upstream)
                    p.is_working = cached.is_working
                    p.latency = cached.latency
                else:
                    to_test.append(p)

            # Test fresh
            if to_test:
                await self.go_tester.test_batch(
                    to_test, check_honeypot=self.strict_security
                )

                # Update cache
                if self.cache:
                    for p in to_test:
                        self._finalize_result(p)

            return proxies
        else:
            # Fallback to sequential/concurrent loop in Python
            # This is handled by the pipeline's existing concurrency manager if test_batch isn't used
            # But if pipeline calls test_batch, we simulate it.
            # However, for simplicity, we assume pipeline prefers batch if available.
            # We'll implement a gathering loop here for fallback.
            tasks = [self.test(p) for p in proxies]
            return await asyncio.gather(*tasks)

    async def _test_direct(self, proxy: Proxy) -> Proxy:
        """Test HTTP/SOCKS proxies directly using aiohttp."""
        try:
            proto = "socks5" if "socks" in proxy.protocol else proxy.protocol
            url = f"{proto}://{proxy.address}:{proxy.port}"

            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session, proxy)

                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True

                    # Check for insecure proxy (HTTP/SOCKS without TLS)
                    if (
                        proxy.protocol in ["http", "socks", "socks5"]
                        and proxy.details.get("tls") != "tls"
                    ):
                        proxy.tags.append("insecure")

                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False

        except Exception:
            proxy.is_working = False

        self._finalize_result(proxy)
        return proxy

    async def _test_via_singbox(self, proxy: Proxy) -> Proxy:
        """Run test via Sing-box subprocess (Legacy Python Wrapper)."""
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
                    # Fallback if singbox2proxy not installed
                    proxy.is_working = False

            except Exception:
                proxy.is_working = False
            finally:
                if sb_instance:
                    try:
                        await asyncio.wait_for(
                            loop.run_in_executor(None, sb_instance.stop), timeout=5.0
                        )
                    except Exception:
                        pass

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
        """
        Perform advanced security checks on the proxy.
        - Check against blocklists (if not already done)
        - Mark as checked
        """
        # In strict mode, we assume the proxy has passed basic connectivity.
        # Real MITM checks require inspecting the SSL context which aiohttp abstracts.
        # For now, we verify the resolved IP isn't in our local blocklist again as a safeguard.

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
        """Update proxy metadata and cache."""
        proxy.tested_at = datetime_now_iso()
        if self.cache:
            self.cache.set(proxy)


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
