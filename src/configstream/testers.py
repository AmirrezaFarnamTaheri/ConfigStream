import asyncio
import importlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional
from typing import TYPE_CHECKING, ClassVar, Optional
from urllib.parse import urlparse

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import AppSettings
from .models import Proxy
from .constants import TEST_URLS
from singbox2proxy import SingBoxProxy

if TYPE_CHECKING:
    from singbox2proxy import SingBoxProxy as _SingBoxProxy
    from .test_cache import TestResultCache

    SingBoxProxyType = _SingBoxProxy
else:
    SingBoxProxyType = Any  # pragma: no cover


SingBoxProxy: Callable[[str], Any] | None = None

logger = logging.getLogger(__name__)


class ProxyTester:
    """Abstract base class for proxy testers."""

    # Keep a class-level reference to the sing-box binary path to avoid repeated lookups
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
    """Proxy tester using sing-box with optional caching and direct testing for HTTP/SOCKS5."""

    async def _test_direct_http_socks(self, proxy: Proxy) -> Proxy:
        """
        Test HTTP/SOCKS5 proxies directly without Sing-Box for better performance.

        This bypasses the expensive process spawning overhead for simple proxy types.
        """
        try:
            # Determine proxy URL format
            if proxy.protocol.lower() in ("http", "https"):
                proxy_url = f"{proxy.protocol}://{proxy.address}:{proxy.port}"
            elif proxy.protocol.lower() in ("socks", "socks5", "socks4", "socks4a"):
                # Normalize to socks5
                protocol = "socks5" if proxy.protocol.lower() in ("socks", "socks5") else proxy.protocol.lower()
                proxy_url = f"{protocol}://{proxy.address}:{proxy.port}"
            else:
                # Fallback to Sing-Box for complex protocols
                return None  # type: ignore

            connector = ProxyConnector.from_url(proxy_url)

            # Use the same test URLs as Sing-Box tests
            prioritized_urls = [
                TEST_URLS["google"],
                TEST_URLS["cloudflare"],
                TEST_URLS["gstatic"],
            ]

            for url_index, test_url in enumerate(prioritized_urls):
                for retry in range(self.max_retries + 1):
                    try:
                        current_timeout = min(self.timeout, 5.0) if url_index > 0 else self.timeout

                        if retry > 0:
                            await asyncio.sleep(0.5 * (2 ** (retry - 1)))

                        async with aiohttp.ClientSession(
                            connector=connector,
                            connector_owner=False,
                            timeout=aiohttp.ClientTimeout(
                                total=current_timeout,
                                connect=min(current_timeout * 0.3, 3.0),
                                sock_read=min(current_timeout * 0.5, 5.0),
                            ),
                        ) as session:
                            start_time = asyncio.get_running_loop().time()
                            async with session.get(test_url) as response:
                                if 200 <= response.status < 300:
                                    end_time = asyncio.get_running_loop().time()
                                    latency_ms = max((end_time - start_time) * 1000, 0.01)
                                    proxy.latency = round(latency_ms, 2)
                                    proxy.is_working = True
                                    break

                        if proxy.is_working:
                            break
                    except (asyncio.TimeoutError, aiohttp.ClientError):
                        if retry == self.max_retries:
                            continue
                        continue

                if proxy.is_working:
                    break

            if not proxy.is_working:
                # security_issues is now always Dict[str, List[str]]
                if "connectivity" not in proxy.security_issues:
                    proxy.security_issues["connectivity"] = []
                proxy.security_issues["connectivity"].append("Direct test: all test URLs failed")

        except Exception as e:
            logger.debug(f"Direct test failed for {proxy.address}:{proxy.port}: {e}")
            return None  # type: ignore

        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        # Store result in cache if enabled
        if self.cache:
            self.cache.set(proxy)

        return proxy

    async def test(self, proxy: Proxy) -> Proxy:
        """Tests a proxy using sing-box and aiohttp, with optional cache lookup and direct testing for HTTP/SOCKS5."""
        # Check cache first if enabled
        if self.cache:
            cached_result = self.cache.get(proxy)
            if cached_result:
                self.cache_hits += 1
                logger.debug(
                    "Using cached result for %s:%s (working=%s, latency=%s)",
                    proxy.address,
                    proxy.port,
                    cached_result.is_working,
                    cached_result.latency,
                )
                return cached_result
            self.cache_misses += 1

        # Perform actual test
        singbox_factory = self._get_singbox_factory()
        sb_proxy: SingBoxProxyType | None = None
        # For HTTP/SOCKS5 proxies, test directly to avoid Sing-Box overhead
        if proxy.protocol.lower() in ("http", "https", "socks", "socks5", "socks4", "socks4a"):
            logger.debug(f"Using direct test for {proxy.protocol} proxy {proxy.address}:{proxy.port}")
            direct_result = await self._test_direct_http_socks(proxy)
            if direct_result:
                return direct_result
            # If direct test failed, fall back to Sing-Box
            logger.debug(f"Direct test failed, falling back to Sing-Box for {proxy.address}:{proxy.port}")

        # Perform Sing-Box test for complex protocols or fallback
        sb_proxy: SingBoxProxy | None = None
        loop = asyncio.get_running_loop()
        try:
            # Run the synchronous SingBoxProxy constructor in a thread to avoid
            # blocking the event loop. The constructor calls start() and waits
            # for the process to be ready.
            sb_proxy = await loop.run_in_executor(None, lambda: singbox_factory(proxy.config))

            if not sb_proxy or not sb_proxy.http_proxy_url:
                proxy.is_working = False
                if "configuration_error" not in proxy.security_issues:
                    proxy.security_issues["configuration_error"] = []
                proxy.security_issues["configuration_error"].append("Proxy http_proxy_url is not set")
                return proxy

            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)

            # Optimize test URL order: try fastest URLs first
            # Google and Cloudflare typically respond fastest
            prioritized_urls = [
                self.config.TEST_URLS["google"],
                self.config.TEST_URLS["cloudflare"],
                self.config.TEST_URLS["gstatic"],
            ]
            fallback_urls = [
                url
                for name, url in self.config.TEST_URLS.items()
                if name not in {"google", "cloudflare", "gstatic"}
            ]
            test_urls = prioritized_urls + fallback_urls

            # Try multiple test URLs with optimized timeout and early termination
            for url_index, test_url in enumerate(test_urls):
                # Retry logic for transient failures
                for retry in range(self.max_retries + 1):
                    try:
                        # Use progressively shorter timeouts for efficiency
                        if url_index == 0:
                            current_timeout = self.timeout
                        elif url_index < 3:
                            current_timeout = min(self.timeout, 5.0)
                        else:
                            current_timeout = min(
                                self.timeout, 3.0
                            )  # Even shorter for fallback URLs

                        # Add exponential backoff for retries
                        if retry > 0:
                            await asyncio.sleep(0.5 * (2 ** (retry - 1)))
                            logger.debug(
                                f"Retry {retry}/{self.max_retries} for {proxy.address}:{proxy.port}"
                            )

                        # Use optimized timeout settings for better stability
                        async with aiohttp.ClientSession(
                            connector=connector,
                            connector_owner=False,
                            timeout=aiohttp.ClientTimeout(
                                total=current_timeout,
                                connect=min(current_timeout * 0.3, 3.0),
                                sock_read=min(current_timeout * 0.5, 5.0),
                            ),
                        ) as session:
                            # monotonic timer on current running loop
                            start_time = asyncio.get_running_loop().time()
                            async with session.get(
                                test_url,
                            ) as response:
                                # Treat any 2xx as success
                                # 204 is common, but many probes return 200
                                if 200 <= response.status < 300:
                                    end_time = asyncio.get_running_loop().time()
                                    latency_ms = max((end_time - start_time) * 1000, 0.01)
                                    proxy.latency = round(latency_ms, 2)
                                    proxy.is_working = True
                                    # Early exit on success - no need to test other URLs
                                    break
                        # If we get here without exception, break retry loop
                        if proxy.is_working:
                            break
                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        if retry == self.max_retries:
                            logger.debug(
                                f"Proxy {proxy.address}:{proxy.port} failed test URL "
                                f"{test_url} after {retry + 1} attempts with {e.__class__.__name__}"
                            )
                        # Continue to next retry or next URL
                        continue
                    except Exception as e:
                        if retry == self.max_retries:
                            logger.debug(
                                f"Test URL {test_url} failed after {retry + 1} attempts "
                                f"with unexpected error: {e}"
                            )
                        continue

                # Break URL loop if proxy is working
                if proxy.is_working:
                    break

            if not proxy.is_working:
                if "connectivity" not in proxy.security_issues:
                    proxy.security_issues["connectivity"] = []
                proxy.security_issues["connectivity"].append("All test URLs failed")

        except RuntimeError as e:
            proxy.is_working = False
            if "singbox_error" not in proxy.security_issues:
                proxy.security_issues["singbox_error"] = []
            proxy.security_issues["singbox_error"].append(f"SingBox error: {e}")
            logger.debug(f"SingBoxProxy error for {proxy.config}: {e}")
        except Exception as e:
            proxy.is_working = False
            error_details = "[MASKED]" if self.config.MASK_SENSITIVE_DATA else str(e)
            if "connectivity" not in proxy.security_issues:
                proxy.security_issues["connectivity"] = []
            proxy.security_issues["connectivity"].append(f"Connection failed: {error_details}")
            logger.error(f"Proxy test error for {proxy.config}: {str(e)[:100]}")
        finally:
            if sb_proxy:
                try:
                    # Run the synchronous stop() method in a thread.
                    await loop.run_in_executor(None, sb_proxy.stop)
                except Exception as e:
                    logger.debug(f"Error stopping SingBoxProxy: {e}")

        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        # Store result in cache if enabled
        if self.cache:
            self.cache.set(proxy)

        return proxy

    @staticmethod
    def _get_singbox_factory() -> Callable[[str], Any]:
        """Return a callable that constructs ``SingBoxProxy`` instances."""

        global SingBoxProxy

        if SingBoxProxy is not None:
            return SingBoxProxy

        try:
            module = importlib.import_module("singbox2proxy")
            SingBoxProxy = getattr(module, "SingBoxProxy")
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError("singbox2proxy is not available") from exc

        return SingBoxProxy

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0.0
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tests": total,
            "hit_rate": round(hit_rate, 3),
        }
