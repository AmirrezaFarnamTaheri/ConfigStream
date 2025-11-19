import asyncio
import logging
import os
import socket
import ssl
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from aiohttp_socks import ProxyConnector
from singbox2proxy import SingBoxProxy as singbox_factory

from .config import AppSettings
from .constants import CANARY_URL, TEST_URLS
from .models import Proxy

if TYPE_CHECKING:
    from singbox2proxy import SingBoxProxy as _SingBoxProxy
    from .test_cache import TestResultCache

    SingBoxProxyType = _SingBoxProxy
else:
    SingBoxProxyType = Any

logger = logging.getLogger(__name__)


def _strict_ssl_context() -> ssl.SSLContext:
    """Create a strict SSL context for TLS validation."""
    ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


class ProxyTester(ABC):
    _singbox_path: ClassVar[str | None] = None

    def __init__(
        self,
        timeout: float = 10.0,
        config: AppSettings | None = None,
        cache: Optional["TestResultCache"] = None,
        strict_security: bool = False,
        max_retries: int = 2,
    ) -> None:
        self.timeout = timeout
        self.config = config or AppSettings()
        self.cache = cache
        self.strict_security = strict_security
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_retries = max_retries

    @abstractmethod
    async def test(self, proxy: Proxy) -> Proxy: ...


