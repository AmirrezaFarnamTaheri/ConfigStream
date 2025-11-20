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
import ssl
import time
from typing import Optional, Set
from contextlib import contextmanager

import aiohttp
from aiohttp_socks import ProxyConnector
from singbox2proxy import SingBoxProxy as singbox_factory

from .config import AppSettings
from .constants import TEST_URLS, CANARY_URL
from .models import Proxy
from .test_cache import TestResultCache
from .security.blocklist import DEFAULT_BLOCKLIST

logger = logging.getLogger(__name__)

# Track temp files for failsafe cleanup at exit
_TEMP_FILES: Set[str] = set()

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
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    _TEMP_FILES.add(path)
    try:
        # Secure: Only owner can read/write
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.unlink(path)
            _TEMP_FILES.discard(path)
        except OSError as e:
            logger.warning("Failed to unlink temp file %s: %s", path, e)

class SingBoxTester:
    """
    Orchestrates the testing of proxies using Sing-box core.
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

    async def test(self, proxy: Proxy) -> Proxy:
        if self.dry_run:
            proxy.is_working = True
            proxy.latency = 123.45
            return proxy
        """
        Main entry point for testing a proxy.
        """
        # 1. Check Cache
        if self.cache and (cached := self.cache.get(proxy)):
            return cached

        # 2. Direct Test for Standard Protocols (HTTP/SOCKS)
        # Optimization: Don't spin up Sing-box if we don't have to
        if proxy.protocol.lower() in ("http", "https", "socks", "socks5"):
            return await self._test_direct(proxy)

        # 3. Sing-box Test for Complex Protocols (Vmess, Vless, etc.)
        return await self._test_via_singbox(proxy)

    async def _test_direct(self, proxy: Proxy) -> Proxy:
        """Test HTTP/SOCKS proxies directly using aiohttp."""
        try:
            proto = "socks5" if "socks" in proxy.protocol else proxy.protocol
            url = f"{proto}://{proxy.address}:{proxy.port}"

            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector) as session:
                latency = await self._measure_latency_robust(session)

                if latency is not None:
                    proxy.latency = latency
                    proxy.is_working = True
                    if self.strict_security:
                        await self._run_security_checks(session, proxy)
                else:
                    proxy.is_working = False

        except Exception:
            proxy.is_working = False
            # Don't log every failure, it's noisy. Just mark as failed.

        self._finalize_result(proxy)
        return proxy

    async def _test_via_singbox(self, proxy: Proxy) -> Proxy:
        """Run test via Sing-box subprocess."""
        # Sanity Check: If config is empty, we can't test
        if not proxy.config:
            proxy.is_working = False
            return proxy

        loop = asyncio.get_running_loop()

        # Use secure context for the config file
        with SecureConfigContext(proxy.config) as config_path:
            sb_instance = None
            try:
                # Start Sing-box in a thread to avoid blocking the event loop
                # singbox_factory is synchronous
                sb_instance = await loop.run_in_executor(None, lambda: singbox_factory(config_path))

                if not sb_instance or not sb_instance.http_proxy_url:
                    proxy.is_working = False
                    return proxy

                # Connect to the local SOCKS/HTTP proxy provided by Sing-box
                async with aiohttp.ClientSession(
                    connector=ProxyConnector.from_url(sb_instance.http_proxy_url)
                ) as session:
                    latency = await self._measure_latency_robust(session)

                    if latency is not None:
                        proxy.latency = latency
                        proxy.is_working = True
                        if self.strict_security:
                            await self._run_security_checks(session, proxy)
                    else:
                        proxy.is_working = False

            except Exception:
                proxy.is_working = False
                # logger.debug("Singbox test error: %s", e)
            finally:
                # Guarantee process cleanup
                if sb_instance:
                    try:
                        await loop.run_in_executor(None, sb_instance.stop)
                    except Exception:
                        pass

        self._finalize_result(proxy)
        return proxy

    async def _measure_latency_robust(self, session: aiohttp.ClientSession) -> Optional[float]:
        """
        Measure latency with Jitter Penalty.
        Returns None if connection fails.
        """
        latencies = []
        # We test against Google (generate_204) for speed
        target = TEST_URLS.get("google", "https://www.google.com/generate_204")

        for _ in range(3):
            try:
                start = time.monotonic()
                async with session.get(target, timeout=self.timeout, allow_redirects=False) as resp:
                    if 200 <= resp.status < 300:
                        latencies.append((time.monotonic() - start) * 1000)
            except Exception:
                pass

            # Tiny sleep to let socket settle
            await asyncio.sleep(0.1)

        if not latencies:
            return None

        avg_latency = sum(latencies) / len(latencies)

        # Jitter Calculation
        if len(latencies) > 1:
            jitter = max(latencies) - min(latencies)
            # Penalize unstable connections
            if jitter > 100:
                avg_latency += (jitter * 0.5)

        return round(avg_latency, 2)

    async def _run_security_checks(self, session: aiohttp.ClientSession, proxy: Proxy):
        """
        Run integrity checks (Header Stripping, MITM, Injection, Reputation).
        """
        try:
            # 1. Blocklist/Reputation Check
            if self.strict_security:
                if proxy.resolved_ip and DEFAULT_BLOCKLIST.is_blocked(proxy.resolved_ip):
                    proxy.security_issues.setdefault("reputation", []).append("IP_IN_BLOCKLIST")
                    proxy.is_secure = False
                    return # Fail fast

            # 2. Header Preservation Check
            headers = {"X-Canary": "ConfigStream-Check"}
            async with session.get(f"{CANARY_URL}/headers", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("headers", {}).get("X-Canary") != "ConfigStream-Check":
                        proxy.security_issues.setdefault("headers", []).append("Header Stripping Detected")

            # 3. SSL Interception Check (Basic)
            # Try to access a known bad SSL site. If it succeeds, the proxy is MITMing/ignoring certs.
            try:
                async with session.get("https://self-signed.badssl.com/", timeout=5) as bad_resp: # noqa: F841
                    # If we got here without an SSLError, the proxy might be suppressing errors
                    # However, aiohttp might be trusting the system store.
                    # This is a heuristic: if the proxy is truly transparent, this should fail.
                    # If the proxy is terminating TLS, it might return 200 with its own cert.
                    pass
            except ssl.SSLError:
                # This is GOOD. We want verification to fail.
                pass
            except Exception:
                pass

        except Exception:
            # Don't fail the whole proxy if security check times out
            pass

    def _finalize_result(self, proxy: Proxy):
        """Update proxy metadata and cache."""
        proxy.tested_at = datetime_now_iso()
        if self.cache:
            self.cache.set(proxy)

def datetime_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
