import asyncio
import importlib
import logging
import ssl
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional, Tuple, cast
from urllib.parse import urljoin

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import AppSettings
from .constants import CANARY_URL, TEST_URLS
from .models import Proxy

if TYPE_CHECKING:
    from singbox2proxy import SingBoxProxy as _SingBoxProxy
    from .test_cache import TestResultCache

    SingBoxProxyType = _SingBoxProxy
else:
    SingBoxProxyType = Any

SingBoxProxy: Callable[[str], Any] | None = None
logger = logging.getLogger(__name__)


def _strict_ssl_context() -> ssl.SSLContext:
    """Create a strict SSL context for TLS validation."""
    ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


class ProxyTester:
    _singbox_path: ClassVar[str | None] = None

    def __init__(
        self,
        timeout: float = 10.0,
        config: AppSettings | None = None,
        cache: Optional["TestResultCache"] = None,
        max_retries: int = 2,
    ) -> None:
        self.timeout = timeout
        self.config = config or AppSettings()
        self.cache = cache
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_retries = max_retries

    async def test(self, proxy: Proxy) -> Proxy:
        raise NotImplementedError


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
                        # If the request succeeds, it means the proxy is insecurely ignoring TLS errors
                        proxy.security_issues.setdefault("tls", []).append(
                            f"INSECURE_{expected_issue}"
                        )
                    else:
                        # A different error occurred
                        proxy.security_issues.setdefault("tls", []).append(f"PROBE_FAILED_{result}")

    async def _test_direct_http_socks(self, proxy: Proxy) -> Optional[Proxy]:
        """Test HTTP/SOCKS5 proxies directly for performance."""
        try:
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
                proxy.security_issues.setdefault("connectivity", []).append("Direct test failed")
        except Exception as e:
            logger.debug(f"Direct test failed for {proxy.address}:{proxy.port}: {e}")
            return None
        finally:
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            if self.cache:
                self.cache.set(proxy)
        return proxy

    async def test(self, proxy: Proxy) -> Proxy:
        """Tests a proxy with optional caching, direct testing, and integrity checks."""
        if self.cache and (cached := self.cache.get(proxy)):
            self.cache_hits += 1
            return cached
        self.cache_misses += 1

        if proxy.protocol.lower() in ("http", "https", "socks", "socks5", "socks4"):
            if direct_result := await self._test_direct_http_socks(proxy):
                return direct_result

        singbox_factory = self._get_singbox_factory()
        sb_proxy: Any = None
        loop = asyncio.get_running_loop()
        try:
            sb_proxy = await loop.run_in_executor(None, lambda: singbox_factory(proxy.config))
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
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            if self.cache:
                self.cache.set(proxy)
        return proxy

    @staticmethod
    def _get_singbox_factory() -> Callable[[str], Any]:
        """Lazily import and return the SingBoxProxy factory."""
        global SingBoxProxy
        if SingBoxProxy is None:
            try:
                module = importlib.import_module("singbox2proxy")
                SingBoxProxy = getattr(module, "SingBoxProxy")
            except Exception as exc:
                raise RuntimeError("singbox2proxy is not available") from exc
        return cast(Callable[[str], Any], SingBoxProxy)

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