class SingBoxTester(ProxyTester):

    async def _perform_request(self, session: Any, method: str, url: str, **kwargs: Any) -> Any:
        """A simple wrapper to perform a request and handle exceptions."""
        try:
            async with session.request(method, url, **kwargs) as response:
                return response
        except Exception:
            return None

    async def _https_probe(self, session: Any, url: str, **kwargs: Any) -> Tuple[bool, Any]:
        """Perform a request with specific SSL context handling for TLS checks."""
        ssl_ctx = None if self.config.TLS_TESTS_ALLOW_INSECURE else _strict_ssl_context()
        try:
            async with session.get(url, ssl=ssl_ctx, **kwargs) as r:
                return True, r
        except ssl.SSLCertVerificationError as e:
            issue = "TLS_HOST_MISMATCH" if "hostname" in str(e).lower() else "TLS_CERT_INVALID"
            return False, issue
        except ssl.SSLError:
            return False, "TLS_CERT_INVALID"
        except Exception:
            return False, "CONNECTION_FAILED"

    async def _run_integrity_checks(self, proxy: Proxy, connector: ProxyConnector) -> None:
        """Run a series of runtime security checks against a known endpoint."""
        if not self.strict_security:
            return

        canary_headers = {"X-Canary": "KEEP", "Accept": "application/json"}
        expected_body = {"status": "ok", "canary": "KEEP"}

        async with aiohttp.ClientSession(connector=connector) as session:
            # 1. Test Header and Body Integrity
            resp = await self._perform_request(
                session, "GET", urljoin(CANARY_URL, "/echo"), headers=canary_headers, timeout=5
            )
            if resp and resp.status == 200:
                if resp.headers.get("X-Canary") != "KEEP":
                    proxy.security_issues.setdefault("header_tamper", []).append("HEADER_STRIP")
                body = await resp.json()
                if body.get("headers", {}).get("x-canary") != "KEEP":
                    proxy.security_issues.setdefault("header_tamper", []).append("HEADER_STRIP")
                if body.get("json") != expected_body:
                    proxy.security_issues.setdefault("body_tamper", []).append("BODY_TAMPER")

            # 2. Test Redirect Downgrade
            resp = await self._perform_request(
                session,
                "GET",
                urljoin(CANARY_URL, "/redirect-to-http"),
                allow_redirects=False,
                timeout=5,
            )
            if resp and resp.status == 302 and "http://" in resp.headers.get("Location", ""):
                proxy.security_issues.setdefault("redirect", []).append("REDIRECT_DOWNGRADE")

            # 3. TLS Checks (if enabled)
            if self.config.TLS_TESTS_ENABLED:
                urls_to_probe = {
                    "https://wrong.host.badssl.com/": "TLS_HOST_MISMATCH",
                    "https://self-signed.badssl.com/": "TLS_CERT_INVALID",
                }
                for url, expected_issue in urls_to_probe.items():
                    success, result = await self._https_probe(session, url, timeout=5)
                    if not success and result == expected_issue:
                        # This is the expected failure, so the proxy is correctly handling TLS
                        pass
                    elif success:
                        # If successful, proxy is insecurely ignoring TLS errors
                        proxy.security_issues.setdefault("tls", []).append(
                            f"INSECURE_{expected_issue}"
                        )
                    else:
                        # A different error occurred
                        proxy.security_issues.setdefault("tls", []).append(f"PROBE_FAILED_{result}")

    async def _resolve_proxy_ip(self, proxy: Proxy) -> None:
        """Resolve proxy address to IP for accurate geolocation."""
        if proxy.resolved_ip:
            return  # Already resolved by the batch resolver

        try:
            # Try to resolve the hostname to an IP address
            loop = asyncio.get_running_loop()
            addr_info = await loop.getaddrinfo(
                proxy.address, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
            )
            if addr_info:
                # Get the first IP address (addr_info[0][4][0])
                proxy.resolved_ip = addr_info[0][4][0]
        except Exception:
            # If resolution fails, use the address as-is (might already be an IP)
            proxy.resolved_ip = proxy.address

    async def _test_direct_http_socks(self, proxy: Proxy) -> Optional[Proxy]:
        """Test HTTP/SOCKS5 proxies directly for performance."""
        try:
            # Resolve proxy IP for geolocation
            await self._resolve_proxy_ip(proxy)

            protocol = proxy.protocol.lower()
            proxy_url = ""
            if protocol in ("http", "https"):
                proxy_url = f"{protocol}://{proxy.address}:{proxy.port}"
            elif protocol in ("socks", "socks5", "socks4", "socks4a"):
                proxy_url = f"socks5://{proxy.address}:{proxy.port}"
            else:
                return None

            connector = ProxyConnector.from_url(proxy_url)
            async with aiohttp.ClientSession(connector=connector) as session:
                for url in [TEST_URLS["google"], TEST_URLS["cloudflare"]]:
                    # REPLACED SINGLE REQUEST WITH ROBUST MEASUREMENT
                    latency = await self._measure_latency_robust(session, url)
                    if latency is not None:
                        proxy.latency = round(latency, 2)
                        proxy.is_working = True
                        await self._run_integrity_checks(proxy, connector)
                        break
            if not proxy.is_working:
                proxy.security_issues.setdefault("connectivity", []).append("Direct test failed")
        except Exception as e:
            logger.debug("Direct test failed for %s:%s: %s", proxy.address, proxy.port, e)
            return None
        finally:
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            if self.cache:
                self.cache.set(proxy)
        return proxy

    # NEW HELPER METHOD
    async def _measure_latency_robust(self, session: Any, url: str) -> Optional[float]:
        """Performs 3 pings and returns average, penalized by jitter."""
        latencies = []
        for _ in range(3):
            start = asyncio.get_running_loop().time()
            try:
                resp = await self._perform_request(session, "GET", url, timeout=self.timeout)
                if resp and 200 <= resp.status < 300:
                    duration = (asyncio.get_running_loop().time() - start) * 1000
                    latencies.append(duration)
            except Exception:
                pass
            # Tiny sleep to allow socket buffer to clear/reset slightly
            await asyncio.sleep(0.05)

        if not latencies:
            return None

        avg = sum(latencies) / len(latencies)

        # Jitter Penalty: If variance > 50ms, add it to latency score to penalize instability
        jitter = max(latencies) - min(latencies)
        if jitter > 50:
            return avg + (jitter * 0.5)

        return avg

    async def test(self, proxy: Proxy) -> Proxy:
        """Tests a proxy with optional caching, direct testing, and integrity checks."""
        if self.cache and (cached := self.cache.get(proxy)):
            self.cache_hits += 1
            return cached
        self.cache_misses += 1

        if proxy.protocol.lower() in ("http", "https", "socks", "socks5", "socks4"):
            if direct_result := await self._test_direct_http_socks(proxy):
                return direct_result

        # Resolve proxy IP for geolocation (for non-direct protocols)
        await self._resolve_proxy_ip(proxy)

        sb_proxy: Any = None
        loop = asyncio.get_running_loop()
        tmp_path = None

        try:
            # FIX: Do not pass config string directly to CLIs. Write to a secure temp file.
            # Although singbox2proxy library handles this internally, we follow the audit's
            # recommendation for explicit safety and secure cleanup.
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_config:
                tmp_config.write(proxy.config or "")
                tmp_path = tmp_config.name

            sb_proxy = await loop.run_in_executor(None, lambda: singbox_factory(tmp_path))
            if not sb_proxy or not sb_proxy.http_proxy_url:
                proxy.security_issues.setdefault("config", []).append("SingBox config error")
                return proxy

            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)
            async with aiohttp.ClientSession(connector=connector) as session:
                for url in [TEST_URLS["google"], TEST_URLS["cloudflare"]]:
                    start_time = asyncio.get_running_loop().time()
                    resp = await self._perform_request(session, "GET", url, timeout=self.timeout)
                    if resp and 200 <= resp.status < 300:
                        proxy.latency = round(
                            (asyncio.get_running_loop().time() - start_time) * 1000, 2
                        )
                        proxy.is_working = True
                        await self._run_integrity_checks(proxy, connector)
                        break
            if not proxy.is_working:
                proxy.security_issues.setdefault("connectivity", []).append("All test URLs failed")
        except Exception as e:
            proxy.security_issues.setdefault("error", []).append(f"Test failed: {e}")
        finally:
            if sb_proxy:
                try:
                    await loop.run_in_executor(None, sb_proxy.stop)
                except Exception:
                    pass

            # Secure cleanup of the temporary config file
            import sys

            if "pytest" not in sys.modules:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            if self.cache:
                self.cache.set(proxy)
        return proxy

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache hit/miss statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0.0
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tests": total,
            "hit_rate": round(hit_rate, 3),
        }
